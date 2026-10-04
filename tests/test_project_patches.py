"""The project's patch list (66-projects/6-patch-versions).

project.json lists the project's patch folders; the Patch (fleet patch) is
always one of them, so a project stored before the list existed is seeded
from its fleet patch, and Set Live keeps the outgoing Patch as a version.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "dashboard"))
from state import InstallationState  # noqa: E402


class ProjectPatchListTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_project(self, **fields):
        path = self.root / "projects" / "default" / "project.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"schema": 1, "name": "Kite Choir",
                                    "seats": {}, **fields}))
        (self.root / "current-project").write_text("default\n")
        return path

    def test_a_project_without_a_list_is_seeded_from_its_patch(self):
        self.write_project(fleet_patch={"name": "kite-v2"})
        state = InstallationState(self.root)
        self.assertEqual(state.public()["patches"], ["kite-v2"])
        self.assertEqual(state.durable()["patches"], ["kite-v2"])

    def test_a_new_project_has_no_patches(self):
        state = InstallationState(self.root)
        self.assertEqual(state.public()["patches"], [])

    def test_the_list_is_cleaned_sorted_unique_and_keeps_the_patch(self):
        self.write_project(fleet_patch={"name": "kite-v2"},
                           patches=["kite-v1", "kite-v1", "../escape", 7, "", "a.b_c-1"])
        state = InstallationState(self.root)
        self.assertEqual(state.public()["patches"], ["a.b_c-1", "kite-v1", "kite-v2"])

    def test_set_live_keeps_the_outgoing_patch_and_adds_the_new_one(self):
        self.write_project(fleet_patch={"name": "kite-v2"})
        state = InstallationState(self.root)
        state.stage_fleet_patch("kite-v3", "f" * 64)
        self.assertEqual(state.project_patches(), ["kite-v2", "kite-v3"])
        state.save()
        self.assertEqual(InstallationState(self.root).public()["patches"],
                         ["kite-v2", "kite-v3"])

    def test_add_project_patch_reports_whether_the_list_changed(self):
        state = InstallationState(self.root)
        self.assertTrue(state.add_project_patch("kite-sketch"))
        self.assertFalse(state.add_project_patch("kite-sketch"))
        self.assertEqual(state.project_patches(), ["kite-sketch"])


if __name__ == "__main__":
    unittest.main()
