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
import socket
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from urllib.parse import urlparse

from peekaboo.cli import main
from peekaboo.config import Config, load_config
from peekaboo.run import TransportError, run

_FIXTURES = Path(__file__).parent / "fixtures"
_USER = {"role": "user", "content": "why is the sky blue?"}


class _Recording:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self.body = body
        self.calls: list[tuple[str, bytes, float]] = []

    def __call__(self, url: str, body: bytes, timeout: float) -> tuple[int, bytes]:
        self.calls.append((url, body, timeout))
        return self.status, self.body


def _fixture(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def _config(runs_dir: Path) -> Config:
    return Config(runs_dir=runs_dir, http_timeout_seconds=7)


class RunTests(unittest.TestCase):
    def test_success_writes_one_turn_and_omits_tools(self):
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

    def test_transport_failure_is_recorded(self):
        with tempfile.TemporaryDirectory() as directory:

            def fail(url: str, body: bytes, timeout: float) -> tuple[int, bytes]:
                raise TransportError("connection refused")

            path = run([_USER], [], config=_config(Path(directory)), transport=fail)
            event = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(event["stop_reason"], "error")
            self.assertEqual(event["error"], "connection refused")
            self.assertIsNone(event["assistant"])
            self.assertIsNone(event["raw_response"])

    def test_tools_are_rejected_before_the_call(self):
        transport = _Recording(200, _fixture("ollama_chat_nostream.json"))
        with self.assertRaises(ValueError):
            run([_USER], [{"name": "read_file"}], config=Config(), transport=transport)
        self.assertEqual(transport.calls, [])


class CliTests(unittest.TestCase):
    def test_chat_prints_the_run_path(self):
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
        transport = _Recording(200, b"{}")
        stderr = StringIO()
        with redirect_stderr(stderr):
            status = main(["chat"], config=Config(), transport=transport)
        self.assertEqual(status, 2)
        self.assertIn("peekaboo chat MESSAGE", stderr.getvalue())
        self.assertEqual(transport.calls, [])


def _listening(base_url: str) -> bool:
    parsed = urlparse(base_url)
    host = parsed.hostname
    if host is None:
        return False
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


class LiveOllamaSmoke(unittest.TestCase):
    """Manual live check. Not a merge gate.

    Skips when nothing is listening. A reply, including an error body,
    is data: the test checks harness fields only.
    """

    def test_one_turn_when_a_daemon_listens(self):
        loaded = load_config()
        if not _listening(loaded.ollama_base_url):
            self.skipTest(
                f"Nothing is listening at {loaded.ollama_base_url}. "
                "Live Ollama smoke skipped."
            )
        with tempfile.TemporaryDirectory() as directory:
            config = Config(
                model=loaded.model,
                ollama_base_url=loaded.ollama_base_url,
                http_timeout_seconds=loaded.http_timeout_seconds,
                runs_dir=Path(directory),
            )
            path = run([_USER], [], config=config)
            event = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(event["messages_sent"], [_USER])
            self.assertIn(event["stop_reason"], ("stop", "error"))
            self.assertNotIn("tools", event)
            self.assertIn("raw_response", event)
