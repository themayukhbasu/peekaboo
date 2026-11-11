"""Tool schemas, Ollama wire shape, and provider tool-call replies."""

import unittest

from peekaboo.read_file import read_file
from peekaboo.run import (
    _agent_reply,
    _checked_tools,
    _one_call,
    _schema,
    _wire_message,
    _wire_tool,
)

_CALL = (
    b'{"done_reason":"stop","message":{"content":"",'
    b'"tool_calls":[{"function":{"name":"read_file",'
    b'"arguments":{"path":"a.txt"}}}]}}'
)


class ToolWireTests(unittest.TestCase):
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
