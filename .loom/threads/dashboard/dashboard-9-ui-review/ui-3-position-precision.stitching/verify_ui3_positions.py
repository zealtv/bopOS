#!/usr/bin/env python3
"""Playwright verification for numeric element positions and room origin."""
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

UID = "02:53:49:4d:00:01"
FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def wait_json(page, path, predicate, timeout=5000):
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        try:
            with open(path, encoding="utf-8") as source:
                value = json.load(source)
            if predicate(value):
                return value
        except (OSError, ValueError):
            pass
        page.wait_for_timeout(100)
    return None


def main():
    with tempfile.TemporaryDirectory() as temp:
        state_file = os.path.join(temp, "installation.json")
        node_state = os.path.join(temp, "nodes")
        os.makedirs(node_state)
        node_file = os.path.join(node_state, UID.replace(":", "-") + ".json")
        with open(state_file, "w", encoding="utf-8") as target:
            json.dump({
                "name": "ui3-position-precision",
                "room": {"width": 10, "depth": 8, "units": "m", "origin": [1, 1]},
                "devices": {
                    UID: {"id": 1, "name": "two-elements", "pos1": [2, 3],
                          "pos2": [4, 5], "params": {}},
                },
            }, target)
        with open(node_file, "w", encoding="utf-8") as target:
            json.dump({"id": 1, "name": "two-elements", "positions": [2, 3, 4, 5]},
                      target)
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"),
            "--port", "18106", "--listen-port", "15576", "--send-port", "16686",
            "--osc-target", "127.0.0.1", "--state-file", state_file,
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "1",
            "--state-dir", node_state, "--target", "127.0.0.1",
            "--report-port", "15576", "--cmd-port", "16686", "--hb-interval", "0.5",
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        try:
            time.sleep(2)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1400, "height": 1000})
                page.goto("http://127.0.0.1:18106/")
                page.wait_for_selector(f'.device-row[data-uid="{UID}"]', timeout=10000)

                marker = page.locator("#spatial .space-origin")
                check("persisted origin renders on the map",
                      marker.get_attribute("transform") == "translate(1 1)",
                      marker.get_attribute("transform"))
                page.locator(f'.device-row[data-uid="{UID}"]').click()
                page.wait_for_selector('[data-position-key="pos2"]', timeout=5000)
                rows = page.locator(".position-row")
                check("true-N positions render one row per element", rows.count() == 2,
                      str(rows.count()))
                check("position labels are 0-indexed",
                      rows.nth(0).locator("strong").inner_text() == "element 0"
                      and rows.nth(1).locator("strong").inner_text() == "element 1")
                first = rows.nth(0)
                second = rows.nth(1)
                check("numeric coordinates are relative to the origin",
                      first.locator('[data-axis="x"]').input_value() == "1"
                      and first.locator('[data-axis="y"]').input_value() == "2"
                      and second.locator('[data-axis="x"]').input_value() == "3"
                      and second.locator('[data-axis="y"]').input_value() == "4")

                first.locator('[data-axis="x"]').fill("2.5")
                first.locator('[data-axis="x"]').dispatch_event("change")
                assigned = wait_json(
                    page, node_file,
                    lambda value: value.get("positions") == [3.5, 3.0, 4.0, 5.0])
                check("numeric entry uses the ordinary assign path",
                      assigned is not None, repr(assigned))
                transform = page.locator(f'#spatial [data-uid="{UID}"] [data-element="0"]').get_attribute("transform")
                check("numeric entry moves the matching element only",
                      transform == "translate(3.5 3)", transform)

                page.fill("#origin-x", "2")
                page.dispatch_event("#origin-x", "change")
                page.fill("#origin-y", "1.5")
                page.dispatch_event("#origin-y", "change")
                saved = wait_json(
                    page, state_file,
                    lambda value: value.get("room", {}).get("origin") == [2.0, 1.5],
                    timeout=7000)
                check("origin persists in installation.json", saved is not None,
                      repr(saved.get("room") if saved else None))
                page.wait_for_function(
                    "() => document.querySelector('.space-origin')?.getAttribute('transform') === 'translate(2 1.5)'",
                    timeout=5000)
                check("origin marker moves without moving the element",
                      page.locator(f'#spatial [data-uid="{UID}"] [data-element="0"]').get_attribute("transform")
                      == "translate(3.5 3)")
                page.locator(f'.device-row[data-uid="{UID}"]').click()
                page.wait_for_selector('[data-position-key="pos1"]', timeout=5000)
                first = page.locator('[data-position-key="pos1"]')
                check("origin change re-labels rather than moves coordinates",
                      first.locator('[data-axis="x"]').input_value() == "1.5"
                      and first.locator('[data-axis="y"]').input_value() == "1.5")

                page.screenshot(path=os.path.join(HERE, "ui3-positions.png"), full_page=True)
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
    print("ui-3 position checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
