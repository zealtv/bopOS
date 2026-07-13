#!/usr/bin/env python3
"""Playwright verification for the ui-1 technical layout pass."""
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
        fleet_path = os.path.join(temp, "fleet.log")
        fleet_log = open(fleet_path, "w", encoding="utf-8")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"),
            "--port", "18104", "--listen-port", "15574", "--send-port", "16684",
            "--osc-target", "127.0.0.1", "--state-file", state_file,
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "2",
            "--target", "127.0.0.1", "--report-port", "15574",
            "--cmd-port", "16684", "--hb-interval", "0.5",
        ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)
        try:
            time.sleep(2)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1400, "height": 1000})
                page.goto("http://127.0.0.1:18104/")
                page.wait_for_selector("#spatial .room", timeout=10000)

                first = page.locator(".layout > *").first.get_attribute("id")
                spatial_box = page.locator("#spatial-section").bounding_box()
                check("map is the first page-body panel", first == "spatial-section", str(first))
                check("map spans the sidebar and technical columns",
                      spatial_box is not None and spatial_box["width"] >= 1390,
                      repr(spatial_box))
                check("synced cue is outside the spatial section",
                      page.locator("#spatial-section #cue-panel").count() == 0
                      and page.locator("main #cue-panel").count() == 1)

                master = page.locator("#master")
                check("technical master control is visible", master.is_visible())
                master.fill("0.42")
                master.dispatch_event("input")
                page.wait_for_function(
                    "() => document.querySelector('#master-out').value === '42%'",
                    timeout=3000)
                for _ in range(30):
                    if os.path.exists(state_file):
                        with open(state_file, encoding="utf-8") as source:
                            if abs(float(json.load(source).get("master", -1)) - 0.42) < 0.001:
                                break
                    page.wait_for_timeout(100)
                with open(state_file, encoding="utf-8") as source:
                    saved_master = json.load(source).get("master")
                check("technical master persists through the real server",
                      abs(float(saved_master) - 0.42) < 0.001, repr(saved_master))

                check("retired aloha surface is absent",
                      "aloha" not in page.locator("body").inner_text().lower())
                page.click("#facilitator-link")
                page.wait_for_url("**/facilitator")
                check("facilitator has a technical-view link",
                      page.locator('#technical-link[href="/"]').is_visible())
                check("dead sound-check button is absent",
                      "sound check" not in page.locator("body").inner_text().lower())
                page.click("#technical-link")
                page.wait_for_url("http://127.0.0.1:18104/")
                check("technical-view link navigates back", page.url.endswith("18104/"))
                page.screenshot(path=os.path.join(HERE, "ui1-layout.png"), full_page=True)
                browser.close()
        finally:
            fleet.terminate()
            server.terminate()
            fleet.wait(timeout=5)
            server.wait(timeout=5)
            fleet_log.close()

        with open(fleet_path, encoding="utf-8") as source:
            log_text = source.read()
        check("simfleet received technical master",
              "os/master 0.42" in log_text, log_text[-1000:])

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("ui-1 layout checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
