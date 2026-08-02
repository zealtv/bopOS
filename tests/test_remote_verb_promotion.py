#!/usr/bin/env python3
"""Venue-owned Remote verb promotion stays durable, bounded, and atomic."""

import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
if str(REPO / "dashboard") not in sys.path:
    sys.path.insert(0, str(REPO / "dashboard"))

from server import Dashboard  # noqa: E402
from state import InstallationState  # noqa: E402


class RemoteVerbStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bopos-remote-verbs-")
        self.path = os.path.join(self.temp.name, "installation.json")
        self.state = InstallationState(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_cleaner_filters_and_uses_one_display_order(self):
        self.assertEqual(
            self.state.clean_facilitator_commands([
                "shutdown", {"bad": True}, "restart-engine", "shutdown",
                "not-a-command", "reboot",
            ]),
            ["restart-engine", "reboot", "shutdown"],
        )

    def test_setting_persists_in_installation_not_patch_state(self):
        self.assertTrue(self.state.set_facilitator_commands([
            "shutdown", "restart-engine", "reboot",
        ]))
        with open(self.path, encoding="utf-8") as source:
            saved = json.load(source)
        self.assertEqual(
            saved["facilitator_commands"],
            ["restart-engine", "reboot", "shutdown"],
        )
        self.assertNotIn("facilitator_commands", saved.get("fleet_patch") or {})

    def test_save_failure_restores_previous_allowlist(self):
        self.state.data["facilitator_commands"] = ["restart-engine"]

        def fail():
            raise OSError("disk full")

        self.state.save = fail
        self.assertFalse(self.state.set_facilitator_commands(["shutdown"]))
        self.assertEqual(
            self.state.data["facilitator_commands"], ["restart-engine"])


class RemoteVerbServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bopos-remote-server-")
        state = InstallationState(
            os.path.join(self.temp.name, "installation.json"))
        state.data["supervisor"] = {"mode": "off"}
        state.data["groups"] = {"0": {"id": 0, "name": "Front"}}
        state.data["seats"] = {
            "1": {"id": 1, "name": "One", "groups": [0],
                  "positions": [], "params": {}, "bound": "physical-1"},
        }
        state.data["devices"] = {
            "physical-1": {"uid": "physical-1", "virtual": False},
        }
        self.dashboard = Dashboard.__new__(Dashboard)
        self.dashboard.state = state
        self.dashboard.supervisor_lock = asyncio.Lock()
        self.dashboard.manifest_lock = asyncio.Lock()
        self.errors = []
        self.broadcasts = []

        class OSC:
            def __init__(osc_self):
                osc_self.actions = []

            def action(osc_self, selector, verb):
                osc_self.actions.append(("selector", selector, verb))

            def uid_action(osc_self, uid, verb):
                osc_self.actions.append(("uid", uid, verb))

        self.dashboard.osc = OSC()

        async def ws_error(_ws, message):
            self.errors.append(message)

        async def broadcast(message, *_args):
            self.broadcasts.append(message)

        self.dashboard.ws_error = ws_error
        self.dashboard.broadcast = broadcast

    async def asyncTearDown(self):
        await self.dashboard.state.close()
        self.temp.cleanup()

    async def test_valid_mutation_persists_and_broadcasts_state(self):
        await self.dashboard.handle_ws({
            "type": "set_facilitator_commands",
            "data": {"commands": ["shutdown", "restart-engine"]},
        })
        self.assertEqual(self.errors, [])
        self.assertEqual(
            self.dashboard.state.data["facilitator_commands"],
            ["restart-engine", "shutdown"],
        )
        self.assertEqual(self.broadcasts, ["state"])

    async def test_unknown_command_is_rejected_without_mutation(self):
        self.dashboard.state.data["facilitator_commands"] = ["reboot"]
        await self.dashboard.handle_ws({
            "type": "set_facilitator_commands",
            "data": {"commands": ["reboot", "format-everything"]},
        })
        self.assertEqual(
            self.dashboard.state.data["facilitator_commands"], ["reboot"])
        self.assertEqual(self.broadcasts, [])
        self.assertEqual(
            self.errors, ["Remote commands must be recognized framework verbs."])

    async def test_persistence_failure_is_operator_visible_and_atomic(self):
        self.dashboard.state.data["facilitator_commands"] = ["reboot"]

        def fail():
            raise OSError("disk full")

        self.dashboard.state.save = fail
        await self.dashboard.handle_ws({
            "type": "set_facilitator_commands",
            "data": {"commands": ["shutdown"]},
        })
        self.assertEqual(
            self.dashboard.state.data["facilitator_commands"], ["reboot"])
        self.assertEqual(self.broadcasts, [])
        self.assertEqual(self.errors, [
            "Could not save Remote commands; the previous setting is still active.",
        ])

    async def test_remote_actions_follow_all_group_and_seat_selectors(self):
        for scope, target_id in (("all", None), ("group", 0), ("seat", 1)):
            data = {"scope": scope, "verb": "restart-engine"}
            if target_id is not None:
                data["id"] = target_id
            await self.dashboard.handle_ws({"type": "action", "data": data})
        self.assertEqual(self.errors, [])
        self.assertEqual(self.dashboard.osc.actions, [
            ("selector", "all", "restart-engine"),
            ("selector", "g0", "restart-engine"),
            ("selector", 1, "restart-engine"),
        ])

    async def test_desktop_action_keeps_exact_uid_targeting(self):
        await self.dashboard.handle_ws({
            "type": "action",
            "data": {"uid": "physical-1", "verb": "reboot"},
        })
        self.assertEqual(
            self.dashboard.osc.actions,
            [("uid", "physical-1", "reboot")],
        )

    async def test_unknown_remote_target_is_rejected(self):
        await self.dashboard.handle_ws({
            "type": "action",
            "data": {"scope": "group", "id": 99, "verb": "shutdown"},
        })
        self.assertEqual(self.dashboard.osc.actions, [])
        self.assertEqual(
            self.errors, ["That Remote command target is unavailable."])


if __name__ == "__main__":
    unittest.main()
