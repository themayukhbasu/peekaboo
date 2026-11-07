"""JSONL run files.

``write_turn`` writes one turn event as a single line under a runs
directory and returns the new file path.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_STAMP = "%Y%m%dT%H%M%S%fZ"


def write_turn(runs_dir: Path, event: dict[str, object]) -> Path:
    """Write one turn event and return the JSONL path.

    ``runs_dir`` is created when it is missing. The name is a UTC
    timestamp. A name that already exists gets a numeric suffix.
    """
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
