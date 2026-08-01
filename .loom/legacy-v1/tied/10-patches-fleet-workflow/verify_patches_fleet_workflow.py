#!/usr/bin/env python3
"""Real-dashboard Playwright pass for Patches-owned fleet deployment."""

import json
import os
import random
import socket
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
        raise SystemExit("cannot locate bopOS repository")
    REPO = parent

FAILURES = []
RESERVED = set()


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                              " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_port(kind):
    for _attempt in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        if (kind, port) in RESERVED:
            continue
        probe = socket.socket(socket.AF_INET, kind)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            probe.close()
            continue
        probe.close()
        RESERVED.add((kind, port))
        return port
    raise RuntimeError("could not reserve a local port")


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def wait_http(url, process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before serving HTTP")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not serve HTTP")


def write_patch(root, name, payload):
    path = os.path.join(root, name)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "main.bin"), "wb") as target:
        target.write(payload)
    with open(os.path.join(path, "bopos.patch.json"), "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "params": [],
                   "caps": [], "slots": []}, target)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-patches-fleet-") as temp:
        state_path = os.path.join(temp, "installation.json")
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        write_patch(patches, "demo-pd", b"demo")
        write_patch(patches, "alpha", b"alpha")
        write_patch(patches, "beta", b"beta-v1")
        bound_uid = "02:53:49:4d:00:01"
        unbound_uid = "02:53:49:4d:00:02"
        state = {"schema": 1, "name": "Patches fleet browser rig", "seats": {
            "1": {"id": 1, "name": "Front", "positions": [[1, 1]],
                  "params": {}, "bound": bound_uid},
        }}
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump(state, target)

        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log_path = os.path.join(temp, "server.log")
        fleet_log_path = os.path.join(temp, "fleet.log")
        server_log = open(server_log_path, "w", encoding="utf-8")
        fleet_log = open(fleet_log_path, "w", encoding="utf-8")
        server = fleet = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", assets, "--patches-dir", patches,
                "--public-url", base_url,
            ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "2", "--unassigned", "1", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.2", "--fetch-seconds", "0.3",
                "--patches-dir", patches,
                "--manifest", os.path.join(patches, "demo-pd", "bopos.patch.json"),
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                page_errors = []
                dialogs = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def accept_dialog(dialog):
                    dialogs.append((dialog.type, dialog.message))
                    dialog.accept()

                page.on("dialog", accept_dialog)
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "() => Object.keys(installation.devices||{}).length === 2")
                page.wait_for_function(
                    "uid => Array.isArray(installation.devices?.[uid]?.patches)",
                    arg=bound_uid)

                page.click("#tab-button-patches")
                page.wait_for_selector("#tab-patches:not([hidden]) #fleet-patch-panel")
                check("Patches exclusively owns desired fleet deployment",
                      page.locator("#tab-patches #fleet-patch-panel").count() == 1
                      and page.locator("#tab-devices #fleet-patch-panel").count() == 0
                      and page.locator("#patch-select").count() == 1)
                check("production choice is distinct from the editor working patch",
                      page.locator("#patch-select").count() == 1
                      and page.locator("#editor-patch").count() == 1)
                page.wait_for_function(
                    "() => [...document.querySelectorAll('#patch-select option')]"
                    ".some(option => option.value === 'beta')")

                page.select_option("#patch-select", "beta")
                page.click("#patch-switch")
                page.wait_for_function(
                    "() => installation.fleet_patch?.name === 'beta'"
                    " && document.querySelector('#fleet-patch-summary')?.innerText.includes('1 current')",
                    timeout=12000)
                check("Deploy creates one desired record and converges assigned targets",
                      page.evaluate("() => Object.keys(installation.fleet_patch||{}).sort()")
                      == ["fingerprint", "name", "previous", "staged_at"]
                      and any(kind == "confirm" and 'Deploy "beta"' in message
                              for kind, message in dialogs), repr(dialogs))
                page.screenshot(path=os.path.join(HERE, "01-patches-fleet.png"),
                                full_page=True)

                with open(os.path.join(patches, "beta", "main.bin"), "wb") as target:
                    target.write(b"beta-v2-with-different-content")
                page.click("#refresh-distribution")
                page.wait_for_function(
                    "() => document.querySelector('#fleet-patch-summary')?.innerText.includes('1 stale')",
                    timeout=8000)
                page.click("#tab-button-devices")
                page.select_option("#device-filter", "bound")
                page.locator("#device-roster .device-row").click()
                page.wait_for_selector("#fleet-patch-retry")
                check("Devices owns observed exception state and one repair action",
                      page.locator("#detail #patch-select, #detail #patch-switch, "
                                   "#detail #fleet-patch-revert").count() == 0
                      and page.locator("#fleet-patch-retry").inner_text().lower()
                          == "sync to fleet patch")
                page.click("#fleet-patch-retry")
                page.wait_for_function(
                    "uid => installation.devices?.[uid]?.patch_badge === 'current'",
                    arg=bound_uid, timeout=12000)
                check("bound exception repair reconverges through desired state", True)

                page.select_option("#device-filter", "unbound")
                page.locator("#device-roster .device-row").click()
                page.wait_for_selector("#detail #patch-diagnostics")
                check("unbound detail is diagnostic without unsafe content targeting",
                      page.locator("#fleet-patch-retry").count() == 0
                      and "assign this device to a seat" in page.locator(
                          ".patch-target-note").inner_text().lower())
                page.evaluate(
                    "uid => ws.send('retry_fleet_patch', {uid})", unbound_uid)
                page.wait_for_timeout(300)
                check("backend rejects a forged unbound repair request explicitly",
                      any(kind == "alert" and "cannot uniquely target unbound" in message
                          for kind, message in dialogs), repr(dialogs))
                page.screenshot(path=os.path.join(HERE, "02-device-exceptions.png"),
                                full_page=True)

                page.click("#tab-button-patches")
                page.select_option("#patch-select", "alpha")
                page.click("#patch-switch")
                page.wait_for_function(
                    "() => installation.fleet_patch?.name === 'alpha'"
                    " && document.querySelector('#fleet-patch-summary')?.innerText.includes('1 current')",
                    timeout=12000)
                check("a later deployment exposes the single previous desired patch",
                      not page.locator("#fleet-patch-revert").is_disabled())
                page.click("#fleet-patch-revert")
                page.wait_for_function(
                    "() => installation.fleet_patch?.name === 'beta'"
                    " && document.querySelector('#fleet-patch-summary')?.innerText.includes('1 current')",
                    timeout=12000)
                check("Patches-owned Revert reconverges through the same coordinator",
                      any(kind == "confirm" and "Revert the fleet" in message
                          for kind, message in dialogs), repr(dialogs))
                check("browser emitted no page errors", not page_errors, repr(page_errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

        if FAILURES:
            with open(server_log_path, encoding="utf-8") as source:
                print("\nserver log tail:\n", source.read()[-3000:])
            with open(fleet_log_path, encoding="utf-8") as source:
                print("\nfleet log tail:\n", source.read()[-3000:])

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("Patches fleet workflow browser checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
