#!/usr/bin/env python3
"""Playwright verification for spatial-1 point authoring and wall bounce."""
import json
import os
import re
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
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def change(page, selector, value):
    page.fill(selector, str(value))
    page.dispatch_event(selector, "change")


def drag_to(page, source, target_x, target_y):
    box = source.bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    for step in range(1, 13):
        page.mouse.move(x + (target_x - x) * step / 12,
                        y + (target_y - y) * step / 12)
    page.mouse.up()


def transform_xy(value):
    match = re.search(r"translate\(([-0-9.eE]+)[ ,]([-0-9.eE]+)\)", value or "")
    return (float(match.group(1)), float(match.group(2))) if match else None


def bounce_unit_checks():
    sys.path.insert(0, os.path.join(REPO, "dashboard"))
    import points
    point = points.sanitize_point({"id": 0, "x": 2, "y": 3,
                                   "motion": {"type": "bounce", "velocity": [3, 2]}},
                                  {"width": 10, "depth": 8})
    check("bounce sanitizer captures origin, velocities, and room bounds",
          point["motion"] == {"type": "bounce", "origin": [2.0, 3.0],
                              "velocity": [3.0, 2.0], "bounds": [10.0, 8.0]},
          repr(point["motion"]))
    check("bounce reflection is deterministic on both axes",
          points.current_xy(point, 3) == (9.0, 7.0)
          and points.current_xy(point, 4) == (6.0, 5.0))


