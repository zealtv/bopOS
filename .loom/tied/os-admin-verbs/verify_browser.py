#!/usr/bin/env python3
"""Browser pass for the os-admin-verbs dashboard delta.

Drives the real UI against a real simfleet: selects a device, clicks
restart-engine and update, and checks the Converged line renders the
/os/rev receipt. Screenshots land beside this script.
"""
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
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"), "--port", "18082",
            "--listen-port", "15552", "--send-port", "16662", "--osc-target", "127.0.0.1",
            "--state-file", os.path.join(temp, "installation.json"),
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "3",
            "--target", "127.0.0.1", "--report-port", "15552", "--cmd-port", "16662",
            "--hb-interval", "1.0", "--boot-secs", "3.0",
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        try:
            time.sleep(3)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.goto("http://127.0.0.1:18082/")
                page.wait_for_selector(".device-row", timeout=10000)
                page.click(".device-row")
                page.wait_for_selector("#detail dl", timeout=5000)

                check("converged placeholder before any verb",
                      "—" in page.locator("#detail dl").first.inner_text())

                restart = page.locator('[data-action="restart-engine"]')
                check("restart-engine button present", restart.count() == 1)
                restart.click()
                page.wait_for_function(
                    "() => document.querySelector('#detail dl').innerText.includes('ago')",
                    timeout=5000)
                text = page.locator("#detail dl").first.inner_text()
                check("converged line shows receipt", "a1b2c3d" in text and "persistent" in text,
                      text)
                page.screenshot(path=os.path.join(HERE, "03-converged.png"))

                # update: accept the confirm, expect the bumped sha to land
                page.on("dialog", lambda dialog: dialog.accept())
                page.click('[data-action="update"]')
                page.wait_for_function(
                    "() => document.querySelector('#detail dl').innerText.includes('a1b2c3e')",
                    timeout=10000)
                check("update receipt shows bumped sha", True)
                page.screenshot(path=os.path.join(HERE, "04-updated.png"))
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
    print("browser checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
