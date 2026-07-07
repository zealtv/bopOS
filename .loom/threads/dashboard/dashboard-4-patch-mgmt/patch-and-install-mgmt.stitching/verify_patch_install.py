#!/usr/bin/env python3
"""Browser pass for patch-and-install-mgmt.

Real dashboard + real simfleet, headless Chromium. Drives patch switch /
add-from-GitHub / pull from the dashboard (asserting the verbs reach simfleet
on the wire and the /os/rev receipts come back), then exercises venue
save/load of installation.json.
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
        fleet_log = open(os.path.join(temp, "fleet.log"), "w")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"), "--port", "18087",
            "--listen-port", "15557", "--send-port", "16667", "--osc-target", "127.0.0.1",
            "--state-file", state_file,
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "3",
            "--target", "127.0.0.1", "--report-port", "15557", "--cmd-port", "16667",
            "--hb-interval", "1.0", "--boot-secs", "2.0",
        ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)
        try:
            time.sleep(3)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 1100})
                # one type-aware handler: prompts (venue "Save as…") get the name,
                # confirms (switch/pull/load) just accept
                prompt_answer = ["botanic-2026"]
                page.on("dialog", lambda d: d.accept(prompt_answer[0])
                        if d.type == "prompt" else d.accept())
                page.goto("http://127.0.0.1:18087/")
                page.wait_for_selector("#assigned .device-row", timeout=10000)
                page.locator("#assigned .device-row").first.click()
                page.wait_for_selector("#patch-switch", timeout=5000)
                check("patch panel shows current patch",
                      "current:" in page.locator("#detail").inner_text())

                # switch patch -> reaches simfleet, receipt updates Converged line
                page.fill("#patch-name", "wind_chimes")
                page.click("#patch-switch")
                page.wait_for_function(
                    "() => document.querySelector('#detail dl').innerText.includes('ago')",
                    timeout=6000)
                check("switch patch: /os/rev receipt landed", True)
                page.screenshot(path=os.path.join(HERE, "01-patch-panel.png"))

                # wait through the sim reboot; the post-reboot report shows the patch
                page.click("#refresh-report")
                got_patch = False
                for _ in range(20):
                    if "wind_chimes" in page.locator("#detail").inner_text():
                        got_patch = True
                        break
                    page.wait_for_timeout(500)
                    page.click("#refresh-report")
                check("switch patch: report reflects new patch", got_patch)

                # add-from-GitHub and pull reach the wire
                page.locator("#assigned .device-row").first.click()
                page.wait_for_selector("#patch-add", timeout=5000)
                page.fill("#patch-user", "bopos")
                page.fill("#patch-repo", "wind-chimes")
                page.click("#patch-add")
                page.wait_for_timeout(500)
                page.click("#patch-pull")
                page.wait_for_timeout(1500)

                # venue save/load
                page.click("#venue-save")
                page.wait_for_function(
                    "() => [...document.querySelectorAll('#venue-select option')]"
                    ".some(o => o.value === 'botanic-2026')", timeout=5000)
                check("venue saved and listed", True)
                check("venue file on disk",
                      os.path.exists(os.path.join(temp, "installations", "botanic-2026.json")))

                # change the room, then load the venue back -> room restored
                page.fill("#room-w", "25")
                page.dispatch_event("#room-w", "change")
                page.wait_for_timeout(400)
                page.select_option("#venue-select", "botanic-2026")
                page.click("#venue-load")
                page.wait_for_function(
                    "() => document.querySelector('#room-w').value === '10'", timeout=5000)
                check("venue load restored the room", True)
                browser.close()
        finally:
            fleet.terminate()
            server.terminate()
            fleet.wait(timeout=5)
            server.wait(timeout=5)
            fleet_log.close()
            log_text = open(fleet_log.name).read()
            check("simfleet saw os/patch wind_chimes", "os/patch wind_chimes" in log_text,
                  log_text[-400:])
            check("simfleet saw os/addpatch", "os/addpatch bopos wind-chimes" in log_text,
                  log_text[-400:])
            check("simfleet saw os/pullpatch", "os/pullpatch" in log_text, log_text[-400:])
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("patch-and-install checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
