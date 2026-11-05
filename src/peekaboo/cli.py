"""Placeholder console entrypoint.

Prints help or the package version. Later milestones add subcommands.
"""

import sys
from collections.abc import Sequence
from importlib.metadata import version

_HELP = """\
usage: peekaboo [--help] [--version]

Learning harness. This command prints help or the version.
"""


def main(argv: Sequence[str] | None = None) -> int:
    """Run the placeholder command. Returns a process status code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args in ([], ["--help"], ["-h"]):
        sys.stdout.write(_HELP)
        return 0
    if args == ["--version"]:
        sys.stdout.write(f"peekaboo {version('peekaboo')}\n")
        return 0
    sys.stderr.write(_HELP)
    return 2
