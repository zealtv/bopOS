#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for the Device-tab "Set patch…"
hand-off (thread 37, stitch 11).

Bob's rulings, each one a check:

  * the hand-off target is the PATCH TAB, not Control -- there is exactly one
    deployment picker and this is a shortcut to it, never a second one;
  * a TAB SWITCH with the device pre-scoped, plus a way back;
  * an unbound device is offered an ORDINARY SEAT in one click, because pinning
    addresses a device by Seat and the operator should not have to learn why;
  * "pinned" keeps meaning patch-pinned only -- a seat-bound standalone device
    gets no second sense of the word.

Owned by code surface (dashboard.js patch diagnostics + fleet patch panel).
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

FAILURES = []
RESERVED = set()
UID_A = "02:53:49:4d:00:01"
UID_B = "02:53:49:4d:00:02"


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


def write_patch(patches, name):
    path = os.path.join(patches, name)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "main.bin"), "wb") as target:
        target.write(name.encode())
    with open(os.path.join(path, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "params": [],
                   "caps": [], "slots": []}, target)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-set-patch-") as temp:
        state_path = os.path.join(temp, "installation.json")
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        write_patch(patches, "alpha")
        write_patch(patches, "beta")
        # Device A is seat-bound (the ordinary path); device B is unbound --
        # the standalone case the one-click Seat exists for.
        state = {
            "schema": 1, "name": "Set patch hand-off rig",
            "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                            "staged_at": time.time(), "previous": None},
            "params_patch": "alpha",
            "seats": {"1": {"id": 1, "name": "Finn", "positions": [[1, 1]],
                            "params": {}, "bound": UID_A}},
        }
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump(state, target)

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
                "--hb-interval", "0.3", "--boot-secs", "0.2",
                "--fetch-seconds", "0.3", "--patches-dir", patches,
                "--assets-dir", assets,
                "--manifest", os.path.join(patches, "alpha",
                                           "bopos.patch.json"),
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440,
                                                  "height": 1200})
                page.set_default_timeout(12000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "() => Object.keys(installation.devices||{}).length === 2")

                page.click("#tab-button-devices")
                page.wait_for_selector("#tab-devices:not([hidden])")
                # Seat rows carry data-uid too (CLAUDE.md testing gotcha 12).
                page.click(f'#device-roster .device-row[data-uid="{UID_A}"]')
                page.wait_for_selector("#patch-diagnostics")

                check("a bound device offers Set patch… in its diagnostics",
                      page.locator("#device-set-patch").count() == 1)

                # --- the hand-off lands on the Patch tab, pre-scoped ---
                page.click("#device-set-patch")
                page.wait_for_selector("#tab-patches:not([hidden])")
                check("Set patch… hands off to the Patches tab",
                      page.locator("#tab-patches").get_attribute("hidden")
                      is None
                      and page.locator("#tab-control").get_attribute("hidden")
                      is not None)
                check("the picker is pre-scoped to that device",
                      page.input_value("#patch-target") == UID_A)
                check("the confirm reads Pin to device",
                      "pin to device"
                      in page.locator("#patch-switch").inner_text().lower())
                check("there is still exactly one deployment picker",
                      page.locator("#patch-target").count() == 1)

                # --- and there is a way back ---
                crumb = page.locator("#patch-handoff-crumb")
                # The crumb names the device by its alias, which is generated,
                # so read it from state rather than hard-coding one.
                alias = page.evaluate(
                    "uid => window.DeviceIdentity.primary("
                    "installation.devices[uid], installation)", arg=UID_A)
                check("a crumb offers the way back to the device",
                      crumb.get_attribute("hidden") is None
                      and alias.lower() in crumb.inner_text().lower(),
                      f"{crumb.inner_text()!r} vs {alias!r}")
                page.click("#patch-handoff-back")
                page.wait_for_selector("#tab-devices:not([hidden])")
                check("the crumb returns to that device",
                      page.evaluate("() => selected") == UID_A)

                # --- an unbound device is offered an ordinary Seat ---
                page.click(f'#device-roster .device-row[data-uid="{UID_B}"]')
                page.wait_for_selector("#patch-diagnostics")
                check("the unbound device is unbound to start with",
                      page.evaluate(
                          "uid => !Object.values(installation.seats||{})"
                          ".some(s => s.bound === uid)", arg=UID_B))
                page.click("#device-set-patch")
                bound = page.wait_for_function(
                    "uid => Object.values(installation.seats||{})"
                    ".some(s => s.bound === uid)", arg=UID_B, timeout=15000)
                check("Set patch… gives an unbound device a Seat in one click",
                      bound is not None)
                page.wait_for_selector("#tab-patches:not([hidden])")
                check("the hand-off completes once the binding lands",
                      page.input_value("#patch-target") == UID_B)

                seat_kind = page.evaluate(
                    "uid => { const seat = Object.values(installation.seats)"
                    ".find(s => s.bound === uid);"
                    " return {id: seat.id, name: seat.name,"
                    " keys: Object.keys(seat)}; }", arg=UID_B)
                check("the Seat is an ordinary Seat, not a hidden one",
                      isinstance(seat_kind["id"], int)
                      and "hidden" not in seat_kind["keys"]
                      and "utility" not in seat_kind["keys"], repr(seat_kind))

                # --- "pinned" still means patch-pinned only ---
                check("binding a Seat does not mark the device pinned",
                      page.evaluate(
                          "uid => installation.devices[uid].patch_pinned"
                          " !== true", arg=UID_B))
                page.select_option("#patch-select", "beta")
                page.click("#patch-switch")
                page.wait_for_function(
                    "uid => installation.devices[uid]?.pinned_patch === 'beta'",
                    arg=UID_B, timeout=20000)
                check("pinning a patch is what makes a device pinned",
                      page.evaluate(
                          "uid => installation.devices[uid].patch_pinned"
                          " === true", arg=UID_B))

                check("no page errors", not errors, repr(errors))
                browser.close()
        finally:
            stop_process(fleet)
            stop_process(server)
            server_log.close()
            fleet_log.close()

    print()
    if FAILURES:
        print("FAILED: " + "; ".join(FAILURES))
        return 1
    print("Set patch hand-off checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
