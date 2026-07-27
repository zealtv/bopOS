#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for the live-param control kinds
reaching the wire (43-live-param-checkbox-nosend, kinds per
01-control-panel/6-non-float-kinds).

The regression: DOM event handlers were bound as `input.onchange = send`, so
the Event object landed in send()'s `override` parameter and went to the wire
as the JSON-serialized event (`{"isTrusted":true}`), which the server rejects
("That live parameter or target is unavailable."). Checkboxes have no
throttled oninput path, so they were fully broken; slider onchange/onpointerup
sends were silently rejected too but masked by oninput.

The 0/1 control is no longer a checkbox: the ratified design makes it a
latching button (`aria-pressed`), and enums join it as a select over the
option index. The regression above is a property of the *binding*, so it is
re-pinned here for every kind that binds.

Under real heartbeat cadence (the re-render race is part of the repro) this
clicks an All-card live toggle and asserts:
  (a) the numeric value reaches the wire (`p/<name>=<value>` in the fleet log),
  (b) the seat params persist into installation.json on disk,
  (c) the toggle state survives heartbeat re-renders (no revert),
  (d) no server error alert fires,
and repeats the wire assertion for the slider's change-commit path, the
integer row, and the enum select.

Owned by code surface (control-surface.js), not by a stitch.
"""

import json
import os
import random
import re
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


def wait_log(path, pattern, timeout=8):
    """Poll the fleet log for a regex (a captured wire write)."""
    deadline = time.monotonic() + timeout
    rx = re.compile(pattern)
    while time.monotonic() < deadline:
        try:
            with open(path, encoding="utf-8") as source:
                if rx.search(source.read()):
                    return True
        except OSError:
            pass
        time.sleep(.1)
    return False


def wait_state(path, predicate, timeout=8):
    """Poll installation.json on disk until predicate(state) is true."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with open(path, encoding="utf-8") as source:
                if predicate(json.load(source)):
                    return True
        except (OSError, ValueError):
            pass
        time.sleep(.1)
    return False


