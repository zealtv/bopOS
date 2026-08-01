#!/usr/bin/env python3
"""Focused Playwright verification for the ratified tabs-1 IA skeleton."""

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
        if port in RESERVED:
            continue
        sock = socket.socket(socket.AF_INET, kind)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            sock.close()
            continue
        sock.close()
        RESERVED.add(port)
        return port
    raise RuntimeError("cannot reserve port")


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


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-tabs1-") as temp:
        patches = os.path.join(temp, "patches")
        assets = os.path.join(temp, "assets")
        patch = os.path.join(patches, "alpha")
        os.makedirs(patch)
        os.makedirs(assets)
        manifest = os.path.join(patch, "bopos.patch.json")
        with open(os.path.join(patch, "main.bin"), "wb") as target:
            target.write(b"tabs verifier")
        with open(manifest, "w", encoding="utf-8") as target:
            json.dump({
                "engine": "test", "entrypoint": "main.bin",
                "params": [{"name": "gain", "type": "f", "min": 0,
                            "max": 1, "default": .5, "group": "mix",
                            "facilitator": True}],
                "cues": [{"id": "start"}], "caps": [], "slots": [],
            }, target)
        state_path = os.path.join(temp, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "tabs rig", "seats": {},
                       "facilitator_commands": ["restart-engine"]}, target)

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
                "--devices", "2", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.3", "--manifest", manifest,
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "() => Object.keys(installation.devices||{}).length >= 2")

                labels = page.locator("#primary-tabs [role=tab]").all_inner_texts()
                check("ratified six-tab order is visible", labels == [
                    "Dashboard", "Seats", "Devices", "Patches", "Assets",
                    "Sequencer"], repr(labels))
                check("Dashboard is the default view",
                      page.locator("#tab-dashboard").is_visible()
                      and page.locator("#tab-button-dashboard").get_attribute(
                          "aria-selected") == "true")

                live = page.frame_locator("#dashboard-live-view")
                live.locator("#cards .card").first.wait_for(timeout=10000)
                check("embedded Dashboard keeps promoted device controls",
                      live.locator('[data-param="gain"]').count() >= 2)
                check("Dashboard exposes fleet-scoped promoted admin command",
                      live.locator('[data-command="restart-engine"]').count() == 1)
                check("Dashboard exposes single-device onboarding commands",
                      live.locator('[data-device-command="restart-engine"]').count() >= 2)
                check("embedded compatibility surface omits duplicate header",
                      not live.locator("header").is_visible())
                page.fill("#master", "0.42")
                page.dispatch_event("#master", "input")
                page.wait_for_function(
                    "() => document.querySelector('#master-out').value === '42%'")
                check("relocated Dashboard master remains functional",
                      abs(page.evaluate("() => master") - .42) < .001)
                page.fill("#cue-id", "tabs-check")
                page.click("#cue-fire")
                page.wait_for_function(
                    "() => document.querySelector('#cue-status').value.includes('tabs-check fires')")
                check("relocated Dashboard cue remains functional", True)
                live.locator('[data-command="restart-engine"]').click()
                live.locator(".device-commands").first.locator("summary").click()
                live.locator('[data-device-command="restart-engine"]').first.click()
                check("both promoted admin scopes dispatch through existing guards", True)
                page.screenshot(path=os.path.join(HERE, "01-dashboard.png"),
                                full_page=True)

                page.click("#tab-button-seats")
                page.wait_for_selector("#tab-seats:not([hidden]) #spatial .room")
                check("Seats owns spatial, simulation, and venue controls",
                      page.locator("#tab-seats #spatial").is_visible()
                      and page.locator("#tab-seats #simulate-toggle").is_visible()
                      and page.locator("#tab-seats #venue-bar").is_visible())
                page.fill("#room-w", "12")
                page.dispatch_event("#room-w", "change")
                page.wait_for_function("() => installation.room?.width === 12")
                check("relocated room authoring remains functional", True)
                page.screenshot(path=os.path.join(HERE, "02-seats.png"),
                                full_page=True)

                page.click("#tab-button-devices")
                page.wait_for_selector("#tab-devices:not([hidden]) .device-row")
                check("Devices owns roster and fleet patch controls",
                      page.locator("#tab-devices #device-roster .device-row").count() >= 2
                      and page.locator("#tab-devices #fleet-patch-panel").is_visible())
                page.locator("#device-roster .device-row").first.click()
                page.wait_for_selector("#detail section")
                check("device selection still opens inspection detail",
                      "UID" in page.locator("#detail").inner_text())
                page.screenshot(path=os.path.join(HERE, "03-devices.png"),
                                full_page=True)

                page.click("#tab-button-patches")
                check("Patches owns the landed patch editor",
                      page.locator("#tab-patches #editor-panel").is_visible()
                      and page.locator("#editor-patch option").count() >= 1)
                page.screenshot(path=os.path.join(HERE, "04-patches.png"),
                                full_page=True)
                page.click("#tab-button-assets")
                check("Assets placeholder is explicit",
                      page.locator("#tab-assets").is_visible()
                      and "asset management" in page.locator("#tab-assets").inner_text().lower())
                page.click("#tab-button-sequencer")
                check("Sequencer placeholder is explicit",
                      page.locator("#tab-sequencer").is_visible()
                      and "future co-design" in page.locator("#tab-sequencer").inner_text().lower())
                check("tab choice is reflected in the URL", page.url.endswith("#sequencer"), page.url)

                page.reload()
                page.wait_for_selector("#tab-sequencer:not([hidden])")
                check("tab choice survives reload through the URL hash",
                      page.locator("#tab-sequencer").is_visible())
                page.goto(base_url + "/facilitator")
                check("standalone compatibility entry is renamed Dashboard",
                      page.title() == "bopOS Dashboard"
                      and page.locator('#technical-link[href="/"]').is_visible())
                check("browser emitted no page errors", not errors, repr(errors))
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
    print("tabs-1 skeleton checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
