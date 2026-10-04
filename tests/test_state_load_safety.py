"""A failed installation/venue load must never destroy its source file."""
import asyncio
import ast
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))
from state import InstallationState


def document():
    return {"schema": 1, "name": "Room", "groups": {"0": {"id": 0, "name": "Front"}},
            "next_group_id": 1, "device_registry": {}, "seats": {
                "2": {"id": 2, "name": "Seat 2", "positions": [[1, 2]],
                      "groups": [0], "bound": "node-a", "params": {"gain": .4}}}}


def invalid_documents():
    yield b'{"schema":'
    yield b'\xff'
    for key, value in (("schema", 99), ("seats", []), ("groups", []),
                       ("next_group_id", 0), ("device_registry", [])):
        doc = document()
        doc[key] = value
        yield json.dumps(doc).encode()
    for key, value in (("groups", [9]), ("positions", [["bad", 2]]), ("bound", 4)):
        doc = document()
        doc["seats"]["2"][key] = value
        yield json.dumps(doc).encode()


class StateLoadSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "installation.json"

    def test_invalid_files_preserved_after_ordinary_and_venue_saves(self):
        for original in invalid_documents():
            with self.subTest(original=original):
                self.path.write_bytes(original)
                state = InstallationState(str(self.path))
                self.assertTrue(state.public()["notices"])
                self.assertIn("original file is preserved", state.public()["notices"][0])
                state.data["master"] = .5
                state.ensure_device_alias("new-node")
                with self.assertRaises(OSError):
                    state.save()
                with self.assertRaises(OSError):
                    state.save_venue("empty")
                self.assertEqual(self.path.read_bytes(), original)
                self.assertFalse(Path(str(self.path) + ".tmp").exists())
                self.assertFalse((self.root / "installations/empty.json").exists())

    def test_unreadable_file_blocks_later_writes(self):
        original = json.dumps(document()).encode()
        self.path.write_bytes(original)
        with mock.patch("builtins.open", side_effect=PermissionError("unreadable")):
            state = InstallationState(str(self.path))
        with self.assertRaises(OSError):
            state.save()
        self.assertEqual(self.path.read_bytes(), original)
        self.assertTrue(state.public()["notices"])

    def test_dangling_symlink_is_not_treated_as_a_new_installation(self):
        self.path.symlink_to("missing-state.json")
        state = InstallationState(str(self.path))
        with self.assertRaises(OSError):
            state.save()
        self.assertTrue(self.path.is_symlink())
        self.assertTrue(state.public()["notices"])

    def test_failed_load_does_not_import_seed(self):
        self.path.write_bytes(b"bad json")
        seed = self.root / "devices.csv"
        seed.write_text("uid,name,id\nnode-a,First,0\n")
        state = InstallationState(str(self.path), str(seed))
        self.assertEqual(state.seats, {})
        self.assertEqual(self.path.read_bytes(), b"bad json")

    def test_dangling_group_is_rejected_without_silently_dropping_membership(self):
        doc = document()
        doc["seats"]["2"]["groups"] = [0, 9]
        original = json.dumps(doc).encode()
        self.path.write_bytes(original)
        state = InstallationState(str(self.path))
        self.assertTrue(state._load_invalid)
        with self.assertRaises(OSError):
            state.save()
        self.assertEqual(self.path.read_bytes(), original)
        self.assertIn("Repair the file", state.public()["notices"][0])

    def test_invalid_venue_preserves_current_state_and_cannot_be_overwritten(self):
        self.path.write_text(json.dumps(document()))
        state = InstallationState(str(self.path))
        before = copy.deepcopy(state.durable())
        original = b'{"schema":1,"seats":{"2":{"id":2,"groups":[99]}}}'
        venue = Path(state.venues_dir()) / "broken.json"
        venue.write_bytes(original)
        self.assertFalse(state.load_venue("broken"))
        self.assertEqual(state.durable(), before)
        self.assertEqual(venue.read_bytes(), original)
        with self.assertRaises(OSError):
            state.save_venue("broken")
        self.assertEqual(venue.read_bytes(), original)
        self.assertEqual(len(state.public()["notices"]), 1)
        state.save()
        self.assertEqual(InstallationState(str(self.path)).durable(), before)

    def test_name_adoption_cannot_rewrite_an_otherwise_invalid_file(self):
        doc = document()
        doc["groups"]["0"]["name"] = ""
        doc["seats"]["2"]["groups"] = [99]
        original = json.dumps(doc).encode()
        self.path.write_bytes(original)
        state = InstallationState(str(self.path))
        self.assertEqual(self.path.read_bytes(), original)
        venue = Path(state.venues_dir()) / "broken.json"
        venue.write_bytes(original)
        self.assertEqual(state.read_venue("broken"), (None, None))
        self.assertEqual(venue.read_bytes(), original)

    def test_retired_patch_fields_are_stripped_on_load_and_save(self):
        doc = document()
        doc["params_patch"] = "obsolete"
        doc["fleet_patch"] = {"name": "alpha", "fingerprint": "a" * 64,
                              "staged_at": 1,
                              "previous": {"name": "obsolete"}}
        self.path.write_text(json.dumps(doc))
        state = InstallationState(str(self.path))
        self.assertNotIn("params_patch", state.public())
        self.assertNotIn("previous", state.data["fleet_patch"])
        state.save()
        saved = json.loads(self.path.read_text())
        self.assertNotIn("params_patch", saved)
        self.assertNotIn("previous", saved["fleet_patch"])
        venue = Path(state.venues_dir()) / "legacy.json"
        venue.write_text(json.dumps(doc))
        self.assertTrue(state.load_venue("legacy"))
        self.assertNotIn("params_patch", state.public())
        self.assertNotIn("previous", state.data["fleet_patch"])


    def test_parameter_reconciliation_uses_the_fleet_patch_name(self):
        self.path.write_text(json.dumps(document()))
        state = InstallationState(str(self.path))
        state.stage_fleet_patch("alpha", "a" * 64)
        state.reconcile_fleet_params("alpha", ["gain", "new"],
                                     {"gain": .1, "new": .2})
        self.assertEqual(state.seats["2"]["params"], {"gain": .4, "new": .2})
        state.reconcile_fleet_params("beta", ["gain"], {"gain": .1})
        state.stage_fleet_patch("beta", "b" * 64)
        self.assertEqual(state.seats["2"]["params"], {"gain": .1})
        self.assertNotIn("previous", state.data["fleet_patch"])

    def test_new_and_valid_installations_still_save_and_reload(self):
        state = InstallationState(str(self.path))
        state.save()
        self.assertEqual(state.public()["notices"], [])
        self.path.write_text(json.dumps(document()))
        state = InstallationState(str(self.path))
        state.data["master"] = .25
        state.save_venue("valid")
        self.assertTrue(state.load_venue("valid"))
        self.assertEqual(InstallationState(str(self.path)).data["master"], .25)
        self.assertEqual(state.public()["notices"], [])


class DebouncedLoadSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_debounce_and_shutdown_preserve_invalid_file_without_task_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "installation.json"
            original = b"broken json"
            path.write_bytes(original)
            state = InstallationState(str(path))
            state.data["master"] = .5
            state.save_debounced()
            await asyncio.sleep(0)
            await state.close()
            self.assertIsNone(state._save_task)
            self.assertEqual(path.read_bytes(), original)


class SaveGuardTests(unittest.TestCase):
    def test_dashboard_state_saves_have_an_oserror_guard(self):
        source = Path(__file__).resolve().parents[1] / "dashboard" / "server.py"
        tree = ast.parse(source.read_text())
        parents = {child: node for node in ast.walk(tree)
                   for child in ast.iter_child_nodes(node)}
        unguarded = []
        for call in ast.walk(tree):
            if not (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "save"
                    and isinstance(call.func.value, ast.Attribute)
                    and call.func.value.attr == "state"
                    and isinstance(call.func.value.value, ast.Name)
                    and call.func.value.value.id == "self"):
                continue
            child = call
            while child in parents:
                parent = parents[child]
                if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    unguarded.append(call.lineno)
                    break
                if isinstance(parent, ast.Try) and child in parent.body:
                    if any(handler.type is None or any(
                            isinstance(node, ast.Name)
                            and node.id in {"OSError", "Exception", "BaseException"}
                            for node in ast.walk(handler.type))
                           for handler in parent.handlers):
                        break
                child = parent
        self.assertEqual(unguarded, [], f"unguarded state.save() lines: {unguarded}")


if __name__ == "__main__":
    unittest.main()
