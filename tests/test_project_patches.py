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
        # Start from a real save (project, site, registry), then set fields.
        InstallationState(self.root).save()
        path = self.root / "projects" / "default" / "project.json"
        doc = json.loads(path.read_text())
        doc.pop("patches", None)
        doc.update(fields)
        path.write_text(json.dumps(doc))
        return path

    def test_a_project_without_a_list_is_seeded_from_its_patch(self):
        self.write_project(fleet_patch={"name": "tune-v2"})
        state = InstallationState(self.root)
        self.assertEqual(state.public()["patches"], ["tune-v2"])
        self.assertEqual(state.durable()["patches"], ["tune-v2"])

    def test_a_new_project_has_no_patches(self):
        state = InstallationState(self.root)
        self.assertEqual(state.public()["patches"], [])

    def test_the_list_is_cleaned_sorted_unique_and_keeps_the_patch(self):
        self.write_project(fleet_patch={"name": "tune-v2"},
                           patches=["tune-v1", "tune-v1", "../escape", 7, "", "a.b_c-1"])
        state = InstallationState(self.root)
        self.assertEqual(state.public()["patches"], ["a.b_c-1", "tune-v1", "tune-v2"])

    def test_set_live_keeps_the_outgoing_patch_and_adds_the_new_one(self):
        self.write_project(fleet_patch={"name": "tune-v2"})
        state = InstallationState(self.root)
        state.stage_fleet_patch("tune-v3", "f" * 64)
        self.assertEqual(state.project_patches(), ["tune-v2", "tune-v3"])
        state.save()
        self.assertEqual(InstallationState(self.root).public()["patches"],
                         ["tune-v2", "tune-v3"])

    def test_add_project_patch_reports_whether_the_list_changed(self):
        state = InstallationState(self.root)
        self.assertTrue(state.add_project_patch("tune-sketch"))
        self.assertFalse(state.add_project_patch("tune-sketch"))
        self.assertEqual(state.project_patches(), ["tune-sketch"])


if __name__ == "__main__":
    unittest.main()
