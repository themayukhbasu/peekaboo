"""Process settings.

Callers receive a Config from load_config. That function is the only
place in the package that reads the process environment or a dotenv
file. With no arguments, it reads ``.env`` in the working directory
when that file is present, then overlays the process environment. A
name set in both places keeps the process value, including a blank one,
so a blank process value uses the spec default rather than the file.
Pass ``environ`` to supply that overlay instead of the process, and
``dotenv_path`` to read a chosen file. An injected mapping with no
``dotenv_path`` does not open a file. A missing file adds nothing.
Parent directories are not searched.

The file is parsed by python-dotenv's ``dotenv_values`` (UTF-8). A
leading UTF-8 BOM is ignored. The rules below are that package's, not
a private parser. File format:
https://github.com/theskumar/python-dotenv#file-format
Variable expansion:
https://github.com/theskumar/python-dotenv#variable-expansion
Bare ``$NAME`` is not expanded (Getting started):
https://github.com/theskumar/python-dotenv#getting-started

A line is ``NAME=VALUE`` or ``export NAME=VALUE``. Blank lines and
``#`` comments are skipped. A name with no ``=`` is ignored. ``NAME=``
is blank. Spaces around the name, ``=``, and the value are ignored.
An unquoted value drops a trailing `` #`` comment.

Single or double quotes may wrap a value. Quotes do not turn expansion
off. Double-quoted values decode the C-style escapes in the file-format
docs, including newline and tab. Single-quoted values decode only a
backslash and a single quote, so a backslash followed by n stays as
written.

``${NAME}`` and ``${NAME:-default}`` expand. Look-up uses an earlier
binding in the file, then the process environment, then the ``:-``
default, then an empty string. A later binding in the file is not
visible. The injected ``environ`` mapping is not an expansion source;
it only overlays the parsed result. An expanded empty string is blank,
so the spec default applies.

Defaults follow the numeric defaults in the first-milestones spec:

* ``model`` — ``llama3.2``, the tag in Ollama's ``/api/chat`` examples.
  Override with ``PEEKABOO_MODEL``.
* ``ollama_base_url`` — ``http://127.0.0.1:11434``.
  Override with ``PEEKABOO_OLLAMA_BASE_URL``, an http or https URL.
  This is not ``OLLAMA_HOST``: that variable is the daemon bind address
  and is often a host:port with no scheme, or ``0.0.0.0``.
* ``http_timeout_seconds`` — ``120``. Override with ``PEEKABOO_HTTP_TIMEOUT``.
* ``runs_dir`` — ``.peekaboo/runs``. Override with ``PEEKABOO_RUNS_DIR``.
* ``peek_host`` / ``peek_port`` — ``127.0.0.1`` and ``8765``.
  Override with ``PEEKABOO_PEEK_HOST`` and ``PEEKABOO_PEEK_PORT``.
* ``read_file_max_chars`` — ``32768`` (32 KiB of decoded text, counted
  in characters). Override with ``PEEKABOO_READ_FILE_MAX_CHARS``.

A missing or blank variable keeps its default. A non-blank value that
cannot be used raises ConfigError and names the variable. Timeouts and
the truncation limit are positive whole numbers. The peek port is a
whole number from 1 to 65535.
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


def _text(env: Mapping[str, str], name: str, default: str) -> str:
    return _present(env, name) or default


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


def _whole_number(
    env: Mapping[str, str],
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int | None,
    description: str,
) -> int:
    raw = _present(env, name)
    if raw is None:
        return default
    try:
        value = int(raw, 10)
    except ValueError:
        value = None
    if value is None or value < minimum or (maximum is not None and value > maximum):
        raise ConfigError(f"{name} must be {description}, got {raw!r}.")
    return value
