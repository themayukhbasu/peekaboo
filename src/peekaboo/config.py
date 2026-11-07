"""Process settings.

Callers receive a Config from load_config. That function is the only
place in the package that reads the process environment or a dotenv
file. With no mapping passed in, it reads ``.env`` from the working
directory when that file is present, then overlays the process
environment. A name set in both places keeps the process value.

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


@dataclass(frozen=True)
class _Defaults:
    """Spec defaults for each Config field."""

    model: str = "llama3.2"
    ollama_base_url: str = "http://127.0.0.1:11434"
    http_timeout_seconds: int = 120
    runs_dir: Path = Path(".peekaboo/runs")
    peek_host: str = "127.0.0.1"
    peek_port: int = 8765
    read_file_max_chars: int = 32 * 1024


DEFAULTS = _Defaults()


@dataclass(frozen=True)
class _Env:
    """Process environment names for each Config field."""

    model: str = "PEEKABOO_MODEL"
    ollama_base_url: str = "PEEKABOO_OLLAMA_BASE_URL"
    http_timeout_seconds: str = "PEEKABOO_HTTP_TIMEOUT"
    runs_dir: str = "PEEKABOO_RUNS_DIR"
    peek_host: str = "PEEKABOO_PEEK_HOST"
    peek_port: str = "PEEKABOO_PEEK_PORT"
    read_file_max_chars: str = "PEEKABOO_READ_FILE_MAX_CHARS"


ENV = _Env()


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

    model: str = DEFAULTS.model
    ollama_base_url: str = DEFAULTS.ollama_base_url
    http_timeout_seconds: int = DEFAULTS.http_timeout_seconds
    runs_dir: Path = DEFAULTS.runs_dir
    peek_host: str = DEFAULTS.peek_host
    peek_port: int = DEFAULTS.peek_port
    read_file_max_chars: int = DEFAULTS.read_file_max_chars


def load_config(environ: Mapping[str, str] | None = None) -> Config:
    """Load settings for this process.

    With no ``environ``, merge ``.env`` in the working directory (if
    that file is present) and then the process environment. The process
    value wins when both name the same variable. Pass ``environ`` to
    read that mapping alone; a ``.env`` file is not opened. Tests use
    this so they do not change the process environment.
    """
    env = _process_environment() if environ is None else environ
    return Config(
        model=_text(env, ENV.model, DEFAULTS.model),
        ollama_base_url=_base_url(env),
        http_timeout_seconds=_whole_number(
            env,
            ENV.http_timeout_seconds,
            DEFAULTS.http_timeout_seconds,
            minimum=1,
            maximum=None,
            description="a positive whole number of seconds",
        ),
        runs_dir=Path(_text(env, ENV.runs_dir, str(DEFAULTS.runs_dir))),
        peek_host=_text(env, ENV.peek_host, DEFAULTS.peek_host),
        peek_port=_whole_number(
            env,
            ENV.peek_port,
            DEFAULTS.peek_port,
            minimum=1,
            maximum=65535,
            description="a whole number from 1 to 65535",
        ),
        read_file_max_chars=_whole_number(
            env,
            ENV.read_file_max_chars,
            DEFAULTS.read_file_max_chars,
            minimum=1,
            maximum=None,
            description="a positive whole number of characters",
        ),
    )


def _process_environment() -> dict[str, str]:
    merged = _read_dotenv(Path(".env"))
    merged.update(os.environ)
    return merged


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped.removeprefix("export ").strip()
        key, separator, value = stripped.partition("=")
        if separator == "" or key.strip() == "":
            continue
        values[key.strip()] = _unquote(value.strip())
    return values


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


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
    value = _present(env, ENV.ollama_base_url)
    if value is None:
        return DEFAULTS.ollama_base_url
    lowered = value.lower()
    if not (lowered.startswith("http://") or lowered.startswith("https://")):
        raise ConfigError(
            f"{ENV.ollama_base_url} must be an http or https URL, got {value!r}."
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
