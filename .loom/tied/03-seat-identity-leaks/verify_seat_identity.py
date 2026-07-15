#!/usr/bin/env python3
"""Focused bind/unbind/remove and Dashboard seat-identity regression."""

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
from pythonosc.osc_message_builder import OscMessageBuilder

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "dashboard", "server.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent

FAILURES = []
RESERVED = set()


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
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
    raise RuntimeError("cannot reserve localhost port")


def packet(address, args):
    builder = OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


def wait_http(url, process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before HTTP startup")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not start")


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-seat-identity-") as root:
        assets, patches = os.path.join(root, "assets"), os.path.join(root, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        state_path = os.path.join(root, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "identity", "seats": {
                "0": {"id": 0, "name": "Seat 0", "positions": [[1, 2]],
                      "params": {}, "bound": None},
            }}, target)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = os.path.join(root, "dashboard.log")
        log = open(log_path, "w", encoding="utf-8")
        process = None
        reporter = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        reporter.bind(("127.0.0.1", 0))
        try:
            process = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(command_port),
                "--state-file", state_path, "--assets-dir", assets,
                "--patches-dir", patches, "--sim-no-engine",
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base_url, process)
            reporter.sendto(packet("/hb", ["node-a", -1, "verify", 1, -45]),
                            ("127.0.0.1", listen_port))
            reporter.sendto(packet("/os/report", [json.dumps({
                "uid": "node-a", "hostname": "technical-host", "patch": "demo-pd",
            })]), ("127.0.0.1", listen_port))

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1400, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "() => installation.devices?.['node-a']?.hostname === 'technical-host'")
                page.click("#tab-button-devices")
                page.click('#unassigned .device-row[data-uid="node-a"]')
                page.click("#device-bind")
                page.wait_for_function(
                    "() => installation.seats?.['0']?.bound === 'node-a'"
                    " && selectedSeat === 0 && selected === 'node-a'")
                check("binding preserves the authored default seat name",
                      page.evaluate("installation.seats['0'].name") == "Seat 0")
                check("binding follows the selected device into its seat detail",
                      page.locator("#seat-name").input_value() == "Seat 0"
                      and page.locator("#seat-device").input_value() == "node-a")

                reporter.sendto(packet("/hb", ["node-a", 0, "verify", 1, -45]),
                                ("127.0.0.1", listen_port))
                live = page.frame_locator("#dashboard-live-view")
                card = live.locator('.card[data-uid="node-a"]')
                card.wait_for(state="attached", timeout=5000)
                card_text = card.inner_text()
                check("bound Dashboard card uses seat name and ID as primary identity",
                      "Seat 0 · ID 0" in card_text, card_text)
                check("bound Dashboard card keeps hostname and uid secondary",
                      "technical-host" in card_text and "node-a" in card_text, card_text)
                check("preset controls remain visibly seat-targeted",
                      page.locator("#preset-bar h3").inner_text() == "Seat presets"
                      and live.locator("#preset-label").inner_text() == "Seat presets")

                page.click("#seat-unbind")
                page.wait_for_function(
                    "() => installation.seats?.['0']?.bound == null"
                    " && selectedSeat === 0 && selected == null")
                check("unbind keeps seat detail but clears stale device selection",
                      page.locator("#seat-name").input_value() == "Seat 0"
                      and page.locator("#seat-unbind").count() == 0)

                page.select_option("#seat-device", "node-a")
                page.click("#seat-bind")
                page.wait_for_function(
                    "() => installation.seats?.['0']?.bound === 'node-a'"
                    " && selectedSeat === 0 && selected === 'node-a'")
                check("rebind restores coherent seat/device selection",
                      page.locator("#seat-device").input_value() == "node-a")

                page.click("#seat-remove")
                page.wait_for_function(
                    "() => !installation.seats?.['0']"
                    " && selectedSeat == null && selected == null")
                check("removing selected seat clears stale detail selection",
                      "Select a seat or device" in page.locator("#detail").inner_text())
                check("browser emitted no page errors", not errors, repr(errors))
                browser.close()
        finally:
            stop(process)
            reporter.close()
            log.close()
        server_log = open(log_path, encoding="utf-8").read()
        check("dashboard process exits cleanly",
              process is not None and process.returncode in (0, -15)
              and "Application shutdown complete" in server_log)
    total = 10
    print(f"\n{total - len(FAILURES)}/{total} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
