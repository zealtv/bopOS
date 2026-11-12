"""Persistence writes keep valid store keys independent."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

import store  # noqa: E402


class StoreTests(unittest.TestCase):
    def test_suffix_keys_survive_writes_to_other_keys(self):
        with tempfile.TemporaryDirectory() as root:
            state = store.Store(root)
            self.assertTrue(state.put("assignment.tmp", ["precious"]))
            self.assertTrue(state.put("assignment", [7]))
            self.assertEqual(state.get("assignment.tmp"), ["precious"])
            self.assertEqual(state.get("assignment"), [7])
            self.assertEqual(sorted(path.name for path in Path(root).iterdir()),
                             ["assignment", "assignment.tmp"])

    def test_failed_replace_preserves_keys_and_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as root:
            state = store.Store(root)
            self.assertTrue(state.put("assignment", [7]))
            self.assertTrue(state.put("assignment.tmp", ["precious"]))
            with mock.patch.object(store.os, "replace", side_effect=OSError("failed")):
                self.assertFalse(state.put("assignment", [8]))
            self.assertEqual(state.get("assignment"), [7])
            self.assertEqual(state.get("assignment.tmp"), ["precious"])
            self.assertEqual(sorted(path.name for path in Path(root).iterdir()),
                             ["assignment", "assignment.tmp"])


if __name__ == "__main__":
    unittest.main()
