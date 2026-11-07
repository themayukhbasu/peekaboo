"""Defaults and environment overrides for load_config."""

import os
import tempfile
import unittest
from contextlib import chdir
from pathlib import Path
from unittest.mock import patch

from peekaboo.config import Config, ConfigError, load_config


class LoadConfigTests(unittest.TestCase):
    def test_empty_environment_uses_spec_defaults(self):
        config = load_config({})
        self.assertEqual(
            config,
            Config(
                model="llama3.2",
                ollama_base_url="http://127.0.0.1:11434",
                http_timeout_seconds=120,
                runs_dir=Path(".peekaboo/runs"),
                peek_host="127.0.0.1",
                peek_port=8765,
                read_file_max_chars=32 * 1024,
            ),
        )

    def test_environment_overrides_each_setting(self):
        config = load_config(
            {
                "PEEKABOO_MODEL": " qwen2.5 ",
                "PEEKABOO_OLLAMA_BASE_URL": "https://ollama.example/v1/",
                "PEEKABOO_HTTP_TIMEOUT": "30",
                "PEEKABOO_RUNS_DIR": "var/runs",
                "PEEKABOO_PEEK_HOST": "localhost",
                "PEEKABOO_PEEK_PORT": "9000",
                "PEEKABOO_READ_FILE_MAX_CHARS": "128",
            }
        )
        self.assertEqual(config.model, "qwen2.5")
        self.assertEqual(config.ollama_base_url, "https://ollama.example/v1")
        self.assertEqual(config.http_timeout_seconds, 30)
        self.assertEqual(config.runs_dir, Path("var/runs"))
        self.assertEqual(config.peek_host, "localhost")
        self.assertEqual(config.peek_port, 9000)
        self.assertEqual(config.read_file_max_chars, 128)

    def test_blank_value_keeps_the_default(self):
        config = load_config(
            {"PEEKABOO_MODEL": "  ", "PEEKABOO_HTTP_TIMEOUT": ""}
        )
        self.assertEqual(config.model, "llama3.2")
        self.assertEqual(config.http_timeout_seconds, 120)

    def test_malformed_timeout_names_the_variable(self):
        with self.assertRaises(ConfigError) as caught:
            load_config({"PEEKABOO_HTTP_TIMEOUT": "12o"})
        self.assertIsInstance(caught.exception, ValueError)
        message = str(caught.exception)
        self.assertIn("PEEKABOO_HTTP_TIMEOUT", message)
        self.assertIn("12o", message)

    def test_non_positive_and_fractional_timeouts_raise(self):
        for raw in ("0", "-3", "120.5"):
            with self.subTest(raw=raw):
                with self.assertRaises(ConfigError):
                    load_config({"PEEKABOO_HTTP_TIMEOUT": raw})

    def test_port_out_of_range_raises(self):
        with self.assertRaises(ConfigError) as caught:
            load_config({"PEEKABOO_PEEK_PORT": "70000"})
        self.assertIn("PEEKABOO_PEEK_PORT", str(caught.exception))

    def test_base_url_without_scheme_raises(self):
        with self.assertRaises(ConfigError) as caught:
            load_config({"PEEKABOO_OLLAMA_BASE_URL": "127.0.0.1:11434"})
        self.assertIn("PEEKABOO_OLLAMA_BASE_URL", str(caught.exception))

    def test_injected_mapping_ignores_the_process_environment(self):
        with patch.dict(os.environ, {"PEEKABOO_MODEL": "from-process"}, clear=False):
            config = load_config({})
        self.assertEqual(config.model, "llama3.2")

    def test_omitted_mapping_reads_the_process_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            with chdir(directory):
                with patch.dict(
                    os.environ, {"PEEKABOO_MODEL": "from-process"}, clear=False
                ):
                    config = load_config()
        self.assertEqual(config.model, "from-process")
        self.assertEqual(config.http_timeout_seconds, 120)

    def test_dotenv_value_applies_when_unset_in_the_process(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / ".env").write_text(
                "PEEKABOO_MODEL=from-dotenv\n", encoding="utf-8"
            )
            with chdir(directory):
                with patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("PEEKABOO_MODEL", None)
                    config = load_config()
        self.assertEqual(config.model, "from-dotenv")

    def test_process_environment_overrides_dotenv(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / ".env").write_text(
                "PEEKABOO_MODEL=from-dotenv\n", encoding="utf-8"
            )
            with chdir(directory):
                with patch.dict(os.environ, {"PEEKABOO_MODEL": "from-process"}):
                    config = load_config()
        self.assertEqual(config.model, "from-process")

    def test_blank_process_value_beats_dotenv(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / ".env").write_text(
                'export PEEKABOO_MODEL="from-dotenv"\n'
                "PEEKABOO_HTTP_TIMEOUT=45\n"
                "PEEKABOO_PEEK_HOST='localhost'\n",
                encoding="utf-8",
            )
            with chdir(directory):
                with patch.dict(os.environ, {"PEEKABOO_MODEL": "   "}, clear=False):
                    os.environ.pop("PEEKABOO_HTTP_TIMEOUT", None)
                    os.environ.pop("PEEKABOO_PEEK_HOST", None)
                    config = load_config()
        self.assertEqual(config.model, "llama3.2")
        self.assertEqual(config.http_timeout_seconds, 45)
        self.assertEqual(config.peek_host, "localhost")

    def test_injected_mapping_ignores_dotenv_on_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / ".env").write_text(
                "PEEKABOO_MODEL=from-dotenv\n", encoding="utf-8"
            )
            with chdir(directory):
                config = load_config({})
        self.assertEqual(config.model, "llama3.2")

    def test_dotenv_path_merges_under_the_injected_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.env"
            path.write_text(
                "PEEKABOO_MODEL=from-dotenv\nPEEKABOO_HTTP_TIMEOUT=15\n",
                encoding="utf-8",
            )
            config = load_config(
                {"PEEKABOO_MODEL": "from-process"},
                dotenv_path=path,
            )
        self.assertEqual(config.model, "from-process")
        self.assertEqual(config.http_timeout_seconds, 15)

    def test_missing_dotenv_path_contributes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            config = load_config({}, dotenv_path=Path(directory) / "missing.env")
        self.assertEqual(config.model, "llama3.2")
        self.assertEqual(config.http_timeout_seconds, 120)
