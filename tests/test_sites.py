"""Site geometry ownership, transactional switching, identity changes and migration."""
import asyncio
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / "dashboard"), str(REPO / "tools")]
from state import InstallationState
from server import Dashboard
from migrate_sites import migrate_sites
from migrate_project import migrate


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = InstallationState(self.root)
        self.state.seats["2"] = {"id": 2, "name": "Voice", "groups": [], "bound": "node-a", "params": {"gain": .5}}
        self.state.data["positions"] = {"2": [[1, 2], [3, 4]]}
        self.state.save()

    def other_site(self):
        site = self.state.site_document()
        site.update(room={"width": 30, "depth": 20, "units": "m", "origin": [2, 3]},
                    listener={"x": 10, "y": 9, "heading": 90, "range": 4}, positions={"2": [[8, 9]]})
        self.state._write_json(self.state.site_path("Broadwalk"), site)
        return site

    def test_round_trip_and_switch_only_geometry(self):
        before = copy.deepcopy(self.state.durable())
        other = self.other_site()
        self.state.data["positions"]["2"][0] = [5, 6]  # unflushed map edit
        self.state.select_site("Broadwalk")
        self.assertEqual(self.state.positions_for(2), [[8, 9]])
        self.assertEqual(self.state.data["room"], other["room"])
        self.assertEqual(self.state.data["listener"], other["listener"])
        after = self.state.durable(); after["current_site"] = before["current_site"]
        self.assertEqual(before, after)
        self.state.select_site("default")
        self.assertEqual(self.state.positions_for(2), [[5, 6], [3, 4]])
        reloaded = InstallationState(self.root)
        self.assertEqual(reloaded.site_document(), self.state.site_document())
        self.assertNotIn("positions", reloaded.seats["2"])
        self.assertEqual(reloaded.public()["seats"]["2"]["positions"], [[5, 6], [3, 4]])
        stored = json.loads(Path(self.state.path).read_text())
        self.assertNotIn("name", stored)
        self.assertNotIn("room", stored)
        self.assertNotIn("listener", stored)
        self.assertNotIn("positions", stored["seats"]["2"])

    def test_missing_corrupt_or_invalid_site_blocks_startup_without_writes(self):
        path = Path(self.state.site_path())
        for raw in (b"bad json", b'{"room":{}}', json.dumps(dict(self.state.site_document(), positions={"99": []})).encode()):
            path.write_bytes(raw)
            before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
            loaded = InstallationState(self.root)
            self.assertTrue(loaded._load_invalid)
            with self.assertRaises(OSError): loaded.save()
            self.assertEqual({p: p.read_bytes() for p in before}, before)
        path.unlink()
        loaded = InstallationState(self.root)
        self.assertTrue(loaded._load_invalid)
        with self.assertRaises(OSError): loaded.save()
        self.assertFalse(path.exists())

    def test_failed_site_switch_preserves_pointer_files_and_geometry(self):
        self.other_site()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        geometry = self.state.site_document()
        real = self.state._write_json
        def failing(path, data):
            if path == self.state.path and data.get("current_site") == "Broadwalk":
                raise OSError("failure")
            real(path, data)
        with mock.patch.object(self.state, "_write_json", side_effect=failing), self.assertRaises(OSError):
            self.state.select_site("Broadwalk")
        self.assertEqual(self.state.data["current_site"], "default")
        self.assertEqual(self.state.site_document(), geometry)
        self.assertEqual({p: p.read_bytes() for p in before}, before)

    def test_reindex_and_delete_adjust_positions_in_all_sites(self):
        self.other_site()
        seat, error = self.state.reindex_seat(2, 7)
        self.assertIsNone(error)
        self.assertEqual(self.state.positions_for(7), [[1, 2], [3, 4]])
        self.state.select_site("Broadwalk")
        self.assertEqual(self.state.positions_for(7), [[8, 9]])
        self.state.delete_seat(7)
        self.assertEqual(self.state.read_site("default")["positions"], {})
        self.assertEqual(self.state.read_site("Broadwalk")["positions"], {})

    def test_failed_site_replace_rolls_back_project_and_cleans_temporary_file(self):
        self.other_site()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        real_replace = os.replace
        def failing(source, destination):
            if destination == self.state.site_path("Broadwalk"):
                raise OSError("site replace failed")
            return real_replace(source, destination)
        with mock.patch("state.os.replace", side_effect=failing), self.assertRaises(OSError):
            self.state.select_site("Broadwalk")
        self.assertEqual(self.state.data["current_site"], "default")
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}, before)

    def test_bad_other_site_prevents_partial_seat_id_change(self):
        self.other_site()
        bad = Path(self.state.site_path("Broadwalk")); bad.write_text("broken")
        original = Path(self.state.path).read_bytes()
        seat, error = self.state.reindex_seat(2, 7)
        self.assertIsNone(seat)
        self.assertIn("2", self.state.seats)
        self.assertEqual(self.state.positions_for(2), [[1, 2], [3, 4]])
        self.assertEqual(Path(self.state.path).read_bytes(), original)
        self.assertEqual(bad.read_text(), "broken")