def main():
    bounce_unit_checks()
    with tempfile.TemporaryDirectory() as temp:
        state_file = os.path.join(temp, "installation.json")
        devices = {
            "02:53:49:4d:00:01": {"id": 1, "name": "left", "pos1": [2, 4],
                                    "pos2": [3, 4], "params": {}},
            "02:53:49:4d:00:02": {"id": 2, "name": "right", "pos1": [8, 4],
                                    "params": {}},
        }
        with open(state_file, "w", encoding="utf-8") as target:
            json.dump({"name": "spatial-authoring", "room": {"width": 10, "depth": 8},
                       "devices": devices}, target)
        sim_state = os.path.join(temp, "sim-state")
        os.makedirs(sim_state)
        for uid, values in devices.items():
            positions = []
            for key in ("pos1", "pos2"):
                if values.get(key):
                    positions.extend(values[key])
            with open(os.path.join(sim_state, uid.replace(":", "-") + ".json"),
                      "w", encoding="utf-8") as target:
                json.dump({"id": values["id"], "name": values["name"],
                           "positions": positions}, target)
        fleet_path = os.path.join(temp, "fleet.log")
        fleet_log = open(fleet_path, "w", encoding="utf-8")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"),
            "--port", "18096", "--listen-port", "15566", "--send-port", "16676",
            "--osc-target", "127.0.0.1", "--state-file", state_file,
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "2",
            "--target", "127.0.0.1", "--report-port", "15566", "--cmd-port", "16676",
            "--hb-interval", "1", "--boot-secs", "1", "--state-dir", sim_state,
        ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)
        try:
            time.sleep(2)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1400, "height": 1100})
                page.goto("http://127.0.0.1:18096/")
                page.wait_for_selector("#spatial g.node[data-uid]", timeout=10000)
                check("one node group per device",
                      page.locator("#spatial g.node[data-uid]").count() == 2)
                check("true elements render inside their device",
                      page.locator('#spatial g.node[data-uid="02:53:49:4d:00:01"] .element').count() == 2)
                colours = page.locator('#spatial g.node[data-uid="02:53:49:4d:00:01"] .element-dot').evaluate_all(
                    "els => els.map(el => el.getAttribute('fill'))")
                numbers = page.locator('#spatial g.node[data-uid="02:53:49:4d:00:01"] .element-number').evaluate_all(
                    "els => els.map(el => el.textContent)")
                check("element index is colour; device is number",
                      len(set(colours)) == 2 and numbers == ["1", "1"], repr((colours, numbers)))

                page.click("#point-add")
                page.wait_for_selector('[data-point-id="0"]', timeout=5000)
                check("point editor opens for arbitrary point 0",
                      not page.locator("#point-editor").is_hidden()
                      and page.locator("#point-title").inner_text() == "Point 0")
                change(page, "#point-radius", 4)
                page.select_option("#point-falloff", "0")
                page.dispatch_event("#point-falloff", "change")
                page.wait_for_timeout(200)
                check("radius and falloff authoring update SVG",
                      abs(float(page.locator('[data-radius-id="0"]').get_attribute("r")) - 4) < 0.01)

                # Display-only falloff: drag from centre onto device 1. The
                # element opacity must rise while distant device 2 falls.
                before_left = float(page.locator('[data-uid="02:53:49:4d:00:01"] .p1').get_attribute("fill-opacity"))
                room = page.locator("#spatial .room").bounding_box()
                page.evaluate("window.scrollTo(0, 0)")
                room = page.locator("#spatial .room").bounding_box()
                target_x = room["x"] + room["width"] * 0.2
                target_y = room["y"] + room["height"] * 0.5
                drag_to(page, page.locator('[data-point-id="0"] .point-handle'), target_x, target_y)
                page.wait_for_timeout(300)
                after_left = float(page.locator('[data-uid="02:53:49:4d:00:01"] .p1').get_attribute("fill-opacity"))
                after_right = float(page.locator('[data-uid="02:53:49:4d:00:02"] .p1').get_attribute("fill-opacity"))
                check("display mirrors falloff without sending gains",
                      after_left > before_left and after_left > after_right,
                      repr((before_left, after_left, after_right)))

                # Bounce is deliberately fast enough to hit both wall pairs
                # during the sample window.
                page.select_option("#point-motion", "bounce")
                page.dispatch_event("#point-motion", "change")
                change(page, "#point-vx", 6)
                change(page, "#point-vy", 5)
                samples = []
                for _ in range(18):
                    page.wait_for_timeout(250)
                    xy = transform_xy(page.locator('[data-point-id="0"]').get_attribute("transform"))
                    if xy:
                        samples.append(xy)
                dx = [b[0] - a[0] for a, b in zip(samples, samples[1:])]
                dy = [b[1] - a[1] for a, b in zip(samples, samples[1:])]
                check("bounce traverses both x and y",
                      max(x for x, _ in samples) - min(x for x, _ in samples) > 4
                      and max(y for _, y in samples) - min(y for _, y in samples) > 3,
                      repr(samples))
                check("bounce reflects from walls on both axes",
                      any(value > 0 for value in dx) and any(value < 0 for value in dx)
                      and any(value > 0 for value in dy) and any(value < 0 for value in dy),
                      repr((dx, dy)))

                change(page, "#room-w", 6)
                change(page, "#room-d", 5)
                page.wait_for_timeout(500)
                resized = transform_xy(page.locator('[data-point-id="0"]').get_attribute("transform"))
                check("active bounce adopts resized room walls",
                      resized is not None and 0 <= resized[0] <= 6 and 0 <= resized[1] <= 5,
                      repr(resized))

                # Off keeps the draft in the editor but clears the wire point;
                # on restores it, then delete removes it completely.
                page.uncheck("#point-enabled")
                page.wait_for_timeout(250)
                check("off clears point but retains editable draft",
                      page.locator('[data-point-id="0"]').count() == 0
                      and not page.locator("#point-editor").is_hidden())
                page.check("#point-enabled")
                page.wait_for_selector('[data-point-id="0"]', timeout=3000)
                page.screenshot(path=os.path.join(HERE, "spatial-authoring.png"))
                page.click("#point-delete")
                page.wait_for_timeout(200)
                check("delete removes point and editor", page.locator('[data-point-id="0"]').count() == 0
                      and page.locator("#point-editor").is_hidden())
                browser.close()
        finally:
            fleet.terminate(); server.terminate()
            fleet.wait(timeout=5); server.wait(timeout=5); fleet_log.close()

        log_text = open(fleet_path, encoding="utf-8").read()
        values = [float(value) for value in re.findall(r"pt 0 el0 v=([0-9.]+)", log_text)]
        check("simfleet consumed changing node-side proximity",
              len(set(values)) > 5, repr(values[-20:]))
        check("point clear released proximity to zero",
              any(value == 0 for value in values), repr(values[-20:]))

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("spatial authoring checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
