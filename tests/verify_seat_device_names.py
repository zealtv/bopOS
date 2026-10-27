"""Real dashboard + physical-protocol peers: device names on the Seats tab.

A "Device names" toggle labels each Seat on the map with its bound device's
name and adds the name to the Seat list rows. It is off by default and
remembered per viewer (81-seats-tab/2-seat-device-names).
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright
from verify_device_roster_sort import RosterPeers, UIDS, write_roster_fixture
from verify_log_destination import free_port, physical_host, wait_http, stop, ROOT
from project_fixture import data_root

SHOTS = os.environ.get("BOPOS_SHOTS")
DORA, ABEL = "02:53:49:4d:00:13", "02:53:49:4d:00:12"


def write_names_fixture(root):
    patches, assets, state, manifest = write_roster_fixture(root)
    data = json.loads(Path(state).read_text(encoding="utf-8"))
    data["room"] = {"width": 10, "depth": 8, "origin": [0, 0]}
    data["seats"] = {
        # Seat 0 is paired: two elements, one label.
        "0": {"id": 0, "name": "Seat 0", "bound": DORA,
              "positions": [[2.0, 2.0], [4.0, 2.0]], "params": {}},
        "1": {"id": 1, "name": "Seat 1", "bound": ABEL,
              "positions": [[6.0, 5.0]], "params": {}},
        "2": {"id": 2, "name": "Seat 2", "bound": None,
              "positions": [[8.0, 2.0]], "params": {}},
    }
    Path(state).write_text(json.dumps(data), encoding="utf-8")
    return patches, assets, state, manifest


def labels(page):
    return page.evaluate("""() => [...document.querySelectorAll('#spatial .seat-device-label')]
        .map(label => [label.closest('g[data-seat-id]').dataset.seatId, label.textContent])""")


def list_names(page):
    return page.evaluate("""() => [...document.querySelectorAll('#assigned .seat-device-name')]
        .map(name => name.textContent)""")


def main():
    failures = []

    def check(label, condition, detail=""):
        print(("PASS " if condition else "FAIL ") + label + (f" — {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(label)

    with tempfile.TemporaryDirectory(prefix="bopos-seat-names-") as root:
        patches, assets, state, manifest = write_names_fixture(root)
        host = physical_host()
        http_port = free_port(socket.SOCK_STREAM)
        report_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM, host)
        base = f"http://127.0.0.1:{http_port}"
        peer = RosterPeers(host, command_port, report_port, manifest)
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
                    page.goto(base + "#seats")
                    page.wait_for_function(
                        "uids => uids.every(uid => installation.devices?.[uid]?.online)", arg=UIDS)

                    toggle = page.locator("#seat-device-names")
                    check("the toggle defaults to off with no labels",
                          not toggle.is_checked() and labels(page) == [] and list_names(page) == [],
                          repr((toggle.is_checked(), labels(page), list_names(page))))
                    title = page.locator('#spatial g[data-seat-id="1"] > title').text_content()
                    check("the Seat tooltip names its device even with labels off",
                          "Abel Fern" in title, repr(title))

                    toggle.check()
                    check("labels name each bound Seat's device once, unbound Seats get none",
                          sorted(labels(page)) == [["0", "Dora Vale"], ["1", "Abel Fern"]], repr(labels(page)))
                    check("the Seat list rows name their devices",
                          list_names(page) == ["Dora Vale", "Abel Fern"], repr(list_names(page)))
                    page.wait_for_timeout(2500)  # several heartbeat re-renders
                    check("labels survive heartbeat re-renders",
                          sorted(labels(page)) == [["0", "Dora Vale"], ["1", "Abel Fern"]], repr(labels(page)))
                    pointer = page.evaluate(
                        "getComputedStyle(document.querySelector('#spatial .seat-device-label')).pointerEvents")
                    check("labels never take the pointer", pointer == "none", pointer)
                    if SHOTS:
                        theme = page.evaluate("document.documentElement.dataset.theme")
                        for shown in ("dark", "light"):
                            page.evaluate("t => document.documentElement.dataset.theme = t", shown)
                            page.locator("#spatial-section").screenshot(
                                path=os.path.join(SHOTS, f"names-{shown}.png"))
                        page.evaluate("t => document.documentElement.dataset.theme = t", theme)

                    dot = page.locator('#spatial g[data-seat-id="1"] .element-dot').bounding_box()
                    room = page.locator("#spatial .room").bounding_box()
                    page.mouse.move(dot["x"] + dot["width"] / 2, dot["y"] + dot["height"] / 2)
                    page.mouse.down()
                    page.mouse.move(room["x"] + room["width"] * 0.3, room["y"] + room["height"] * 0.8, steps=8)
                    page.mouse.up()
                    page.wait_for_function(
                        "() => (installation.seats['1'].positions[0] || [9])[0] < 4")
                    check("a labelled Seat still drags", True)

                    page.reload()
                    page.wait_for_function(
                        "uids => uids.every(uid => installation.devices?.[uid]?.online)", arg=UIDS)
                    page.wait_for_selector("#spatial .seat-device-label")
                    check("the toggle survives a reload",
                          page.locator("#seat-device-names").is_checked()
                          and sorted(labels(page)) == [["0", "Dora Vale"], ["1", "Abel Fern"]],
                          repr(labels(page)))

                    page.set_viewport_size({"width": 390, "height": 844})
                    page.wait_for_timeout(150)
                    check("no horizontal scroll at 390 px",
                          page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                    if SHOTS:
                        page.locator("#spatial-section").screenshot(path=os.path.join(SHOTS, "names-390.png"))
                    page.locator("#seat-device-names").uncheck()
                    check("turning it off clears the labels", labels(page) == [] and list_names(page) == [])
                    check("the Seats tab emitted no page errors", not errors, repr(errors))
                    browser.close()
            finally:
                peer.close(); stop(dashboard)
    if failures:
        raise SystemExit(f"{len(failures)} seat name check(s) failed")
    print("Seat device name checks passed")


if __name__ == "__main__":
    main()