class MigrationTests(unittest.TestCase):
    def test_existing_project_and_matching_venues_convert_preserving_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); project = root / "projects/Choir/project.json"
            project.parent.mkdir(parents=True)
            old = {"schema": 1, "name": "Workshop", "room": {"width": 10, "depth": 8},
                   "seats": {"2": {"id": 2, "name": "Voice", "positions": [[1, 2]]}},
                   "groups": {}, "next_group_id": 0, "master": .7}
            original = json.dumps(old); project.write_text(original)
            (root / "current-project").write_text("Choir\n")
            venues = root / "installations"; venues.mkdir()
            matching = dict(old, seats={"2": {"id": 2, "positions": [[7, 8]]}}, master=.1)
            (venues / "Broadwalk.json").write_text(json.dumps(matching))
            (venues / "mismatch.json").write_text(json.dumps(dict(old, seats={"9": {"id": 9}})))
            sources = {p: p.read_bytes() for p in venues.iterdir()}
            created, skipped = migrate_sites(project)
            self.assertEqual(len(created), 2)
            self.assertEqual([p.name for p, reason in skipped], ["mismatch.json"])
            self.assertEqual(project.with_name("project.json.pre-sites").read_text(), original)
            self.assertEqual({p: p.read_bytes() for p in sources}, sources)
            state = InstallationState(root)
            self.assertFalse(state._load_invalid)
            self.assertEqual(state.positions_for(2), [[1, 2]])
            state.select_site("Broadwalk")
            self.assertEqual(state.positions_for(2), [[7, 8]])
            self.assertEqual(state.data["master"], .7)
            self.assertEqual(state.project, "Choir")
            with self.assertRaises(FileExistsError): migrate_sites(project)

    def test_installation_migration_also_writes_sites(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root / "installation.json"
            source.write_text(json.dumps({"schema": 1, "name": "A / Choir", "seats": {"0": {"id": 0, "positions": [[3, 4]]}}}))
            (root / "installations").mkdir()
            (root / "installations/10x8-test.json").write_text(source.read_text())
            migrate(source, root / "host")
            state = InstallationState(root / "host")
            self.assertEqual(state.project, "A-Choir")
            self.assertEqual(state.list_sites(), ["10x8-test", "default"])
            self.assertEqual(state.positions_for(0), [[3, 4]])


class SwitchingWireTests(unittest.IsolatedAsyncioTestCase):
    async def test_switch_replays_bound_assignment_with_selected_positions(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = SimpleNamespace(data_dir=temporary, devices_file=None, listen_port=0, send_port=0,
                osc_target="255.255.255.255", public_url="http://localhost")
            dash = Dashboard(args)
            dash.state.seats["2"] = {"id": 2, "name": "Voice", "groups": [], "bound": "node-a", "params": {}}
            dash.state.ensure("node-a").update(online=True)
            dash.state.data["positions"] = {"2": [[1, 2]]}; dash.state.save()
            other = dash.state.site_document(); other["positions"] = {"2": [[7, 8]]}
            dash.state._write_json(dash.state.site_path("Broadwalk"), other)
            calls = []
            with mock.patch.object(dash.osc, "assign", side_effect=lambda *args: calls.append(args)):
                await dash.handle_ws({"type": "select_site", "data": {"name": "Broadwalk"}})
            self.assertEqual(calls, [("node-a", 2, "Voice", [[7, 8]])])
            dash.osc.close(); await dash.state.close()


if __name__ == "__main__": unittest.main()
