"""The ``read_file`` tool.

``read_file`` reads one path inside a workspace. A missing path, a
directory, and a path that resolves outside the workspace return a
short string. Text longer than the character limit is cut and marked.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

_PARAMETERS: dict[str, object] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path of the file inside the workspace.",
        }
    },
    "required": ["path"],
}


# ``__call__`` is the tool. A second method would not be part of it.
class ReadFile:  # pylint: disable=too-few-public-methods
    """Callable tool. The loop passes the model's arguments object."""

    name = "read_file"
    description = "Read a UTF-8 text file inside the workspace."
    parameters = _PARAMETERS

    def __call__(self, arguments: object, *, workspace: Path, max_chars: int) -> str:
        """Return file text, or a short error string.

        ``workspace`` is the root. ``max_chars`` counts decoded
        characters. A longer file ends with a newline and ``[truncated]``.
        """
        path = _path(arguments)
        if path is None:
            return "read_file needs a string path."
        located = _candidate(workspace, path)
        if isinstance(located, str):
            return located
        return _text(located, path, max_chars)


def _candidate(workspace: Path, path: str) -> Path | str:
    """Return the file inside ``workspace``, or a short error string."""
    try:
        root = workspace.resolve()
        candidate = (root / path).resolve()
    except OSError:
        return f"Could not read {path!r}."
    try:
        candidate.relative_to(root)
    except ValueError:
        return f"{path!r} is outside the workspace."
    if candidate.is_file():
        return candidate
    if candidate.exists():
        return f"{path!r} is not a file."
    return f"{path!r} was not found."


def _text(candidate: Path, path: str, max_chars: int) -> str:
    """Return file text, cut at ``max_chars`` decoded characters."""
    try:
        with candidate.open(encoding="utf-8") as handle:
            text = handle.read(max_chars + 1)
    except UnicodeDecodeError:
        return f"{path!r} is not UTF-8 text."
    except OSError:
        return f"Could not read {path!r}."
    if len(text) > max_chars:
        return text[:max_chars] + "\n[truncated]"
    return text


def _path(arguments: object) -> str | None:
    """Return a non-empty string ``path``, or ``None``."""
    if not isinstance(arguments, Mapping):
        return None
    path = arguments.get("path")
    if not isinstance(path, str) or path == "":
        return None
    return path


read_file = ReadFile()
