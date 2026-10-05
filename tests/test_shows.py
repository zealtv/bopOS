"""A project's several shows: storage, migration, and the menu's show actions."""
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
from migrate_shows import migrate_shows
import show_model


STEP = {"kind": "step", "uid": "0000000a", "alias": "Opening", "duration_s": 4,
        "play_count": 1, "then_actions": [], "messages": []}


def files(root):
    return {path: path.read_bytes() for path in Path(root).rglob("*") if path.is_file()}


class ShowStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = InstallationState(self.root)
        self.state.save()
        show_model.save_show(self.state.show_path, dict(show_model.empty_show("Show"), items=[STEP]))

    def test_new_shows_are_empty_or_copies_and_become_current(self):
        self.state.create_show("Second Half", "Show")
        self.assertEqual(self.state.data["current_show"], "Second Half")
        self.assertEqual(self.state.show_path, str(self.root / "projects/default/shows/Second Half.json"))
        source = show_model.load_show(self.state.show_file("Show"))[0]
        self.assertEqual(json.loads(Path(self.state.show_path).read_text()),
                         dict(source, name="Second Half"))
        self.state.create_show("Rehearsal")
        self.assertEqual(json.loads(Path(self.state.show_path).read_text()),
                         show_model.empty_show("Rehearsal"))
        self.assertEqual(self.state.list_shows(), ["Rehearsal", "Second Half", "Show"])
        reloaded = InstallationState(self.root)
        self.assertEqual(reloaded.data["current_show"], "Rehearsal")
        self.assertEqual(json.loads(Path(reloaded.path).read_text())["current_show"], "Rehearsal")
        self.assertEqual(reloaded.public()["shows"], ["Rehearsal", "Second Half", "Show"])
        self.assertEqual(reloaded.public()["current_show"], "Rehearsal")

    def test_step_counts_skip_dividers_and_mark_unreadable_shows(self):
        divider = {"kind": "divider", "uid": "0000000b", "alias": None}
        show_model.save_show(self.state.show_path, dict(show_model.empty_show("Show"), items=[STEP, divider]))
        self.state.create_show("Empty")
        os.remove(self.state.show_path)
        (Path(self.state.shows_dir()) / "Broken.json").write_text("broken JSON")
        self.assertEqual(self.state.public()["show_steps"], {"Broken": None, "Empty": 0, "Show": 1})

    def test_out_of_range_numbers_mark_only_that_show_unreadable(self):
        bad = dict(STEP, messages=[{"uid": "0000000c", "address": "/x", "target": "all",
                                    "args": [{"type": "i", "value": float("inf")}]}])
        (Path(self.state.shows_dir()) / "Bad.json").write_text(
            json.dumps(dict(show_model.empty_show("Bad"), items=[bad])))
        self.assertEqual(self.state.public()["show_steps"], {"Bad": None, "Show": 1})

    def test_open_show_before_its_first_edit_copies_empty_and_is_listed(self):
        self.state.create_show("Fresh")
        os.remove(self.state.show_path)
        self.assertIn("Fresh", self.state.list_shows())
        self.state.create_show("Copy", "Fresh")
        self.assertEqual(json.loads(Path(self.state.show_path).read_text())["items"], [])

    def test_names_collisions_and_missing_sources_change_nothing(self):
        self.state.create_show("Other")
        self.state.select_show("Show")
        for name in ("", "../bad", "bad/name", "..", " leading", "trailing ", "a\nb", "Other", "Show", None, 3):
            with self.subTest(name=name):
                before = files(self.root)
                with self.assertRaises((ValueError, OSError, TypeError)): self.state.create_show(name)
                if name != "Show":
                    with self.assertRaises((ValueError, OSError, TypeError)): self.state.rename_show(name)
                self.assertEqual(files(self.root), before)
                self.assertEqual(self.state.data["current_show"], "Show")
        before = files(self.root)
        for source in ("Missing", "../default/project"):
            with self.assertRaises((ValueError, OSError)): self.state.create_show("New", source)
        with self.assertRaises(OSError): self.state.select_show("Missing")
        self.assertEqual(files(self.root), before)

    def test_rename_moves_the_file_and_rolls_back_a_failed_pointer_write(self):
        original = Path(self.state.show_path).read_bytes()
        self.state.rename_show("Opening Night")
        self.assertFalse((self.root / "projects/default/shows/Show.json").exists())
        self.assertEqual(Path(self.state.show_path).read_bytes(), original)
        self.assertEqual(InstallationState(self.root).data["current_show"], "Opening Night")
        before = files(self.root)
        with mock.patch.object(self.state, "save", side_effect=OSError("disk")):
            with self.assertRaises(OSError): self.state.rename_show("Closing")
            with self.assertRaises(OSError): self.state.create_show("Closing")
        self.assertEqual(files(self.root), before)
        self.assertEqual(self.state.data["current_show"], "Opening Night")

    def test_delete_takes_only_other_shows(self):
        self.state.create_show("Other")
        with self.assertRaises(ValueError): self.state.delete_show("Other")
        self.state.select_show("Show")
        self.state.delete_show("Other")
        self.assertEqual(self.state.list_shows(), ["Show"])
        for name in ("Other", "Show", "../default/project"):
            with self.assertRaises((ValueError, OSError)): self.state.delete_show(name)
        self.assertTrue(Path(self.state.show_path).exists())

    def test_invalid_current_show_blocks_the_project(self):
        doc = json.loads(Path(self.state.path).read_text())
        Path(self.state.path).write_text(json.dumps(dict(doc, current_show="../x")))
        self.assertTrue(InstallationState(self.root)._load_invalid)

    def test_project_rename_carries_its_shows(self):
        self.state.create_show("Other", "Show")
        self.state.rename_project("Choir")
        self.assertEqual(self.state.show_path, str(self.root / "projects/Choir/shows/Other.json"))
        self.assertEqual(self.state.list_shows(), ["Other", "Show"])


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        InstallationState(self.root).save()
        self.project = self.root / "projects/default/project.json"
        doc = json.loads(self.project.read_text())
        del doc["current_show"]
        self.project.write_text(json.dumps(doc))
        self.legacy = self.project.with_name("show.json")

    def test_unmigrated_show_loads_read_only_and_refuses_show_actions(self):
        body = json.dumps({"schema": 1, "name": "Kite", "items": [STEP]}).encode()
        self.legacy.write_bytes(body)
        state = InstallationState(self.root)
        self.assertTrue(state.show_unmigrated)
        self.assertFalse(state._load_invalid)
        before = files(self.root)
        for action in (lambda: state.create_show("New"), lambda: state.rename_show("New"),
                       lambda: state.select_show("Show"), lambda: state.delete_show("Show")):
            with self.assertRaises(OSError): action()
        self.assertEqual(files(self.root), before)
        dash = object.__new__(Dashboard)
        dash.state = state
        dash.load_project_show()
        self.assertTrue(dash.show_load_invalid)
        self.assertTrue(any(str(self.legacy) in notice for notice in state.data["notices"]))
        self.assertEqual(self.legacy.read_bytes(), body)

    def test_stale_pointer_from_an_installation_still_counts_as_unmigrated(self):
        # The live rig's project.json carried the installation's
        # `current_show` beside its show.json, with no shows/ folder.
        doc = json.loads(self.project.read_text())
        self.project.write_text(json.dumps(dict(doc, current_show="test")))
        self.legacy.write_text(json.dumps({"schema": 1, "name": "test", "items": [STEP]}))
        self.assertTrue(InstallationState(self.root).show_unmigrated)
        migrate_shows(self.project)
        state = InstallationState(self.root)
        self.assertFalse(state.show_unmigrated)
        self.assertEqual(show_model.load_show(state.show_path)[0]["items"][0]["alias"], "Opening")

    def test_migration_converts_byte_exact_and_keeps_every_source(self):
        body = json.dumps({"schema": 1, "name": "Kite Choir", "items": [STEP]}, indent=4).encode()
        self.legacy.write_bytes(body)
        original = self.project.read_bytes()
        created = migrate_shows(self.project)
        self.assertEqual(created, self.project.parent / "shows/Kite Choir.json")
        self.assertEqual(created.read_bytes(), body)
        self.assertEqual(self.legacy.read_bytes(), body)
        self.assertEqual(self.project.with_name("project.json.pre-shows").read_bytes(), original)
        state = InstallationState(self.root)
        self.assertFalse(state.show_unmigrated)
        self.assertEqual(state.data["current_show"], "Kite Choir")
        self.assertEqual(state.show_path, str(created))
        before = files(self.root)
        with self.assertRaises(FileExistsError): migrate_shows(self.project)
        self.assertEqual(files(self.root), before)

    def test_unusable_name_becomes_show_and_invalid_show_changes_nothing(self):
        self.legacy.write_text(json.dumps({"schema": 1, "name": "a/b", "items": []}))
        self.assertEqual(migrate_shows(self.project).name, "Show.json")
        self.project.write_bytes(self.project.with_name("project.json.pre-shows").read_bytes())
        for path in (self.project.with_name("project.json.pre-shows"), self.project.parent / "shows/Show.json"):
            path.unlink()
        (self.project.parent / "shows").rmdir()
        for body in ("broken JSON", '{"schema": 99, "items": []}'):
            with self.subTest(body=body):
                self.legacy.write_text(body)
                before = files(self.root)
                with self.assertRaises(ValueError): migrate_shows(self.project)
                self.assertEqual(files(self.root), before)
                self.assertFalse((self.project.parent / "shows").exists())


