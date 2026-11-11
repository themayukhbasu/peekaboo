"""Process settings.

``load_config`` is the only reader of the process environment and of a
dotenv file. With no arguments it reads ``.env`` in the working directory
when that file is present, then overlays the process environment. A name
set in both places keeps the process value, including a blank one. Pass
``environ`` to supply that overlay instead of the process, and
``dotenv_path`` to read a chosen file. An injected mapping with no
``dotenv_path`` does not open a file.

The file is parsed by python-dotenv's ``dotenv_values`` (UTF-8). Syntax
and expansion follow that package:
https://github.com/theskumar/python-dotenv#file-format

Defaults live on ``default.*`` and variable names on ``env_name.*``.
A missing or blank value keeps its default. A non-blank value that
cannot be used raises ``ConfigError`` and names the variable.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class _Defaults:
    """Spec defaults. Read them as ``default.model`` and the other fields."""

    model: str = "llama3.2"
    ollama_base_url: str = "http://127.0.0.1:11434"
    http_timeout_seconds: int = 120
    runs_dir: Path = Path(".peekaboo/runs")
    peek_host: str = "127.0.0.1"
    peek_port: int = 8765
    read_file_max_chars: int = 32 * 1024


default = _Defaults()


@dataclass(frozen=True)
class _EnvName:
    """Environment variable names. Read them as ``env_name.model``."""

    model: str = "PEEKABOO_MODEL"
    ollama_base_url: str = "PEEKABOO_OLLAMA_BASE_URL"
    http_timeout_seconds: str = "PEEKABOO_HTTP_TIMEOUT"
    runs_dir: str = "PEEKABOO_RUNS_DIR"
    peek_host: str = "PEEKABOO_PEEK_HOST"
    peek_port: str = "PEEKABOO_PEEK_PORT"
    read_file_max_chars: str = "PEEKABOO_READ_FILE_MAX_CHARS"


env_name = _EnvName()


class ConfigError(ValueError):
    """A setting is present in the environment but not usable."""


@dataclass(frozen=True)
class Config:
    """Settings for one process.

    ``runs_dir`` is stored as given, so a relative path stays relative
    to the working directory of the process that uses it.
    ``read_file_max_chars`` limits decoded text, not raw file bytes.
    ``http_timeout_seconds`` is a whole number of seconds.
    """

    model: str = default.model
    ollama_base_url: str = default.ollama_base_url
    http_timeout_seconds: int = default.http_timeout_seconds
    runs_dir: Path = default.runs_dir
    peek_host: str = default.peek_host
    peek_port: int = default.peek_port
    read_file_max_chars: int = default.read_file_max_chars


def load_config(
    environ: Mapping[str, str] | None = None,
    *,
    dotenv_path: Path | None = None,
) -> Config:
    """Load settings for this process.

    ``environ`` replaces the process environment. ``dotenv_path`` chooses
    the dotenv file. See the module docstring for merge order and syntax.
    """
    env = _merged_environment(environ, dotenv_path)
    return Config(
        model=_text(env, env_name.model, default.model),
        ollama_base_url=_base_url(env),
        http_timeout_seconds=_whole_number(
            env,
            env_name.http_timeout_seconds,
            default.http_timeout_seconds,
            minimum=1,
            maximum=None,
            description="a positive whole number of seconds",
        ),
        runs_dir=Path(_text(env, env_name.runs_dir, str(default.runs_dir))),
        peek_host=_text(env, env_name.peek_host, default.peek_host),
        peek_port=_whole_number(
            env,
            env_name.peek_port,
            default.peek_port,
            minimum=1,
            maximum=65535,
            description="a whole number from 1 to 65535",
        ),
        read_file_max_chars=_whole_number(
            env,
            env_name.read_file_max_chars,
            default.read_file_max_chars,
            minimum=1,
            maximum=None,
            description="a positive whole number of characters",
        ),
    )


def _merged_environment(
    environ: Mapping[str, str] | None,
    dotenv_path: Path | None,
) -> Mapping[str, str]:
    process = os.environ if environ is None else environ
    if dotenv_path is None and environ is not None:
        return process
    path = Path(".env") if dotenv_path is None else dotenv_path
    merged = _read_dotenv(path)
    merged.update(process)
    return merged


def _read_dotenv(path: Path) -> dict[str, str]:
    """Return string bindings from one file. A missing file adds nothing.

    python-dotenv yields ``None`` for a name with no ``=``. Those names
    are omitted. An empty string is kept so the process overlay can
    replace a blank file value.
    """
    parsed = dotenv_values(path, encoding="utf-8")
    return {key: value for key, value in parsed.items() if value is not None}


def _present(env: Mapping[str, str], name: str) -> str | None:
    raw = env.get(name)
    if raw is None:
        return None
    text = raw.strip()
    if text == "":
        return None
    return text


def _text(env: Mapping[str, str], name: str, fallback: str) -> str:
    return _present(env, name) or fallback


def _base_url(env: Mapping[str, str]) -> str:
    value = _present(env, env_name.ollama_base_url)
    if value is None:
        return default.ollama_base_url
    lowered = value.lower()
    if not (lowered.startswith("http://") or lowered.startswith("https://")):
        raise ConfigError(
            f"{env_name.ollama_base_url} must be an http or https URL, got {value!r}."
        )
    return value.rstrip("/")


# Bounds and the error wording stay with the name and the fallback.
def _whole_number(  # pylint: disable=too-many-arguments
    env: Mapping[str, str],
    name: str,
    fallback: int,
    *,
    minimum: int,
    maximum: int | None,
    description: str,
) -> int:
    raw = _present(env, name)
    if raw is None:
        return fallback
    try:
        value = int(raw, 10)
    except ValueError:
        value = None
    if value is None or value < minimum or (maximum is not None and value > maximum):
        raise ConfigError(f"{name} must be {description}, got {raw!r}.")
    return value
