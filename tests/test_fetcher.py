"""Durable byte-convergence and landing tests for node fetching."""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest import mock
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

    def test_file_fetch_copies_only_canonical_source_files(self):
        write_file(self.source / "nested" / "keep.txt", b"keep")
        write_file(self.source / ".hidden" / "secret.txt", b"hidden")
        write_file(self.source / "unfinished.part", b"partial")
        outside = self.root / "outside"
        write_file(outside / "secret.txt", b"outside")
        (self.source / "linked-file.txt").symlink_to(outside / "secret.txt")
        (self.source / "linked-dir").symlink_to(outside, target_is_directory=True)
        (self.source / "nested" / "linked-dir").symlink_to(
            outside, target_is_directory=True)

        ok, detail = self.fetch("pack")

        self.assertTrue(ok, detail)
        destination = self.assets / "pack"
        self.assertEqual(sorted(path.relative_to(destination).as_posix()
                                for path in destination.rglob("*") if path.is_file()),
                         ["nested/keep.txt"])
        self.assertFalse((destination / "linked-dir").exists())
        self.assertFalse((destination / "nested" / "linked-dir").exists())
        self.assertEqual(fetcher.identity.directory_manifest(str(self.source)),
                         fetcher.identity.directory_manifest(str(destination)))
        self.assertEqual(fetcher.identity.fingerprint(str(self.source)),
                         fetcher.identity.fingerprint(str(destination)))

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

    def test_patch_fetch_prunes_stale_nested_files(self):
        destination = self.patches / "stage"
        write_patch(destination, b"old")
        write_file(destination / "stale.txt", b"remove")
        write_file(destination / "nested" / "dawn.json", b"host authored")
        write_patch(self.source, b"new")

        ok, _detail = self.fetch("patch:stage")

        self.assertTrue(ok)
        self.assertFalse((destination / "nested").exists())
        self.assertFalse((destination / "stale.txt").exists())

    def test_file_patch_fetch_transfers_nested_source_content(self):
        write_patch(self.source, b"new")
        write_file(self.source / "nested" / "source-only.json", b"do not fetch")

        ok, _detail = self.fetch("patch:stage")

        self.assertTrue(ok)
        destination = self.patches / "stage"
        self.assertEqual((destination / "main.bin").read_bytes(), b"new")
        self.assertEqual((destination / "nested" / "source-only.json").read_bytes(), b"do not fetch")

    def test_patch_fetch_still_refuses_symlinks_inside_nested(self):
        destination = self.patches / "stage"
        write_patch(destination, b"old")
        outside = self.root / "outside-nested.json"
        outside.write_bytes(b"outside")
        (destination / "nested").mkdir()
        (destination / "nested" / "linked.json").symlink_to(outside)
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
        outside = self.root / "outside"
        outside.mkdir()
        unsafe_asset = self.assets / "unsafe"
        unsafe_asset.mkdir(parents=True)
        (unsafe_asset / "nested").symlink_to(outside, target_is_directory=True)

        self.assertFalse(self.fetch("patch:../escape")[0])
        self.assertFalse(self.fetch("unsafe")[0])
        self.assertEqual(list(outside.iterdir()), [])

    def test_existing_clone_is_converted_only_after_validation(self):
        destination = self.patches / "stage"
        write_patch(destination, b"old")
        write_file(destination / ".git" / "config", b"old metadata")
        write_file(destination / "obsolete.bin", b"obsolete")
        write_patch(self.source, b"new")
        write_file(self.source / ".git" / "config", b"host metadata")
        real_load = fetcher.patch_manifest.load

        def validate(staging):
            self.assertEqual((destination / "main.bin").read_bytes(), b"old")
            self.assertEqual((destination / ".git" / "config").read_bytes(), b"old metadata")
            self.assertFalse(Path(staging, ".git").exists())
            return real_load(staging)

        with mock.patch.object(fetcher.patch_manifest, "load", side_effect=validate):
            self.assertTrue(self.fetch("patch:stage")[0])
        self.assertEqual((destination / "main.bin").read_bytes(), b"new")
        self.assertFalse((destination / ".git").exists())
        self.assertFalse((destination / "obsolete.bin").exists())
        self.assertEqual(sorted(path.name for path in self.patches.iterdir()), ["stage"])

    def test_git_pointer_file_is_removed_without_following_external_target(self):
        destination = self.patches / "stage"
        write_patch(destination, b"old")
        external = self.root / "external-repository"
        write_file(external / "config", b"external metadata")
        (destination / ".git").write_text(f"gitdir: {external}\n")
        write_patch(self.source, b"new")
        self.assertTrue(self.fetch("patch:stage")[0])
        self.assertFalse((destination / ".git").exists())
        self.assertEqual((external / "config").read_bytes(), b"external metadata")

    def test_clone_metadata_and_bytes_survive_fetch_validation_and_install_failures(self):
        for metadata_file in (False, True):
            for failure in ("fetch", "validation", "installation"):
                with self.subTest(metadata_file=metadata_file, failure=failure), \
                        tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    destination, source = root / "patches" / "stage", root / "source"
                    write_patch(destination, b"old")
                    metadata = destination / ".git" if metadata_file else destination / ".git/config"
                    write_file(metadata, b"gitdir: /unused\n" if metadata_file else b"metadata")
                    original = {p.relative_to(destination): p.read_bytes()
                                for p in destination.rglob("*") if p.is_file()}
                    write_patch(source, b"new")
                    if failure == "validation":
                        (source / manifest.MANIFEST_NAME).write_text("invalid JSON")
                    if failure == "fetch":
                        source = root / "missing"
                    real_replace = os.replace

                    def replace(src, dst):
                        if failure == "installation" and Path(src).name.startswith(".fetch-") \
                                and Path(dst) == destination:
                            raise OSError("replacement failed")
                        return real_replace(src, dst)

                    with mock.patch.object(fetcher.os, "replace", side_effect=replace):
                        ok, detail = fetcher.fetch(source.as_uri(), "patch:stage",
                                                   str(root / "assets"), str(root / "patches"))
                    self.assertFalse(ok, detail)
                    self.assertEqual({p.relative_to(destination): p.read_bytes()
                                      for p in destination.rglob("*") if p.is_file()}, original)
                    self.assertEqual(sorted(p.name for p in destination.parent.iterdir()), ["stage"])

    def test_clone_metadata_symlink_still_refuses_conversion(self):
        destination = self.patches / "stage"
        write_patch(destination, b"old")
        external = self.root / "external"
        write_file(external / "config", b"external")
        (destination / ".git").symlink_to(external, target_is_directory=True)
        write_patch(self.source, b"new")
        self.assertFalse(self.fetch("patch:stage")[0])
        self.assertEqual((destination / "main.bin").read_bytes(), b"old")
        self.assertTrue((destination / ".git").is_symlink())
        self.assertEqual((external / "config").read_bytes(), b"external")


if __name__ == "__main__":
    unittest.main()
