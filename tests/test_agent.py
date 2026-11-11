"""Tool wire format, the agent loop, and ``peekaboo agent``."""

import json
import os
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from peekaboo.cli import main
from peekaboo.config import Config, load_config
from peekaboo.tools.read_file import read_file
from peekaboo.run import (
    _agent_reply,
    _checked_tools,
    _one_call,
    _schema,
    _wire_message,
    _wire_tool,
    run,
)

_CALL = (
    b'{"done_reason":"stop","message":{"content":"",'
    b'"tool_calls":[{"function":{"name":"read_file",'
    b'"arguments":{"path":"a.txt"}}}]}}'
)


class ToolWireTests(unittest.TestCase):
    """Schema envelope, wire projection, and tools that are rejected."""

    def test_schema_envelope_and_rejected_tools(self):
        """``read_file`` is one function. A dict or a duplicate name is not."""
        self.assertEqual(_checked_tools([read_file]), [read_file])
        schema = _schema(read_file)
        self.assertEqual(schema["name"], "read_file")
        self.assertEqual(schema["parameters"]["required"], ["path"])
        self.assertEqual(_wire_tool(schema), {"type": "function", "function": schema})
        with self.assertRaises(ValueError):
            _checked_tools([{"name": "read_file"}])
        with self.assertRaises(ValueError):
            _checked_tools([read_file, read_file])

    def test_harness_calls_project_to_id_and_function(self):
        """A harness call becomes ``id`` plus ``function``."""
        wire = _wire_message(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "tool_name": "read_file",
                        "tool_call_id": "call_a1b2c3d4",
                        "arguments": {"path": "a.txt"},
                    }
                ],
            }
        )
        function = wire["tool_calls"][0]["function"]
        self.assertEqual(wire["tool_calls"][0]["id"], "call_a1b2c3d4")
        self.assertEqual(function["index"], 0)
        self.assertEqual(function["arguments"], {"path": "a.txt"})


class ReplyParseTests(unittest.TestCase):
    """Stop replies still yield calls. Provider errors stay text."""

    def test_stop_still_parses_calls_and_errors_stay_text(self):
        """Tool calls are read when ``done_reason`` is stop. Errors keep text."""
        assistant, calls, failure, parsed = _agent_reply(200, _CALL)
        self.assertIsNone(failure)
        self.assertEqual(assistant, {"role": "assistant", "content": ""})
        self.assertEqual(calls[0].call_id, "call_0")
        self.assertEqual(calls[0].arguments, {"path": "a.txt"})
        self.assertEqual(parsed["done_reason"], "stop")
        self.assertIsNone(_one_call({"function": {}}, 0))
        _missed, _none, error, _parsed = _agent_reply(
            404, b'{"error":"model \'llama3.2\' not found"}'
        )
        self.assertEqual(error, "model 'llama3.2' not found")


_FIXTURES = Path(__file__).parent / "fixtures"
_USER = {"role": "user", "content": "Read the file."}
_TOOL = (
    b'{"done_reason":"stop","message":{"role":"assistant","content":"",'
    b'"tool_calls":[{"id":"call_a1b2c3d4","function":{"name":"read_file",'
    b'"arguments":{"path":"a.txt"}}}]}}'
)


class _Script:  # pylint: disable=too-few-public-methods
    """Transport that returns canned bodies in order and records each call."""

    def __init__(self, responses: list[tuple[int, bytes]]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, bytes, float]] = []

    def __call__(self, url: str, body: bytes, timeout: float) -> tuple[int, bytes]:
        self.calls.append((url, body, timeout))
        if not self._responses:
            raise AssertionError("the model was called after the script ended")
        return self._responses.pop(0)


def _fixture(name: str) -> bytes:
    """Read one canned provider body from ``tests/fixtures``."""
    return (_FIXTURES / name).read_bytes()


def _with_id(body: bytes, call_id: str) -> bytes:
    """Return ``body`` with the first tool call's ``id`` set to ``call_id``."""
    payload = json.loads(body)
    payload["message"]["tool_calls"][0]["id"] = call_id
    return json.dumps(payload).encode("utf-8")


