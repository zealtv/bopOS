"""Project switching, folder identity, site creation and host-global registry."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))
from state import InstallationState
from server import Dashboard


class ProjectStorageMenuTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = InstallationState(self.root)
        self.state.ensure_device_alias("node-a")
        self.state.save()

    def test_new_project_is_empty_and_does_not_change_registry_or_selection(self):
        registry = Path(self.state.registry_path).read_bytes()
        empty = self.state.create_project("Plants")
        self.assertEqual(empty.seats, {})
        self.assertEqual(empty.project_patches(), [])
        self.assertIsNone(empty.data["fleet_patch"])
        self.assertFalse(Path(empty.show_path).exists())
        self.assertEqual(empty.list_sites(), ["default"])
        self.assertEqual(Path(self.state.registry_path).read_bytes(), registry)
        self.assertEqual(Path(self.state.current_path).read_text(), "default\n")

    def test_rename_moves_all_project_files_and_updates_only_folder_identity(self):
        Path(self.state.show_path).write_text('{"schema":1,"items":[]}')
        self.state.create_site("Workshop", "default")
        files = {p.relative_to(Path(self.state.path).parent): p.read_bytes()
                 for p in Path(self.state.path).parent.rglob("*") if p.is_file()}
        registry = Path(self.state.registry_path).read_bytes()
        self.state.rename_project("Choir")
        self.assertEqual(self.state.project, "Choir")
        self.assertEqual(Path(self.state.current_path).read_text(), "Choir\n")
        self.assertFalse((self.root / "projects/default").exists())
        self.assertEqual({p.relative_to(Path(self.state.path).parent): p.read_bytes()
                          for p in Path(self.state.path).parent.rglob("*") if p.is_file()}, files)
        self.assertEqual(Path(self.state.registry_path).read_bytes(), registry)
        self.assertNotIn("project_name", self.state.durable())

    def test_names_collisions_and_invalid_target_preserve_files(self):
        self.state.create_project("Plants")
        for name in ("", "../bad", "/absolute", "..", "bad/name", "bad..name", " leading", "trailing ", "bad\\name", "a\nb", "Plants"):
            with self.subTest(name=name):
                before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
                with self.assertRaises((ValueError, OSError)): self.state.create_project(name)
                with self.assertRaises((ValueError, OSError)): self.state.rename_project(name)
                self.assertEqual({p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}, before)
        target = self.root / "projects/Plants/project.json"
        target.write_text("broken JSON")
        with self.assertRaises(OSError): self.state.prepare_project("Plants")
        self.assertEqual(target.read_text(), "broken JSON")

    def test_names_with_spaces_round_trip_as_the_only_identity(self):
        new = self.state.create_project("Kite Choir 2._-")
        self.state.select_project(new)
        self.state.create_site("Northern Broadwalk", "default")
        loaded = InstallationState(self.root)
        self.assertEqual(loaded.project, "Kite Choir 2._-")
        self.assertEqual(loaded.data["current_site"], "Northern Broadwalk")
        self.assertTrue(Path(loaded.site_path()).name == "Northern Broadwalk.json")
        self.assertNotIn("name", loaded.durable())
        self.state.rename_project("The Plants")
        self.assertEqual(InstallationState(self.root).project, "The Plants")
        for selection in (" The Plants\n", "The Plants \n", "A..B\n"):
            Path(self.state.current_path).write_text(selection)
            invalid = InstallationState(self.root)
            self.assertTrue(invalid._load_invalid)
            with self.assertRaises(OSError): invalid.save()

    def test_rename_rolls_back_when_selection_write_fails(self):
        with mock.patch.object(self.state, "write_current_project", side_effect=OSError("failure")):
            with self.assertRaises(OSError): self.state.rename_project("Choir")
        self.assertEqual(self.state.project, "default")
        self.assertTrue(Path(self.state.path).exists())
        self.assertFalse((self.root / "projects/Choir").exists())

    def test_site_copy_includes_unflushed_edits_and_empty_has_no_positions(self):
        self.state.seats["1"] = {"id":1,"name":"Voice","bound":None,"groups":[],"params":{}}
        self.state.data["positions"] = {"1":[[2,3]]}
        source = copy.deepcopy(self.state.site_document())
        self.state.create_site("Copy", "default")
        self.assertEqual(self.state.site_document(), source)
        self.state.create_site("Empty")
        self.assertEqual(self.state.positions_for(1), [])
        self.assertEqual(self.state.data["room"], self.state.DEFAULT_ROOM)
        self.assertEqual(self.state.read_site("Copy"), source)
        with self.assertRaises(OSError): self.state.create_site("Copy")


class SwitchingTests(unittest.IsolatedAsyncioTestCase):
    async def test_switch_replays_new_fleet_and_unassigns_only_online_outsiders(self):
        with tempfile.TemporaryDirectory() as root:
            args = SimpleNamespace(data_dir=root, devices_file=None, listen_port=0, send_port=0,
                osc_target="127.0.0.1", public_url="http://localhost", patches_dir=root+"/patches",assets_dir=root+"/assets")
            dash = Dashboard(args)
            for uid, online in (("kept",True),("outside",True),("offline",False)):
                dash.state.ensure(uid).update(online=online)
                dash.state.ensure_device_alias(uid)
            dash.state.save()
            new = dash.state.create_project("Plants")
            new.seats["8"] = {"id":8,"name":"Leaf","bound":"kept","groups":[],"params":{}}
            new.data["positions"] = {"8":[[7,8]]}
            new.save()
            registry = Path(dash.state.registry_path).read_bytes()
            with mock.patch.object(dash.osc,"uid_command") as unassign, mock.patch.object(dash.osc,"assign") as assign, mock.patch.object(dash.show_engine,"stop_all_steps",new_callable=mock.AsyncMock) as stop:
                await dash.open_project("Plants")
                unassign.assert_called_once_with("outside","unassign")
                assign.assert_called_once_with("kept",8,"Leaf",[[7,8]])
                stop.assert_awaited_once()
            self.assertEqual(dash.state.project,"Plants")
            self.assertEqual(Path(dash.state.current_path).read_text(),"Plants\n")
            self.assertEqual(Path(dash.state.registry_path).read_bytes(),registry)
            self.assertEqual(set(dash.state.devices),{"kept","outside","offline"})
            for mode in ("simulate","edit"):
                dash.state.data["supervisor"]["mode"] = mode
                with self.assertRaises(ValueError): await dash.open_project("default")
            dash.osc.close()


if __name__ == "__main__": unittest.main()
