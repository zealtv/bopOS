#!/usr/bin/env python3
"""Verification for dashboard-7-remove-param-roles.

Unit: any manifest `role` key is rejected loudly; a facilitator-less manifest
draws the status-only advisory. Browser: the facilitator view renders one
labelled control per facilitator:true param (gain and backing in the default
manifest), nothing for unpromoted params, and a promoted slider still sends
the raw /p value on the wire.
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


def set_slider(page, selector, value):
    page.eval_on_selector(selector, """(el, v) => {
        el.value = v;
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
    }""", value)


def unit_checks():
    sys.path.insert(0, os.path.join(REPO, "python"))
    import manifest

    with tempfile.TemporaryDirectory() as temp:
        open(os.path.join(temp, "main.pd"), "w").close()
        path = os.path.join(temp, "bopos.patch.json")

        def write(params):
            with open(path, "w", encoding="utf-8") as target:
                json.dump({"entrypoint": "main.pd", "params": params}, target)

        write([{"name": "gain", "type": "f", "role": "volume"}])
        _, error = manifest.load(temp)
        check("role 'volume' is rejected loudly",
              error is not None and "role was removed" in error, str(error))

        write([{"name": "level", "type": "f", "role": "meter"}])
        _, error = manifest.load(temp)
        check("role 'meter' is rejected loudly",
              error is not None and "role was removed" in error, str(error))

        write([{"name": "gain", "type": "f", "facilitator": True},
               {"name": "gain2", "type": "f", "facilitator": True}])
        loaded, error = manifest.load(temp)
        check("multiple facilitator params are legal",
              error is None and manifest.warnings(loaded) == [], str(error))

        write([{"name": "echo", "type": "i"}])
        loaded, error = manifest.load(temp)
        notes = manifest.warnings(loaded) if loaded else []
        check("facilitator-less manifest draws the status-only advisory",
              error is None and any("facilitator" in note for note in notes),
              str(error) + repr(notes))

        loaded, error = manifest.load(os.path.join(REPO, "patches", "default"))
        check("default patch manifest is valid with no role key",
              error is None and not any("role" in param for param in loaded["params"]),
              str(error))


def browser_checks(browser):
    http_port, osc_listen, osc_command = 18096, 15566, 16676
    with tempfile.TemporaryDirectory() as temp:
        state_file = os.path.join(temp, "installation.json")
        with open(state_file, "w", encoding="utf-8") as target:
            json.dump({"name": "dashboard-7", "devices": {},
                       "facilitator_commands": []}, target)
        log_path = os.path.join(temp, "fleet.log")
        fleet_log = open(log_path, "w", encoding="utf-8")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"),
            "--port", str(http_port), "--listen-port", str(osc_listen),
            "--send-port", str(osc_command), "--osc-target", "127.0.0.1",
            "--state-file", state_file,
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"),
            "--devices", "2", "--target", "127.0.0.1",
            "--report-port", str(osc_listen), "--cmd-port", str(osc_command),
            "--hb-interval", "1", "--boot-secs", "1",
        ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)
        try:
            time.sleep(2)
            page = browser.new_page(viewport={"width": 900, "height": 1100})
            page.goto("http://127.0.0.1:{}/facilitator".format(http_port))
            page.wait_for_selector('[data-param="gain"]', timeout=10000)

            check("gain renders as a promoted control on every card",
                  page.locator('[data-param="gain"]').count() == 2)
            check("backing renders as a promoted control on every card",
                  page.locator('[data-param="backing"]').count() == 2)
            check("unpromoted echo stays off the facilitator surface",
                  page.locator('[data-param="echo"]').count() == 0)
            # inner_text applies text-transform; compare lowercased
            labels = page.locator(".promoted span").all_inner_texts()
            labels = [label.strip().lower() for label in labels]
            check("promoted controls are labelled with the param name",
                  labels.count("gain") == 2 and labels.count("backing") == 2,
                  repr(labels))
            check("no unlabelled volume slider remains in card-main",
                  page.locator(".card-main input").count() == 0)

            set_slider(page, '[data-param="gain"]', "0.41")
            page.wait_for_timeout(400)
            page.screenshot(path=os.path.join(HERE, "role-removal.png"))
            page.close()
        finally:
            fleet.terminate()
            server.terminate()
            fleet.wait(timeout=5)
            server.wait(timeout=5)
            fleet_log.close()

        log_text = open(log_path, encoding="utf-8").read()
        check("promoted gain slider sends the raw /p value",
              "p/gain=0.41" in log_text, log_text[-600:])


def main():
    unit_checks()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        browser_checks(browser)
        browser.close()
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("role removal checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
