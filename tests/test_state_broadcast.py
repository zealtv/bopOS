#!/usr/bin/env python3
"""Living regression for the payload contract of a `state` broadcast.

Thread 50. `Dashboard.broadcast` builds the enriched `public_state()` itself
for the `state` message type and ignores whatever the caller passed. Clients
replace `installation` wholesale on `state` (`dashboard.js:140`), so the
enriched snapshot — `live_controls` above all — is the only payload any surface
can use; a bare `state.public()` would blank the Control columns' parameter
rows.

That coercion is what makes it safe for 37 call sites to say `broadcast("state")`
and pass nothing. These tests pin the coercion, not the call sites: they fail if
someone "restores" a caller-supplied payload as the thing actually sent.
"""

import asyncio
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

from server import Dashboard  # noqa: E402

ENRICHED_KEYS = ("live_controls", "supervisor", "host_version",
                 "fleet_patch", "devices", "editor")


class RecordingClient:
    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)


class StateBroadcastPayloadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        # Ports nothing else in the suite binds; the bridge is constructed but
        # never driven here.
        self.dashboard = Dashboard(Namespace(
            state_file=os.path.join(self.temporary.name, "installation.json"),
            devices_file=os.path.join(self.temporary.name, "devices.json"),
            listen_port=15557, send_port=16667, osc_target="127.0.0.1",
            assets_dir=os.path.join(self.temporary.name, "assets"),
            patches_dir=str(ROOT / "patches"),
        ))
        self.client = RecordingClient()
        self.dashboard.clients.add(self.client)

    async def asyncTearDown(self):
        self.dashboard.osc.close()
        await self.dashboard.state.close()
        self.temporary.cleanup()

    async def delivered(self, *args):
        await self.dashboard.broadcast("state", *args)
        message = self.client.messages[-1]
        self.assertEqual(message["type"], "state")
        return message["data"]

    async def test_payloadless_broadcast_delivers_enriched_state(self):
        """The form every call site uses carries the keys clients need."""
        data = await self.delivered()
        for key in ENRICHED_KEYS:
            self.assertIn(key, data, f"`state` must carry {key!r}")

    async def test_caller_payload_cannot_narrow_what_is_sent(self):
        """The bare durable snapshot is not what goes on the wire.

        `state.public()` is `state.data`: no `live_controls`, no `supervisor`,
        no `host_version`, and an unresolved `fleet_patch`. Passing it — which
        30 call sites once did — must not reach a client.
        """
        bare = self.dashboard.state.public()
        self.assertNotIn("live_controls", bare)

        data = await self.delivered(bare)
        for key in ENRICHED_KEYS:
            self.assertIn(key, data, f"`state` must carry {key!r}")

    async def test_every_payload_form_delivers_the_same_snapshot(self):
        """No call site can be read as choosing a different payload."""
        forms = [
            await self.delivered(),
            await self.delivered(None),
            await self.delivered(self.dashboard.state.public()),
            await self.delivered(await self.dashboard.public_state()),
            await self.delivered({"live_controls": "sabotage"}),
        ]
        first = forms[0]
        for other in forms[1:]:
            self.assertEqual(set(first), set(other))
        for form in forms:
            self.assertNotEqual(form.get("live_controls"), "sabotage")


class StateBroadcastCallSiteTests(unittest.TestCase):
    """The call sites stay payloadless, so reading one stays honest.

    Source-level on purpose: the behavioural tests above already prove a stray
    argument would be harmless, and that is exactly why nothing else would ever
    catch one being reintroduced.
    """

    def test_no_state_broadcast_passes_a_payload(self):
        offenders = []
        for name in ("server.py", "osc_bridge.py"):
            path = ROOT / "dashboard" / name
            for number, line in enumerate(
                    path.read_text().splitlines(), start=1):
                if 'broadcast("state"' in line and 'broadcast("state")' not in line:
                    offenders.append(f"{name}:{number}: {line.strip()}")
        self.assertEqual(offenders, [], "`state` broadcasts take no payload; "
                                        "see tests/test_state_broadcast.py")


if __name__ == "__main__":
    unittest.main()
