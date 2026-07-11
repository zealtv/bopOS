#!/usr/bin/env python3
"""Browser verification for seam-4 facilitator promotion.

Runs the real dashboard and simfleet. Checks fail-closed defaults, promoted
patch params on every device card, raw /p values on the wire, sanitized
installation command allowlisting, confirm gating, and hold-to-confirm for a
destructive command.
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
    sys.path.insert(0, os.path.join(REPO, "dashboard"))
    import manifest
    from state import InstallationState

    with tempfile.TemporaryDirectory() as temp:
        open(os.path.join(temp, "main.pd"), "w").close()
        path = os.path.join(temp, "bopos.patch.json")
        with open(path, "w", encoding="utf-8") as target:
            json.dump({"entrypoint": "main.pd", "params": [
                {"name": "backing", "type": "f", "facilitator": "yes"}
            ]}, target)
        _, error = manifest.load(temp)
        check("manifest rejects non-boolean facilitator flag",
              error is not None and "facilitator must be true or false" in error,
              str(error))

        state_path = os.path.join(temp, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({"devices": {}}, target)
        state = InstallationState(state_path)
        check("missing command allowlist defaults empty",
              state.data["facilitator_commands"] == [])


def launch(temp, http_port, osc_listen, osc_command, commands):
    state_file = os.path.join(temp, "installation.json")
    with open(state_file, "w", encoding="utf-8") as target:
        json.dump({"name": "seam-4", "devices": {},
                   "facilitator_commands": commands}, target)
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
    return server, fleet, fleet_log, state_file, log_path


def stop(server, fleet, fleet_log):
    fleet.terminate()
    server.terminate()
    fleet.wait(timeout=5)
    server.wait(timeout=5)
    fleet_log.close()


def phase_default_empty(browser):
    with tempfile.TemporaryDirectory() as temp:
        server, fleet, fleet_log, _, _ = launch(temp, 18094, 15564, 16674, [])
        try:
            time.sleep(2)
            page = browser.new_page(viewport={"width": 900, "height": 1100})
            page.goto("http://127.0.0.1:18094/facilitator")
            page.wait_for_selector('[data-param="backing"]', timeout=10000)
            check("promoted backing control appears on every device card",
                  page.locator('[data-param="backing"]').count() == 2)
            check("volume control remains one per device",
                  page.locator('[data-param="gain"]').count() == 2)
            check("default facilitator command allowlist is empty",
                  page.locator("[data-command]").count() == 0)
            check("unpromoted echo stays out of facilitator",
                  page.locator('[data-param="echo"]').count() == 0)
            check("meter role stays out of facilitator controls",
                  page.locator('[data-param="level"]').count() == 0)
            page.close()
        finally:
            stop(server, fleet, fleet_log)


def phase_allowlisted(browser):
    with tempfile.TemporaryDirectory() as temp:
        commands = ["restart-engine", "bogus", "update", "restart-engine"]
        server, fleet, fleet_log, state_file, log_path = launch(
            temp, 18095, 15565, 16675, commands)
        try:
            time.sleep(2)
            page = browser.new_page(viewport={"width": 900, "height": 1100})
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto("http://127.0.0.1:18095/facilitator")
            page.wait_for_selector('[data-param="backing"]', timeout=10000)
            check("unknown and duplicate commands are removed",
                  page.locator("[data-command]").count() == 2
                  and page.locator('[data-command="bogus"]').count() == 0)

            set_slider(page, '[data-param="backing"]', "0.33")
            page.wait_for_timeout(300)

            # Non-destructive command is confirm-gated.
            page.click('[data-command="restart-engine"]')
            page.wait_for_timeout(300)

            # A short press must not fire the destructive action.
            update = page.locator('[data-command="update"]')
            update.dispatch_event("pointerdown")
            page.wait_for_timeout(250)
            update.dispatch_event("pointerup")
            page.wait_for_timeout(200)
            before = open(log_path, encoding="utf-8").read()
            check("short destructive press does not fire", "os/update" not in before)

            # Holding past the threshold fires once for the fleet.
            update.dispatch_event("pointerdown")
            page.wait_for_timeout(1350)
            update.dispatch_event("pointerup")
            page.wait_for_timeout(500)
            page.screenshot(path=os.path.join(HERE, "facilitator-promotion.png"))
            page.close()
            time.sleep(1.2)  # allow debounced durable state save
        finally:
            stop(server, fleet, fleet_log)

        log_text = open(log_path, encoding="utf-8").read()
        saved = json.load(open(state_file, encoding="utf-8"))
        check("promoted param sends raw patch value", "p/backing=0.33" in log_text,
              log_text[-600:])
        check("confirmed restart-engine reaches all devices",
              log_text.count("os/restart-engine") == 2, log_text[-600:])
        check("held update reaches all devices exactly once",
              log_text.count("os/update") == 2, log_text[-600:])
        check("sanitized command allowlist persists",
              saved.get("facilitator_commands") == ["restart-engine", "update"],
              repr(saved.get("facilitator_commands")))


def main():
    unit_checks()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        phase_default_empty(browser)
        phase_allowlisted(browser)
        browser.close()
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("facilitator promotion checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
