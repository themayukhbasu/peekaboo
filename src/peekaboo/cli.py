"""Console entrypoint.

``peekaboo chat`` sends one user message and prints the run path.
``--help`` and ``--version`` stay on the top-level command.
"""

import sys
from collections.abc import Sequence
from importlib.metadata import version

from peekaboo.config import Config, ConfigError, load_config
from peekaboo.run import Transport, run

_HELP = """\
usage: peekaboo [--help] [--version]
       peekaboo chat MESSAGE

Learning harness. `chat` sends one user message and prints the run path.
"""

_CHAT_HELP = """\
usage: peekaboo chat MESSAGE

Send one user message, with no tools and no system message.
Prints the run file path.
"""


def main(
    argv: Sequence[str] | None = None,
    *,
    config: Config | None = None,
    transport: Transport | None = None,
) -> int:
    """Run the command. Returns a process status code.

    ``config`` and ``transport`` replace the defaults for tests.
    Omit them to load settings and call Ollama.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args in ([], ["--help"], ["-h"]):
        sys.stdout.write(_HELP)
        return 0
    if args == ["--version"]:
        sys.stdout.write(f"peekaboo {version('peekaboo')}\n")
        return 0
    if args[:1] == ["chat"]:
        return _chat(args[1:], config=config, transport=transport)
    sys.stderr.write(_HELP)
    return 2


def _chat(
    args: list[str],
    *,
    config: Config | None,
    transport: Transport | None,
) -> int:
    if args in (["--help"], ["-h"]):
        sys.stdout.write(_CHAT_HELP)
        return 0
    message = " ".join(args).strip()
    if message == "":
        sys.stderr.write(_CHAT_HELP)
        return 2
    if config is None:
        try:
            config = load_config()
        except ConfigError as error:
            sys.stderr.write(f"{error}\n")
            return 2
    try:
        path = run(
            [{"role": "user", "content": message}],
            [],
            config=config,
            transport=transport,
        )
    except (ValueError, OSError) as error:
        sys.stderr.write(f"{error}\n")
        return 1
    sys.stdout.write(f"{path}\n")
    return 0
