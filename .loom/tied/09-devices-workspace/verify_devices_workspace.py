#!/usr/bin/env python3
"""Real-dashboard Playwright pass for the physical Devices workspace."""

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


def log_contains(path, needle, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with open(path, encoding="utf-8") as source:
                if needle in source.read():
                    return True
        except OSError:
            pass
        time.sleep(.05)
    return False


def write_patch(root, name, payload):
    path = os.path.join(root, name)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "main.bin"), "wb") as target:
        target.write(payload)
    with open(os.path.join(path, "bopos.patch.json"), "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "params": [],
                   "caps": [], "slots": []}, target)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-devices-workspace-") as temp:
        state_path = os.path.join(temp, "installation.json")
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        write_patch(patches, "demo-pd", b"demo")
        write_patch(patches, "beta", b"beta-v1")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "Devices browser rig", "seats": {}}, target)

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
                "--devices", "2", "--unassigned", "2", "--target", "127.0.0.1",
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
                page.click("#tab-button-seats")
                page.click("#seat-add")
                page.wait_for_function("() => !!installation.seats?.['0']")
                page.click("#seat-add")
                page.wait_for_function("() => !!installation.seats?.['1']")

                page.click("#tab-button-devices")
                page.wait_for_selector("#tab-devices:not([hidden]) #device-roster")
                check("one physical roster renders each uid exactly once",
                      page.locator("#device-roster .device-row").count() == 2
                      and page.locator("#unassigned").count() == 0
                      and len(set(page.locator("#device-roster .device-row")
                                      .evaluate_all("rows => rows.map(row => row.dataset.uid)"))) == 2)
                check("roster labels both devices as unbound",
                      [text.lower() for text in page.locator(
                          "#device-roster .device-binding-badge").all_inner_texts()]
                      == ["unbound", "unbound"])

                page.select_option("#device-filter", "bound")
                check("bound filter is empty before assignment",
                      page.locator("#device-roster .device-row").count() == 0)
                page.select_option("#device-filter", "unbound")
                check("unbound filter uses the same roster",
                      page.locator("#device-roster .device-row").count() == 2)

                first = page.locator("#device-roster .device-row").first
                uid = first.get_attribute("data-uid")
                first.click()
                page.wait_for_selector("#detail #device-binding")
                detail = page.locator("#detail").inner_text().lower()
                check("detail exposes identity, health, version and report",
                      all(term in detail for term in
                          ("uid", "health", "last seen", "version", "engine", "report")),
                      detail)
                check("Devices excludes Seat authoring, geometry and mix parameters",
                      page.locator("#detail #seat-name, #detail #seat-id, "
                                   "#detail [data-seat-element], #detail [data-param]").count() == 0)
                check("unbound detail offers only empty Seats through the binding shortcut",
                      page.locator("#device-seat option").count() == 2
                      and page.locator("#device-bind").is_enabled())

                page.click("#detail [data-identify]")
                check("direct Identify reaches the selected uid",
                      log_contains(fleet_log_path, "identify"))
                page.click("#refresh-report")
                page.wait_for_function(
                    "uid => installation.devices?.[uid]?.report?.contract_version === '1.5'",
                    arg=uid)
                check("Refresh report returns attributable device facts", True)

                page.select_option("#device-seat", "0")
                page.click("#device-bind")
                page.wait_for_function(
                    "uid => installation.seats?.['0']?.bound === uid", arg=uid)
                check("device-first shortcut uses the authoritative Seat binding", True)
                check("bound detail replaces assignment controls with a Seat link",
                      page.locator("#device-open-seat").count() == 1
                      and page.locator("#device-seat, #device-bind").count() == 0)

                page.wait_for_function(
                    "() => [...document.querySelectorAll('#patch-select option')]"
                    ".some(option => option.value === 'beta')")
                page.select_option("#patch-select", "beta")
                page.click("#patch-switch")
                page.wait_for_function(
                    "() => document.querySelector('#fleet-patch-summary')?.innerText.includes('1 current')",
                    timeout=12000)
                with open(os.path.join(patches, "beta", "main.bin"), "wb") as target:
                    target.write(b"beta-v2-with-different-content")
                page.click("#refresh-distribution")
                page.wait_for_function(
                    "() => document.querySelector('#fleet-patch-summary')?.innerText.includes('1 stale')",
                    timeout=8000)
                check("host content drift is visible on the physical device",
                      page.locator("#fleet-patch-retry").count() == 1
                      and "repair" in page.locator(
                          "#fleet-patch-retry").inner_text().lower())
                page.click("#fleet-patch-retry")
                page.wait_for_function(
                    "() => document.querySelector('#fleet-patch-summary')?.innerText.includes('1 current')",
                    timeout=12000)
                check("one-click repair reconverges the selected device", True)

                page.select_option("#device-filter", "bound")
                check("bound filter shows the newly assigned row once",
                      page.locator("#device-roster .device-row").count() == 1
                      and "bound · seat 0" in page.locator(
                          "#device-roster .device-binding-badge").inner_text().lower())
                page.click("#device-open-seat")
                check("Open Seat crosses to the authoritative workspace",
                      not page.locator("#tab-seats").get_attribute("hidden")
                      and page.input_value("#seat-id") == "0")

                page.click("#tab-button-devices")
                page.select_option("#device-filter", "unbound")
                page.locator("#device-roster .device-row").click()
                page.click('#detail [data-action="restart-engine"]')
                check("individual lifecycle actions are confirmation-guarded and UID-routed",
                      any(kind == "confirm" and "restart engine" in message.lower()
                          for kind, message in dialogs)
                      and log_contains(fleet_log_path, "os/restart-engine"), repr(dialogs))

                page.click('[data-all="shutdown"]')
                check("Shutdown All is explicit and confirmation-guarded",
                      any(kind == "confirm" and "shutdown all physical devices" in message.lower()
                          for kind, message in dialogs)
                      and log_contains(fleet_log_path, "os/shutdown"), repr(dialogs))
                page.screenshot(path=os.path.join(HERE, "devices-workspace.png"),
                                full_page=True)
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
    print("Devices workspace browser checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
