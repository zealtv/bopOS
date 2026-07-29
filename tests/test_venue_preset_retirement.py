#!/usr/bin/env python3
"""Living regressions for retiring installation-scoped venue presets."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "dashboard"))

from state import InstallationState  # noqa: E402


def legacy_document():
    return {
        "schema": 1,
        "name": "Legacy venue",
        "groups": {},
        "next_group_id": 0,
        "seats": {
            "2": {
                "id": 2,
                "name": "Seat 2",
                "positions": [[1, 2]],
                "params": {"gain": 0.25},
                "groups": [],
                "bound": None,
            },
        },
        "presets": {
            "morning": {
                "master": 0.5,
                "seats": {"2": {"gain": 0.25}},
            },
        },
    }


class VenuePresetRetirementTests(unittest.TestCase):
    def test_legacy_installation_loads_and_drops_presets_on_save(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "installation.json"
            path.write_text(json.dumps(legacy_document()), encoding="utf-8")

            state = InstallationState(str(path))

            self.assertNotIn("presets", state.public())
            self.assertNotIn("presets", state.durable())
            state.save()
            self.assertNotIn(
                "presets", json.loads(path.read_text(encoding="utf-8")))

    def test_seat_reindex_and_delete_ignore_retired_preset_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "installation.json"
            path.write_text(json.dumps(legacy_document()), encoding="utf-8")
            state = InstallationState(str(path))

            seat, error = state.reindex_seat(2, 5)
            self.assertIsNone(error)
            self.assertEqual(seat["id"], 5)
            self.assertEqual(state.delete_seat(5)["id"], 5)
            self.assertEqual(state.seats, {})

    def test_legacy_venue_snapshot_loads_without_propagating_presets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = InstallationState(str(root / "installation.json"))
            venues = root / "installations"
            venues.mkdir()
            venue_path = venues / "legacy.json"
            venue_path.write_text(
                json.dumps(legacy_document()), encoding="utf-8")

            loaded, seats = state.read_venue("legacy")

            self.assertNotIn("presets", loaded)
            self.assertTrue(state.load_venue("legacy", (loaded, seats)))
            self.assertNotIn("presets", state.public())
            state.save_venue("legacy")
            self.assertNotIn(
                "presets", json.loads(venue_path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
