#!/usr/bin/env python3
"""Verify converged appearance replay through the bridge and simulated node."""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True


def root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "tools/simfleet.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = root()
sys.path[:0] = [str(ROOT), str(ROOT / "dashboard"), str(ROOT / "tools")]

import osc_bridge as bridge_module  # noqa: E402
from osc_bridge import OSCBridge  # noqa: E402
from pythonosc.osc_message import OscMessage  # noqa: E402
from server import Dashboard  # noqa: E402
from simfleet import ContractProtocol, Device, SimFleet  # noqa: E402
from state import InstallationState  # noqa: E402


class Wire:
    def __init__(self):
        self.frames = []

    def sendto(self, data, target):
        self.frames.append((data, target))

    def close(self):
        pass


def decoded(wire):
    return [(OscMessage(data).address, list(OscMessage(data).params))
            for data, _target in wire.frames]


def hb(bridge, device):
    message = OscMessage(ContractProtocol.heartbeat(device))
    bridge.handle(message.address, list(message.params), "127.0.0.1")


def deliver(wire, fleet):
    frames = list(wire.frames)
    wire.frames.clear()
    for data, _target in frames:
        fleet.receive_contract(data, ("127.0.0.1", 16660))
    return [(OscMessage(data).address, list(OscMessage(data).params))
            for data, _target in frames]


async def exercise():
    with tempfile.TemporaryDirectory(prefix="bopos-live-catchup-") as directory:
        state_path = Path(directory, "installation.json")
        state_path.write_text(json.dumps({
            "schema": 1, "name": "catchup", "params_patch": "demo-pd",
            "seats": {"1": {"id": 1, "name": "One", "positions": [[1, 1]],
                              "groups": [], "bound": "node-a",
                              "params": {"gain": 0.73, "stale": 99}}},
        }), encoding="utf-8")
        state = InstallationState(str(state_path))
        args = SimpleNamespace(cmd_port=0, target="127.0.0.1", report_port=5550,
                               state_dir=directory, sync_skew_ms=0.0, drop=0.0,
                               jitter_ms=0.0, hb_interval=.5, boot_secs=.1,
                               manifest=None, assets_dir=directory,
                               patches_dir=directory)
        device = Device("node-a", "node-a", -1, "verify")
        device.state = "running"
        fleet = SimFleet(args, [device])
        fleet.sock.close()
        fleet.sock = Wire()
        wire = Wire()
        replayed = []
        holder = {}

        def replay(seat):
            replayed.append(seat["id"])
            holder["bridge"].set_param(seat["id"], "gain", seat["params"]["gain"])

        bridge = OSCBridge(state, lambda *_: None, 0, 16660, "127.0.0.1", replay)
        holder["bridge"] = bridge
        bridge.sender = wire
        old_limit = bridge_module.ASSIGN_REPLAY_MIN_SECONDS
        bridge_module.ASSIGN_REPLAY_MIN_SECONDS = 0
        try:
            hb(bridge, device)
            first = deliver(wire, fleet)
            assert any(address == "/all/os/assign" for address, _ in first)
            assert not any(address == "/1/p/gain" for address, _ in first)
            hb(bridge, device)
            converged = deliver(wire, fleet)
            assert any(address == "/1/p/gain" and abs(values[0] - .73) < 1e-5
                       for address, values in converged)
            assert abs(device.params.get("gain", 0) - .73) < 1e-5
            assert replayed == [1]

            for _ in range(4):
                hb(bridge, device)
                steady = deliver(wire, fleet)
                assert not any(address == "/1/p/gain" for address, _ in steady)
            assert replayed == [1]

            state.devices["node-a"]["online"] = False
            hb(bridge, device)
            reconnect_assign = deliver(wire, fleet)
            assert any(address == "/all/os/assign" for address, _ in reconnect_assign)
            hb(bridge, device)
            reconnect_params = deliver(wire, fleet)
            assert any(address == "/1/p/gain" for address, _ in reconnect_params)
            assert replayed == [1, 1]

            state.data["supervisor"] = {"mode": "simulate"}
            virtual = Device("audition-0001", "audition-0001", -1, "verify",
                             ephemeral=True)
            virtual.state = "running"
            fleet.devices = [virtual]
            hb(bridge, virtual)
            deliver(wire, fleet)
            hb(bridge, virtual)
            virtual_params = deliver(wire, fleet)
            assert any(address == "/1/p/gain" for address, _ in virtual_params)
            assert abs(virtual.params.get("gain", 0) - .73) < 1e-5

            dashboard = Dashboard.__new__(Dashboard)
            sent = []
            dashboard.osc = SimpleNamespace(
                set_param=lambda seat_id, identity, value:
                    sent.append((seat_id, identity, value)))
            dashboard.live_control_declarations = lambda: [{"identity": "gain"}]
            dashboard.replay_live_params_for_seat(state.data["seats"]["1"])
            assert sent == [(1, "gain", .73)]
            print("[PASS] assignment precedes converged parameter replay")
            print("[PASS] simulated node applies the replayed promoted value")
            print("[PASS] steady heartbeats do not form a resend loop")
            print("[PASS] reconnection produces one fresh converged replay")
            print("[PASS] managed Simulation devices use the same convergence gate")
            print("[PASS] staged declaration filtering excludes durable stale keys")
        finally:
            bridge_module.ASSIGN_REPLAY_MIN_SECONDS = old_limit
            bridge.close()
            fleet.sock.close()
            await state.close()


if __name__ == "__main__":
    asyncio.run(exercise())
