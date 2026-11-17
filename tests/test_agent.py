"""Tool wire format and the agent loop through ``run``."""

import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from peekaboo.config import Config
from peekaboo.tools.read_file import read_file
from peekaboo.run import TransportError, run

_UNREADABLE = "The provider returned tool calls that could not be read."
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
    return (_FIXTURES / name).read_bytes()


def _with_id(body: bytes, call_id: str) -> bytes:
    payload = json.loads(body)
    payload["message"]["tool_calls"][0]["id"] = call_id
    return json.dumps(payload).encode("utf-8")


def _events(path: Path) -> list[dict[str, object]]:
    """Return each JSON object in a run file, in file order."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@contextmanager
def _drive(responses, tools=None, text="hello\n", transport=None, **settings):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "a.txt").write_text(text, encoding="utf-8")
        config = Config(runs_dir=root / "runs", **settings)
        if transport is None:
            transport = _Script(responses)
        offered = [read_file] if tools is None else tools
        path = run([_USER], offered, config=config, transport=transport, workspace=root)
        yield path, transport


def _named_tool(name: str, result: object):
    def call(_arguments: object, **_rest: object) -> object:
        if isinstance(result, Exception):
            raise result
        return result

    call.name, call.description = name, "Test tool."
    call.parameters = {"type": "object", "properties": {}}
    return call


_BAD_BATCH = (
    b'{"message":{"role":"assistant","content":"","tool_calls":['
    b'{"id":"call_raise","function":{"name":"boom","arguments":{}}},'
    b'{"id":"call_miss","function":{"name":"nope","arguments":{}}},'
    b'{"id":"call_odd","function":{"name":"odd","arguments":{}}}]}}'
)


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
            path = run(
                [_USER],
                [read_file],
                config=config,
                transport=transport,
                workspace=root,
            )
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
        responses = [(200, _fixture("ollama_one_tool_call.json")), (200, plain)]
        with _drive(responses, http_timeout_seconds=7) as (path, transport):
            first = json.loads(transport.calls[0][1])
            self.assertIs(first["stream"], False)
            tool = first["tools"][0]
            self.assertEqual(tool["type"], "function")
            self.assertEqual(tool["function"]["parameters"]["required"], ["path"])
            follow = json.loads(transport.calls[1][1])["messages"]
            self.assertEqual(follow[2]["tool_calls"][0]["function"]["index"], 0)
            self.assertEqual(
                follow[2]["tool_calls"][0]["function"]["arguments"], {"path": "a.txt"}
            )
            event = _events(path)[0]
            self.assertEqual(event["raw_response"]["done_reason"], "stop")
            self.assertNotIn("done_reason", event)
            self.assertNotIn("type", event["tools"][0])

    def test_several_calls_continue_after_a_miss(self):
        """Calls run in array order. A missing path does not skip the next."""
        responses = [
            (200, _fixture("ollama_two_tool_calls.json")),
            (200, _fixture("ollama_chat_nostream.json")),
        ]
        with _drive(responses, text="from-a", read_file_max_chars=100) as (
            path,
            transport,
        ):
            sent = json.loads(transport.calls[1][1])["messages"]
            self.assertIn("not found", sent[3]["content"])
            self.assertEqual(sent[3]["tool_call_id"], "call_a1b2c3d4")
            self.assertEqual(sent[4]["content"], "from-a")
            self.assertEqual(sent[4]["tool_call_id"], "call_e5f6g7h8")
            self.assertEqual(len(_events(path)[0]["assistant"]["tool_calls"]), 2)

    def test_last_allowed_call_does_not_run_tools(self):
        """Eight tool-call replies stop before the eighth call is run."""
        body = _fixture("ollama_one_tool_call.json")
        responses = [(200, _with_id(body, f"call_{index}")) for index in range(8)]
        with _drive(responses) as (path, transport):
            self.assertEqual(len(transport.calls), 8)
            events = _events(path)
            self.assertEqual(events[-1]["stop_reason"], "max_turns")
            self.assertEqual(
                events[-1]["assistant"]["tool_calls"][0]["tool_call_id"], "call_7"
            )
            sent_ids = [
                message["tool_call_id"]
                for message in events[-1]["messages_sent"]
                if message.get("role") == "tool"
            ]
            self.assertEqual(sent_ids, [f"call_{index}" for index in range(7)])

    def test_eighth_reply_without_tools_is_stop(self):
        """A plain reply on the eighth model call uses ``stop``, not the cap."""
        body = _fixture("ollama_one_tool_call.json")
        responses = [(200, _with_id(body, f"call_{index}")) for index in range(7)]
        responses.append((200, _fixture("ollama_chat_nostream.json")))
        with _drive(responses) as (path, transport):
            events = _events(path)
            self.assertEqual(len(transport.calls), 8)
            self.assertEqual(events[-1]["stop_reason"], "stop")
            self.assertNotIn("tool_calls", events[-1]["assistant"])

    def test_provider_error_stops_without_retry(self):
        """A failed provider call sets ``error`` and does not call again."""
        responses = [(404, _fixture("ollama_model_not_found.json"))]
        with _drive(responses) as (path, transport):
            self.assertEqual(len(transport.calls), 1)
            event = _events(path)[0]
            self.assertEqual(event["stop_reason"], "error")
            self.assertEqual(event["error"], "model 'llama3.2' not found")

    def test_batch_records_a_raise_an_unknown_name_and_a_non_text_result(self):
        """A raise, an unknown tool, and a non-text result stay in the batch."""
        tools = [_named_tool("boom", RuntimeError("kaput")), _named_tool("odd", 5)]
        responses = [(200, _BAD_BATCH), (200, _fixture("ollama_chat_nostream.json"))]
        with _drive(responses, tools) as (path, transport):
            sent = json.loads(transport.calls[1][1])["messages"]
            self.assertEqual(sent[3]["content"], "boom failed (kaput).")
            self.assertEqual(sent[4]["content"], "Unknown tool nope.")
            self.assertEqual(sent[5]["content"], "odd failed (result was not text).")
            self.assertEqual(_events(path)[-1]["stop_reason"], "stop")

    def test_transport_error_is_one_error_turn(self):
        """A transport error stops the agent loop and is not retried."""
        seen: list[str] = []

        def fail(_url: str, _body: bytes, _timeout: float) -> tuple[int, bytes]:
            seen.append(_url)
            raise TransportError("connection refused")

        with _drive([], transport=fail) as (path, _transport):
            event = _events(path)[0]
            self.assertEqual(len(seen), 1)
            self.assertEqual(event["stop_reason"], "error")
            self.assertEqual(event["error"], "connection refused")

    def test_two_replies_without_ids_get_distinct_fallback_ids(self):
        """Two tool replies with no id are ``call_0`` then ``call_1`` on the wire."""
        no_id = (
            b'{"done_reason":"stop","message":{"role":"assistant","content":"",'
            b'"tool_calls":[{"function":{"name":"read_file",'
            b'"arguments":{"path":"a.txt"}}}]}}'
        )
        plain = _fixture("ollama_chat_nostream.json")
        with _drive([(200, no_id), (200, no_id), (200, plain)]) as (_path, transport):
            posted = json.loads(transport.calls[2][1])["messages"]
            ids = []
            for message in posted:
                calls = message.get("tool_calls")
                if isinstance(calls, list) and calls:
                    ids.append(calls[0]["id"])
                if message.get("role") == "tool":
                    ids.append(message["tool_call_id"])
            self.assertEqual(ids, ["call_0", "call_0", "call_1", "call_1"])

    def test_unreadable_tool_calls_are_one_error_turn(self):
        """A string ``arguments`` value, a non-mapping call, or a nameless call stops."""
        bodies = (
            b'{"message":{"content":"","tool_calls":[{"function":'
            b'{"name":"read_file","arguments":"{\\"path\\": \\"a.txt\\"}"}}]}}',
            b'{"message":{"content":"","tool_calls":[1]}}',
            b'{"message":{"content":"","tool_calls":[{"function":{}}]}}',
        )
        for raw in bodies:
            with _drive([(200, raw)]) as (path, _transport):
                event = _events(path)[0]
                self.assertEqual(event["stop_reason"], "error")
                self.assertEqual(event["error"], _UNREADABLE)
                self.assertIsNone(event["assistant"])

    def test_duplicate_tool_name_does_not_call(self):
        """Two tools with one name are rejected before the provider."""
        transport = _Script([])
        with self.assertRaises(ValueError) as raised:
            run(
                [_USER],
                [read_file, read_file],
                config=Config(),
                transport=transport,
                workspace=Path("."),
            )
        self.assertIn("Duplicate tool name", str(raised.exception))
        self.assertEqual(transport.calls, [])
