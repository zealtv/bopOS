#!/usr/bin/env python3
"""Real-dashboard Playwright pass for the Seats workspace."""

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


def wait_log(path, needle, timeout=5):
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


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-seats-workspace-") as temp:
        state_path = os.path.join(temp, "installation.json")
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "Seats browser rig", "seats": {}}, target)

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
            ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "2", "--unassigned", "2", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.2",
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "() => Object.keys(installation.devices||{}).length === 2")

                page.click("#tab-button-seats")
                page.wait_for_selector("#tab-seats:not([hidden]) #seat-add")
                page.click("#seat-add")
                page.wait_for_function("() => !!installation.seats?.['0']")
                page.wait_for_selector('#seat-detail #seat-name[value="Seat 0"]')
                check("Create Seat opens its dedicated inspector",
                      page.locator("#seat-detail h3").first.inner_text().lower()
                      == "seat workspace")
                check("Seats inspector owns map-first assignment controls",
                      page.locator("#seat-identify").count() == 1
                      and page.locator("#seat-bind").count() == 1
                      and page.locator("#seat-device option").count() >= 2)
                inspector_text = page.locator("#seat-detail").inner_text().lower()
                check("Seats inspector excludes device diagnostics, params and assets",
                      not any(term in inspector_text for term in (
                          "version", "engine", "rssi", "ip address", "patch diagnostics",
                          "params", "asset send", "report")), inspector_text)

                page.fill("#seat-name", "Front left")
                page.click("#seat-rename")
                page.wait_for_function(
                    "() => installation.seats?.['0']?.name === 'Front left'")
                check("Seat name persists through the workspace", True)

                page.click("#seat-element-add")
                page.wait_for_function(
                    "() => installation.seats?.['0']?.positions?.length === 1")
                page.fill('#seat-detail [data-seat-element="0"] [data-axis="x"]', "3.25")
                page.dispatch_event(
                    '#seat-detail [data-seat-element="0"] [data-axis="x"]', "change")
                page.wait_for_function(
                    "() => installation.seats?.['0']?.positions?.[0]?.[0] === 3.25")
                page.fill('#seat-detail [data-seat-element="0"] [data-axis="y"]', "4.5")
                page.dispatch_event(
                    '#seat-detail [data-seat-element="0"] [data-axis="y"]', "change")
                page.wait_for_function(
                    "() => installation.seats?.['0']?.positions?.[0]?.[1] === 4.5")
                check("Seat element position persists", True)

                uid = page.locator('#seat-device option:not([value=""])').first.get_attribute("value")
                page.select_option("#seat-device", uid)
                page.click("#seat-identify")
                check("Identify reaches the selected physical simulator",
                      wait_log(fleet_log_path, "identify"))
                page.click("#seat-bind")
                page.wait_for_function(
                    "uid => installation.seats?.['0']?.bound === uid", arg=uid)
                check("Assign binds the selected physical device", True)

                page.fill("#seat-id", "4")
                page.click("#seat-reindex")
                page.wait_for_function(
                    "uid => !installation.seats?.['0'] && installation.seats?.['4']?.bound === uid",
                    arg=uid)
                check("Reindex preserves the binding and selects the new Seat ID",
                      page.input_value("#seat-id") == "4")
                page.screenshot(path=os.path.join(HERE, "01-seats-workspace.png"),
                                full_page=True)

                page.click("#tab-button-devices")
                page.locator(f'#device-roster .device-row[data-uid="{uid}"]').click()
                page.wait_for_selector("#detail #patch-diagnostics")
                check("Devices retains device diagnostics",
                      page.locator("#detail #patch-diagnostics").count() == 1)
                check("Devices detail has no editable Seat, position, or params controls",
                      page.locator("#detail #seat-name, #detail #seat-id, #detail #seat-device, "
                                   "#detail [data-param], #detail .position-coordinate").count() == 0)
                page.screenshot(path=os.path.join(HERE, "02-device-boundary.png"),
                                full_page=True)

                page.click("#tab-button-seats")
                page.locator('.seat-row[data-seat-id="4"]').click()
                page.click("#seat-remove")
                page.wait_for_function("() => !installation.seats?.['4']")
                page.wait_for_function(
                    "uid => installation.devices?.[uid]?.id === -1 && "
                    "!installation.devices?.[uid]?.revoking_assignment", arg=uid)
                check("Delete revokes the live assignment before removing the Seat", True)
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
    print("Seats workspace browser checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
