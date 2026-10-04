#!/usr/bin/env python3
from project_fixture import project_path, data_root
"""Unknown legacy fields do not enter current installation or venue state."""

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
        "obsolete_field": {
            "morning": {
                "master": 0.5,
                "seats": {"2": {"gain": 0.25}},
            },
        },
    }


class VenueUnknownFieldRetirementTests(unittest.TestCase):
    def test_legacy_installation_loads_and_drops_obsolete_field_on_save(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = project_path(temporary)
            path.write_text(json.dumps(legacy_document()), encoding="utf-8")

            state = InstallationState(data_root(str(path)))

            self.assertNotIn("obsolete_field", state.public())
            self.assertNotIn("obsolete_field", state.durable())
            state.save()
            self.assertNotIn(
                "obsolete_field", json.loads(path.read_text(encoding="utf-8")))

    def test_seat_reindex_and_delete_ignore_retired_unknown_field_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = project_path(temporary)
            path.write_text(json.dumps(legacy_document()), encoding="utf-8")
            state = InstallationState(data_root(str(path)))

            seat, error = state.reindex_seat(2, 5)
            self.assertIsNone(error)
            self.assertEqual(seat["id"], 5)
            self.assertEqual(state.delete_seat(5)["id"], 5)
            self.assertEqual(state.seats, {})

    def test_legacy_venue_snapshot_loads_without_propagating_obsolete_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = InstallationState(data_root(str(project_path(root))))
            venues = root / "installations"
            venues.mkdir()
            venue_path = venues / "legacy.json"
            venue_path.write_text(
                json.dumps(legacy_document()), encoding="utf-8")

            loaded, seats = state.read_venue("legacy")

            self.assertNotIn("obsolete_field", loaded)
            self.assertTrue(state.load_venue("legacy", (loaded, seats)))
            self.assertNotIn("obsolete_field", state.public())
            state.save_venue("legacy")
            self.assertNotIn(
                "obsolete_field", json.loads(venue_path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
