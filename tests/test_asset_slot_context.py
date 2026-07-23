#!/usr/bin/env python3
"""Living tests for asset-slot discovery and engine run context."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
PYTHON = REPO / "python"
if str(PYTHON) not in sys.path:
    sys.path.insert(0, str(PYTHON))
DASHBOARD = REPO / "dashboard"
if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

import asset_slots  # noqa: E402
import identity  # noqa: E402
import runcontext  # noqa: E402
import server as dashboard_server  # noqa: E402
from tools import simfleet  # noqa: E402


class AssetSlotContextTests(unittest.TestCase):
    def test_identity_imports_through_the_python_package(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from python import identity; "
                "assert identity.valid_asset_slot('slot')",
            ],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_discovery_is_absolute_sorted_and_excludes_non_slots(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "assets"
            (root / "z slot").mkdir(parents=True)
            (root / "alpha").mkdir()
            (root / ".hashcache").mkdir()
            (root / "README.md").write_text("not a slot")
            (root / "linked").symlink_to(root / "alpha", target_is_directory=True)

            self.assertEqual(asset_slots.installed_names(root), ["alpha", "z slot"])
            self.assertEqual(
                asset_slots.installed_paths(root),
                [str(root / "alpha"), str(root / "z slot")],
            )

    def test_run_context_lists_every_installed_slot_not_manifest_subset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "assets" / "declared").mkdir(parents=True)
            (root / "assets" / "extra").mkdir()
            context = runcontext.generate(
                patch=None,
                repo_dir=str(root),
                assets_dir=str(root / "assets"),
                now=0,
            )
            self.assertEqual(
                context["assets"],
                [str(root / "assets" / "declared"),
                 str(root / "assets" / "extra")],
            )

    def test_dashboard_catalog_uses_the_same_slot_discovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            patches = root / "patches"
            (assets / "slot b").mkdir(parents=True)
            (assets / "slot b" / "sound.wav").write_bytes(b"audio")
            (assets / ".hidden").mkdir()
            (assets / "bad\nname").mkdir()
            patches.mkdir()

            catalog = dashboard_server.distribution_catalog(assets, patches)
            self.assertEqual(
                [entry["name"] for entry in catalog["assets"]],
                ["slot b"],
            )

    def test_environment_and_pd_forms_carry_the_same_ordered_paths(self):
        paths = [
            "/home/pi/bopOS/assets/a;slot",
            "/home/pi/bopOS/assets/z slot",
            "/home/pi/bopOS/assets/dollar$slot",
        ]
        self.assertEqual(json.loads(asset_slots.json_list(paths)), paths)
        self.assertEqual(
            asset_slots.fudi_list(paths),
            "/home/pi/bopOS/assets/a\\;slot "
            "/home/pi/bopOS/assets/z\\ slot "
            "/home/pi/bopOS/assets/dollar\\$slot",
        )
        self.assertEqual(asset_slots.json_list([]), "[]")
        self.assertEqual(asset_slots.fudi_list([]), "")

    def test_slot_names_are_visible_single_folder_names(self):
        for valid in ("belief-system-000", "two words", "semi;colon", "日本語"):
            self.assertTrue(identity.valid_asset_slot(valid), valid)
        for invalid in ("", ".hidden", "nested/name", "back\\slash",
                        "line\nbreak", "tab\tname", "\x00"):
            self.assertFalse(identity.valid_asset_slot(invalid), repr(invalid))

    def test_launch_surfaces_no_longer_send_the_scalar_assets_root(self):
        start = (REPO / "bash" / "start-engine.sh").read_text()
        audition = (REPO / "tools" / "audition.py").read_text()
        supercollider = (REPO / "patches" / "demo-sc" / "main.scd").read_text()
        pd_adapter = (REPO / "pd" / "bopos~.pd").read_text()
        pd_template = (
            REPO / "patches" / ".templates" / "bopos-template.pd"
        ).read_text()

        self.assertIn("bopos-context assets $BOPOS_ASSETS_PD;", start)
        self.assertNotIn("bopos-context assets $BOPOS_DIR/assets;", start)
        self.assertLess(
            start.index('rmdir "$ASSETS_DIR/samplepacks"'),
            start.index('python3 "$BOPOS_DIR/python/runcontext.py"'),
            "retired empty compatibility slots must be removed before discovery",
        )
        self.assertIn("asset_slots.fudi_list(context['assets'])", audition)
        self.assertIn('asset_slots.json_list(context["assets"])', audition)
        self.assertIn('("BOPOS_ASSETS".getenv ? "[]").parseJSON', supercollider)
        self.assertNotIn("bopos-assets-path", pd_adapter)
        self.assertNotIn("bopos-assets-path", pd_template)
        self.assertIn("route patch assets", pd_template)
        self.assertIn("list length", pd_template)
        self.assertIn("route id groups os audition", pd_adapter)
        self.assertEqual(pd_adapter.count("clip~ -1 1"), 2)

        contract = (REPO / "docs" / "OSC-CONTRACT.md").read_text()
        self.assertIn("**Version 1.9**", contract)
        self.assertIn("`BOPOS_ASSETS` is a UTF-8 JSON array", contract)

    def test_simfleet_context_is_a_restart_snapshot(self):
        device = simfleet.Device(
            "02:00:00:00:00:01", "bop001", 1, "1234567"
        )
        device.asset_slots["z"] = {}
        device.capture_engine_context()
        self.assertEqual(
            device.engine_asset_paths,
            ["/home/pi/bopOS/assets/z"],
        )
        device.asset_slots["a"] = {}
        self.assertEqual(
            device.engine_asset_paths,
            ["/home/pi/bopOS/assets/z"],
            "inventory changes must not mutate launch context live",
        )
        device.capture_engine_context()
        self.assertEqual(
            device.engine_asset_paths,
            ["/home/pi/bopOS/assets/a", "/home/pi/bopOS/assets/z"],
        )


if __name__ == "__main__":
    unittest.main()
