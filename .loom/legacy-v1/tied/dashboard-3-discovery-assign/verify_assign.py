#!/usr/bin/env python3
"""Browser pass for dashboard-3-discovery-assign.

Real dashboard + real simfleet with two unassigned devices and a node-side
state dir. Drives the whole story: unassigned pool appears, identify flashes
one box, assign pushes /os/assign, the node persists it, the device joins
the assigned list, positions ride a follow-up assign when dragged onto the
map, ID collisions are refused, and bopos.devices exports the result.
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


def main():
    with tempfile.TemporaryDirectory() as temp:
        state_file = os.path.join(temp, "installation.json")
        node_state = os.path.join(temp, "nodes")
        fleet_log = open(os.path.join(temp, "fleet.log"), "w")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"), "--port", "18084",
            "--listen-port", "15554", "--send-port", "16664", "--osc-target", "127.0.0.1",
            "--state-file", state_file,
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "4",
            "--unassigned", "2", "--state-dir", node_state, "--target", "127.0.0.1",
            "--report-port", "15554", "--cmd-port", "16664", "--hb-interval", "1.0",
        ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)
        try:
            time.sleep(3)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 960})
                dialogs = []
                page.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
                page.goto("http://127.0.0.1:18084/")

                # unassigned pool fills from fast heartbeats, keyed by uid
                page.wait_for_selector("#unassigned .device-row", timeout=10000)
                unassigned = page.locator("#unassigned .device-row")
                check("unassigned pool shows both new boxes", unassigned.count() == 2,
                      str(unassigned.count()))

                first_uid = unassigned.first.get_attribute("data-uid")
                unassigned.first.click()
                page.wait_for_selector("#assign-send", timeout=5000)
                check("assign form with next-free id",
                      page.locator("#assign-id").input_value() == "3",
                      page.locator("#assign-id").input_value())
                check("params/actions hidden while unassigned",
                      page.locator('[data-action="update"]').count() == 0)
                page.screenshot(path=os.path.join(HERE, "01-assign-form.png"))

                # identify goes uid-targeted
                page.click("[data-identify]")
                time.sleep(1.0)

                # assign: name + id, then the node acks and joins the list
                page.fill("#assign-name", "planter nw")
                page.click("#assign-send")
                page.wait_for_selector(f'#assigned .device-row[data-uid="{first_uid}"]',
                                       timeout=8000)
                check("assigned list gains the device", True)
                # inner_text applies the row's text-transform:capitalize, so lowercase
                check("sanitised name shown",
                      "planter-nw" in page.locator(
                          f'.device-row[data-uid="{first_uid}"]').inner_text().lower())

                # node-side persistence (simfleet writes its state dir)
                time.sleep(1.0)
                node_file = os.path.join(node_state, first_uid.replace(":", "-") + ".json")
                saved = json.load(open(node_file)) if os.path.exists(node_file) else {}
                check("node persisted the assignment",
                      saved.get("id") == 3 and saved.get("name") == "planter-nw", repr(saved))

                # clicking the assign button auto-scrolled the page; bring the
                # map back to the top so its tray is on-screen for the drag
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(200)

                # drag onto the map -> positions ride a follow-up /os/assign
                room_box = page.locator("#spatial rect.room").bounding_box()
                circle = page.locator(f'#spatial g[data-uid="{first_uid}"] circle.p1')
                box = circle.bounding_box()
                x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                # the room can extend past the viewport top; keep the target on-screen
                # and safely inside the room rectangle
                tx = room_box["x"] + room_box["width"] * 0.5
                ty = min(max(room_box["y"] + room_box["height"] * 0.5, 60),
                         min(room_box["y"] + room_box["height"] - 40, 900))
                page.mouse.move(x, y); page.mouse.down()
                for step in range(1, 11):
                    page.mouse.move(x + (tx - x) * step / 10, y + (ty - y) * step / 10)
                page.mouse.up()
                time.sleep(1.0)
                saved = json.load(open(node_file))
                check("node persisted the position",
                      len(saved.get("positions") or []) == 2, repr(saved))

                # id collision is refused with an explanation
                page.locator("#unassigned .device-row").first.click()
                page.wait_for_selector("#assign-send", timeout=5000)
                page.fill("#assign-name", "dupe")
                page.fill("#assign-id", "3")
                page.click("#assign-send")
                for _ in range(30):
                    if dialogs:
                        break
                    page.wait_for_timeout(100)
                check("id collision refused", dialogs and "already" in dialogs[-1],
                      repr(dialogs))

                # export reflects the new assignment
                export = page.evaluate("fetch('/bopos.devices').then(r => r.text())")
                check("bopos.devices export has the new row",
                      f"{first_uid}, planter-nw, 3" in export, export)
                page.screenshot(path=os.path.join(HERE, "02-assigned.png"))
                browser.close()
        finally:
            fleet.terminate()
            server.terminate()
            fleet.wait(timeout=5)
            server.wait(timeout=5)
            fleet_log.close()
            log_text = open(fleet_log.name).read()
            check("simfleet saw a uid-targeted identify", "identify" in log_text)
            check("simfleet logged the assignment", "assigned id=3 name=planter-nw" in log_text)
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("assign checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