class DashboardCase(unittest.IsolatedAsyncioTestCase):
    """A dashboard on a fresh project whose open show has one step."""

    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = self.temp.name
        args = SimpleNamespace(data_dir=root, devices_file=None, listen_port=0, send_port=0,
            osc_target="127.0.0.1", public_url="http://localhost",
            patches_dir=root + "/patches", assets_dir=root + "/assets")
        self.dash = Dashboard(args)
        self.addCleanup(self.dash.osc.close)
        self.dash.state.save()
        self.dash.broadcast = mock.AsyncMock()
        self.dash.ws_error = mock.AsyncMock()
        await self.dash.handle_ws({"type": "add_step", "data": {}})

    async def send(self, kind, **data):
        await self.dash.handle_ws({"type": kind, "data": data})


class ShowActionTests(DashboardCase):

    async def test_open_new_rename_delete_in_every_mode(self):
        dash = self.dash
        for mode in ("off", "simulate", "edit"):
            with self.subTest(mode=mode):
                dash.state.data["supervisor"]["mode"] = mode
                name = f"Copy {mode}"
                await self.send("create_show", name=name, source="Show")
                self.assertEqual(dash.state.data["current_show"], name)
                self.assertEqual(len(dash.show["items"]), 1)
                self.assertEqual(dash.show["name"], name)
                self.assertIs(dash.show_engine.show, dash.show)
                await self.send("open_show", name="Show")
                self.assertEqual(dash.state.data["current_show"], "Show")
                await self.send("rename_show", name="Main")
                self.assertEqual(dash.show["name"], "Main")
                await self.send("delete_show", name=name)
                await self.send("rename_show", name="Show")
                self.assertEqual(dash.state.list_shows(), ["Show"])
        dash.ws_error.assert_not_awaited()
        sent = [call.args[0] for call in dash.broadcast.await_args_list]
        self.assertIn("show", sent)
        self.assertIn("state", sent)

    async def test_refused_while_a_show_is_playing_or_paused(self):
        dash = self.dash
        await self.send("create_show", name="Other")
        await self.send("open_show", name="Show")
        before = files(self.temp.name)
        for state in ("playing", "paused"):
            dash.show_engine.playback = {"0000000a": {"state": state}}
            for kind, name in (("open_show", "Other"), ("create_show", "New"),
                               ("rename_show", "New"), ("delete_show", "Other")):
                with self.subTest(state=state, kind=kind):
                    dash.ws_error.reset_mock()
                    await self.send(kind, name=name)
                    dash.ws_error.assert_awaited_once()
        self.assertEqual(dash.state.data["current_show"], "Show")
        self.assertEqual(files(self.temp.name), before)
        dash.show_engine.playback = {}
        await self.send("open_show", name="Other")
        self.assertEqual(dash.state.data["current_show"], "Other")

    async def test_undo_is_per_show_and_cleared_on_switch(self):
        dash = self.dash
        self.assertEqual(len(dash.show_undo), 1)
        await self.send("rename_show", name="Renamed")
        self.assertEqual(len(dash.show_undo), 1)
        await self.send("undo_show")
        self.assertEqual(dash.show, show_model.empty_show("Renamed"))
        await self.send("add_step")
        await self.send("create_show", name="Other")
        self.assertEqual(dash.show_undo, [])
        await self.send("undo_show")
        self.assertEqual(json.loads(Path(dash.state.show_file("Renamed")).read_text())["items"][0]["kind"], "step")

    async def test_failures_report_and_switching_away_clears_a_damaged_show_notice(self):
        dash = self.dash
        await self.send("create_show", name="Broken")
        Path(dash.state.show_path).write_text("broken JSON")
        await self.send("open_show", name="Show")
        await self.send("open_show", name="Broken")
        self.assertTrue(dash.show_load_invalid)
        self.assertTrue(any("Broken.json" in notice for notice in dash.state.data["notices"]))
        await self.send("rename_show", name="Fixed")
        dash.ws_error.assert_awaited_once()
        await self.send("open_show", name="Show")
        self.assertFalse(dash.show_load_invalid)
        self.assertFalse(any("Broken.json" in notice for notice in dash.state.data["notices"]))
        for kind, data in (("open_show", {"name": "Missing"}), ("create_show", {"name": "Show"}),
                           ("create_show", {"name": "X", "source": "Missing"}),
                           ("delete_show", {"name": "Show"})):
            dash.ws_error.reset_mock()
            await self.send(kind, **data)
            dash.ws_error.assert_awaited_once()



