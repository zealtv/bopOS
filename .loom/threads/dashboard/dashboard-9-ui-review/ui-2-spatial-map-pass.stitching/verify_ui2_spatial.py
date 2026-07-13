#!/usr/bin/env python3
"""Playwright verification for the ui-2 spatial map interaction pass."""
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
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def transform_xy(value):
    match = re.search(r"translate\(([-0-9.eE]+)[ ,]([-0-9.eE]+)\)", value or "")
    return (float(match.group(1)), float(match.group(2))) if match else None


def drag(page, locator, x, y):
    box = locator.bounding_box()
    start_x = box["x"] + box["width"] / 2
    start_y = box["y"] + box["height"] / 2
    page.mouse.move(start_x, start_y)
    page.mouse.down()
    for step in range(1, 11):
        page.mouse.move(start_x + (x - start_x) * step / 10,
                        start_y + (y - start_y) * step / 10)
    page.mouse.up()


def main():
    with tempfile.TemporaryDirectory() as temp:
        state_file = os.path.join(temp, "installation.json")
        with open(state_file, "w", encoding="utf-8") as target:
            json.dump({
                "name": "ui2-spatial",
                "room": {"width": 10, "depth": 8, "units": "m"},
                "listener": {"x": 5, "y": 4, "heading": 0},
                "devices": {
                    "02:53:49:4d:20:00": {
                        "id": 0, "name": "element-zero", "pos1": [2, 4],
                    }
                },
            }, target)
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"),
            "--port", "18105", "--listen-port", "15575", "--send-port", "16685",
            "--osc-target", "127.0.0.1", "--state-file", state_file,
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        try:
            time.sleep(1)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1400, "height": 1000})
                page.goto("http://127.0.0.1:18105/")
                page.wait_for_selector("#spatial .listener-tip", timeout=10000)
                page.evaluate("window.scrollTo(0, 0)")

                check("listener number input is removed",
                      page.locator("#listener-heading").count() == 0)
                body = page.locator("#spatial .listener-body").bounding_box()
                tip = page.locator("#spatial .listener-tip")
                drag(page, tip, body["x"] + body["width"] / 2 + 55,
                     body["y"] + body["height"] / 2)
                page.wait_for_function(
                    "() => parseInt(document.querySelector('#listener-heading-readout').value) >= 80",
                    timeout=5000)
                heading = page.locator("#listener-heading-readout").evaluate(
                    "element => element.value")
                check("heading handle drag turns the listener dial",
                      80 <= int(heading.rstrip("°")) <= 100, heading)

                dot = page.locator(".element-dot").first
                opacity_before = dot.get_attribute("fill-opacity")
                page.click("#point-add")
                page.wait_for_selector('[data-point-id="0"]', timeout=5000)
                room = page.locator("#spatial .room").bounding_box()
                drag(page, page.locator('[data-point-id="0"] .point-handle'),
                     room["x"] + room["width"] * 0.2,
                     room["y"] + room["height"] * 0.5)
                page.wait_for_timeout(200)
                opacity_after = page.locator(".element-dot").first.get_attribute("fill-opacity")
                check("element opacity stays constant as point amplitude changes",
                      opacity_before == opacity_after == "0.9",
                      repr((opacity_before, opacity_after)))
                field = page.locator('[data-radius-id="0"]')
                check("point has a coloured falloff indicator",
                      field.evaluate("element => getComputedStyle(element).stroke")
                      != "none")

                page.select_option("#point-motion", "bounce")
                page.dispatch_event("#point-motion", "change")
                page.wait_for_timeout(250)
                point = page.locator('[data-point-id="0"]')
                before_size = transform_xy(point.get_attribute("transform"))
                page.fill("#point-radius", "20")
                page.dispatch_event("#point-radius", "change")
                after_size = transform_xy(point.get_attribute("transform"))
                check("size edit does not move the point",
                      max(abs(a - b) for a, b in zip(before_size, after_size)) < 0.01,
                      repr((before_size, after_size)))
                clipped_by = field.evaluate(
                    "element => element.parentElement.getAttribute('clip-path')")
                check("out-of-bounds point field is clipped to the room",
                      clipped_by == "url(#spatial-room-clip)", repr(clipped_by))

                before_speed = transform_xy(point.get_attribute("transform"))
                page.fill("#point-vx", "3")
                page.dispatch_event("#point-vx", "change")
                after_speed = transform_xy(point.get_attribute("transform"))
                check("speed edit does not move the point",
                      max(abs(a - b) for a, b in zip(before_speed, after_speed)) < 0.01,
                      repr((before_speed, after_speed)))

                page.click("#point-add")
                page.wait_for_selector('[data-point-select="1"]', timeout=5000)
                page.click('[data-point-select="0"]')
                check("points list selects the same editor as the map",
                      page.locator("#point-title").inner_text() == "Point 0"
                      and page.locator('[data-point-select="0"]').get_attribute("class").endswith("selected"))
                check("point handles are clipped with the same room mask",
                      page.locator(".point-handles").get_attribute("clip-path")
                      == "url(#spatial-room-clip)")

                page.screenshot(path=os.path.join(HERE, "ui2-spatial.png"), full_page=True)
                browser.close()
        finally:
            server.terminate()
            server.wait(timeout=5)

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("ui-2 spatial checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