def make_fixture(root):
    patches = os.path.join(root, "patches")
    assets = os.path.join(root, "assets")
    state_dir = os.path.join(root, "sim-state")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(assets)
    os.makedirs(state_dir)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"param-kinds-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            # i with min 0 / max 1 renders as the latching toggle button.
            {"name": "gate", "type": "i", "min": 0, "max": 1,
             "default": 0, "dashboard": True},
            {"name": "density", "type": "f", "min": 0, "max": 1,
             "default": .2, "dashboard": True},
            {"name": "steps", "type": "i", "min": 0, "max": 8,
             "default": 2, "dashboard": True},
            {"name": "mode", "type": "i", "options": ["dry", "hall", "plate"],
             "default": 0, "dashboard": True},
        ], "cues": [], "caps": [], "slots": [],
    }
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump(manifest, target, indent=2)
    uids = ["02:53:49:4d:00:01", "02:53:49:4d:00:02"]

    def seat(seat_id, name, uid):
        # Identical values keep the All aggregate non-mixed.
        return {"id": seat_id, "name": name, "positions": [[seat_id, 1]],
                "groups": [], "bound": uid, "patch": "alpha",
                "params": {"gate": 0, "density": .2, "steps": 2, "mode": 0}}

    state = {
        "schema": 1, "name": "Param kinds verifier",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "seats": {"1": seat(1, "Freda", uids[0]),
                  "2": seat(2, "Sparks", uids[1])},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-live-param-kinds-") as temp:
        state_path = make_fixture(temp)
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        state_dir = os.path.join(temp, "sim-state")
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
                "--listen-port", str(listen_port),
                "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", assets, "--patches-dir", patches,
                "--public-url", base_url,
            ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            # Fast heartbeats keep renderCards() churning during the
            # pointerdown -> change gesture — the race is part of the repro.
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "2", "--target", "127.0.0.1",
                "--report-port", str(listen_port),
                "--cmd-port", str(send_port),
                "--hb-interval", "0.2", "--boot-secs", "0.2",
                "--state-dir", state_dir, "--manifest",
                os.path.join(patches, "alpha", "bopos.patch.json"),
                "--patches-dir", patches, "--assets-dir", assets,
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 900, "height": 1200})
                page.set_default_timeout(10000)
                page_errors, alerts = [], []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.on("dialog",
                        lambda dialog: (alerts.append(dialog.message),
                                        dialog.dismiss()))
                page.goto(base_url + "/facilitator")
                page.wait_for_selector('.live-card[data-live-scope="all"]')
                page.wait_for_function(
                    "() => Object.keys(installation.devices||{}).length === 2")

                gate = ('.live-card[data-live-scope="all"] '
                        'button.live-toggle[data-live-param]'
                        '[data-param-path="gate"]')
                check("All card renders the 0/1 int param as a latching button",
                      page.locator(gate).count() == 1
                      and page.locator(gate).get_attribute("aria-pressed")
                      == "false")

                # --- toggle on: numeric wire value, disk persistence ---
                page.locator(gate).click()
                check("latching the toggle sends the numeric value to the wire",
                      wait_log(fleet_log_path, r"p/gate=1(\b|\.)"),
                      "fleet log missing p/gate=1")
                check("the latched value persists into installation.json seats",
                      wait_state(state_path, lambda state: all(
                          seat.get("params", {}).get("gate") == 1
                          for seat in state.get("seats", {}).values())))

                # --- survives heartbeat re-renders: no revert, no alert ---
                page.wait_for_timeout(1500)
                check("the toggle stays latched across heartbeat re-renders",
                      page.locator(gate).get_attribute("aria-pressed")
                      == "true")
                check("no server rejection alert fired", not alerts, repr(alerts))

                # --- toggle off round-trips too ---
                page.locator(gate).click()
                check("unlatching sends 0 to the wire",
                      wait_log(fleet_log_path, r"p/gate=0(\b|\.)"),
                      "fleet log missing p/gate=0")
                check("the unlatched value persists into installation.json",
                      wait_state(state_path, lambda state: all(
                          seat.get("params", {}).get("gate") == 0
                          for seat in state.get("seats", {}).values())))

                # --- the slider's change-commit path sends a number as well ---
                slider = ('.live-card[data-live-scope="all"] '
                          'input[type="range"][data-live-param]'
                          '[data-param-path="density"]')
                # fires input AND change. `press` re-checks actionability, so a
                # heartbeat re-render between focusing and typing cannot
                # swallow the keystroke — focus() + keyboard.press() did, and
                # that was this file's one intermittent failure.
                page.locator(slider).press("ArrowRight")
                check("slider change-commit reaches the wire numerically",
                      wait_log(fleet_log_path, r"p/density=0\.21(\b|0)"),
                      "fleet log missing p/density=0.21")

                # --- the integer row steps by 1 on the same numeric path ---
                steps = ('.live-card[data-live-scope="all"] '
                         'input[type="range"][data-live-param]'
                         '[data-param-path="steps"]')
                # `press` re-checks actionability, so a heartbeat re-render
                # between focusing and typing cannot swallow the keystroke.
                page.locator(steps).press("ArrowRight")
                check("an integer row steps by one to the wire",
                      wait_log(fleet_log_path, r"p/steps=3(\b|\.)"),
                      "fleet log missing p/steps=3")

                # --- the enum select sends the option index, not the label ---
                enum = ('.live-card[data-live-scope="all"] '
                        'select.live-enum[data-live-param]'
                        '[data-param-path="mode"]')
                check("All card renders the enum param as a select",
                      page.locator(enum).count() == 1)
                page.select_option(enum, "2")
                check("choosing an option sends its index to the wire",
                      wait_log(fleet_log_path, r"p/mode=2(\b|\.)"),
                      "fleet log missing p/mode=2")
                check("the enum index persists into installation.json seats",
                      wait_state(state_path, lambda state: all(
                          seat.get("params", {}).get("mode") == 2
                          for seat in state.get("seats", {}).values())))
                page.wait_for_timeout(1500)
                check("the enum selection survives heartbeat re-renders",
                      page.locator(enum).input_value() == "2")

                page.wait_for_timeout(400)
                check("no rejection alert across the whole run", not alerts,
                      repr(alerts))
                check("no page errors", not page_errors, repr(page_errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()
        if FAILURES:
            for path in (server_log_path, fleet_log_path):
                try:
                    with open(path, encoding="utf-8") as source:
                        print(f"\n{os.path.basename(path)} tail:\n",
                              source.read()[-3000:])
                except OSError:
                    pass
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("Live-param kind browser checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