class ShowNumberBoundaryTests(DashboardCase):
    """67/24: malformed numbers fail closed at the show boundary."""

    async def test_out_of_range_edits_return_an_error_and_change_nothing(self):
        dash = self.dash
        step = dash.show["items"][0]["uid"]
        await self.send("add_message", step_uid=step, message={
            "address": "/x", "target": "all", "args": []})
        message = dash.show["items"][0]["messages"][0]["uid"]
        before = copy.deepcopy(dash.show)
        for kind, data in (
            ("update_step", {"uid": step, "duration_s": 10 ** 400}),
            ("add_message", {"step_uid": step, "message": {
                "address": "/x", "target": "all", "args": [{"type": "i", "value": float("inf")}]}}),
            ("update_message", {"uid": message, "args": [{"type": "i", "value": 2 ** 31}]}),
            ("update_message", {"uid": message, "address": "/a b#"}),
        ):
            with self.subTest(kind=kind, data=data):
                dash.ws_error.reset_mock()
                await self.send(kind, **data)
                dash.ws_error.assert_awaited_once()
                self.assertEqual(dash.show, before)

    async def test_open_show_with_an_out_of_range_number_starts_read_only(self):
        dash = self.dash
        doc = json.loads(Path(dash.state.show_path).read_text())
        doc["items"][0]["duration_s"] = 10 ** 400
        Path(dash.state.show_path).write_text(json.dumps(doc))
        restarted = Dashboard(dash.args)
        self.addCleanup(restarted.osc.close)
        self.assertTrue(restarted.show_load_invalid)
        self.assertEqual(restarted.show["items"], [])
        self.assertIsNone(restarted.state.public()["show_steps"]["Show"])


