#!/usr/bin/env python3
"""Browser pass for the spatial map stitch.

Real dashboard + real simfleet, headless Chromium: devices start unplaced in
the tray, get dragged onto the room, gain a second speaker point, and the
positions + room bounds land in installation.json. Screenshots beside this
script.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def drag(page, source_box, dx, dy):
    x, y = source_box["x"] + source_box["width"] / 2, source_box["y"] + source_box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    for step in range(1, 11):
        page.mouse.move(x + dx * step / 10, y + dy * step / 10)
    page.mouse.up()


def main():
    with tempfile.TemporaryDirectory() as temp:
        state_file = os.path.join(temp, "installation.json")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"), "--port", "18083",
            "--listen-port", "15553", "--send-port", "16663", "--osc-target", "127.0.0.1",
            "--state-file", state_file,
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "3",
            "--target", "127.0.0.1", "--report-port", "15553", "--cmd-port", "16663",
            "--hb-interval", "1.0",
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        try:
            time.sleep(3)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 960})
                page.goto("http://127.0.0.1:18083/")
                page.wait_for_selector("#spatial g[data-uid]", timeout=10000)

                nodes = page.locator("#spatial g[data-uid]")
                check("all assigned devices on the map", nodes.count() == 3,
                      str(nodes.count()))
                room_box = page.locator("#spatial rect.room").bounding_box()
                tray_box = page.locator("#spatial rect.tray").bounding_box()
                first = nodes.first
                circle_box = first.locator("circle.p1").bounding_box()
                check("unplaced devices start in the tray",
                      circle_box["y"] > tray_box["y"] - 5, repr(circle_box))

                # click (no drag) selects the device
                uid = first.get_attribute("data-uid")
                first.locator("circle.p1").click()
                page.wait_for_selector("#detail dl", timeout=5000)
                check("click selects the device", uid in page.locator("#detail").inner_text())
                page.screenshot(path=os.path.join(HERE, "01-tray.png"))

                # drag from the tray into the room
                target_x = room_box["x"] + room_box["width"] * 0.3
                target_y = room_box["y"] + room_box["height"] * 0.4
                circle_box = first.locator("circle.p1").bounding_box()
                drag(page, circle_box,
                     target_x - circle_box["x"] - circle_box["width"] / 2,
                     target_y - circle_box["y"] - circle_box["height"] / 2)
                time.sleep(0.3)
                moved_box = page.locator(f'#spatial g[data-uid="{uid}"] circle.p1').bounding_box()
                check("drag places the device in the room",
                      abs(moved_box["x"] - target_x) < 25 and moved_box["y"] < tray_box["y"],
                      repr(moved_box))

                # double-click adds the second speaker point
                page.locator(f'#spatial g[data-uid="{uid}"] circle.p1').dblclick()
                page.wait_for_selector(f'#spatial g[data-uid="{uid}"] circle.p2', timeout=3000)
                check("dblclick adds pos2 + pair line",
                      page.locator(f'#spatial g[data-uid="{uid}"] line.pair').count() == 1)
                page.screenshot(path=os.path.join(HERE, "02-placed.png"))

                # room resize
                page.fill("#room-w", "20")
                page.dispatch_event("#room-w", "change")
                time.sleep(0.3)

                # positions + room persist to installation.json (debounced save)
                time.sleep(1.5)
                with open(state_file) as source:
                    saved = json.load(source)
                device = saved["devices"].get(uid, {})
                check("pos1 persisted", isinstance(device.get("pos1"), list)
                      and len(device["pos1"]) == 2, repr(device))
                check("pos2 persisted", isinstance(device.get("pos2"), list), repr(device))
                check("room persisted", saved.get("room", {}).get("width") == 20,
                      repr(saved.get("room")))
                in_room = device.get("pos1") or [99, 99]
                check("pos1 within room bounds", 0 <= in_room[0] <= 20 and 0 <= in_room[1] <= 8,
                      repr(in_room))

                # second browser sees the placement (multi-browser sync)
                page2 = browser.new_page(viewport={"width": 1280, "height": 960})
                page2.goto("http://127.0.0.1:18083/")
                page2.wait_for_selector(f'#spatial g[data-uid="{uid}"] circle.p2', timeout=5000)
                check("second browser sees the placement", True)

                # drag back into the tray unplaces
                moved_box = page.locator(f'#spatial g[data-uid="{uid}"] circle.p1').bounding_box()
                tray_box = page.locator("#spatial rect.tray").bounding_box()
                drag(page, moved_box, 0, tray_box["y"] + 20 - moved_box["y"])
                time.sleep(1.5)
                with open(state_file) as source:
                    saved = json.load(source)
                check("tray drop unplaces (pos cleared)",
                      saved["devices"].get(uid, {}).get("pos1") is None,
                      repr(saved["devices"].get(uid)))
                browser.close()
        finally:
            fleet.terminate()
            server.terminate()
            fleet.wait(timeout=5)
            server.wait(timeout=5)
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("spatial checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
