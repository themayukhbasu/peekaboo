"""Local peek over JSONL run files.

``bind`` serves ``peek.html`` for ``config.runs_dir``. It does not call
the model or write run files.
"""

import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from peekaboo.config import Config

_MARKER = "<!--PEEK-->"


def bind(config: Config) -> HTTPServer:
    """Bind the peek on ``config.peek_host`` and ``config.peek_port``."""
    return _Server(config)


class _Server(HTTPServer):
    """Peek server that keeps the ``Config`` it was bound with."""

    def __init__(self, config: Config) -> None:
        """Bind ``config`` and remember it for each request."""
        super().__init__((config.peek_host, config.peek_port), _Handler)
        self.config = config


class _Handler(BaseHTTPRequestHandler):
    """GET handler for the runs list and one run page."""

    def do_GET(self) -> None:
        """Write the HTML page for this request path."""
        server = self.server
        if not isinstance(server, _Server):
            raise RuntimeError("The peek handler was not bound with bind.")
        status, inner = _view(server.config, self.path)
        page = _page(inner)
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def log_message(self, format: str, *args: object) -> None:
        """Skip the default stderr access log."""


def _page(inner: str) -> bytes:
    """Fill the packaged HTML shell with ``inner``."""
    shell = files("peekaboo").joinpath("peek.html").read_text(encoding="utf-8")
    return shell.replace(_MARKER, inner, 1).encode("utf-8")


def _view(config: Config, target: str) -> tuple[int, str]:
    """Map a request path to a status and an HTML fragment."""
    parts = [unquote(part) for part in urlsplit(target).path.split("/") if part]
    if not parts:
        return 200, _index(config.runs_dir)
    if len(parts) == 2 and parts[0] == "runs":
        path = _jsonl(config.runs_dir, parts[1])
        if path is not None:
            return 200, _run(path)
    return 404, "<p>No such run.</p>"


def _index(runs_dir: Path) -> str:
    """Render filename links for JSONL files directly in ``runs_dir``."""
    names = _names(runs_dir)
    if not names:
        return "<h1>Runs</h1><p>No runs.</p>"
    items = "".join(
        f'<li><a href="/runs/{quote(name, safe="")}">{html.escape(name)}</a></li>'
        for name in names
    )
    return f"<h1>Runs</h1><ul>{items}</ul>"


def _names(runs_dir: Path) -> list[str]:
    """List JSONL filenames that stay inside ``runs_dir``."""
    root = runs_dir.resolve()
    if not root.is_dir():
        return []
    try:
        entries = list(root.iterdir())
    except OSError:
        return []
    names = [path.name for path in entries if _jsonl(root, path.name) is not None]
    names.sort()
    return names


def _jsonl(runs_dir: Path, name: str) -> Path | None:
    """Return one regular ``*.jsonl`` file named ``name`` inside ``runs_dir``."""
    if not name.endswith(".jsonl") or name != Path(name).name:
        return None
    root = runs_dir.resolve()
    candidate = root / name
    try:
        if candidate.is_symlink() or not candidate.is_file():
            return None
        if candidate.resolve().parent != root:
            return None
    except OSError:
        return None
    return candidate


def _run(path: Path) -> str:
    """Render every JSONL line in ``path`` as a turn."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return "<p>This run cannot be read as text.</p>"
    title = html.escape(path.name)
    parts = [f'<p><a href="/">Runs</a></p><h1>{title}</h1>']
    if not lines:
        parts.append("<p>No turns.</p>")
    parts.extend(_turn(index, line) for index, line in enumerate(lines, start=1))
    return "".join(parts)


def _turn(index: int, line: str) -> str:
    """Render one turn, or a short note when the line is not an object."""
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        event = None
    if not isinstance(event, dict):
        return f"<h2>Turn {index}</h2><p>This line is not valid JSON.</p>"
    raw = event.get("raw_response")
    shown = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
    fields = (
        ("Model", _plain(event.get("model"))),
        ("Messages sent", _pairs(event.get("messages_sent"))),
        ("Assistant", _pairs(event.get("assistant"))),
        ("Stop reason", _plain(event.get("stop_reason"))),
        ("Error", _plain(event.get("error"))),
    )
    body = "".join(f"<h3>{label}</h3>{block}" for label, block in fields)
    raw_block = (
        f"<details><summary>Raw response</summary><pre>{_escape(shown)}</pre></details>"
    )
    return f"<h2>Turn {index}</h2>{body}{raw_block}"


def _pairs(value: object) -> str:
    """Render role and content, whether ``value`` is one message or a list."""
    items = [value] if isinstance(value, dict) else value
    if not isinstance(items, list):
        return _plain(value)
    blocks: list[str] = []
    for item in items:
        if isinstance(item, dict):
            blocks.append(
                f"<p>{_escape(item.get('role'))}</p><pre>{_escape(item.get('content'))}</pre>"
            )
        else:
            blocks.append(_plain(item))
    return "".join(blocks)


def _plain(value: object) -> str:
    """Escape ``value`` inside a ``pre`` block."""
    return f"<pre>{_escape(value)}</pre>"


def _escape(value: object) -> str:
    """Escape ``value`` for HTML. ``None`` is the word null."""
    if value is None:
        return "null"
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(value, quote=True)
