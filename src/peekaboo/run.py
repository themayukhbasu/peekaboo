"""One-shot model run.

``run`` posts the messages it is given and writes one JSONL turn under
``config.runs_dir``. Chat passes one user message and an empty tools
list. A provider failure is recorded on that turn and is not retried.
"""

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

from peekaboo.config import Config

Transport = Callable[[str, bytes, float], tuple[int, bytes]]

_STAMP = "%Y%m%dT%H%M%S%fZ"
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class TransportError(OSError):
    """No HTTP response arrived. A status and a body are not this error."""


def urllib_transport(url: str, body: bytes, timeout: float) -> tuple[int, bytes]:
    """POST ``body`` and return the status and response bytes.

    A non-2xx status is still a response. ``TransportError`` means
    nothing came back. Proxy variables are ignored; pass the URL in.
    """
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with _OPENER.open(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        try:
            return error.code, error.read()
        finally:
            error.close()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise TransportError(f"Could not reach the provider ({reason}).") from error


def run(
    messages: Sequence[Mapping[str, str]],
    tools: Sequence[object],
    *,
    config: Config,
    transport: Transport | None = None,
) -> Path:
    """Send one non-streaming chat request and return the run path.

    ``tools`` must be empty. The default ``transport`` is stdlib
    ``urllib``. Provider failure is written on the turn, not raised.
    """
    if len(tools) != 0:
        raise ValueError("This run accepts no tools.")
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
    return _write_turn(config.runs_dir, event)


def _messages(messages: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
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
    parsed: object = None
    if raw is not None:
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = raw.decode("utf-8", errors="replace")
    assistant = _assistant(parsed) if status is not None and 200 <= status < 300 else None
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


def _assistant(parsed: object) -> dict[str, str] | None:
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
    if isinstance(parsed, dict):
        message = parsed.get("error")
        if isinstance(message, str) and message.strip() != "":
            return message
    if status is not None:
        return f"The provider returned HTTP {status}."
    return fallback


def _write_turn(runs_dir: Path, event: dict[str, object]) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime(_STAMP)
    line = json.dumps(event, ensure_ascii=False) + "\n"
    for suffix in range(100):
        name = f"{stamp}.jsonl" if suffix == 0 else f"{stamp}-{suffix}.jsonl"
        path = runs_dir / name
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(line)
        except FileExistsError:
            continue
        return path
    raise OSError(f"Could not create a run file in {runs_dir}.")
