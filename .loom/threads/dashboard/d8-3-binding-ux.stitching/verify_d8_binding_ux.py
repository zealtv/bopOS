#!/usr/bin/env python3
"""Playwright walkthrough for composer-first seat authoring and binding."""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent

FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}" +
          (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def wait_http(url, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError(f"dashboard did not start at {url}")


def main():
    fleet = None
    with tempfile.TemporaryDirectory() as temp:
        state_file = os.path.join(temp, "installation.json")
        server_log = open(os.path.join(temp, "server.log"), "w")
        fleet_log = open(os.path.join(temp, "fleet.log"), "w")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"),
            "--host", "127.0.0.1", "--port", "18283",
            "--listen-port", "15683", "--send-port", "16783",
            "--osc-target", "127.0.0.1", "--state-file", state_file,
            "--assets-dir", os.path.join(temp, "assets"),
            "--patches-dir", os.path.join(temp, "patches"),
            "--sim-audio-backend", "none", "--sim-no-engine",
        ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
        try:
            wait_http("http://127.0.0.1:18283/")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1280, "height": 1050})
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto("http://127.0.0.1:18283/")
                page.wait_for_selector("#ws-status.online")

                room = page.locator("#spatial rect.room")
                box = room.bounding_box()
                room.click(position={"x": box["width"] * .25, "y": box["height"] * .35})
                page.wait_for_selector('#assigned .seat-row[data-seat-id="0"]')
                room.click(position={"x": box["width"] * .65, "y": box["height"] * .55})
                page.wait_for_selector('#assigned .seat-row[data-seat-id="1"]')
                check("empty map clicks author ordered 0-indexed seats",
                      page.locator("#assigned .seat-row").count() == 2)

                name = page.locator('.seat-row[data-seat-id="0"] [data-seat-name]')
                name.fill("front left")
                name.press("Tab")
                page.wait_for_timeout(1200)
                saved = json.load(open(state_file, encoding="utf-8"))
                check("seat name edits inline", saved["seats"]["0"]["name"] == "front left")

                dot = page.locator('#spatial g[data-seat-id="0"] circle[data-point="0"]')
                before = list(saved["seats"]["0"]["positions"][0])
                dot_box = dot.bounding_box()
                x = dot_box["x"] + dot_box["width"] / 2
                y = dot_box["y"] + dot_box["height"] / 2
                page.mouse.move(x, y); page.mouse.down(); page.mouse.move(x + 70, y + 40,
                                                                            steps=8); page.mouse.up()
                page.wait_for_timeout(1200)
                saved = json.load(open(state_file, encoding="utf-8"))
                check("seat dot drag persists map position",
                      saved["seats"]["0"]["positions"][0] != before)

                page.click("#simulate-toggle")
                page.wait_for_function("document.querySelector('#simulate-status').textContent === 'running'")
                page.wait_for_function("[...document.querySelectorAll('#assigned .seat-row small')].every(x => x.textContent.includes('sim'))")
                check("authored seats become simulated occupancy", True)
                page.click("#simulate-toggle")
                page.wait_for_function("document.querySelector('#simulate-status').textContent === 'off'")

                fleet = subprocess.Popen([
                    sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                    "--devices", "3", "--unassigned", "3", "--target", "127.0.0.1",
                    "--report-port", "15683", "--cmd-port", "16783", "--hb-interval", "2",
                    "--state-dir", os.path.join(temp, "nodes"),
                ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)
                page.wait_for_function("document.querySelectorAll('#unassigned .device-row').length === 3",
                                       timeout=12000)
                first = page.locator("#unassigned .device-row").first
                uid = first.get_attribute("data-uid")
                hostname = first.locator("strong").inner_text()
                check("unbound devices report hostnames", bool(hostname) and hostname != uid,
                      f"{hostname!r} / {uid!r}")

                first.click()
                page.select_option("#device-seat", "1")
                page.click("#device-bind")
                page.wait_for_function("uid => document.querySelector('.seat-row[data-seat-id=\"1\"]').dataset.uid === uid", arg=uid)
                check("device-side bind suggests hostname for fresh seat",
                      page.locator('.seat-row[data-seat-id="1"] [data-seat-name]').input_value().lower() == hostname.lower())

                page.locator('.seat-row[data-seat-id="0"] small').click()
                page.select_option("#seat-device", uid)
                page.click("#seat-bind")
                page.wait_for_function("uid => document.querySelector('.seat-row[data-seat-id=\"0\"]').dataset.uid === uid && !document.querySelector('.seat-row[data-seat-id=\"1\"]').dataset.uid",
                                       arg=uid)
                check("seat-side rebind swaps device without losing either seat", True)

                page.evaluate('ws.send("save_venue", {name:"walkthrough"})')
                page.wait_for_function("[...document.querySelectorAll('#venue-select option')].some(x => x.textContent === 'walkthrough')")
                fleet.terminate(); fleet.wait(timeout=5); fleet = None
                page.locator('.seat-row[data-seat-id="0"] small').click()
                page.click("#seat-unbind")
                page.locator(f'#unassigned .device-row[data-uid="{uid}"]').click()
                page.click("#device-forget")
                page.evaluate('ws.send("load_venue", {name:"walkthrough"})')
                page.wait_for_function("!document.querySelector('#venue-rebind').hidden")
                check("venue load names rebound and waiting outcomes honestly",
                      "Waiting:" in page.locator("#venue-rebind").inner_text()
                      and uid in page.locator("#venue-rebind").inner_text())

                remaining = page.locator("#unassigned .device-row")
                while remaining.count():
                    remaining.first.click()
                    page.click("#device-forget")
                    page.wait_for_timeout(100)
                check("remaining discovered devices can be forgotten", remaining.count() == 0)
                check("bulk offline-forget affordance remains available",
                      page.locator("#forget-offline").is_visible())
                browser.close()
        finally:
            if fleet is not None:
                fleet.terminate(); fleet.wait(timeout=5)
            server.terminate(); server.wait(timeout=5)
            server_log.close(); fleet_log.close()
            if server.returncode not in (-15, 0):
                print(open(server_log.name, encoding="utf-8").read())
    print(f"\n{10-len(FAILURES)}/10 passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
