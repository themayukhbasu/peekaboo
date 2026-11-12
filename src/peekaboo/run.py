"""One run of the chat loop or the agent loop.

``run`` posts the messages it is given and writes one JSONL file under
``config.runs_dir``. An empty ``tools`` list is chat: one user message,
no system message, and no tools on the request. A non-empty list is the
agent loop. A provider failure is recorded on that turn and is not retried.
"""

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple
from urllib import error as urllib_error
from urllib import request as urllib_request

from peekaboo.config import Config
from peekaboo.runs import RunLog, write_turn

Transport = Callable[[str, bytes, float], tuple[int, bytes]]

_OPENER = urllib_request.build_opener(urllib_request.ProxyHandler({}))
_MAX_TURNS = 8
_SYSTEM = (
    "You may call read_file to read a file in the workspace. Pass one path argument."
)


class TransportError(OSError):
    """No HTTP response arrived. A status and a body are not this error."""


class _Call(NamedTuple):
    """One tool call taken from a provider message."""

    name: str
    call_id: str
    arguments: object


def urllib_transport(url: str, body: bytes, timeout: float) -> tuple[int, bytes]:
    """POST ``body`` and return the status and response bytes.

    A non-2xx status is still a response. ``TransportError`` means
    nothing came back. Proxy variables are ignored; pass the URL in.
    """
    request = urllib_request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with _OPENER.open(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib_error.HTTPError as error:
        try:
            return error.code, error.read()
        finally:
            error.close()
    except (urllib_error.URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise TransportError(f"Could not reach the provider ({reason}).") from error


def run(
    messages: Sequence[Mapping[str, str]],
    tools: Sequence[object],
    *,
    config: Config,
    transport: Transport | None = None,
) -> Path:
    """Send the messages and return the run path.

    An empty ``tools`` list is one chat turn. Anything else is the
    agent loop: one fixed system message, then up to eight model
    calls. The default ``transport`` is stdlib ``urllib``. Provider
    failure is written on the turn, not raised.
    """
    if len(tools) != 0:
        return _agent_run(messages, tools, config=config, transport=transport)
    sent = _messages(messages)
    post = urllib_transport if transport is None else transport
    url = f"{config.ollama_base_url.rstrip('/')}/api/chat"
    body = json.dumps(
        {"model": config.model, "messages": sent, "stream": False}
    ).encode("utf-8")
    try:
        status, raw = post(url, body, float(config.http_timeout_seconds))
    except TransportError as error:
        event = _event(config.model, sent, None, None, str(error))
    else:
        event = _event(config.model, sent, status, raw, "The provider call failed.")
    return write_turn(config.runs_dir, event)


def _agent_run(  # pylint: disable=too-many-locals
    messages: Sequence[Mapping[str, str]],
    tools: Sequence[object],
    *,
    config: Config,
    transport: Transport | None,
) -> Path:
    """Run tool calls until the model stops, the cap, or a provider error.

    The workspace is the process working directory. Tool calls on the
    eighth model call are recorded and not run.
    """
    offered = _checked_tools(tools)
    history: list[dict[str, object]] = [
        {"role": "system", "content": _SYSTEM},
        *_messages(messages),
    ]
    schemas = [_schema(tool) for tool in offered]
    by_name = {tool.name: tool for tool in offered}
    log = RunLog(config.runs_dir)
    workspace = Path.cwd()
    post = urllib_transport if transport is None else transport
    url = f"{config.ollama_base_url.rstrip('/')}/api/chat"
    timeout = float(config.http_timeout_seconds)
    for turn in range(1, _MAX_TURNS + 1):
        posted = list(history)
        body = json.dumps(
            {
                "model": config.model,
                "messages": [_wire_message(item) for item in posted],
                "tools": [_wire_tool(schema) for schema in schemas],
                "stream": False,
            }
        ).encode("utf-8")
        try:
            status, raw = post(url, body, timeout)
        except TransportError as error:
            log.append(
                _agent_event(
                    config.model, posted, None, "error", str(error), None, schemas
                )
            )
            return log.path
        assistant, calls, failure, parsed = _agent_reply(status, raw)
        if failure is not None:
            log.append(
                _agent_event(
                    config.model, posted, None, "error", failure, parsed, schemas
                )
            )
            return log.path
        if calls and turn < _MAX_TURNS:
            reason = "tool_calls"
        elif calls:
            reason = "max_turns"
        else:
            reason = "stop"
        if calls:
            assistant = {
                **assistant,
                "tool_calls": [_harness_call(call) for call in calls],
            }
        log.append(
            _agent_event(config.model, posted, assistant, reason, None, parsed, schemas)
        )
        if reason != "tool_calls":
            return log.path
        history.append(assistant)
        history.extend(
            _run_batch(
                calls,
                by_name,
                workspace=workspace,
                max_chars=config.read_file_max_chars,
            )
        )
    raise OSError("The agent loop ended without writing a turn.")


def _checked_tools(tools: Sequence[object]) -> list[object]:
    """Return ``tools`` when each one has a schema and can be called."""
    seen: dict[str, object] = {}
    for tool in tools:
        name = getattr(tool, "name", None)
        description = getattr(tool, "description", None)
        parameters = getattr(tool, "parameters", None)
        if (
            not callable(tool)
            or not isinstance(name, str)
            or name == ""
            or not isinstance(description, str)
            or not isinstance(parameters, Mapping)
        ):
            raise ValueError(
                "Each tool needs a name, description, parameters, and call."
            )
        if name in seen:
            raise ValueError(f"Duplicate tool name {name}.")
        seen[name] = tool
    return list(seen.values())


def _schema(tool: object) -> dict[str, object]:
    """Copy the harness schema fields off one tool."""
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.parameters,
    }


def _wire_tool(schema: Mapping[str, object]) -> dict[str, object]:
    """Wrap one schema in Ollama's ``type`` / ``function`` envelope."""
    return {"type": "function", "function": dict(schema)}


def _wire_message(message: Mapping[str, object]) -> dict[str, object]:
    """Project one harness message onto an Ollama chat message.

    Assistant tool calls become ``id`` plus ``function`` with an
    arguments object. ``done_reason`` is not read.
    """
    calls = message.get("tool_calls")
    if not isinstance(calls, list):
        return dict(message)
    wire_calls = []
    for index, call in enumerate(calls):
        if not isinstance(call, Mapping):
            continue
        arguments = call.get("arguments")
        if not isinstance(arguments, dict):
            arguments = {}
        wire_calls.append(
            {
                "id": call.get("tool_call_id", ""),
                "function": {
                    "index": index,
                    "name": call.get("tool_name", ""),
                    "arguments": arguments,
                },
            }
        )
    return {
        "role": message.get("role", "assistant"),
        "content": message.get("content", ""),
        "tool_calls": wire_calls,
    }


def _harness_call(call: _Call) -> dict[str, object]:
    """Return the event shape of one tool call."""
    return {
        "tool_name": call.name,
        "tool_call_id": call.call_id,
        "arguments": call.arguments,
    }


def _run_batch(
    calls: Sequence[_Call],
    by_name: Mapping[str, object],
    *,
    workspace: Path,
    max_chars: int,
) -> list[dict[str, str]]:
    """Run ``calls`` in order. A failure is an error string; the rest run."""
    results = []
    for call in calls:
        tool = by_name.get(call.name)
        if tool is None:
            content = f"Unknown tool {call.name}."
        else:
            try:
                content = tool(call.arguments, workspace=workspace, max_chars=max_chars)
            except Exception as error:  # pylint: disable=broad-exception-caught
                content = f"{call.name} failed ({error})."
            if not isinstance(content, str):
                content = f"{call.name} failed (result was not text)."
        results.append(
            {
                "role": "tool",
                "content": content,
                "tool_name": call.name,
                "tool_call_id": call.call_id,
            }
        )
    return results


def _agent_reply(
    status: int | None,
    raw: bytes | None,
) -> tuple[dict[str, str] | None, list[_Call], str | None, object]:
    """Parse one agent reply into an assistant, calls, an error, and the body.

    A non-empty ``tool_calls`` list is a tool turn even when ``content``
    is empty and ``done_reason`` is ``stop``. A missing ``content``
    counts as an empty string.
    """
    parsed = _decode(raw)
    message = parsed.get("message") if isinstance(parsed, dict) else None
    if status is None or not 200 <= status < 300 or not isinstance(message, dict):
        return (
            None,
            [],
            _error_text(status, parsed, "The provider call failed."),
            parsed,
        )
    if "content" in message:
        content = message["content"]
        if not isinstance(content, str):
            return (
                None,
                [],
                _error_text(status, parsed, "The provider call failed."),
                parsed,
            )
    else:
        content = ""
    role = message.get("role", "assistant")
    if not isinstance(role, str):
        return (
            None,
            [],
            _error_text(status, parsed, "The provider call failed."),
            parsed,
        )
    raw_calls = message.get("tool_calls", [])
    if not isinstance(raw_calls, list):
        return (
            None,
            [],
            "The provider returned tool calls that could not be read.",
            parsed,
        )
    calls: list[_Call] = []
    for index, item in enumerate(raw_calls):
        call = _one_call(item, index)
        if call is None:
            return (
                None,
                [],
                "The provider returned tool calls that could not be read.",
                parsed,
            )
        calls.append(call)
    return {"role": role, "content": content}, calls, None, parsed


def _one_call(item: object, index: int) -> _Call | None:
    """Return one call, or ``None`` when the object has no function name."""
    if not isinstance(item, dict):
        return None
    function = item.get("function")
    if not isinstance(function, dict):
        return None
    name = function.get("name")
    if not isinstance(name, str) or name == "":
        return None
    call_id = item.get("id")
    if not isinstance(call_id, str) or call_id == "":
        call_id = f"call_{index}"
    return _Call(name, call_id, function.get("arguments", {}))


def _agent_event(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    model: str,
    sent: list[dict[str, object]],
    assistant: dict[str, object] | None,
    stop_reason: str,
    error: str | None,
    raw: object,
    schemas: list[dict[str, object]],
) -> dict[str, object]:
    """Build one agent turn, including the tool schema that was sent."""
    return {
        "model": model,
        "messages_sent": sent,
        "assistant": assistant,
        "stop_reason": stop_reason,
        "error": error,
        "raw_response": raw,
        "tools": schemas,
    }


def _messages(messages: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """Copy each message to string ``role`` and ``content``."""
    if len(messages) == 0:
        raise ValueError("A run needs at least one message.")
    sent: list[dict[str, str]] = []
    for message in messages:
        try:
            role = message["role"]
            content = message["content"]
        except KeyError as error:
            raise ValueError("Each message needs a role and content.") from error
        if not isinstance(role, str) or not isinstance(content, str):
            raise ValueError("Each message needs a string role and content.")
        sent.append({"role": role, "content": content})
    return sent


def _event(
    model: str,
    sent: list[dict[str, str]],
    status: int | None,
    raw: bytes | None,
    fallback: str,
) -> dict[str, object]:
    """Build one chat turn from the sent messages and the provider reply."""
    parsed = _decode(raw)
    if status is not None and 200 <= status < 300:
        assistant = _assistant(parsed)
    else:
        assistant = None
    if assistant is None:
        error: str | None = _error_text(status, parsed, fallback)
        stop_reason = "error"
    else:
        error = None
        stop_reason = "stop"
    return {
        "model": model,
        "messages_sent": sent,
        "assistant": assistant,
        "stop_reason": stop_reason,
        "error": error,
        "raw_response": parsed,
    }


def _decode(raw: bytes | None) -> object:
    """Decode a provider body. ``None`` means nothing arrived."""
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return raw.decode("utf-8", errors="replace")


def _assistant(parsed: object) -> dict[str, str] | None:
    """Return the assistant role and content, or ``None`` if they are absent."""
    if not isinstance(parsed, dict):
        return None
    message = parsed.get("message")
    if not isinstance(message, dict):
        return None
    role = message.get("role", "assistant")
    content = message.get("content")
    if not isinstance(role, str) or not isinstance(content, str):
        return None
    return {"role": role, "content": content}


def _error_text(status: int | None, parsed: object, fallback: str) -> str:
    """Pick the error text for a turn that has no assistant message."""
    if isinstance(parsed, dict):
        message = parsed.get("error")
        if isinstance(message, str) and message.strip() != "":
            return message
    if status is not None and 200 <= status < 300:
        return f"The provider returned HTTP {status} without an assistant message."
    if status is not None:
        return f"The provider returned HTTP {status}."
    return fallback
