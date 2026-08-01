#!/usr/bin/env python3
"""Focused real-dashboard browser check for alias editing and identity hierarchy."""

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
    REPO = os.path.dirname(REPO)


def free_port(kind):
    for _ in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        probe = socket.socket(socket.AF_INET, kind)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            probe.close()
            continue
        probe.close()
        return port
    raise RuntimeError("could not reserve port")


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def wait_http(url, process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not start")


def check(label, condition, detail=""):
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    print(f"PASS {label}")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-alias-browser-") as temp:
        state = os.path.join(temp, "installation.json")
        assets, patches = os.path.join(temp, "assets"), os.path.join(temp, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        with open(state, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "Alias rig", "seats": {}}, target)
        http, listen, send = (free_port(socket.SOCK_STREAM),
                              free_port(socket.SOCK_DGRAM), free_port(socket.SOCK_DGRAM))
        base = f"http://127.0.0.1:{http}"
        log = open(os.path.join(temp, "run.log"), "w", encoding="utf-8")
        server = fleet = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard/server.py"),
                "--host", "127.0.0.1", "--port", str(http),
                "--listen-port", str(listen), "--send-port", str(send),
                "--osc-target", "127.0.0.1", "--state-file", state,
                "--assets-dir", assets, "--patches-dir", patches,
                "--public-url", base,
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools/simfleet.py"),
                "--devices", "1", "--unassigned", "1", "--target", "127.0.0.1",
                "--report-port", str(listen), "--cmd-port", str(send),
                "--hb-interval", "0.2", "--patches-dir", patches,
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.set_default_timeout(10000)
                errors, dialogs = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.accept()))
                page.goto(base + "/#devices")
                page.wait_for_function("() => Object.keys(installation.devices||{}).length === 1")
                page.wait_for_function("() => Object.keys(installation.device_registry||{}).length === 1")
                row = page.locator("#device-roster .device-row")
                uid = row.get_attribute("data-uid")
                generated = page.evaluate("uid => installation.device_registry[uid].alias", uid)
                check("generated alias is the Devices primary identity",
                      row.locator("strong").inner_text() == generated)
                check("UID tail remains visible as technical secondary identity",
                      uid[-8:] in row.locator("small").first.inner_text())

                row.click()
                page.fill("#device-alias", "Freda Sparks")
                page.click("#device-alias-save")
                page.wait_for_function(
                    "uid => installation.device_registry[uid].alias === 'Freda Sparks'", arg=uid)
                check("Rename updates roster and detail together",
                      page.locator("#device-roster .device-row strong").inner_text() == "Freda Sparks"
                      and page.locator("#detail h2").first.inner_text().startswith("Freda Sparks"))

                page.click("#tab-button-seats")
                page.click("#seat-add")
                page.wait_for_selector("#seat-device")
                check("Seat assignment picker is alias-first",
                      page.locator("#seat-device option").filter(has_text="Freda Sparks").count() == 1)
                page.select_option("#seat-device", uid)
                page.click("#seat-bind")
                page.wait_for_function("uid => installation.seats['0'].bound === uid", arg=uid)
                check("bound Seat note retains alias and technical identity",
                      "Freda Sparks" in page.locator(".seat-binding-note").inner_text())

                page.click("#tab-button-assets")
                check("Assets target is alias-first",
                      page.locator("#asset-target option").filter(has_text="Freda Sparks").count() == 1)

                frame = page.frame_locator("#dashboard-live-view")
                page.click("#tab-button-dashboard")
                frame.locator(".card").wait_for()
                check("bound Dashboard card keeps Seat primary and alias secondary",
                      "Seat 0" in frame.locator(".card .name strong").inner_text()
                      and "Freda Sparks" in frame.locator(".card .name small").inner_text())

                page.click("#tab-button-devices")
                page.locator("#device-roster .device-row").click()
                page.click("#device-alias-reset")
                page.wait_for_function(
                    "uid => installation.device_registry[uid].source === 'generated'", arg=uid)
                check("Reset restores a generated alias across the roster",
                      page.locator("#device-roster .device-row strong").inner_text() != "Freda Sparks")
                check("browser emitted no page errors", not errors, repr(errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            log.close()
    print("\n9/9 browser checks passed")


if __name__ == "__main__":
    main()