class ClearShowTests(DashboardCase):
    """66/9 Clear Show: one undoable edit on the open show."""

    def test_mutation_empties_items_only(self):
        show = dict(show_model.empty_show("Main"), items=[STEP, {"kind": "divider", "uid": "0000000b", "alias": None}])
        cleared, result, error = show_model.clear_items(show)
        self.assertEqual((cleared, result, error), (show_model.empty_show("Main"), None, None))
        self.assertEqual(len(show["items"]), 2)

    async def test_clear_saves_broadcasts_and_undoes(self):
        dash = self.dash
        await self.send("add_divider")
        before = copy.deepcopy(dash.show)
        project = Path(dash.state.path).read_bytes()
        dash.broadcast.reset_mock()
        await self.send("clear_show")
        self.assertEqual(dash.show, show_model.empty_show("Show"))
        self.assertEqual(json.loads(Path(dash.state.show_path).read_text())["items"], [])
        self.assertIs(dash.show_engine.show, dash.show)
        self.assertIn("show", [call.args[0] for call in dash.broadcast.await_args_list])
        self.assertEqual(Path(dash.state.path).read_bytes(), project)
        await self.send("undo_show")
        self.assertEqual(dash.show, before)
        self.assertEqual(show_model.load_show(dash.state.show_path)[0], before)
        dash.ws_error.assert_not_awaited()

    async def test_refused_while_playing_or_paused_and_empty_is_a_no_op(self):
        dash = self.dash
        saved = Path(dash.state.show_path).read_bytes()
        for state in ("playing", "paused"):
            dash.show_engine.playback = {dash.show["items"][0]["uid"]: {"state": state}}
            dash.ws_error.reset_mock()
            await self.send("clear_show")
            dash.ws_error.assert_awaited_once()
            self.assertEqual(len(dash.show["items"]), 1)
            self.assertEqual(Path(dash.state.show_path).read_bytes(), saved)
        dash.show_engine.playback = {}
        await self.send("clear_show")
        undo = len(dash.show_undo)
        await self.send("clear_show")
        self.assertEqual(len(dash.show_undo), undo)


