#!/usr/bin/env python3
"""Living tests for physical identity and content-fingerprint convergence."""

import json
import shutil
import sys
import tempfile
import types
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
for source in (REPO / "python", REPO / "dashboard", REPO / "tools"):
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))

import identity  # noqa: E402
import pyOSC3  # noqa: E402


class FakeServer:
    def __init__(self, _target):
        self.handlers = {}

    def addMsgHandler(self, address, callback):
        self.handlers[address] = callback

    def close(self):
        pass


class FakeClient:
    def connect(self, _target):
        pass

    def send(self, _message):
        pass


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
ORIGINAL_ARGV = sys.argv
sys.argv = ["bopos.py", "unknown"]

import bopos  # noqa: E402
import osc_bridge  # noqa: E402
import server as dashboard_server  # noqa: E402
import simfleet  # noqa: E402
from state import InstallationState, patch_badge  # noqa: E402

sys.argv = ORIGINAL_ARGV


class MemoryStore:
    def __init__(self, **values):
        self.values = values

    def get(self, key):
        return self.values.get(key, [])

    def put(self, key, value):
        self.values[key] = list(value)
        return True


class NodeIdentityTests(unittest.TestCase):
    def test_uid_resolution_uses_pinned_then_runtime_then_hardware_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "state").mkdir()
            pin = root / "state" / "uid"
            pin.write_text("pinned-box\n")
            with (
                mock.patch.object(bopos, "BOPOS_DIR", str(root)),
                mock.patch.object(
                    bopos, "discover_primary_mac",
                    return_value="02:00:00:00:00:09",
                ),
            ):
                self.assertEqual(
                    bopos.resolve_uid(["bopos.py", "runtime-box"]),
                    "pinned-box",
                )
                pin.unlink()
                self.assertEqual(
                    bopos.resolve_uid(["bopos.py", "runtime-box"]),
                    "runtime-box",
                )
                self.assertEqual(
                    bopos.resolve_uid(["bopos.py", "unknown"]),
                    "02:00:00:00:00:09",
                )

    def test_uid_resolution_has_an_opaque_per_boot_fallback(self):
        fallback = "12345678-1234-5678-1234-567812345678"
        with (
            tempfile.TemporaryDirectory() as temporary,
            mock.patch.object(bopos, "BOPOS_DIR", temporary),
            mock.patch.object(bopos, "discover_primary_mac", return_value=None),
            mock.patch.object(
                bopos.uuid, "uuid4",
                return_value=bopos.uuid.UUID(fallback),
            ),
        ):
            self.assertEqual(
                bopos.resolve_uid(["bopos.py", "unknown"]),
                fallback,
            )

    def test_persisted_assignment_and_unassignment_outrank_seed(self):
        with tempfile.TemporaryDirectory() as temporary:
            seed = Path(temporary) / "bopos.devices"
            seed.write_text("node-a,Seed seat,7\n")

            self.assertEqual(
                bopos.resolve_id(
                    "node-a", str(seed),
                    MemoryStore(assignment=[42, "Live seat"]),
                ),
                42,
            )
            self.assertEqual(
                bopos.resolve_id(
                    "node-a", str(seed),
                    MemoryStore(assignment=[-1, "Unassigned"]),
                ),
                -1,
                "the unassignment tombstone must not resurrect a seed binding",
            )
            self.assertEqual(
                bopos.resolve_id("node-a", str(seed), MemoryStore()),
                7,
            )
            self.assertEqual(
                bopos.resolve_id("other", str(seed), MemoryStore()),
                -1,
            )

    def test_assignment_is_exact_uid_full_state(self):
        store = MemoryStore(groups=[8])
        state = types.SimpleNamespace(
            uid="node-a", id=3, groups=(8,), store=store, elements=[[9, 9]]
        )
        with (
            mock.patch.object(bopos, "send_groups_to_engine"),
            mock.patch.object(bopos, "send_to_engine"),
        ):
            self.assertFalse(
                bopos.apply_assign(["node-b", 4, "Seat 4", 1, 2], state)
            )
            self.assertTrue(
                bopos.apply_assign(
                    ["node-a", 4, "Seat 4", 1, 2, 3, 4], state
                )
            )

        self.assertEqual(state.id, 4)
        self.assertEqual(state.groups, ())
        self.assertEqual(state.elements, [[1.0, 2.0], [3.0, 4.0]])
        self.assertEqual(
            store.values["assignment"],
            [4, "Seat 4", 1.0, 2.0, 3.0, 4.0],
        )

    def test_unassignment_persists_tombstone_and_clears_routing_identity(self):
        store = MemoryStore(
            assignment=[7, "Authored seat", 1, 2],
            groups=[3, 5],
        )
        state = types.SimpleNamespace(
            uid="node-a", id=7, groups=(3, 5), store=store,
            elements=[[1, 2]],
        )
        with (
            mock.patch.object(bopos, "send_groups_to_engine"),
            mock.patch.object(bopos, "send_to_engine"),
        ):
            self.assertTrue(bopos.apply_unassign(state))

        self.assertEqual(state.id, -1)
        self.assertEqual(state.groups, ())
        self.assertEqual(state.elements, [])
        self.assertEqual(store.values["assignment"], [-1, "Authored seat"])


