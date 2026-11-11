"""``read_file`` path confinement and truncation.

The character cap comes from ``load_config``. ``read_file_max_chars``
is already a spec field; these tests do not add it.
"""

import tempfile
import unittest
from pathlib import Path

from peekaboo.config import env_name, load_config
from peekaboo.tools.read_file import read_file


class ReadFileTests(unittest.TestCase):
    def test_path_and_truncation(self):
        """Missing, escaped, and long paths are strings. The cap comes from config."""
        loaded = load_config({env_name.read_file_max_chars: "4"})
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            outside = parent / "outside.txt"
            outside.write_text("secret", encoding="utf-8")
            root = parent / "workspace"
            root.mkdir()
            (root / "a.txt").write_text("abcdef", encoding="utf-8")
            (root / "bad.txt").write_bytes(b"\xff")
            (root / "link.txt").symlink_to(outside)
            self.assertEqual(
                read_file({"path": "a.txt"}, workspace=root, max_chars=100),
                "abcdef",
            )
            self.assertEqual(
                read_file(
                    {"path": "a.txt"},
                    workspace=root,
                    max_chars=loaded.read_file_max_chars,
                ),
                "abcd\n[truncated]",
            )
            self.assertIn(
                "not found",
                read_file({"path": "missing.txt"}, workspace=root, max_chars=100),
            )
            self.assertIn(
                "outside",
                read_file({"path": "../outside.txt"}, workspace=root, max_chars=100),
            )
            self.assertIn(
                "outside",
                read_file({"path": str(outside)}, workspace=root, max_chars=100),
            )
            self.assertIn(
                "outside",
                read_file({"path": "link.txt"}, workspace=root, max_chars=100),
            )
            self.assertIn(
                "not a file",
                read_file({"path": "."}, workspace=root, max_chars=100),
            )
            self.assertIn(
                "UTF-8",
                read_file({"path": "bad.txt"}, workspace=root, max_chars=100),
            )
            self.assertEqual(
                read_file({}, workspace=root, max_chars=100),
                "read_file needs a string path.",
            )
