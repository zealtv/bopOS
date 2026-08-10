"""Durable tests for resolving the Pure Data executable at run time.

Every case runs against a fabricated /Applications-shaped tmpdir, never
against whatever Pd the developer's machine happens to carry -- otherwise
the test asserts the machine rather than the code.
"""

import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import audition  # noqa: E402


def make_bundle(app_dir, name, executable=True):
    """Create <app_dir>/<name>/Contents/Resources/bin/pd."""
    binary = Path(app_dir) / name / "Contents" / "Resources" / "bin" / "pd"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text("#!/bin/sh\nexit 0\n")
    binary.chmod(0o755 if executable else 0o644)
    return str(binary)


class PdBundleSortTests(unittest.TestCase):
    def test_version_sort_is_numeric_not_lexicographic(self):
        with tempfile.TemporaryDirectory() as apps:
            for name in ("Pd-0.9-1.app", "Pd-0.55-2.app", "Pd-0.55-10.app",
                         "Pd-0.56-2.app"):
                make_bundle(apps, name)
            order = [os.path.basename(Path(binary).parents[3])
                     for _version, binary in audition.pd_bundle_candidates((apps,))]
            self.assertEqual(order, ["Pd-0.56-2.app", "Pd-0.55-10.app",
                                     "Pd-0.55-2.app", "Pd-0.9-1.app"])

    def test_non_pd_entries_and_missing_dirs_are_ignored(self):
        with tempfile.TemporaryDirectory() as apps:
            make_bundle(apps, "Pd-0.55-2.app")
            (Path(apps) / "Pd.app").mkdir()
            (Path(apps) / "Pd-0.55.app").mkdir()
            (Path(apps) / "Thincast Client Updater.app").mkdir()
            candidates = audition.pd_bundle_candidates(
                (apps, os.path.join(apps, "nope")))
            self.assertEqual([version for version, _binary in candidates],
                             [(0, 55, 2)])


class ResolvePdBinTests(unittest.TestCase):
    def test_darwin_prefers_the_highest_installed_bundle(self):
        with tempfile.TemporaryDirectory() as apps:
            make_bundle(apps, "Pd-0.55-0.app")
            newest = make_bundle(apps, "Pd-0.56-2.app")
            self.assertEqual(
                audition.resolve_pd_bin(platform="darwin", app_dirs=(apps,)),
                newest)

    def test_non_executable_bundle_is_skipped(self):
        with tempfile.TemporaryDirectory() as apps:
            older = make_bundle(apps, "Pd-0.55-0.app")
            make_bundle(apps, "Pd-0.56-2.app", executable=False)
            self.assertEqual(
                audition.resolve_pd_bin(platform="darwin", app_dirs=(apps,)),
                older)

    def test_explicit_pd_bin_wins_outright(self):
        with tempfile.TemporaryDirectory() as apps:
            make_bundle(apps, "Pd-0.56-2.app")
            self.assertEqual(
                audition.resolve_pd_bin("/somewhere/else/pd", platform="darwin",
                                        app_dirs=(apps,)),
                "/somewhere/else/pd")

    def test_no_candidates_resolves_to_none_not_a_literal(self):
        with tempfile.TemporaryDirectory() as apps:
            with unittest.mock.patch.object(audition.shutil, "which",
                                            return_value=None):
                with unittest.mock.patch.object(audition, "PD_FALLBACK_PATHS", ()):
                    self.assertIsNone(
                        audition.resolve_pd_bin(platform="darwin", app_dirs=(apps,)))

    def test_linux_resolves_through_path(self):
        with tempfile.TemporaryDirectory() as apps:
            make_bundle(apps, "Pd-0.56-2.app")
            with unittest.mock.patch.object(audition.shutil, "which",
                                            return_value="/usr/bin/pd"):
                self.assertEqual(
                    audition.resolve_pd_bin(platform="linux", app_dirs=(apps,)),
                    "/usr/bin/pd")

    def test_argparse_default_is_unset_rather_than_a_hardcoded_build(self):
        self.assertIsNone(audition.parse_args([]).pd_bin)


class PreflightTests(unittest.TestCase):
    """The named preflight error, and the --no-engine path that must not run it."""

    class Args:
        def __init__(self, **kwargs):
            self.pd_bin = None
            self.no_engine = False
            self.engine = None
            self.engine_command = None
            self.__dict__.update(kwargs)

    def rig(self, **kwargs):
        rig = audition.AuditionRig.__new__(audition.AuditionRig)
        rig.args = self.Args(**kwargs)
        rig._pd_bin = None
        return rig

    def test_missing_binary_raises_a_named_error(self):
        rig = self.rig(pd_bin="/no/such/pd")
        with self.assertRaises(audition.PdBinaryError) as caught:
            rig.pd_binary()
        message = str(caught.exception)
        self.assertIn("/no/such/pd", message)
        self.assertIn("--pd-bin", message)

    def test_resolved_binary_is_cached(self):
        with tempfile.TemporaryDirectory() as apps:
            binary = make_bundle(apps, "Pd-0.56-2.app")
            rig = self.rig(pd_bin=binary)
            self.assertEqual(rig.pd_binary(), binary)
            self.assertEqual(rig._pd_bin, binary)

    def test_no_engine_never_resolves_and_never_fails(self):
        rig = self.rig(pd_bin="/no/such/pd", no_engine=True)
        calls = []

        def explode():
            calls.append(1)
            raise AssertionError("resolver ran on the --no-engine path")

        rig.pd_binary = explode
        rig._load_patch = lambda: (_ for _ in ()).throw(
            AssertionError("--no-engine must return before loading a patch"))
        rig.start_engines()
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
