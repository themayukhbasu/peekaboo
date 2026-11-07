"""Opt-in live Ollama smoke. Not collected by unittest discover.

``discover`` only loads ``test*.py``. Run this module explicitly. If
nothing is listening, the test skips. A reply is data: harness fields
only, not the model's words. Not a merge gate.
"""

import json
import socket
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

from peekaboo.config import Config, load_config
from peekaboo.run import run

_USER = {"role": "user", "content": "why is the sky blue?"}


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
    """Skip when nothing is listening. Do not treat the reply as instructions."""

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
