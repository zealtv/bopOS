#!/usr/bin/env python3
"""Browser check for the host-backed managed-simulation patch workflow."""

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
while not os.path.isfile(os.path.join(REPO, "tools", "audition.py")):
    REPO = os.path.dirname(REPO)

HTTP_PORT, OSC_LISTEN, OSC_COMMAND = 18143, 15583, 16693
BASE_URL = f"http://127.0.0.1:{HTTP_PORT}"
FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def write_patch(root, name):
    path = os.path.join(root, name)
    os.makedirs(path)
    with open(os.path.join(path, "main.bin"), "wb") as target:
        target.write(name.encode())
    with open(os.path.join(path, "bopos.patch.json"), "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "params": [],
                   "caps": [], "slots": []}, target)


def main():
    with tempfile.TemporaryDirectory() as temp:
        patches, assets = os.path.join(temp, "patches"), os.path.join(temp, "assets")
        os.makedirs(assets)
        write_patch(patches, "alpha")
        write_patch(patches, "beta")
        state = {"schema": 1, "name": "test", "seats": {
            "0": {"id": 0, "name": "seat-0", "positions": [[1, 1]],
                  "patch": "alpha", "params": {}, "bound": None}}}
        state_path = os.path.join(temp, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump(state, target)
        log_path = os.path.join(temp, "server.log")
        log = open(log_path, "w", encoding="utf-8")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard", "server.py"),
            "--port", str(HTTP_PORT), "--listen-port", str(OSC_LISTEN),
            "--send-port", str(OSC_COMMAND), "--osc-target", "127.0.0.1",
            "--state-file", state_path, "--assets-dir", assets,
            "--patches-dir", patches, "--sim-no-engine",
            "--sim-audio-backend", "none", "--sim-engine-port-base", "26693",
        ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 8
            while True:
                try:
                    urllib.request.urlopen(BASE_URL, timeout=.5).close()
                    break
                except Exception:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(.1)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1300, "height": 950})
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(BASE_URL)
                page.click("#simulate-toggle")
                page.wait_for_function(
                    "() => document.querySelector('#simulate-status')?.innerText.includes('alpha')",
                    timeout=8000)
                page.wait_for_function(
                    "() => document.querySelector('.seat-row small')?.innerText.includes('sim')",
                    timeout=8000)
                page.locator(".seat-row .dot").first.click()
                page.wait_for_timeout(1500)
                option_values = page.locator("#patch-select option").evaluate_all(
                    "options => options.map(option => option.value)")
                check("simulation dropdown contains the host patch catalog",
                      set(option_values) == {"alpha", "beta"},
                      repr(option_values) + " detail=" + page.locator("#detail").inner_text())
                check("simulation labels the dropdown as host-backed",
                      "Host-backed simulated fleet" in page.locator("#detail").inner_text())
                check("simulation has no Send and Sync surface",
                      page.locator("#distribution").count() == 0
                      and "Send patch" not in page.locator("#detail").inner_text())
                page.select_option("#patch-select", "beta")
                page.click("#patch-switch")
                page.wait_for_function(
                    "() => document.querySelector('#simulate-status')?.innerText.includes('beta')",
                    timeout=8000)
                page.wait_for_function(
                    "() => document.querySelector('.seat-row small')?.innerText.includes('sim')",
                    timeout=8000)
                page.locator(".seat-row .dot").first.click()
                page.wait_for_function(
                    "() => document.querySelector('#detail')?.innerText.includes('current: beta')",
                    timeout=5000)
                check("one switch changes the whole simulated fleet patch",
                      "running · beta" in page.locator("#simulate-status").inner_text())
                check("simulated patch inventory remains the host catalog after restart",
                      set(page.locator("#patch-select option").all_inner_texts())
                      == {"alpha", "beta"})
                browser.close()
        finally:
            server.terminate()
            server.wait(timeout=5)
            log.close()
            if server.returncode not in (0, -15):
                with open(log_path, encoding="utf-8") as source:
                    print(source.read())

    print(f"\n{5 - len(FAILURES)}/5 passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
