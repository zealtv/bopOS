"""Project and host registry persistence, plus the one-off migration."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "dashboard"))
sys.path.insert(0, str(REPO / "tools"))
from state import InstallationState
from migrate_project import migrate


class ProjectStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_new_project_round_trip_and_host_registry_survives_other_project(self):
        state = InstallationState(self.root)
        state.data.update(name="Workshop", master=.7, event_lead_ms=250,
                          facilitator_commands=["reboot"], current_show="opening")
        state.ensure_device_alias("node-a")
        state.save()
        doc = json.loads(Path(state.path).read_text())
        self.assertNotIn("device_registry", doc)
        self.assertEqual((self.root / "current-project").read_text(), "default\n")
        reloaded = InstallationState(self.root)
        self.assertEqual(reloaded.durable(), state.durable())
        self.assertEqual(reloaded.device_registry, state.device_registry)
        other = self.root / "projects" / "other" / "project.json"
        other.parent.mkdir()
        other.write_text(json.dumps({"schema": 1, "name": "Other", "seats": {}}))
        (self.root / "current-project").write_text("other\n")
        opened = InstallationState(self.root)
        self.assertEqual(opened.data["name"], "Other")
        self.assertEqual(opened.device_registry, state.device_registry)
        self.assertEqual(json.loads(Path(state.path).read_text()), doc)

    def test_invalid_selection_and_registry_preserve_all_sources(self):
        state = InstallationState(self.root)
        state.save()
        marker = self.root / "current-project"
        marker.write_text("../outside\n")
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        broken = InstallationState(self.root)
        with self.assertRaises(OSError):
            broken.save()
        self.assertEqual({p: p.read_bytes() for p in before}, before)
        marker.write_text("default\n")
        registry = self.root / "devices.json"
        registry.write_text("broken JSON")
        broken = InstallationState(self.root)
        with self.assertRaises(OSError):
            broken.save()
        self.assertEqual(registry.read_text(), "broken JSON")

    def test_missing_selection_opens_default_even_with_other_projects(self):
        state = InstallationState(self.root)
        state.data["name"] = "Workshop"
        state.save()
        marker = self.root / "current-project"
        marker.unlink()
        other = self.root / "projects" / "other" / "project.json"
        other.parent.mkdir()
        other.write_text(json.dumps({"schema": 1, "name": "Other", "seats": {}}))
        original = other.read_bytes()
        opened = InstallationState(self.root)
        self.assertFalse(opened._load_invalid)
        self.assertEqual(opened.project, "default")
        self.assertEqual(opened.data["name"], "Workshop")
        opened.save()
        self.assertEqual(marker.read_text(), "default\n")
        self.assertEqual(other.read_bytes(), original)

    def test_existing_unreadable_selection_blocks_saves(self):
        state = InstallationState(self.root)
        state.save()
        marker = self.root / "current-project"
        with mock.patch("builtins.open", side_effect=PermissionError("unreadable")):
            opened = InstallationState(self.root)
        self.assertTrue(opened._load_invalid)
        with self.assertRaises(OSError):
            opened.save()
        self.assertEqual(marker.read_text(), "default\n")

    def test_migration_preserves_source_and_refuses_existing_destinations(self):
        source = self.root / "installation.json"
        original = json.dumps({"schema": 1, "name": "Kite Choir", "seats": {
            "0": {"id": 0, "name": "Voice", "bound": "node-a",
                  "positions": [[1, 2]], "params": {"gain": .4}}},
            "fleet_patch": {"name": "kite-v1", "previous": {"name": "old"}},
            "params_patch": "old", "current_show": "opening",
            "device_registry": {"node-a": {
                "alias": "Finn Jet", "source": "custom", "generator": 2,
                "device_enabled": False, "desired_patch": {"name": "old"}}}})
        source.write_text(original)
        output = self.root / "host"
        paths = migrate(source, output)
        state = InstallationState(output)
        self.assertEqual(source.read_text(), original)
        self.assertEqual(state.project, "Kite-Choir")
        self.assertEqual(state.public()["project"], "Kite-Choir")
        self.assertNotIn("project", state.durable())
        self.assertNotIn("project_name", state.durable())
        self.assertEqual(state.seats["0"]["positions"], [[1, 2]])
        self.assertEqual(state.seats["0"]["params"], {"gain": .4})
        self.assertFalse(state.device_registry["node-a"]["device_enabled"])
        self.assertNotIn("desired_patch", state.device_registry["node-a"])
        self.assertNotIn("params_patch", state.durable())
        self.assertNotIn("previous", state.data["fleet_patch"])
        before = [p.read_bytes() for p in paths]
        with self.assertRaises(FileExistsError):
            migrate(source, output)
        self.assertEqual([p.read_bytes() for p in paths], before)
        self.assertEqual(source.read_text(), original)

    def test_venue_load_changes_site_label_without_changing_project_identity(self):
        state = InstallationState(self.root)
        state.data["name"] = "Workshop"
        state.save()
        state.save_venue("Broadwalk")
        self.assertTrue(state.load_venue("Broadwalk"))
        self.assertEqual(state.public()["name"], "Broadwalk")
        self.assertEqual(state.public()["project"], "default")
        self.assertEqual((self.root / "current-project").read_text(), "default\n")
        self.assertEqual(InstallationState(self.root).project, "default")

    def test_invalid_migration_creates_no_destination(self):
        source = self.root / "installation.json"
        source.write_text('{"schema":99,"seats":{}}')
        destination = self.root / "host"
        with self.assertRaises(ValueError):
            migrate(source, destination)
        self.assertFalse(destination.exists())

    def test_runtime_paths_are_gitignored(self):
        for path in ("dashboard/projects/demo/project.json", "dashboard/devices.json",
                     "dashboard/current-project"):
            with self.subTest(path=path):
                self.assertEqual(subprocess.run(
                    ["git", "check-ignore", "-q", path], cwd=REPO).returncode, 0)


if __name__ == "__main__":
    unittest.main()
