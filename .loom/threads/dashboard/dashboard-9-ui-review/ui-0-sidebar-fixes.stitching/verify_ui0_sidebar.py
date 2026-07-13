#!/usr/bin/env python3
"""Playwright verification for ui-0 sidebar spinner and heartbeat blips."""
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
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"),
            "--port", "18103", "--listen-port", "15573", "--send-port", "16683",
            "--osc-target", "127.0.0.1", "--state-file", state_file,
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "3",
            "--unassigned", "1", "--state-dir", node_state,
            "--target", "127.0.0.1", "--report-port", "15573",
            "--cmd-port", "16683", "--hb-interval", "0.5",
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        try:
            time.sleep(2)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.goto("http://127.0.0.1:18103/")
                row = page.locator("#unassigned .device-row").first
                row.wait_for(timeout=10000)
                uid = row.get_attribute("data-uid")
                row.click()
                spinner = page.locator("#assign-id")
                spinner.wait_for(timeout=5000)
                page.evaluate("window.__ui0Heartbeats = []; ws.on('heartbeat', data => window.__ui0Heartbeats.push(data))")

                # Reproduce a native spinner click without relying on browser chrome:
                # pointerdown marks the form as interacting, stepUp changes its value,
                # and pointerup used to rebuild the panel from nextFreeId().
                before = int(spinner.input_value())
                spinner.dispatch_event("pointerdown")
                spinner.evaluate("element => element.stepUp()")
                spinner.dispatch_event("input")
                spinner.dispatch_event("pointerup")
                after = int(page.locator("#assign-id").input_value())
                check("spinner increment survives pointerup", after == before + 1,
                      repr((before, after)))

                page.wait_for_function(
                    "uid => window.__ui0Heartbeats.some(beat => beat.uid === uid)",
                    arg=uid, timeout=5000)
                page.wait_for_function("""uid => {
                    const row = [...document.querySelectorAll('.device-row')]
                      .find(element => element.dataset.uid === uid);
                    return !!row?.querySelector('.heartbeat-blip')?.dataset.heartbeatAt;
                }""", arg=uid, timeout=5000)
                blip = page.locator(f'.device-row[data-uid="{uid}"] .heartbeat-blip')
                check("heartbeat visibly pulses its device row",
                      blip.evaluate("element => element.classList.contains('pulse')")
                      and blip.get_attribute("data-heartbeat-at") is not None)
                check("heartbeat does not reset spinner",
                      int(page.locator("#assign-id").input_value()) == after)

                page.fill("#assign-name", "spinner-proof")
                page.click("#assign-send")
                page.wait_for_selector(f'#assigned .device-row[data-uid="{uid}"]',
                                       timeout=8000)
                check("edited id reaches assignment",
                      f"ID {after}" in page.locator(
                          f'.device-row[data-uid="{uid}"]').inner_text())
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
    print("ui-0 sidebar checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
