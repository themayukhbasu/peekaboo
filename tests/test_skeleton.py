# Help text is repeated so the test checks CLI output, not a private constant.
# pylint: disable=duplicate-code
"""Smoke tests for the package skeleton."""

import subprocess
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

from peekaboo.cli import main

_HELP = """\
usage: peekaboo [--help] [--version]
       peekaboo chat MESSAGE
       peekaboo peek

Learning harness. `chat` sends one user message and prints the run path.
`peek` serves a local page of those runs.
"""


class CliTests(unittest.TestCase):
    """Top-level help, version, and an unknown argument."""

    def test_no_args_prints_help(self):
        """No arguments print help and exit 0."""
        stdout = StringIO()
        with redirect_stdout(stdout):
            status = main([])
        self.assertEqual(status, 0)
        self.assertEqual(stdout.getvalue(), _HELP)

    def test_help_flag_prints_help(self):
        """``--help`` prints the same help and exits 0."""
        stdout = StringIO()
        with redirect_stdout(stdout):
            status = main(["--help"])
        self.assertEqual(status, 0)
        self.assertEqual(stdout.getvalue(), _HELP)

    def test_version_prints_package_version(self):
        """``--version`` prints the installed package version."""
        stdout = StringIO()
        with redirect_stdout(stdout):
            status = main(["--version"])
        self.assertEqual(status, 0)
        self.assertEqual(stdout.getvalue(), "peekaboo 0.1.0\n")

    def test_unknown_argument_prints_help_on_stderr(self):
        """An unknown argument prints help on stderr and exits 2."""
        stderr = StringIO()
        with redirect_stderr(stderr):
            status = main(["nope"])
        self.assertEqual(status, 2)
        self.assertEqual(stderr.getvalue(), _HELP)

    def test_console_script_prints_version(self):
        """The installed ``peekaboo`` script prints the package version."""
        completed = subprocess.run(
            ["peekaboo", "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "peekaboo 0.1.0\n")
