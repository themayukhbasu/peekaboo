"""Defaults, environment overrides, and dotenv syntax for load_config."""

import os
import tempfile
import unittest
from contextlib import chdir
from pathlib import Path
from unittest.mock import patch

from peekaboo.config import Config, ConfigError, default, env_name, load_config


class LoadConfigTests(unittest.TestCase):  # pylint: disable=too-many-public-methods
    """``load_config`` defaults, overrides, and dotenv merge.

    The cases stay in one class rather than being split to meet a count.
    """

    def test_empty_environment_uses_spec_defaults(self):
        """An empty mapping keeps every spec default."""
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

    def test_default_object_exposes_spec_values(self):
        """``default`` holds the spec values."""
        self.assertEqual(default.model, "llama3.2")
        self.assertEqual(default.ollama_base_url, "http://127.0.0.1:11434")
        self.assertEqual(default.http_timeout_seconds, 120)
        self.assertEqual(default.runs_dir, Path(".peekaboo/runs"))
        self.assertEqual(default.peek_host, "127.0.0.1")
        self.assertEqual(default.peek_port, 8765)
        self.assertEqual(default.read_file_max_chars, 32 * 1024)

    def test_env_name_object_exposes_variable_names(self):
        """``env_name`` holds the environment variable names."""
        self.assertEqual(env_name.model, "PEEKABOO_MODEL")
        self.assertEqual(env_name.ollama_base_url, "PEEKABOO_OLLAMA_BASE_URL")
        self.assertEqual(env_name.http_timeout_seconds, "PEEKABOO_HTTP_TIMEOUT")
        self.assertEqual(env_name.runs_dir, "PEEKABOO_RUNS_DIR")
        self.assertEqual(env_name.peek_host, "PEEKABOO_PEEK_HOST")
        self.assertEqual(env_name.peek_port, "PEEKABOO_PEEK_PORT")
        self.assertEqual(env_name.read_file_max_chars, "PEEKABOO_READ_FILE_MAX_CHARS")

    def test_environment_overrides_each_setting(self):
        """A non-blank value replaces each setting."""
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
        """A blank value keeps the spec default."""
        config = load_config({"PEEKABOO_MODEL": "  ", "PEEKABOO_HTTP_TIMEOUT": ""})
        self.assertEqual(config.model, "llama3.2")
        self.assertEqual(config.http_timeout_seconds, 120)

    def test_malformed_timeout_names_the_variable(self):
        """A bad timeout names ``PEEKABOO_HTTP_TIMEOUT``."""
        with self.assertRaises(ConfigError) as caught:
            load_config({"PEEKABOO_HTTP_TIMEOUT": "12o"})
        self.assertIsInstance(caught.exception, ValueError)
        message = str(caught.exception)
        self.assertIn("PEEKABOO_HTTP_TIMEOUT", message)
        self.assertIn("12o", message)

    def test_non_positive_and_fractional_timeouts_raise(self):
        """Zero, negative, and fractional timeouts are rejected."""
        for raw in ("0", "-3", "120.5"):
            with self.subTest(raw=raw):
                with self.assertRaises(ConfigError):
                    load_config({"PEEKABOO_HTTP_TIMEOUT": raw})

    def test_port_out_of_range_raises(self):
        """A port above 65535 is rejected."""
        with self.assertRaises(ConfigError) as caught:
            load_config({"PEEKABOO_PEEK_PORT": "70000"})
        self.assertIn("PEEKABOO_PEEK_PORT", str(caught.exception))

    def test_base_url_without_scheme_raises(self):
        """A base URL without a scheme is rejected."""
        with self.assertRaises(ConfigError) as caught:
            load_config({"PEEKABOO_OLLAMA_BASE_URL": "127.0.0.1:11434"})
        self.assertIn("PEEKABOO_OLLAMA_BASE_URL", str(caught.exception))

    def test_injected_mapping_ignores_the_process_environment(self):
        """An injected mapping does not read the process environment."""
        with patch.dict(os.environ, {"PEEKABOO_MODEL": "from-process"}, clear=False):
            config = load_config({})
        self.assertEqual(config.model, "llama3.2")

    def test_omitted_mapping_reads_the_process_environment(self):
        """Omitting the mapping reads the process environment."""
        with tempfile.TemporaryDirectory() as directory:
            with chdir(directory):
                with patch.dict(
                    os.environ, {"PEEKABOO_MODEL": "from-process"}, clear=False
                ):
                    config = load_config()
        self.assertEqual(config.model, "from-process")
        self.assertEqual(config.http_timeout_seconds, 120)

    def test_dotenv_value_applies_when_unset_in_the_process(self):
        """A dotenv value applies when the process does not set that name."""
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
        """A process value replaces the dotenv value."""
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / ".env").write_text(
                "PEEKABOO_MODEL=from-dotenv\n", encoding="utf-8"
            )
            with chdir(directory):
                with patch.dict(os.environ, {"PEEKABOO_MODEL": "from-process"}):
                    config = load_config()
        self.assertEqual(config.model, "from-process")

    def test_blank_process_value_beats_dotenv(self):
        """A blank process value beats the dotenv value and keeps the default."""
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
        """An injected mapping with no dotenv path ignores ``.env``."""
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / ".env").write_text(
                "PEEKABOO_MODEL=from-dotenv\n", encoding="utf-8"
            )
            with chdir(directory):
                config = load_config({})
        self.assertEqual(config.model, "llama3.2")

    def test_dotenv_path_merges_under_the_injected_mapping(self):
        """A chosen dotenv file sits under the injected mapping."""
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
        """A missing dotenv path adds nothing."""
        with tempfile.TemporaryDirectory() as directory:
            config = load_config({}, dotenv_path=Path(directory) / "missing.env")
        self.assertEqual(config.model, "llama3.2")
        self.assertEqual(config.http_timeout_seconds, 120)

    def test_double_quoted_newline_and_braced_expansion(self):
        """Double quotes expand a newline and a braced name."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.env"
            path.write_text(
                "TAG=qwen\n"
                'PEEKABOO_MODEL="${TAG}\\n2.5"\n'
                "PEEKABOO_READ_FILE_MAX_CHARS=64 # chars\n",
                encoding="utf-8",
            )
            config = load_config({}, dotenv_path=path)
        self.assertEqual(config.model, "qwen\n2.5")
        self.assertEqual(config.read_file_max_chars, 64)

    def test_single_quotes_expand_braces_and_keep_a_bare_dollar(self):
        """A single-quoted bare ``$TAG`` stays literal, and ``${TAG}`` expands."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.env"
            path.write_text(
                "TAG=qwen\n"
                "PEEKABOO_MODEL='$TAG'\n"
                "PEEKABOO_RUNS_DIR='dir/${TAG}'\n"
                "PEEKABOO_PEEK_HOST='local\\nhost'\n",
                encoding="utf-8",
            )
            config = load_config({}, dotenv_path=path)
        self.assertEqual(config.model, "$TAG")
        self.assertEqual(config.runs_dir, Path("dir/qwen"))
        self.assertEqual(config.peek_host, "local\\nhost")

    def test_braced_default_applies_and_a_name_without_equals_is_ignored(self):
        """``${NAME:-15}`` applies, and a name with no ``=`` is ignored."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.env"
            path.write_text(
                "PEEKABOO_MODEL\nPEEKABOO_HTTP_TIMEOUT=${MISSING_TIMEOUT_991:-15}\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("MISSING_TIMEOUT_991", None)
                config = load_config({}, dotenv_path=path)
        self.assertEqual(config.model, "llama3.2")
        self.assertEqual(config.http_timeout_seconds, 15)

    def test_earlier_file_binding_beats_the_process_during_expansion(self):
        """An earlier binding in the file beats the process during expansion."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.env"
            path.write_text(
                "PEEKABOO_DOTENV_PROBE=from-file\n"
                "PEEKABOO_MODEL=${PEEKABOO_DOTENV_PROBE}\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ, {"PEEKABOO_DOTENV_PROBE": "from-process"}, clear=False
            ):
                config = load_config({}, dotenv_path=path)
        self.assertEqual(config.model, "from-file")

    def test_expansion_uses_the_process_environment_not_the_injected_mapping(self):
        """Expansion reads the process environment, not the injected mapping."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.env"
            path.write_text(
                "PEEKABOO_MODEL=${PEEKABOO_DOTENV_PROBE}\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ, {"PEEKABOO_DOTENV_PROBE": "from-process"}, clear=False
            ):
                config = load_config(
                    {"PEEKABOO_DOTENV_PROBE": "from-inject"},
                    dotenv_path=path,
                )
        self.assertEqual(config.model, "from-process")

    def test_later_file_binding_is_not_visible_during_expansion(self):
        """A later binding in the file is not visible during expansion."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.env"
            path.write_text(
                "PEEKABOO_MODEL=${PEEKABOO_DOTENV_PROBE}\n"
                "PEEKABOO_DOTENV_PROBE=from-file\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("PEEKABOO_DOTENV_PROBE", None)
                config = load_config({}, dotenv_path=path)
        self.assertEqual(config.model, "llama3.2")

    def test_leading_utf8_bom_does_not_hide_the_first_name(self):
        """A leading UTF-8 BOM does not hide the first name."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.env"
            path.write_bytes(b"\xef\xbb\xbfPEEKABOO_MODEL=from-dotenv\n")
            config = load_config({}, dotenv_path=path)
        self.assertEqual(config.model, "from-dotenv")
