"""``RunLog`` appends and the one-event ``write_turn`` path."""

import tempfile
import unittest
from pathlib import Path

from peekaboo.runs import RunLog, write_turn

_STAMP = r"^\d{8}T\d{12}Z\.jsonl$"


class RunLogTests(unittest.TestCase):
    def test_later_appends_stay_in_the_first_file(self):
        """The first append creates one stamped file. Later lines join it."""
        with tempfile.TemporaryDirectory() as directory:
            runs = Path(directory)
            log = RunLog(runs)
            first = log.append({"n": 1})
            second = log.append({"n": 2})
            self.assertEqual(first, second)
            self.assertEqual(first.parent, runs)
            self.assertRegex(first.name, _STAMP)
            self.assertEqual(list(runs.iterdir()), [first])
            self.assertEqual(
                first.read_text(encoding="utf-8"),
                '{"n": 1}\n{"n": 2}\n',
            )

    def test_write_turn_creates_a_new_file_per_call(self):
        """Each ``write_turn`` call exclusive-creates its own file."""
        with tempfile.TemporaryDirectory() as directory:
            runs = Path(directory)
            one = write_turn(runs, {"n": 1})
            two = write_turn(runs, {"n": 2})
            self.assertNotEqual(one, two)
            self.assertRegex(one.name, _STAMP)
            self.assertRegex(two.name, r"^\d{8}T\d{12}Z(?:-\d+)?\.jsonl$")
            self.assertEqual(one.read_text(encoding="utf-8"), '{"n": 1}\n')
            self.assertEqual(two.read_text(encoding="utf-8"), '{"n": 2}\n')
            self.assertEqual(set(runs.iterdir()), {one, two})
