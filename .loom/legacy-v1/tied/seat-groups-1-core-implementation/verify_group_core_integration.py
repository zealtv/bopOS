#!/usr/bin/env python3
"""Combined dashboard-to-simfleet verification for the Seat-group core."""

import asyncio
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "dashboard" / "osc_bridge.py").is_file():
            return parent
    raise RuntimeError("could not locate repository root")


ROOT = repo_root()
sys.path[:0] = [str(ROOT), str(ROOT / "dashboard"), str(ROOT / "tools")]

from pythonosc.osc_message import OscMessage  # noqa: E402
from osc_bridge import OSCBridge  # noqa: E402
from state import InstallationState  # noqa: E402
from simfleet import Device, SimFleet  # noqa: E402


class DatagramQueue:
    def __init__(self):
        self.frames = []

    def sendto(self, data, target):
        self.frames.append((data, target))

    def close(self):
        pass


def seat(seat_id, groups, uid=None, gain=0.0):
    return {
        "id": seat_id,
        "name": f"Seat {seat_id}",
        "positions": [[float(seat_id), 1.0]],
        "params": {"gain0": gain},
        "groups": list(groups),
        "bound": uid,
    }


def decoded(frames):
    return [(OscMessage(data).address, list(OscMessage(data).params))
            for data, _target in frames]


async def verify():
    with tempfile.TemporaryDirectory(prefix="bopos-group-core-") as directory:
        state = InstallationState(str(Path(directory) / "installation.json"))
        state.data["groups"] = {"3": {"id": 3, "name": "Front"}}
        state.data["next_group_id"] = 4
        state.data["seats"] = {
            "1": seat(1, [3], "node-a", 0.1),
            "2": seat(2, [3], None, 0.2),
        }
        runtime = state.ensure("node-a")
        runtime.update(id=1, ip="127.0.0.1", online=True)

        bridge = OSCBridge(state, lambda _kind, _data: None,
                           0, 16660, "127.0.0.1")
        dashboard_wire = DatagramQueue()
        bridge.sender = dashboard_wire

        args = SimpleNamespace(
            cmd_port=0, target="127.0.0.1", report_port=5550,
            state_dir=directory, sync_skew_ms=0.0, drop=0.0,
            jitter_ms=0.0, hb_interval=0.5, boot_secs=0.1,
            manifest=None,
        )
        device = Device("node-a", "Seat 1", 1, "abc1234")
        device.state = "running"
        fleet = SimFleet(args, [device])
        fleet.sock.close()
        node_wire = DatagramQueue()
        fleet.sock = node_wire

        assert bridge.send_groups("node-a")
        assert decoded(dashboard_wire.frames) == [
            ("/all/os/groups", ["node-a", 3])]
        for datagram, _target in dashboard_wire.frames:
            fleet.receive_contract(datagram, ("127.0.0.1", 16660))
        assert device.groups == (3,)
        assert decoded(node_wire.frames) == [("/os/groups", ["node-a", 3])]
        for datagram, _target in node_wire.frames:
            message = OscMessage(datagram)
            bridge.handle(message.address, list(message.params), "127.0.0.1")
        assert state.devices["node-a"]["group_sync"]["status"] == "current"
        assert "node-a" not in bridge._group_pending

        dashboard_wire.frames.clear()
        members = bridge.set_group_param(3, "gain0", 0.75)
        assert [member["id"] for member in members] == [1, 2]
        assert state.seats["1"]["params"]["gain0"] == 0.75
        assert state.seats["2"]["params"]["gain0"] == 0.75
        assert decoded(dashboard_wire.frames) == [("/g3/p/gain0", [0.75])]
        for datagram, _target in dashboard_wire.frames:
            fleet.receive_contract(datagram, ("127.0.0.1", 16660))
        assert device.params["gain0"] == 0.75

        bridge.close()
        fleet.sock.close()
        await state.close()


def main():
    try:
        asyncio.run(verify())
    except Exception as error:
        print(f"[FAIL] dashboard-to-simfleet group convergence -- {error}")
        return 1
    print("[PASS] dashboard-to-simfleet group convergence and parameter fan-out")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
