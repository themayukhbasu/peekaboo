"""Peek pages over a temporary runs directory.

The client is ``http.client``. No browser and no Ollama.
"""

import json
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.client import HTTPConnection
from importlib.resources import files
from io import StringIO
from pathlib import Path

from peekaboo.cli import main
from peekaboo.config import Config
from peekaboo.peek import bind


def _event(content: str, reply: str, raw: object) -> str:
    """Return one chat-shaped JSONL line, including an ignored tools key."""
    return json.dumps(
        {
            "model": "llama3.2",
            "messages_sent": [{"role": "user", "content": content}],
            "assistant": {"role": "assistant", "content": reply},
            "stop_reason": "stop",
            "error": None,
            "raw_response": raw,
            "tools": [{"name": "read_file"}],
        }
    )


class _Peek:
    """Stdlib HTTP client for a peek on a temporary port."""

    def __init__(self, runs_dir: Path) -> None:
        """Bind a peek for ``runs_dir`` without serving yet."""
        self.server = bind(
            Config(runs_dir=runs_dir, peek_host="127.0.0.1", peek_port=0)
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> "_Peek":
        """Start serving and return this client."""
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        """Stop the server thread."""
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def get(self, path: str) -> tuple[int, str]:
        """Fetch ``path`` and return the status and HTML."""
        host, port = self.server.server_address[:2]
        last: Exception | None = None
        for _ in range(50):
            try:
                connection = HTTPConnection(str(host), int(port), timeout=2)
                connection.request("GET", path)
                response = connection.getresponse()
                body = response.read().decode("utf-8")
                status = response.status
                connection.close()
                return status, body
            except OSError as error:
                last = error
                time.sleep(0.02)
        raise AssertionError(last)


class PeekTests(unittest.TestCase):
    def test_index_links_are_filenames_only(self) -> None:
        """The first page links JSONL filenames and not their prompts."""
        with tempfile.TemporaryDirectory() as directory:
            runs = Path(directory)
            prompt = "PROMPT-ONLY-ON-THE-RUN"
            (runs / "one.jsonl").write_text(
                _event(prompt, "reply", {"body": "raw"}) + "\n",
                encoding="utf-8",
            )
            (runs / "odd<script>.jsonl").write_text(
                _event("other", "other-reply", None) + "\n",
                encoding="utf-8",
            )
            with _Peek(runs) as peek:
                status, body = peek.get("/")
        self.assertEqual(status, 200)
        self.assertIn('<a href="/runs/one.jsonl">one.jsonl</a>', body)
        self.assertIn("odd&lt;script&gt;.jsonl", body)
        self.assertNotIn("<script>", body)
        self.assertNotIn(prompt, body)
        self.assertNotIn("reply", body)
        self.assertNotIn("stop", body)

    def test_each_turn_shows_harness_fields_and_collapses_raw(self) -> None:
        """Each JSONL line is a turn, and the raw body stays collapsed."""
        with tempfile.TemporaryDirectory() as directory:
            runs = Path(directory)
            markup = "<script>alert(1)</script>"
            lines = [
                _event("PROMPT-ONE", "REPLY-ONE", {"secret": "RAW-ONE"}),
                _event(markup, "REPLY-TWO", "RAW-TWO"),
            ]
            (runs / "chat.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
            with _Peek(runs) as peek:
                status, body = peek.get("/runs/chat.jsonl")
        self.assertEqual(status, 200)
        self.assertLess(body.index("REPLY-ONE"), body.index("REPLY-TWO"))
        for label in ("Model", "Messages sent", "Assistant", "Stop reason", "Error"):
            self.assertIn(f"<h3>{label}</h3>", body)
        self.assertIn("llama3.2", body)
        self.assertIn("<pre>stop</pre>", body)
        self.assertIn("<pre>null</pre>", body)
        self.assertNotIn("<script>", body)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", body)
        self.assertNotIn("read_file", body)
        self.assertNotIn("<details open", body)
        self.assertEqual(body.count("<details>"), 2)
        self.assertLess(body.index("<details>"), body.index("RAW-ONE"))
        self.assertLess(body.index("RAW-ONE"), body.index("RAW-TWO"))
        self.assertIn("<title>Peek</title>", body)

    def test_requests_stay_inside_the_runs_directory(self) -> None:
        """Traversal and symlinks cannot read a file outside the runs directory."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret = root / "secret.txt"
            secret.write_text("SECRET-OUTSIDE", encoding="utf-8")
            runs = root / "runs"
            runs.mkdir()
            (runs / "link.jsonl").symlink_to(secret)
            (runs / "ok.jsonl").write_text("{}\n", encoding="utf-8")
            with _Peek(runs) as peek:
                index_status, index = peek.get("/")
                link_status, link = peek.get("/runs/link.jsonl")
                parent_status, parent = peek.get("/runs/../secret.txt")
                encoded_status, encoded = peek.get("/runs/%2e%2e%2fsecret.txt")
        self.assertEqual(index_status, 200)
        self.assertIn("ok.jsonl", index)
        self.assertNotIn("link.jsonl", index)
        self.assertEqual(link_status, 404)
        self.assertEqual(parent_status, 404)
        self.assertEqual(encoded_status, 404)
        for body in (index, link, parent, encoded):
            self.assertNotIn("SECRET-OUTSIDE", body)
            self.assertNotIn(str(secret), body)

    def test_null_byte_in_the_run_name_is_a_missing_run(self) -> None:
        """A decoded NUL in the run name is a 404, not a dropped connection."""
        with tempfile.TemporaryDirectory() as directory:
            runs = Path(directory)
            (runs / "ok.jsonl").write_text("{}\n", encoding="utf-8")
            with _Peek(runs) as peek:
                status, body = peek.get("/runs/a%00.jsonl")
        self.assertEqual(status, 404)
        self.assertIn("No such run.", body)
        self.assertNotIn("ok.jsonl", body)

    def test_absent_directory_and_bad_lines_stay_on_the_page(self) -> None:
        """A missing directory or a bad line is a short page, not a traceback."""
        with tempfile.TemporaryDirectory() as directory:
            absent = Path(directory) / "absent-runs"
            with _Peek(absent) as peek:
                status, body = peek.get("/")
            self.assertEqual(status, 200)
            self.assertIn("No runs.", body)
            self.assertNotIn("absent-runs", body)
            runs = Path(directory) / "runs"
            runs.mkdir()
            (runs / "bad.jsonl").write_text(
                _event("kept", "kept-reply", None) + "\nnot-json\n",
                encoding="utf-8",
            )
            (runs / "bytes.jsonl").write_bytes(b"\xff")
            with _Peek(runs) as peek:
                missing_status, missing = peek.get("/runs/missing.jsonl")
                bad_status, bad = peek.get("/runs/bad.jsonl")
                byte_status, byte_body = peek.get("/runs/bytes.jsonl")
        self.assertEqual(missing_status, 404)
        self.assertIn("No such run.", missing)
        self.assertEqual(bad_status, 200)
        self.assertIn("kept-reply", bad)
        self.assertIn("This line is not valid JSON.", bad)
        self.assertNotIn("not-json", bad)
        self.assertEqual(byte_status, 200)
        self.assertIn("This run cannot be read as text.", byte_body)

    def test_help_and_the_packaged_page(self) -> None:
        """In-process peek help and the packaged shell agree on the page."""
        shell = files("peekaboo").joinpath("peek.html").read_text(encoding="utf-8")
        self.assertIn("<title>Peek</title>", shell)
        self.assertIn("<!--PEEK-->", shell)
        stdout = StringIO()
        with redirect_stdout(stdout):
            status = main(["peek", "--help"])
        self.assertEqual(status, 0)
        self.assertIn("http://127.0.0.1:8765", stdout.getvalue())
        self.assertIn("Ctrl-C", stdout.getvalue())
        error = StringIO()
        with redirect_stderr(error):
            status = main(["peek", "extra"])
        self.assertEqual(status, 2)
        self.assertIn("peekaboo peek", error.getvalue())