class ShowPlaybackConsistencyTests(DashboardCase):
    """67/25: playback lists only steps that exist and are timing."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.dash.show_engine.bridge = mock.Mock()
        self.first = self.dash.show["items"][0]["uid"]

    async def add_timed_step(self):
        await self.send("add_step", after_uid=self.first)
        uid = self.dash.show["items"][1]["uid"]
        await self.send("update_step", uid=uid, duration_s=0.05)
        return uid

    async def test_undo_that_removes_a_playing_step_stops_it(self):
        dash = self.dash
        uid = await self.add_timed_step()
        await self.send("step_start", uid=uid)
        await self.send("undo_show")  # the duration edit; the step stays
        self.assertIn(uid, dash.show_engine.playback)
        await self.send("undo_show")  # the add
        self.assertFalse(dash.show_playing())
        await self.send("clear_show")
        self.assertEqual(dash.show["items"], [])
        dash.ws_error.assert_not_awaited()

    async def test_a_failing_send_still_times_the_step_and_clear_works_after(self):
        dash = self.dash
        uid = await self.add_timed_step()
        await self.send("add_message", step_uid=uid, message={
            "address": "/x", "target": "all", "args": []})
        await self.send("add_message", step_uid=uid, message={
            "address": "/y", "target": "all", "args": []})
        dash.show_engine.bridge.send.side_effect = [RuntimeError("build"), None]
        with self.assertLogs("bopos.show_engine", "ERROR"):
            await self.send("step_start", uid=uid)
        dash.show_engine.bridge.send.assert_called_with("/y", [])
        self.assertIsNotNone(dash.show_engine.playback[uid]["timer"])
        await asyncio.sleep(0.15)
        self.assertFalse(dash.show_playing())
        await self.send("clear_show")
        self.assertEqual(dash.show["items"], [])
        dash.ws_error.assert_not_awaited()

    async def test_remove_stops_a_playing_step_only_when_the_removal_lands(self):
        dash = self.dash
        await self.send("step_start", uid=self.first)
        dash.show_load_invalid = True  # write-blocked: the removal is refused
        await self.send("remove_item", uid=self.first)
        dash.ws_error.assert_awaited_once()
        self.assertEqual(dash.show_engine.playback[self.first]["state"], "playing")
        dash.show_load_invalid = False
        await self.send("remove_item", uid=self.first)
        self.assertEqual(dash.show["items"], [])
        self.assertFalse(dash.show_playing())


if __name__ == "__main__":
    unittest.main()