def _events(path: Path) -> list[dict[str, object]]:
    """Return each JSON object in a run file, in file order."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@contextmanager
def _cwd(path: Path) -> Iterator[None]:
    """Use ``path`` as the process working directory for one block."""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class AgentRunTests(unittest.TestCase):
    """One ``read_file`` call, then a plain reply, stops the loop."""

    def test_tool_call_then_stop(self):
        """One ``read_file`` call is sent back, then a plain reply stops."""
        plain = (_FIXTURES / "ollama_chat_nostream.json").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("hello\n", encoding="utf-8")
            config = Config(runs_dir=root / "runs")
            transport = _Script([(200, _TOOL), (200, plain)])
            with _cwd(root):
                path = run([_USER], [read_file], config=config, transport=transport)
            self.assertEqual(len(transport.calls), 2)
            sent = json.loads(transport.calls[1][1])["messages"]
            self.assertEqual(sent[0]["role"], "system")
            self.assertEqual(sent[3]["content"], "hello\n")
            self.assertEqual(sent[3]["tool_call_id"], "call_a1b2c3d4")
            events = _events(path)
            self.assertEqual(events[0]["stop_reason"], "tool_calls")
            self.assertEqual(events[1]["stop_reason"], "stop")
            self.assertEqual(events[0]["tools"][0]["name"], "read_file")

    def test_one_fixture_call_records_the_wire(self):
        """The canned tool call is posted back, then a plain reply stops."""
        plain = _fixture("ollama_chat_nostream.json")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("hello\n", encoding="utf-8")
            config = Config(runs_dir=root / "runs", http_timeout_seconds=7)
            transport = _Script(
                [(200, _fixture("ollama_one_tool_call.json")), (200, plain)]
            )
            with _cwd(root):
                path = run([_USER], [read_file], config=config, transport=transport)
            self.assertEqual(len(transport.calls), 2)
            first = json.loads(transport.calls[0][1])
            self.assertIs(first["stream"], False)
            self.assertIn("read_file", first["messages"][0]["content"])
            self.assertEqual(first["messages"][1], _USER)
            tool = first["tools"][0]
            self.assertEqual(tool["type"], "function")
            self.assertEqual(tool["function"]["parameters"]["required"], ["path"])
            second = json.loads(transport.calls[1][1])
            follow = second["messages"]
            self.assertEqual(follow[2]["tool_calls"][0]["function"]["index"], 0)
            self.assertEqual(
                follow[2]["tool_calls"][0]["function"]["arguments"], {"path": "a.txt"}
            )
            self.assertEqual(
                follow[3],
                {
                    "role": "tool",
                    "content": "hello\n",
                    "tool_name": "read_file",
                    "tool_call_id": "call_a1b2c3d4",
                },
            )
            events = _events(path)
            self.assertEqual(events[0]["raw_response"]["done_reason"], "stop")
            self.assertNotIn("done_reason", events[0])
            self.assertNotIn("type", events[0]["tools"][0])
            assistant = events[0]["assistant"]
            self.assertEqual(assistant["content"], "")
            self.assertEqual(assistant["tool_calls"][0]["tool_name"], "read_file")
            self.assertNotIn("tool_calls", events[0]["messages_sent"][-1])
            self.assertRegex(path.name, r"^\d{8}T\d{12}Z\.jsonl$")

    def test_several_calls_continue_after_a_miss(self):
        """Calls run in array order. A missing path does not skip the next."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("from-a", encoding="utf-8")
            config = Config(runs_dir=root / "runs", read_file_max_chars=100)
            transport = _Script(
                [
                    (200, _fixture("ollama_two_tool_calls.json")),
                    (200, _fixture("ollama_chat_nostream.json")),
                ]
            )
            with _cwd(root):
                path = run([_USER], [read_file], config=config, transport=transport)
            sent = json.loads(transport.calls[1][1])["messages"]
            self.assertEqual(sent[3]["tool_call_id"], "call_a1b2c3d4")
            self.assertIn("not found", sent[3]["content"])
            self.assertEqual(sent[4]["tool_call_id"], "call_e5f6g7h8")
            self.assertEqual(sent[4]["content"], "from-a")
            self.assertEqual(sent[2]["tool_calls"][0]["function"]["index"], 0)
            self.assertEqual(sent[2]["tool_calls"][1]["function"]["index"], 1)
            events = _events(path)
            self.assertEqual(len(events), 2)
            self.assertEqual(len(events[0]["assistant"]["tool_calls"]), 2)

    def test_last_allowed_call_does_not_run_tools(self):
        """Eight tool-call replies stop before the eighth call is run."""
        body = _fixture("ollama_one_tool_call.json")
        responses = [(200, _with_id(body, f"call_{index}")) for index in range(8)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("hello\n", encoding="utf-8")
            config = Config(runs_dir=root / "runs")
            transport = _Script(responses)
            with _cwd(root):
                path = run([_USER], [read_file], config=config, transport=transport)
            self.assertEqual(len(transport.calls), 8)
            events = _events(path)
            self.assertEqual(len(events), 8)
            self.assertEqual(events[-1]["stop_reason"], "max_turns")
            self.assertEqual(
                events[-1]["assistant"]["tool_calls"][0]["tool_call_id"], "call_7"
            )
            sent_on_last = [
                message["tool_call_id"]
                for message in events[-1]["messages_sent"]
                if message.get("role") == "tool"
            ]
            self.assertEqual(sent_on_last, [f"call_{index}" for index in range(7)])
            for event in events:
                for message in event["messages_sent"]:
                    self.assertNotEqual(message.get("tool_call_id"), "call_7")

    def test_eighth_reply_without_tools_is_stop(self):
        """A plain reply on the eighth model call uses ``stop``, not the cap."""
        body = _fixture("ollama_one_tool_call.json")
        responses = [(200, _with_id(body, f"call_{index}")) for index in range(7)]
        responses.append((200, _fixture("ollama_chat_nostream.json")))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("hello\n", encoding="utf-8")
            config = Config(runs_dir=root / "runs")
            transport = _Script(responses)
            with _cwd(root):
                path = run([_USER], [read_file], config=config, transport=transport)
            events = _events(path)
            self.assertEqual(len(transport.calls), 8)
            self.assertEqual(events[-1]["stop_reason"], "stop")
            self.assertNotIn("tool_calls", events[-1]["assistant"])

    def test_provider_error_stops_without_retry(self):
        """A failed provider call sets ``error`` and does not call again."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(runs_dir=root / "runs")
            transport = _Script([(404, _fixture("ollama_model_not_found.json"))])
            with _cwd(root):
                path = run([_USER], [read_file], config=config, transport=transport)
            self.assertEqual(len(transport.calls), 1)
            event = _events(path)[0]
            self.assertEqual(event["stop_reason"], "error")
            self.assertEqual(event["error"], "model 'llama3.2' not found")
            self.assertIsNone(event["assistant"])
            self.assertEqual(event["tools"][0]["name"], "read_file")
            self.assertEqual(event["messages_sent"][0]["role"], "system")


class AgentCliTests(unittest.TestCase):
    def test_agent_prints_the_run_path(self):
        """``peekaboo agent`` prints the run path and exits."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("hello\n", encoding="utf-8")
            config = Config(runs_dir=root / "runs", http_timeout_seconds=7)
            transport = _Script(
                [
                    (200, _fixture("ollama_one_tool_call.json")),
                    (200, _fixture("ollama_chat_nostream.json")),
                ]
            )
            stdout = StringIO()
            with _cwd(root), redirect_stdout(stdout):
                status = main(
                    ["agent", "Read", "the", "file."],
                    config=config,
                    transport=transport,
                )
            self.assertEqual(status, 0)
            path = Path(stdout.getvalue().strip())
            self.assertEqual(path.parent, root / "runs")
            self.assertEqual(_events(path)[-1]["stop_reason"], "stop")

    def test_blank_agent_does_not_call(self):
        """``peekaboo agent`` with no message exits before the provider."""
        transport = _Script([])
        stderr = StringIO()
        with redirect_stderr(stderr):
            status = main(["agent"], config=load_config({}), transport=transport)
        self.assertEqual(status, 2)
        self.assertIn("peekaboo agent MESSAGE", stderr.getvalue())
        self.assertEqual(transport.calls, [])
