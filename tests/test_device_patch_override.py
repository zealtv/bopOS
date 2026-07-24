#!/usr/bin/env python3
"""Living tests for the per-device desired-patch override (thread 37).

Foundation layer only: durable persistence of a device's patch pin and the
registry round-trip that keeps it. The convergence path and UI are a later
bite; these guard the data model those build on. Homed in tests/ by code
surface per the thread-27 durable-tests policy.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
for path in (REPO / "python", REPO / "dashboard"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import device_aliases  # noqa: E402
from state import InstallationState  # noqa: E402

FP = "a" * 64  # a plausible 64-hex content fingerprint


def _registry_entry(alias="Finn Jet", **extra):
    entry = {"alias": alias, "source": "custom", "generator": 2,
             "device_enabled": True}
    entry.update(extra)
    return entry


class CleanDesiredPatch(unittest.TestCase):
    def test_absent_or_malformed_collapses_to_none(self):
        for value in (None, {}, {"name": ""}, {"name": "   "}, "roomtone", 5):
            self.assertIsNone(device_aliases.clean_desired_patch(value))

    def test_name_only_keeps_none_fingerprint(self):
        self.assertEqual(
            device_aliases.clean_desired_patch({"name": "roomtone"}),
            {"name": "roomtone", "fingerprint": None})

    def test_valid_fingerprint_survives_blank_dropped(self):
        self.assertEqual(
            device_aliases.clean_desired_patch(
                {"name": "roomtone", "fingerprint": FP}),
            {"name": "roomtone", "fingerprint": FP})
        self.assertEqual(
            device_aliases.clean_desired_patch(
                {"name": "roomtone", "fingerprint": "  "}),
            {"name": "roomtone", "fingerprint": None})


class RegistryRoundTrip(unittest.TestCase):
    def test_clean_registry_preserves_valid_override_and_drops_bad(self):
        cleaned = device_aliases.clean_registry({
            "node-a": _registry_entry(
                "Finn Jet",
                desired_patch={"name": "roomtone", "fingerprint": FP}),
            "node-b": _registry_entry(
                "Ciro Toast", desired_patch={"name": ""}),
            "node-c": _registry_entry("Amara Vale"),
        })
        self.assertEqual(cleaned["node-a"]["desired_patch"],
                         {"name": "roomtone", "fingerprint": FP})
        self.assertNotIn("desired_patch", cleaned["node-b"])
        self.assertNotIn("desired_patch", cleaned["node-c"])

    def test_alias_rename_keeps_the_pin(self):
        registry = {"node-a": _registry_entry(
            desired_patch={"name": "roomtone", "fingerprint": FP})}
        entry, error = device_aliases.set_custom(registry, "node-a", "Ciro Toast")
        self.assertIsNone(error)
        self.assertEqual(entry["desired_patch"],
                         {"name": "roomtone", "fingerprint": FP})


class StatePersistence(unittest.TestCase):
    def _state(self, root, registry=None):
        path = os.path.join(root, "installation.json")
        with open(path, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "t", "seats": {},
                       "device_registry": registry or {
                           "node-a": _registry_entry()}}, target)
        return path, InstallationState(path)

    def test_set_and_clear_round_trip_through_disk(self):
        with tempfile.TemporaryDirectory() as root:
            path, state = self._state(root)
            self.assertIsNone(state.device_patch_for("node-a"))

            self.assertTrue(
                state.set_device_patch_override("node-a", "roomtone", FP))
            self.assertEqual(state.device_patch_for("node-a"),
                             {"name": "roomtone", "fingerprint": FP})
            with open(path, encoding="utf-8") as source:
                saved = json.load(source)
            self.assertEqual(
                saved["device_registry"]["node-a"]["desired_patch"],
                {"name": "roomtone", "fingerprint": FP})

            # survives a fresh load
            reloaded = InstallationState(path)
            self.assertEqual(reloaded.device_patch_for("node-a"),
                             {"name": "roomtone", "fingerprint": FP})

            self.assertTrue(state.clear_device_patch_override("node-a"))
            self.assertIsNone(state.device_patch_for("node-a"))
            with open(path, encoding="utf-8") as source:
                saved = json.load(source)
            self.assertNotIn("desired_patch",
                             saved["device_registry"]["node-a"])

    def test_override_requires_a_registered_device(self):
        with tempfile.TemporaryDirectory() as root:
            _path, state = self._state(root)
            self.assertFalse(
                state.set_device_patch_override("ghost", "roomtone", FP))
            self.assertFalse(state.set_device_patch_override("node-a", "", FP))
            self.assertFalse(state.clear_device_patch_override("node-a"))


if __name__ == "__main__":
    unittest.main()
