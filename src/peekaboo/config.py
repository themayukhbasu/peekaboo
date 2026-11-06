"""Process settings.

Callers receive a Config from load_config. That function is the only
place in the package that reads the process environment. It does not
open dotenv files.

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

DEFAULT_MODEL = "llama3.2"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_HTTP_TIMEOUT_SECONDS = 120
DEFAULT_RUNS_DIR = Path(".peekaboo/runs")
DEFAULT_PEEK_HOST = "127.0.0.1"
DEFAULT_PEEK_PORT = 8765
DEFAULT_READ_FILE_MAX_CHARS = 32 * 1024

_ENV_MODEL = "PEEKABOO_MODEL"
_ENV_OLLAMA_BASE_URL = "PEEKABOO_OLLAMA_BASE_URL"
_ENV_HTTP_TIMEOUT = "PEEKABOO_HTTP_TIMEOUT"
_ENV_RUNS_DIR = "PEEKABOO_RUNS_DIR"
_ENV_PEEK_HOST = "PEEKABOO_PEEK_HOST"
_ENV_PEEK_PORT = "PEEKABOO_PEEK_PORT"
_ENV_READ_FILE_MAX_CHARS = "PEEKABOO_READ_FILE_MAX_CHARS"


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

    model: str = DEFAULT_MODEL
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL
    http_timeout_seconds: int = DEFAULT_HTTP_TIMEOUT_SECONDS
    runs_dir: Path = DEFAULT_RUNS_DIR
    peek_host: str = DEFAULT_PEEK_HOST
    peek_port: int = DEFAULT_PEEK_PORT
    read_file_max_chars: int = DEFAULT_READ_FILE_MAX_CHARS


def load_config(environ: Mapping[str, str] | None = None) -> Config:
    """Load settings for this process.

    Pass ``environ`` to read that mapping instead of ``os.environ``.
    Tests use this so they do not change the process environment.
    """
    env = os.environ if environ is None else environ
    return Config(
        model=_text(env, _ENV_MODEL, DEFAULT_MODEL),
        ollama_base_url=_base_url(env),
        http_timeout_seconds=_whole_number(
            env,
            _ENV_HTTP_TIMEOUT,
            DEFAULT_HTTP_TIMEOUT_SECONDS,
            minimum=1,
            maximum=None,
            description="a positive whole number of seconds",
        ),
        runs_dir=Path(_text(env, _ENV_RUNS_DIR, str(DEFAULT_RUNS_DIR))),
        peek_host=_text(env, _ENV_PEEK_HOST, DEFAULT_PEEK_HOST),
        peek_port=_whole_number(
            env,
            _ENV_PEEK_PORT,
            DEFAULT_PEEK_PORT,
            minimum=1,
            maximum=65535,
            description="a whole number from 1 to 65535",
        ),
        read_file_max_chars=_whole_number(
            env,
            _ENV_READ_FILE_MAX_CHARS,
            DEFAULT_READ_FILE_MAX_CHARS,
            minimum=1,
            maximum=None,
            description="a positive whole number of characters",
        ),
    )


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
    value = _present(env, _ENV_OLLAMA_BASE_URL)
    if value is None:
        return DEFAULT_OLLAMA_BASE_URL
    lowered = value.lower()
    if not (lowered.startswith("http://") or lowered.startswith("https://")):
        raise ConfigError(
            f"{_ENV_OLLAMA_BASE_URL} must be an http or https URL, got {value!r}."
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
