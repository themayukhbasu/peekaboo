"""Console entrypoint.

``peekaboo chat`` sends one user message and prints the run path.
``peekaboo agent`` sends one user message with ``read_file``.
``peekaboo peek`` serves the local run viewer.
``--help`` and ``--version`` stay on the top-level command.
"""

import sys
from collections.abc import Sequence
from importlib.metadata import version

from peekaboo.config import Config, ConfigError, load_config
from peekaboo.peek import bind
from peekaboo.run import Transport, run
from peekaboo.tools.read_file import read_file

_HELP = """\
usage: peekaboo [--help] [--version]
       peekaboo chat MESSAGE
       peekaboo agent MESSAGE
       peekaboo peek

Learning harness. `chat` sends one user message and prints the run path.
`agent` sends one user message, may call read_file, and prints the run path.
`peek` serves a local page of those runs.
"""

_CHAT_HELP = """\
usage: peekaboo chat MESSAGE

Send one user message, with no tools and no system message.
Prints the run file path.
"""

_AGENT_HELP = """\
usage: peekaboo agent MESSAGE

Send one user message. The model may call read_file in the working directory.
Prints the run file path.
"""

_PEEK_HELP = """\
usage: peekaboo peek

Serve a local page of run files. The default address is
http://127.0.0.1:8765. Stops on Ctrl-C. Does not open a browser.
"""


def main(
    argv: Sequence[str] | None = None,
    *,
    config: Config | None = None,
    transport: Transport | None = None,
) -> int:
    """Run the command. Returns a process status code.

    ``config`` and ``transport`` replace the defaults for tests.
    Omit them to load settings and, for chat and agent, call Ollama.
    ``peek`` does not use ``transport``.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args in ([], ["--help"], ["-h"]):
        sys.stdout.write(_HELP)
        return 0
    if args == ["--version"]:
        sys.stdout.write(f"peekaboo {version('peekaboo')}\n")
        return 0
    if args[:1] == ["chat"]:
        return _command(
            args[1:],
            tools=[],
            usage=_CHAT_HELP,
            config=config,
            transport=transport,
        )
    if args[:1] == ["agent"]:
        return _command(
            args[1:],
            tools=[read_file],
            usage=_AGENT_HELP,
            config=config,
            transport=transport,
        )
    if args[:1] == ["peek"]:
        return _peek(args[1:], config=config)
    sys.stderr.write(_HELP)
    return 2


def _command(
    args: list[str],
    *,
    tools: Sequence[object],
    usage: str,
    config: Config | None,
    transport: Transport | None,
) -> int:
    """Run one one-shot command and return a process status code.

    Help and a blank message do not call the provider. Otherwise one
    user message is sent and the run path is printed.
    """
    if args in (["--help"], ["-h"]):
        sys.stdout.write(usage)
        return 0
    message = " ".join(args).strip()
    if message == "":
        sys.stderr.write(usage)
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
            tools,
            config=config,
            transport=transport,
        )
    except (ValueError, OSError) as error:
        sys.stderr.write(f"{error}\n")
        return 1
    sys.stdout.write(f"{path}\n")
    return 0


def _peek(args: list[str], *, config: Config | None) -> int:
    """Serve the peek until Ctrl-C and return a process status code.

    Help does not bind a socket. Otherwise the process listens until
    it is interrupted.
    """
    if args in (["--help"], ["-h"]):
        sys.stdout.write(_PEEK_HELP)
        return 0
    if args:
        sys.stderr.write(_PEEK_HELP)
        return 2
    if config is None:
        try:
            config = load_config()
        except ConfigError as error:
            sys.stderr.write(f"{error}\n")
            return 2
    try:
        bind(config).serve_forever()
    except KeyboardInterrupt:
        return 0
    except OSError as error:
        sys.stderr.write(f"{error}\n")
        return 1
    return 0
