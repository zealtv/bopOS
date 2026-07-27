#!/usr/bin/env python3
"""Verify manifest parameter visibility across bopOS control surfaces.

The desktop Control tab and Device control panel expose the complete manifest.
The standalone facilitator page exposes only declarations marked
``dashboard: true``. The persisted compatibility field keeps its old name,
while the Patch-tab authoring label describes its narrowed meaning.
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
ROOT = os.path.realpath(os.path.dirname(__file__))
while not os.path.isfile(os.path.join(ROOT, "tools", "simfleet.py")):
    parent = os.path.dirname(ROOT)
    if parent == ROOT:
        raise SystemExit("cannot locate bopOS repository")
    ROOT = parent

FAILURES = []
RESERVED = set()
UID = "02:53:49:4d:00:01"


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""), flush=True)
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


PARAMS = [
    {"name": "gain", "type": "f", "min": 0, "max": 1, "default": .5,
     "dashboard": True},
    {"path": ["texture"], "name": "density", "type": "f",
     "min": 0, "max": 1, "default": .2, "dashboard": False},
    {"path": ["texture"], "name": "rate", "type": "i",
     "min": 1, "max": 8, "default": 3},
]


def write_fixture(temp):
    patches = os.path.join(temp, "patches")
    assets = os.path.join(temp, "assets")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(assets)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"manifest-visibility")
    manifest = os.path.join(patch, "bopos.patch.json")
    with open(manifest, "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin",
                   "params": PARAMS, "cues": [], "caps": [], "slots": []},
                  target)
    state_path = os.path.join(temp, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump({
            "schema": 1, "name": "Manifest visibility rig",
            "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                            "staged_at": time.time(), "previous": None},
            "params_patch": "alpha",
            "seats": {
                "1": {"id": 1, "name": "Finn", "positions": [[1, 1]],
                      "bound": UID,
                      "params": {"gain": .5, "texture/density": .2,
                                 "texture/rate": 3}},
            },
        }, target)
    return state_path, patches, assets, manifest


def identities(locator):
    return sorted(locator.evaluate_all(
        "nodes => nodes.map(node => node.dataset.paramPath)"))


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-param-visibility-") as temp:
        state_path, patches, assets, manifest = write_fixture(temp)
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
                sys.executable, os.path.join(ROOT, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port),
                "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", assets, "--patches-dir", patches,
                "--public-url", base_url,
            ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(ROOT, "tools", "simfleet.py"),
                "--devices", "1", "--target", "127.0.0.1",
                "--report-port", str(listen_port),
                "--cmd-port", str(send_port), "--hb-interval", "0.3",
                "--boot-secs", "0.2", "--manifest", manifest,
                "--patches-dir", patches, "--assets-dir", assets,
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440,
                                                  "height": 1100})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-control")
                frame = page.frame_locator("#dashboard-live-view")
                controls = frame.locator("[data-live-param]")
                controls.first.wait_for()
                expected = ["gain", "texture/density", "texture/rate"]
                check("Control tab shows every manifest parameter",
                      identities(controls) == expected, repr(identities(controls)))
                check("Control preserves the nested texture branch",
                      frame.locator(".live-param-branch h3",
                                    has_text="texture").count() >= 1)
                check("unflagged numeric params retain generator authoring",
                      frame.locator(
                          '.live-param[data-param-path="texture/density"]'
                          ' [data-gen-toggle]'
                      ).count() >= 1)

                facilitator = browser.new_page()
                facilitator_errors = []
                facilitator.on(
                    "pageerror",
                    lambda error: facilitator_errors.append(str(error)))
                facilitator.goto(base_url + "/facilitator")
                facilitator.locator("[data-live-param]").first.wait_for()
                visible = identities(
                    facilitator.locator("[data-live-param]"))
                check("standalone facilitator shows only flagged parameters",
                      visible == ["gain"], repr(visible))

                page.click("#tab-button-devices")
                page.wait_for_function(
                    "uid => installation.devices[uid]?.online === true",
                    arg=UID)
                page.click(
                    f'#device-roster .device-row[data-uid="{UID}"]')
                page.click("#device-control-toggle")
                device_controls = page.locator(
                    "#device-control-body [data-live-param]")
                device_controls.first.wait_for()
                check("Device control shows every manifest parameter",
                      identities(device_controls) == expected,
                      repr(identities(device_controls)))

                page.click("#tab-button-patches")
                page.wait_for_selector("#manifest-params .manifest-check")
                check("Patch-tab checkbox is labelled Facilitator",
                      page.locator(
                          "#manifest-params .manifest-check").first.inner_text(
                          ).strip() == "Facilitator")
                check("browser surfaces emitted no page errors",
                      not errors and not facilitator_errors,
                      repr(errors + facilitator_errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

    print()
    if FAILURES:
        print("FAILED: " + "; ".join(FAILURES))
        return 1
    print("Manifest parameter visibility checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
