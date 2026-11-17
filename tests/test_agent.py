"""Tool schemas, Ollama wire shape, and provider tool-call replies."""

import unittest

from peekaboo.tools.read_file import read_file
from peekaboo.run import (
    _FallbackIds,
    _checked_tools,
    _parse_agent_reply,
    _parse_tool_call,
    _schema,
    _wire_message,
    _wire_tool,
)

_UNREADABLE = "The provider returned tool calls that could not be read."


def _harness_message(arguments: object) -> dict[str, object]:
    """One assistant message carrying a single harness tool call."""
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "tool_name": "read_file",
                "tool_call_id": "call_a1b2c3d4",
                "arguments": arguments,
            }
        ],
    }


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
        """A harness call becomes ``id`` plus ``function``. Arguments stay put."""
        recorded = {"path": "a.txt"}
        wire = _wire_message(_harness_message(recorded))
        function = wire["tool_calls"][0]["function"]
        self.assertEqual(wire["tool_calls"][0]["id"], "call_a1b2c3d4")
        self.assertEqual(function["index"], 0)
        self.assertIs(function["arguments"], recorded)
        forwarded = _wire_message(_harness_message("not-an-object"))
        self.assertEqual(
            forwarded["tool_calls"][0]["function"]["arguments"], "not-an-object"
        )


class ReplyParseTests(unittest.TestCase):
    """Stop replies still yield calls. A call that cannot be sent back is an error."""

    def test_stop_still_parses_calls_and_errors_stay_text(self):
        """Tool calls are read when ``done_reason`` is stop. Errors keep text."""
        reply = _parse_agent_reply(200, _CALL, _FallbackIds())
        self.assertIsNone(reply.error)
        self.assertEqual(reply.assistant, {"role": "assistant", "content": ""})
        self.assertEqual(reply.calls[0].call_id, "call_0")
        self.assertEqual(reply.calls[0].arguments, {"path": "a.txt"})
        self.assertEqual(reply.body["done_reason"], "stop")
        self.assertIsNone(_parse_tool_call({"function": {}}, _FallbackIds()))
        missed = _parse_agent_reply(
            404,
            b'{"error":"model \'llama3.2\' not found"}',
            _FallbackIds(),
        )
        self.assertEqual(missed.error, "model 'llama3.2' not found")

    def test_missing_ids_differ_across_replies(self):
        """Two replies that share one issuer do not both become ``call_0``."""
        issued = _FallbackIds()
        first = _parse_agent_reply(200, _CALL, issued)
        second = _parse_agent_reply(200, _CALL, issued)
        self.assertIsNone(first.error)
        self.assertIsNone(second.error)
        self.assertEqual(first.calls[0].call_id, "call_0")
        self.assertEqual(second.calls[0].call_id, "call_1")

    def test_unreadable_calls_reject_the_reply(self):
        """A non-mapping call or non-object arguments rejects the reply."""
        string_args = (
            b'{"message":{"content":"","tool_calls":[{"function":'
            b'{"name":"read_file","arguments":"{\\"path\\":\\"a.txt\\"}"}}]}}'
        )
        not_a_call = b'{"message":{"content":"","tool_calls":[1]}}'
        for raw in (string_args, not_a_call):
            reply = _parse_agent_reply(200, raw, _FallbackIds())
            self.assertIsNone(reply.assistant)
            self.assertEqual(reply.calls, ())
            self.assertEqual(reply.error, _UNREADABLE)