class ContentIdentityTests(unittest.TestCase):
    def test_canonical_walk_ignores_framework_and_inflight_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plain = root / "plain"
            noisy = root / "noisy"
            (plain / "nested").mkdir(parents=True)
            (plain / "voice.wav").write_bytes(b"voice")
            (plain / "nested" / "tone.wav").write_bytes(b"tone")
            shutil.copytree(plain, noisy)
            (noisy / ".git").mkdir()
            (noisy / ".git" / "config").write_text("ignored")
            (noisy / ".hidden").write_text("ignored")
            (noisy / "voice.wav.part").write_text("ignored")
            (noisy / "linked").symlink_to(plain / "voice.wav")

            self.assertEqual(
                identity.fingerprint(noisy),
                identity.fingerprint(plain),
            )
            before = identity.fingerprint(plain)
            (plain / "voice.wav").write_bytes(b"changed visible content")
            self.assertNotEqual(identity.fingerprint(plain), before)

    def test_cached_inventory_is_unknown_until_warm_and_after_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            slot = Path(temporary) / "slot"
            slot.mkdir()
            payload = slot / "sound.wav"
            payload.write_bytes(b"first")

            self.assertIsNone(
                identity.cached_directory_info(slot)["fingerprint"]
            )
            identity.warm_hash_cache(slot)
            self.assertEqual(
                identity.cached_directory_info(slot)["fingerprint"],
                identity.fingerprint(slot),
            )
            payload.write_bytes(b"second version")
            self.assertIsNone(
                identity.cached_directory_info(slot)["fingerprint"],
                "changed bytes must degrade to unknown until re-hashed",
            )

    def test_host_node_and_simulator_share_patch_and_asset_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            patches, assets = root / "patches", root / "assets"
            patch, slot = patches / "alpha", assets / "field recordings"
            patch.mkdir(parents=True)
            slot.mkdir(parents=True)
            (patch / "main.bin").write_bytes(b"patch bytes")
            (slot / "sound.wav").write_bytes(b"asset bytes")
            (patches / "active_patch.txt").write_text("alpha\n")

            host_patch = dashboard_server.directory_info(
                patches, "alpha", "patch"
            )["fingerprint"]
            host_asset = dashboard_server.directory_info(
                assets, "field recordings", "asset"
            )["fingerprint"]
            identity.warm_hash_cache(assets)

            with (
                mock.patch.object(bopos, "BOPOS_DIR", str(root)),
                mock.patch.object(
                    bopos, "active_patch_path", return_value=str(patch)
                ),
                mock.patch.object(simfleet, "PATCHES_DIR", str(patches)),
            ):
                node_patch = next(
                    item for item in bopos.installed_patches()
                    if item["name"] == "alpha"
                )["fingerprint"]
                node_asset = next(
                    item for item in bopos.installed_assets(str(assets))
                    if item["name"] == "field recordings"
                )["fingerprint"]
                simulated_patch = simfleet.host_patch_fingerprint("alpha")
                simulated_asset = simfleet.host_asset_facts(
                    str(assets), "field recordings"
                )["fingerprint"]

            self.assertRegex(host_patch, r"^[0-9a-f]{64}$")
            self.assertEqual(
                {host_patch, node_patch, simulated_patch},
                {host_patch},
            )
            self.assertEqual(
                {host_asset, node_asset, simulated_asset},
                {host_asset},
            )

    def test_patch_drift_is_derived_without_mutating_device_state(self):
        current = "a" * 64
        old = "b" * 64
        desired = {"name": "alpha", "fingerprint": current}
        base = {
            "online": True,
            "patches": [{
                "name": "alpha", "active": True, "fingerprint": current,
            }],
            "fetch": {},
            "patch_switch": None,
        }
        cases = (
            ("unset", base, None, "unset"),
            ("offline", {**base, "online": False}, desired, "unknown"),
            ("unobserved", {**base, "patches": None}, desired, "unknown"),
            ("missing", {**base, "patches": []}, desired, "missing"),
            (
                "wrong active",
                {**base, "patches": [
                    {"name": "alpha", "active": False,
                     "fingerprint": current},
                    {"name": "beta", "active": True},
                ]},
                desired,
                "mismatch",
            ),
            (
                "identity unavailable",
                {**base, "patches": [
                    {"name": "alpha", "active": True},
                ]},
                desired,
                "stale_unverified",
            ),
            (
                "bytes differ",
                {**base, "patches": [{
                    "name": "alpha", "active": True, "fingerprint": old,
                }]},
                desired,
                "stale",
            ),
            ("same bytes", base, desired, "current"),
        )

        for label, device, wanted, expected in cases:
            before = deepcopy(device)
            with self.subTest(label=label):
                self.assertEqual(patch_badge(device, wanted), expected)
                self.assertEqual(device, before)
                self.assertNotIn("patch_badge", device)

    def test_wire_inventory_evolves_additively_and_degrades_unknown_facts(self):
        uid = "physical-1"
        with tempfile.TemporaryDirectory() as temporary:
            state = InstallationState(
                str(Path(temporary) / "installation.json")
            )
            state.ensure(uid)["ip"] = "192.0.2.4"
            bridge = osc_bridge.OSCBridge(
                state, lambda *_args: None, 5550, 6660, "127.0.0.1"
            )
            good = "c" * 64
            try:
                bridge.handle("/os/patches", [json.dumps([
                    {"name": "current", "active": True, "fingerprint": good,
                     "future_fact": {"safe": True}},
                    {"name": "older-node", "active": False},
                    {"name": "bad", "fingerprint": "not-a-fingerprint"},
                ])], "192.0.2.4")
                patches = {
                    item["name"]: item for item in state.devices[uid]["patches"]
                }
                self.assertEqual(patches["current"]["fingerprint"], good)
                self.assertNotIn("fingerprint", patches["older-node"])
                self.assertNotIn("fingerprint", patches["bad"])

                with mock.patch.object(
                    bridge, "_schedule_asset_requery"
                ), mock.patch.object(bridge, "_cancel_asset_requery"):
                    bridge.handle("/os/assets", [json.dumps([
                        {"name": "current", "fingerprint": good,
                         "files": 2, "bytes": 10, "future_fact": "ignored"},
                        {"name": "warming", "fingerprint": None,
                         "files": 2, "bytes": 10},
                        {"name": "bad", "fingerprint": "short",
                         "files": 2, "bytes": 10},
                    ])], "192.0.2.4")
                assets = {
                    item["name"]: item for item in state.devices[uid]["assets"]
                }
                self.assertEqual(assets["current"]["fingerprint"], good)
                self.assertIsNone(assets["warming"]["fingerprint"])
                self.assertTrue(assets["bad"]["unknown"])
            finally:
                bridge.close()


if __name__ == "__main__":
    unittest.main()
