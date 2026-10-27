"""Real dashboard + four physical-protocol peers: the Devices roster order.

The roster used to sort by last heartbeat, so rows swapped places every few
seconds. It now holds a chosen order (name, seat, status, signal, IP, patch
problems) with name and uid as tie-breaks, and remembers the choice.
"""
import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from verify_log_destination import (PhysicalPeer, free_port, physical_host,
                                    wait_http, stop, write_fixture, ROOT)
from project_fixture import data_root, project_path

# uid -> (alias, seat id or -1, rssi or None); listed in no meaningful order.
PEERS = {
    "02:53:49:4d:00:11": ("Cara Moss", -1, -55),
    "02:53:49:4d:00:12": ("Abel Fern", 1, -70),
    "02:53:49:4d:00:13": ("Dora Vale", 0, None),
    "02:53:49:4d:00:14": ("Bea Lark", -1, -40),
}
UIDS = list(PEERS)


class RosterPeers(PhysicalPeer):
    beat = 0

    def heartbeat(self):
        # Rotate the send order so a heartbeat-driven sort would reshuffle.
        self.beat += 1
        shift = self.beat % len(UIDS)
        for uid in UIDS[shift:] + UIDS[:shift]:
            alias, seat, rssi = PEERS[uid]
            args = [uid, seat, "physical-test", 1] + ([rssi] if rssi is not None else [])
            self.send("/hb", *args)


def write_roster_fixture(root):
    patches, assets, state, manifest = write_fixture(root)
    data = json.loads(Path(state).read_text(encoding="utf-8"))
    data["seats"] = {
        str(seat): {"id": seat, "name": f"Seat {seat}", "bound": uid,
                    "positions": [], "params": {}}
        for uid, (_alias, seat, _rssi) in PEERS.items() if seat >= 0}
    data["device_registry"] = {
        uid: {"alias": alias, "source": "custom", "generator": 2, "device_enabled": True}
        for uid, (alias, _seat, _rssi) in PEERS.items()}
    Path(state).write_text(json.dumps(data), encoding="utf-8")
    return patches, assets, state, manifest


def roster(page):
    return page.evaluate(
        "() => [...document.querySelectorAll('#device-roster .device-row')]"
        ".map(row => row.querySelector('strong').textContent)")


def main():
    failures = []

    def check(label, condition, detail=""):
        print(("PASS " if condition else "FAIL ") + label + (f" — {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(label)

    with tempfile.TemporaryDirectory(prefix="bopos-roster-") as root:
        patches, assets, state, manifest = write_roster_fixture(root)
        host = physical_host()
        http_port = free_port(socket.SOCK_STREAM)
        report_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM, host)
        # Private input and stream ports, so a dashboard already running on
        # this machine (5551/5552) does not stop this one starting.
        input_port = free_port(socket.SOCK_DGRAM)
        stream_port = free_port(socket.SOCK_DGRAM)
        base = f"http://127.0.0.1:{http_port}"
        peer = RosterPeers(host, command_port, report_port, manifest)
        with (Path(root) / "dashboard.log").open("w") as output:
            dashboard = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard/server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(report_port), "--send-port", str(command_port),
                "--input-port", str(input_port), "--stream-port", str(stream_port),
                "--osc-target", host, "--data-dir", data_root(str(state)),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base,
            ], cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
            try:
                peer.start(); wait_http(base, dashboard)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(base + "#devices")
                    page.wait_for_function(
                        "uids => uids.every(uid => installation.devices?.[uid]?.online)", arg=UIDS)

                    by_name = ["Abel Fern", "Bea Lark", "Cara Moss", "Dora Vale"]
                    check("the roster sorts by name by default",
                          page.locator("#device-sort").input_value() == "name"
                          and roster(page) == by_name, repr(roster(page)))
                    seen = set()
                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline:
                        seen.add(tuple(roster(page)))
                        time.sleep(0.1)
                    check("heartbeats arriving in a rotating order never move a row",
                          seen == {tuple(by_name)}, repr(seen))

                    page.locator("#device-sort").select_option("seat")
                    check("seat order puts bound seats first, by id, then unbound by name",
                          roster(page) == ["Dora Vale", "Abel Fern", "Bea Lark", "Cara Moss"],
                          repr(roster(page)))
                    page.locator("#device-sort").select_option("signal")
                    check("signal order puts the strongest first and unreported last",
                          roster(page) == ["Bea Lark", "Cara Moss", "Abel Fern", "Dora Vale"],
                          repr(roster(page)))
                    page.locator("#device-filter").select_option("unbound")
                    check("the show filter still applies within the chosen order",
                          roster(page) == ["Bea Lark", "Cara Moss"], repr(roster(page)))
                    page.locator("#device-filter").select_option("all")

                    page.reload()
                    page.wait_for_function(
                        "uids => uids.every(uid => installation.devices?.[uid]?.online)", arg=UIDS)
                    check("the chosen order survives a reload",
                          page.locator("#device-sort").input_value() == "signal"
                          and roster(page) == ["Bea Lark", "Cara Moss", "Abel Fern", "Dora Vale"],
                          repr(roster(page)))

                    page.set_viewport_size({"width": 390, "height": 844})
                    page.wait_for_timeout(100)
                    check("the roster controls fit a phone width",
                          page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                    check("the roster emitted no page errors", not errors, repr(errors))
                    browser.close()
            finally:
                peer.close(); stop(dashboard)
    if failures:
        raise SystemExit(f"{len(failures)} roster check(s) failed")
    print("Device roster sort checks passed")


if __name__ == "__main__":
    main()
