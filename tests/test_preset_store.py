"""Durable tests for strict host-side patch preset storage."""

import asyncio
import datetime as dt
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
for source in (ROOT, ROOT / "python", ROOT / "dashboard"):
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))

import manifest  # noqa: E402
import preset_store  # noqa: E402
import server  # noqa: E402


class PresetStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bopos-presets-")
        self.root = Path(self.temp.name)
        self.patches = self.root / "patches"
        self.patch = self.patches / "alpha"
        self.patch.mkdir(parents=True)
        (self.patch / "main.bin").write_bytes(b"engine")
        candidate = {
            "engine": "test",
            "entrypoint": "main.bin",
            "params": [
                {"name": "gain", "kind": "float", "min": 0, "max": 1},
                {"name": "count", "kind": "int", "min": 0, "max": 8},
                {"name": "gate", "kind": "toggle"},
                {"name": "mode", "kind": "enum", "options": ["dry", "wet"]},
                {"name": "voice", "kind": "text"},
            ],
        }
        written, error = manifest.write_atomic(self.patch, candidate)
        self.assertIsNone(error)
        self.manifest = written
        self.store = preset_store.PresetStore(self.patches)
        self.now = dt.datetime(2026, 7, 29, 1, 2, 3, tzinfo=dt.timezone.utc)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, name="Dawn", params=None, revision=None):
        return self.store.save(
            "alpha",
            name,
            {
                "gain": [0.25],
                "count": ["lfo", "sine", 0, 8, "4s"],
                "voice": ["aah"],
            } if params is None else params,
            revision=revision,
            now=self.now,
        )

    def test_schema_projection_is_order_independent_and_label_sensitive(self):
        reverse = dict(self.manifest)
        reverse["params"] = list(reversed(self.manifest["params"]))
        self.assertEqual(
            preset_store.schema_fingerprint(self.manifest),
            preset_store.schema_fingerprint(reverse),
        )
        changed = json.loads(json.dumps(self.manifest))
        changed["params"][3]["options"] = ["wet", "dry"]
        self.assertNotEqual(
            preset_store.schema_fingerprint(self.manifest),
            preset_store.schema_fingerprint(changed),
        )
        projection = preset_store.schema_projection(self.manifest)
        self.assertEqual(
            list(projection[0]),
            ["identity", "kind", "min", "max", "options"],
        )

    def test_atomic_crud_and_revision_compare_and_swap(self):
        created = self.save()
        self.assertEqual(created["slug"], "Dawn")
        self.assertRegex(created["revision"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(created["document"]["saved"], "2026-07-29T01:02:03Z")
        self.assertEqual(self.store.read("alpha", "Dawn"), created)
        self.assertEqual(self.store.list("alpha")[0]["valid"], True)

        with self.assertRaises(preset_store.PresetConflictError):
            self.save(params={"gain": [0.5]})
        with self.assertRaises(preset_store.PresetConflictError):
            self.save(params={"gain": [0.5]}, revision="sha256:" + "0" * 64)

        updated = self.save(
            params={"gain": [0.5]},
            revision=created["revision"],
        )
        self.assertNotEqual(updated["revision"], created["revision"])
        self.assertEqual(updated["document"]["params"], {"gain": [0.5]})

        with self.assertRaises(preset_store.PresetConflictError):
            self.store.delete("alpha", "Dawn", created["revision"])
        self.assertTrue(
            self.store.delete("alpha", "Dawn", updated["revision"])
        )
        self.assertEqual(self.store.list("alpha"), [])

    def test_slug_collision_is_not_a_silent_overwrite(self):
        self.save(name="Morning Glow", params={"gain": [0.2]})
        with self.assertRaises(preset_store.PresetConflictError):
            self.save(name="Morning@Glow", params={"gain": [0.8]})
        record = self.store.read("alpha", "Morning-Glow")
        self.assertEqual(record["document"]["name"], "Morning Glow")
        self.assertEqual(record["document"]["params"]["gain"], [0.2])

    def test_invalid_files_are_visible_and_refused(self):
        presets = self.patch / "presets"
        presets.mkdir()
        (presets / "broken.json").write_text("{not-json")
        listing = self.store.list("alpha")
        self.assertEqual(len(listing), 1)
        self.assertFalse(listing[0]["valid"])
        self.assertTrue(listing[0]["error"])
        self.assertRegex(listing[0]["revision"], r"^sha256:[0-9a-f]{64}$")
        with self.assertRaises(preset_store.PresetStoreError):
            self.store.read("alpha", "broken")
        self.assertTrue(
            self.store.delete("alpha", "broken", listing[0]["revision"])
        )
        self.assertEqual(self.store.list("alpha"), [])

    def test_store_rejects_empty_nonfinite_and_transition_entries(self):
        invalid = (
            {},
            {"gain": [math.nan]},
            {"gain": ["stop"]},
            {"gain": [1, "2s"]},
            {"gain": ["loop", 1, "2s"]},
        )
        for params in invalid:
            with self.subTest(params=params):
                with self.assertRaises(preset_store.PresetStoreError):
                    self.save(params=params)

        created = self.save(params={
            "gain": ["loop", 0, "1s", 1, "1s", "c:1"],
        })
        self.assertEqual(created["document"]["params"]["gain"][0], "loop")

    def test_symlinked_store_paths_are_refused(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.patch / "presets").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(preset_store.PresetStoreError):
            self.save(params={"gain": [0.5]})
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlinked_preset_file_is_listed_invalid_and_refused(self):
        presets = self.patch / "presets"
        presets.mkdir()
        outside = self.root / "outside.json"
        outside.write_text("{}")
        (presets / "linked.json").symlink_to(outside)

        listing = self.store.list("alpha")

        self.assertEqual(listing[0]["slug"], "linked")
        self.assertFalse(listing[0]["valid"])
        with self.assertRaises(preset_store.PresetStoreError):
            self.store.read("alpha", "linked")

    def test_cache_invalidates_when_file_changes_externally(self):
        created = self.save(params={"gain": [0.25]})
        path = self.patch / "presets" / "Dawn.json"
        document = json.loads(path.read_text())
        document["params"]["gain"] = [0.75]
        path.write_text(json.dumps(document))

        changed = self.store.read("alpha", "Dawn")
        self.assertNotEqual(changed["revision"], created["revision"])
        self.assertEqual(changed["document"]["params"]["gain"], [0.75])

    def test_drift_resolution_applies_clamps_and_drops_per_entry(self):
        result = preset_store.resolve_entries({
            "gain": [1.5],
            "count": ["lfo", "sine", -2, 12, "4s"],
            "voice": ["aah"],
            "missing": [1],
            "gate": ["wrong-kind"],
        }, self.manifest)

        self.assertEqual(result["params"]["gain"], [1])
        self.assertEqual(
            result["params"]["count"],
            ["lfo", "sine", 0, 8, "4s"],
        )
        self.assertEqual(result["params"]["voice"], ["aah"])
        self.assertEqual(
            result["counts"],
            {"applied": 1, "clamped": 2, "dropped": 2},
        )
        self.assertEqual(
            result["verdicts"]["missing"],
            {"status": "dropped", "reason": "identity absent"},
        )
        self.assertEqual(result["verdicts"]["gate"]["reason"], "kind changed")


class DistributionDenyTests(unittest.TestCase):
    @staticmethod
    async def request(app, path):
        sent = []
        received = False

        async def receive():
            nonlocal received
            if not received:
                received = True
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)

        await app({
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [],
            "client": ("test", 1),
            "server": ("test", 80),
        }, receive, send)
        return next(message["status"] for message in sent
                    if message["type"] == "http.response.start")

    def test_patch_presets_are_denied_before_static_lookup(self):
        with tempfile.TemporaryDirectory(prefix="bopos-static-") as temporary:
            app = FastAPI()
            app.mount("/patches", server.DistributionStaticFiles(
                directory=temporary, patch_root=True))
            for path in (
                "/patches/alpha/presets/dawn.json",
                "/patches/alpha//presets/dawn.json",
            ):
                with self.subTest(path=path):
                    status = asyncio.run(self.request(app, path))
                    self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
