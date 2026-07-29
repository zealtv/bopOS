"""Durable byte-convergence and landing tests for node fetching."""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

import fetcher  # noqa: E402
import manifest  # noqa: E402


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def write_patch(path, payload=b"current"):
    path.mkdir(parents=True, exist_ok=True)
    write_file(path / "main.bin", payload)
    (path / manifest.MANIFEST_NAME).write_text(json.dumps({
        "engine": "test",
        "entrypoint": "main.bin",
        "params": [],
        "caps": [],
        "slots": [],
    }))


class FetchManifestTests(unittest.TestCase):
    def test_safe_paths_reject_escape_and_ambiguous_components(self):
        for value in (
            "",
            "../x",
            "/x",
            "a/../x",
            "a//x",
            "a/./x",
            r"C:\x",
            "nul\x00byte",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    fetcher.safe_path(value)
        self.assertEqual(fetcher.safe_path("nested/file.wav"),
                         os.path.join("nested", "file.wav"))

    def test_transfer_manifest_is_exact_bounded_and_canonical(self):
        digest = hashlib.sha256(b"data").hexdigest()
        parsed = fetcher.parse_manifest({"files": [{
            "path": "nested/file.wav",
            "size": 4,
            "sha256": digest.upper(),
        }]})
        self.assertEqual(parsed, [{
            "path": os.path.join("nested", "file.wav"),
            "size": 4,
            "sha256": digest,
        }])

        invalid = (
            {},
            {"files": "not-a-list"},
            {"files": [{"path": "../x", "size": 1, "sha256": "0" * 64}]},
            {"files": [{"path": "x", "size": -1, "sha256": "0" * 64}]},
            {"files": [{"path": "x", "size": True, "sha256": "0" * 64}]},
            {"files": [{"path": "x", "size": 1, "sha256": "short"}]},
            {"files": [
                {"path": "x", "size": 1, "sha256": "0" * 64},
                {"path": "x", "size": 1, "sha256": "0" * 64},
            ]},
        )
        for candidate in invalid:
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValueError):
                    fetcher.parse_manifest(candidate)


class FileConvergenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bopos-fetcher-")
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.assets = self.root / "assets"
        self.patches = self.root / "patches"
        self.source.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def fetch(self, slot):
        return fetcher.fetch(
            self.source.as_uri(), slot, str(self.assets), str(self.patches)
        )

    def test_asset_fetch_converges_prunes_and_skips_matching_bytes(self):
        write_file(self.source / "one.txt", b"one")
        write_file(self.source / "nested" / "two.txt", b"two")

        ok, _detail = self.fetch("pack")
        self.assertTrue(ok)
        target = self.assets / "pack"
        self.assertEqual((target / "one.txt").read_bytes(), b"one")
        self.assertEqual((target / "nested" / "two.txt").read_bytes(), b"two")

        first_mtime = (target / "one.txt").stat().st_mtime_ns
        ok, _detail = self.fetch("pack")
        self.assertTrue(ok)
        self.assertEqual((target / "one.txt").stat().st_mtime_ns, first_mtime)

        write_file(self.source / "one.txt", b"changed")
        (self.source / "nested" / "two.txt").unlink()
        ok, _detail = self.fetch("pack")
        self.assertTrue(ok)
        self.assertEqual((target / "one.txt").read_bytes(), b"changed")
        self.assertFalse((target / "nested" / "two.txt").exists())
        self.assertEqual(list(target.rglob("*.part")), [])

    def test_valid_patch_replaces_only_after_staging_converges(self):
        destination = self.patches / "stage"
        write_patch(destination, b"old")
        write_file(destination / "stale.txt", b"remove")
        write_patch(self.source, b"new")

        ok, _detail = self.fetch("patch:stage")

        self.assertTrue(ok)
        self.assertEqual((destination / "main.bin").read_bytes(), b"new")
        self.assertFalse((destination / "stale.txt").exists())
        loaded, error = manifest.load(destination)
        self.assertIsNone(error)
        self.assertEqual(loaded["entrypoint"], "main.bin")

    def test_patch_fetch_preserves_host_presets_and_prunes_other_stale_files(self):
        destination = self.patches / "stage"
        write_patch(destination, b"old")
        write_file(destination / "stale.txt", b"remove")
        write_file(destination / "presets" / "dawn.json", b"host authored")
        write_patch(self.source, b"new")

        ok, _detail = self.fetch("patch:stage")

        self.assertTrue(ok)
        self.assertEqual(
            (destination / "presets" / "dawn.json").read_bytes(),
            b"host authored",
        )
        self.assertFalse((destination / "stale.txt").exists())

    def test_file_patch_fetch_does_not_transfer_source_presets(self):
        write_patch(self.source, b"new")
        write_file(self.source / "presets" / "source-only.json", b"do not fetch")

        ok, _detail = self.fetch("patch:stage")

        self.assertTrue(ok)
        destination = self.patches / "stage"
        self.assertEqual((destination / "main.bin").read_bytes(), b"new")
        self.assertFalse((destination / "presets").exists())

    def test_patch_fetch_still_refuses_symlinks_inside_presets(self):
        destination = self.patches / "stage"
        write_patch(destination, b"old")
        outside = self.root / "outside-preset.json"
        outside.write_bytes(b"outside")
        (destination / "presets").mkdir()
        (destination / "presets" / "linked.json").symlink_to(outside)
        write_patch(self.source, b"new")

        ok, _detail = self.fetch("patch:stage")

        self.assertFalse(ok)
        self.assertEqual((destination / "main.bin").read_bytes(), b"old")
        self.assertEqual(outside.read_bytes(), b"outside")

    def test_invalid_fetched_patch_leaves_current_bytes_intact(self):
        destination = self.patches / "stage"
        write_patch(destination, b"old")
        write_file(self.source / "payload.bin", b"invalid-without-manifest")

        ok, _detail = self.fetch("patch:stage")

        self.assertFalse(ok)
        self.assertEqual((destination / "main.bin").read_bytes(), b"old")
        self.assertTrue((destination / manifest.MANIFEST_NAME).is_file())
        self.assertFalse((destination / "payload.bin").exists())

    def test_patch_and_asset_landings_reject_unsafe_destinations(self):
        write_patch(self.source)
        write_patch(self.patches / "git-managed")
        (self.patches / "git-managed" / ".git").mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        unsafe_asset = self.assets / "unsafe"
        unsafe_asset.mkdir(parents=True)
        (unsafe_asset / "nested").symlink_to(outside, target_is_directory=True)

        self.assertFalse(self.fetch("patch:../escape")[0])
        self.assertFalse(self.fetch("patch:git-managed")[0])
        self.assertFalse(self.fetch("unsafe")[0])
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
