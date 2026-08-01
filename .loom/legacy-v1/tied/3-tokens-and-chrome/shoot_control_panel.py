#!/usr/bin/env python3
"""Screenshot harness for the control-panel token/chrome slice (01/3).

Not a check — an evidence generator. Boots the real dashboard + simfleet on
free ports and captures the two hosts of the shared ControlSurface in both
themes:

  * the Control tab's iframe surface (#dashboard-live-view)
  * the Device tab's control panel (#device-control)

Usage: shoot_control_panel.py <output-dir>

Run once on the pre-change tree (before/) and once after (after/).
"""

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

RESERVED = set()
UID_A = "02:53:49:4d:00:01"
UID_B = "02:53:49:4d:00:02"


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


def stop_process(process):
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


def make_fixture(root):
    """A manifest broad enough to show every chrome the slice touches: a
    float slider, an int 0/1 checkbox, a text param, and a nested branch."""
    patches = os.path.join(root, "patches")
    assets = os.path.join(root, "assets")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(assets)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"control-panel-shoot")
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin",
            "params": [
                {"name": "density", "type": "f", "min": 0, "max": 1,
                 "default": .35, "dashboard": True},
                {"name": "spread", "type": "f", "min": 0, "max": 1,
                 "default": .7, "dashboard": True},
                {"name": "engaged", "type": "i", "min": 0, "max": 1,
                 "default": 1, "dashboard": True},
                # The validator only allows numeric defaults, so a string
                # param must omit `default` (CLAUDE.md testing gotcha 7).
                {"name": "label", "type": "s", "dashboard": True},
                {"path": ["filter"], "name": "cutoff", "type": "f",
                 "min": 0, "max": 1, "default": .5, "dashboard": True},
                {"path": ["filter"], "name": "resonance", "type": "f",
                 "min": 0, "max": 1, "default": .2, "dashboard": True},
            ],
            "cues": [{"id": "go", "label": "Go"}],
            "caps": [], "slots": [],
        }, target)

    def seat(seat_id, name, uid, groups):
        return {"id": seat_id, "name": name, "positions": [[seat_id, 1]],
                "groups": groups, "bound": uid, "patch": "alpha",
                "params": {"density": .35, "spread": .7, "engaged": 1,
                           "filter/cutoff": .5, "filter/resonance": .2}}

    state = {
        "schema": 1, "name": "Control panel shoot",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "groups": {"0": {"id": 0, "name": "Front"}},
        "seats": {"1": seat(1, "Freda", UID_A, [0]),
                  "2": seat(2, "Sparks", UID_B, [])},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path


def set_theme(page, theme):
    page.evaluate("theme => localStorage.setItem('bopos-theme', theme)", theme)
    page.reload()
    page.wait_for_selector("#ws-status.online")


def shoot(page, out_dir, theme):
    # --- Control tab: the surface lives in an iframe ---
    page.goto(page.url.split("#")[0] + "#control")
    page.wait_for_selector("#tab-control:not([hidden])")
    frame = page.frame_locator("#dashboard-live-view")
    frame.locator('.live-card[data-live-scope="all"] .live-param').first \
        .wait_for()
    time.sleep(.6)
    page.locator("#dashboard-live-view").screenshot(
        path=os.path.join(out_dir, f"control-tab-{theme}.png"))

    # A drawer open, so the generator chrome is in the frame too. Heartbeat
    # re-renders keep the rows perpetually "unstable", so Playwright's
    # actionability wait can time out — dispatch the click directly instead
    # (CLAUDE.md testing gotcha 6).
    def click_in_frame(selector):
        page.frames[-1].evaluate(
            "sel => document.querySelector(sel)?.click()", selector)

    click_in_frame('[data-gen-mode="gen"]')
    frame.locator(".live-param-gen").first.wait_for()
    time.sleep(.4)
    page.locator("#dashboard-live-view").screenshot(
        path=os.path.join(out_dir, f"control-tab-drawer-{theme}.png"))
    click_in_frame('[data-gen-mode="value"]')

    # --- Device tab: the same rows inside the device panel ---
    page.click("#tab-button-devices")
    page.wait_for_selector("#tab-devices:not([hidden])")
    # data-uid is not unique across tabs — scope to the roster.
    page.click(f'#device-roster .device-row[data-uid="{UID_A}"]')
    page.wait_for_selector("#device-control")
    toggle = page.locator("#device-control-toggle")
    if toggle.get_attribute("aria-expanded") != "true":
        toggle.click()
    page.wait_for_selector("#device-control .live-param")
    time.sleep(.6)
    page.locator("#device-control").screenshot(
        path=os.path.join(out_dir, f"device-panel-{theme}.png"))


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: shoot_control_panel.py <output-dir>")
    out_dir = os.path.realpath(sys.argv[1])
    os.makedirs(out_dir, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="bopos-panel-shoot-") as temp:
        state_path = make_fixture(temp)
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log = open(os.path.join(temp, "server.log"), "w",
                          encoding="utf-8")
        fleet_log = open(os.path.join(temp, "fleet.log"), "w",
                         encoding="utf-8")
        server = fleet = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port),
                "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", assets, "--patches-dir", patches,
                "--public-url", base_url,
            ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "2", "--target", "127.0.0.1",
                "--report-port", str(listen_port),
                "--cmd-port", str(send_port),
                "--hb-interval", "0.5", "--boot-secs", "0.2",
                "--patches-dir", patches, "--assets-dir", assets,
                "--manifest", os.path.join(patches, "alpha",
                                           "bopos.patch.json"),
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440,
                                                  "height": 1200})
                page.set_default_timeout(15000)
                page.goto(base_url + "#control")
                page.wait_for_selector("#ws-status.online")
                for theme in ("dark", "light"):
                    set_theme(page, theme)
                    shoot(page, out_dir, theme)
                browser.close()
        finally:
            stop_process(fleet)
            stop_process(server)
            server_log.close()
            fleet_log.close()

    print("screenshots written to " + out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
