"""Tool wire format and the agent loop through ``run``."""

import json
import os
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from peekaboo.config import Config
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
