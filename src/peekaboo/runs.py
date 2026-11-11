"""JSONL run files.

``RunLog`` is one file for one run. The first append creates it, and
later appends add one turn event per line. ``write_turn`` is the
one-event case: it still opens a new file.
"""

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

_STAMP = "%Y%m%dT%H%M%S%fZ"


# Append is the whole interface. A second method would not be part of it.
class RunLog:  # pylint: disable=too-few-public-methods
    """One JSONL file. Append once per model call."""

    def __init__(self, runs_dir: Path) -> None:
        """Remember ``runs_dir``. The file is created on the first append."""
        self._runs_dir = runs_dir
        self.path: Path | None = None

    def append(self, event: Mapping[str, object]) -> Path:
        """Append one turn event and return the run path.

        The first call exclusive-creates a UTC-stamped file. Later
        calls append to that same file.
        """
        line = json.dumps(event, ensure_ascii=False) + "\n"
        if self.path is None:
            self.path = _create(self._runs_dir, line)
            return self.path
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
        return self.path


def write_turn(runs_dir: Path, event: dict[str, object]) -> Path:
    """Write one turn event to a new file and return its path.

    A run with several model calls keeps one ``RunLog`` and appends.
    This helper opens a new file for a single event.
    """
    return RunLog(runs_dir).append(event)


def _create(runs_dir: Path, line: str) -> Path:
    """Exclusive-create a stamped file containing ``line``."""
    runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime(_STAMP)
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
