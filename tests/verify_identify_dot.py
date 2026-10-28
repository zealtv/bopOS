"""Real dashboard + physical-protocol peers: identify from a status dot.

Clicking a device's status dot on the Devices roster, or a Seat card's dot on
the Remote, sends `/all/os/to <uid> identify` for that device. Remote Seat
cards also name their device (83-identify-from-status-dot).
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from verify_device_roster_sort import RosterPeers, UIDS, write_roster_fixture
from verify_log_destination import free_port, physical_host, wait_http, stop, ROOT
from project_fixture import data_root

SHOTS = os.environ.get("BOPOS_SHOTS")
DORA, ABEL, CARA = "02:53:49:4d:00:13", "02:53:49:4d:00:12", "02:53:49:4d:00:11"


def write_identify_fixture(root):
    patches, assets, state, manifest = write_roster_fixture(root)
    data = json.loads(Path(state).read_text(encoding="utf-8"))
    # Seat 0 = Dora, Seat 1 = Abel (as in the roster fixture), Seat 2 unbound.
    data["seats"]["2"] = {"id": 2, "name": "Seat 2", "bound": None,
                          "positions": [], "params": {}}
    Path(state).write_text(json.dumps(data), encoding="utf-8")
    return patches, assets, state, manifest


def main():
    failures = []

    def check(label, condition, detail=""):
        print(("PASS " if condition else "FAIL ") + label + (f" — {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(label)

    with tempfile.TemporaryDirectory(prefix="bopos-identify-") as root:
        patches, assets, state, manifest = write_identify_fixture(root)
        host = physical_host()
        http_port = free_port(socket.SOCK_STREAM)
        report_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM, host)
        base = f"http://127.0.0.1:{http_port}"
        peer = RosterPeers(host, command_port, report_port, manifest)

        def identified():
            with peer.lock:
                return [args[0] for address, args in peer.frames
                        if address == "/all/os/to" and len(args) >= 2 and args[1] == "identify"]

        def wait_identified(uid, before):
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if identified()[before:] == [uid]:
                    return True
                time.sleep(0.05)
            return False

        with (Path(root) / "dashboard.log").open("w") as output:
            dashboard = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard/server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(report_port), "--send-port", str(command_port),
                "--input-port", str(free_port(socket.SOCK_DGRAM)),
                "--stream-port", str(free_port(socket.SOCK_DGRAM)),
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

                    # Devices tab
                    page.locator(f'#device-roster [data-uid="{ABEL}"]').click()
                    before = len(identified())
                    page.locator(f'#device-roster [data-identify-uid="{CARA}"]').click()
                    check("a roster dot click identifies that device",
                          wait_identified(CARA, before), repr(identified()[before:]))
                    selected = page.evaluate(
                        "() => document.querySelector('#device-roster .device-row.selected')?.dataset.uid")
                    check("the dot click leaves the selection alone", selected == ABEL, repr(selected))
                    check("the dot pulses after the click",
                          page.locator(f'#device-roster [data-identify-uid="{CARA}"].identify-pulse').count() == 1)
                    iterations = page.evaluate(
                        "() => getComputedStyle(document.querySelector('#device-roster .identify-pulse')).animationIterationCount")
                    check("the pulse is finite, not a lasting state", iterations == "2", iterations)

                    # Remote
                    remote = browser.new_page(viewport={"width": 390, "height": 844})
                    remote.on("pageerror", lambda error: errors.append(str(error)))
                    remote.goto(base + "/facilitator")
                    remote.wait_for_selector('.seat-card[data-live-id="0"] .dot-identify')
                    meta = remote.locator('.seat-card[data-live-id="0"] .name small').text_content()
                    check("a Remote Seat card names its device", meta == "Seat 0 · Dora Vale · online", repr(meta))
                    unbound = remote.locator('.seat-card[data-live-id="2"]')
                    check("an unbound Seat card has no identify button and no name",
                          unbound.locator(".dot-identify").count() == 0
                          and unbound.locator(".name small").text_content() == "Seat 2 · unbound",
                          repr(unbound.locator(".name small").text_content()))
                    box = remote.locator('.seat-card[data-live-id="1"] .dot-identify').bounding_box()
                    check("the Remote dot has a finger-sized target",
                          box["width"] >= 28 and box["height"] >= 28, repr(box))
                    before = len(identified())
                    remote.locator('.seat-card[data-live-id="1"] .dot-identify').click()
                    check("a Remote dot tap identifies the Seat's device",
                          wait_identified(ABEL, before), repr(identified()[before:]))
                    check("no horizontal scroll on the Remote at 390 px",
                          remote.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                    if SHOTS:
                        remote.locator('.seat-card[data-live-id="1"]').screenshot(
                            path=os.path.join(SHOTS, "remote-seat-card.png"))

                    page.goto(base + "#control")
                    page.wait_for_timeout(500)
                    check("the desktop dashboard has no Remote identify buttons",
                          page.locator(".dot-identify").count() == 0)
                    check("no page errors", not errors, repr(errors))
                    browser.close()
            finally:
                peer.close(); stop(dashboard)
    if failures:
        raise SystemExit(f"{len(failures)} identify check(s) failed")
    print("Identify dot checks passed")


if __name__ == "__main__":
    main()
