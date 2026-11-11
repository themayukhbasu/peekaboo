"""One-shot chat through ``run`` and ``peekaboo chat``.

``ollama_chat_nostream.json`` is the "Chat request (No streaming)" sample
from Ollama ``docs/api.md`` at commit e9fde36d75fe. It is a documentation
sample, not a live capture:
https://github.com/ollama/ollama/blob/e9fde36d75fea66579d84099956ce1430792737a/docs/api.md

``ollama_model_not_found.json`` is reconstructed from the ``{"error": ...}``
object in ``server/routes.go`` at that commit (model-not-found is HTTP 404).
No daemon was run. The research note on ``research/ollama-chat-tool-calls``
(issue #11) did not capture a live body either.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from peekaboo.cli import main
from peekaboo.config import Config
from peekaboo.run import TransportError, run

_FIXTURES = Path(__file__).parent / "fixtures"
_USER = {"role": "user", "content": "why is the sky blue?"}


class _Recording:
    """Transport that returns one fixed response and records each call."""

    def __init__(self, status: int, body: bytes) -> None:
        """Store the status and body this transport will return."""
        self.status = status
        self.body = body
        self.calls: list[tuple[str, bytes, float]] = []

    def __call__(self, url: str, body: bytes, timeout: float) -> tuple[int, bytes]:
        """Record the call and return the stored status and body."""
        self.calls.append((url, body, timeout))
        return self.status, self.body


def _fixture(name: str) -> bytes:
    """Read one canned provider body from ``tests/fixtures``."""
    return (_FIXTURES / name).read_bytes()


def _config(runs_dir: Path) -> Config:
    """Return settings that write the run under ``runs_dir``."""
    return Config(runs_dir=runs_dir, http_timeout_seconds=7)


class RunTests(unittest.TestCase):
    def test_success_writes_one_turn_and_omits_tools(self):
        """A 200 reply writes one JSONL turn and the request has no tools."""
        with tempfile.TemporaryDirectory() as directory:
            runs = Path(directory)
            transport = _Recording(200, _fixture("ollama_chat_nostream.json"))
            path = run([_USER], [], config=_config(runs), transport=transport)
            self.assertEqual(path.parent, runs)
            self.assertRegex(path.name, r"^\d{8}T\d{12}Z\.jsonl$")
            self.assertEqual(len(transport.calls), 1)
            url, body, timeout = transport.calls[0]
            sent = json.loads(body)
            self.assertEqual(url, "http://127.0.0.1:11434/api/chat")
            self.assertEqual(timeout, 7)
            self.assertEqual(sent["model"], "llama3.2")
            self.assertIs(sent["stream"], False)
            self.assertEqual(sent["messages"], [_USER])
            self.assertNotIn("tools", sent)
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.splitlines(), [text[:-1]])
            event = json.loads(text)
            self.assertEqual(
                event,
                {
                    "model": "llama3.2",
                    "messages_sent": [_USER],
                    "assistant": {
                        "role": "assistant",
                        "content": "Hello! How are you today?",
                    },
                    "stop_reason": "stop",
                    "error": None,
                    "raw_response": json.loads(_fixture("ollama_chat_nostream.json")),
                },
            )

    def test_error_body_is_recorded_without_retry(self):
        """A provider error body is stored on the turn and is not retried."""
        with tempfile.TemporaryDirectory() as directory:
            transport = _Recording(404, _fixture("ollama_model_not_found.json"))
            path = run(
                [_USER],
                [],
                config=_config(Path(directory)),
                transport=transport,
            )
            event = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(transport.calls), 1)
            self.assertEqual(event["stop_reason"], "error")
            self.assertEqual(event["error"], "model 'llama3.2' not found")
            self.assertIsNone(event["assistant"])
            self.assertEqual(event["raw_response"]["error"], event["error"])
            self.assertNotIn("tools", event)

    def test_success_status_without_assistant_names_the_gap(self):
        """HTTP 200 with no assistant message is recorded as an error turn."""
        with tempfile.TemporaryDirectory() as directory:
            transport = _Recording(200, b'{"done": true}')
            path = run(
                [_USER],
                [],
                config=_config(Path(directory)),
                transport=transport,
            )
            event = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(event["stop_reason"], "error")
            self.assertIsNone(event["assistant"])
            self.assertEqual(
                event["error"],
                "The provider returned HTTP 200 without an assistant message.",
            )

    def test_transport_failure_is_recorded(self):
        """A transport that never answers is stored as an error turn."""
        with tempfile.TemporaryDirectory() as directory:

            def fail(url: str, body: bytes, timeout: float) -> tuple[int, bytes]:
                """Stand in for a provider that never answers."""
                raise TransportError("connection refused")

            path = run([_USER], [], config=_config(Path(directory)), transport=fail)
            event = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(event["stop_reason"], "error")
            self.assertEqual(event["error"], "connection refused")
            self.assertIsNone(event["assistant"])
            self.assertIsNone(event["raw_response"])

    def test_tools_are_rejected_before_the_call(self):
        """A plain dict is not a tool and is rejected before the provider call."""
        transport = _Recording(200, _fixture("ollama_chat_nostream.json"))
        with self.assertRaises(ValueError):
            run([_USER], [{"name": "read_file"}], config=Config(), transport=transport)
        self.assertEqual(transport.calls, [])


class CliTests(unittest.TestCase):
    def test_chat_prints_the_run_path(self):
        """``peekaboo chat`` prints the run path for one user message."""
        with tempfile.TemporaryDirectory() as directory:
            runs = Path(directory)
            transport = _Recording(200, _fixture("ollama_chat_nostream.json"))
            stdout = StringIO()
            with redirect_stdout(stdout):
                status = main(
                    ["chat", "why", "is", "the", "sky", "blue?"],
                    config=_config(runs),
                    transport=transport,
                )
            self.assertEqual(status, 0)
            path = Path(stdout.getvalue().strip())
            self.assertEqual(path.parent, runs)
            sent = json.loads(transport.calls[0][1])
            self.assertEqual(sent["messages"], [_USER])
            self.assertNotIn("tools", sent)
            self.assertEqual(len(transport.calls), 1)

    def test_missing_message_does_not_call(self):
        """``peekaboo chat`` with no message exits before calling the provider."""
        transport = _Recording(200, b"{}")
        stderr = StringIO()
        with redirect_stderr(stderr):
            status = main(["chat"], config=Config(), transport=transport)
        self.assertEqual(status, 2)
        self.assertIn("peekaboo chat MESSAGE", stderr.getvalue())
        self.assertEqual(transport.calls, [])

    def test_default_discovery_omits_the_opt_in_module(self):
        """Default discovery does not load the live smoke module."""
        root = Path(__file__).parents[1]
        script = '''
import socket
import unittest
import dotenv

def boom(*args, **kwargs):
    """Fail if discovery opens a socket or reads a dotenv file."""
    raise SystemExit("discovery touched the network or a dotenv file")

socket.create_connection = boom
dotenv.dotenv_values = boom
suite = unittest.defaultTestLoader.discover("tests")

def ids(item):
    """Yield each test id in a suite."""
    if isinstance(item, unittest.TestSuite):
        for child in item:
            yield from ids(child)
    else:
        yield item.id()

print("\\n".join(ids(suite)))
'''
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        for test_id in completed.stdout.splitlines():
            self.assertNotIn("LiveOllamaSmoke", test_id)
            self.assertFalse(test_id.startswith("live_smoke"))
