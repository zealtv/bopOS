#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for the generator drawer on the live
control surface (thread 37, stitch 08).

Bob ratified three things about this affordance, and each one is a check here:

  1. DRAWER, not popover, in every host -- so a numeric row has a value/gen
     switch that opens an inline drawer, and there is no popover variant.
  2. MIXED AGGREGATES USE THE EXISTING PATTERN -- the aggregate is never
     disabled because members disagree, and committing a generator sets all
     members. The failure mode this guards is a `mode === 'gen'` branch.
  3. STOP LIVES INSIDE THE DRAWER -- the switch stays strictly two-state, so
     stop is a control in the drawer and not a third segment.

It also pins the wire: the drawer compiles to the OSC contract section 3.2
grammar and reaches the node through set_live_automation, and stop clears the
recorded automation again.

Owned by code surface (control-surface.js + param-generator.js).
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


def read_log(path):
    try:
        with open(path, encoding="utf-8") as source:
            return source.read()
    except OSError:
        return ""


def wait_log(path, pattern, timeout=8):
    deadline = time.monotonic() + timeout
    rx = re.compile(pattern)
    while time.monotonic() < deadline:
        if rx.search(read_log(path)):
            return True
        time.sleep(.1)
    return False


# simfleet does not echo the generator command: it parses the section 3.2
# message, runs a real generator engine, and logs the scalar ticks the engine
# emits. So "the generator reached the wire and is running" is visible as a
# stream of *changing* p/<name>= values, which is a stronger claim than an echo
# would have been.
def density_ticks(path):
    return re.findall(r"p/density=([\d.eE+-]+)", read_log(path))


def wait_ticking(path, distinct=3, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if len(set(density_ticks(path))) >= distinct:
            return True
        time.sleep(.2)
    return False


UIDS = ["02:53:49:4d:00:01", "02:53:49:4d:00:02"]


def make_fixture(root, mixed):
    """`mixed` gives the two seats different values for `density`, which is how
    the aggregate lands in its mixed state without any UI interaction."""
    patches = os.path.join(root, "patches")
    assets = os.path.join(root, "assets")
    state_dir = os.path.join(root, "sim-state")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(assets)
    os.makedirs(state_dir)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"generator-drawer-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"name": "density", "type": "f", "min": 0, "max": 1,
             "default": .2, "dashboard": True},
            {"name": "label", "type": "s", "dashboard": True},
        ], "cues": [], "caps": [], "slots": [],
    }
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump(manifest, target, indent=2)

    def seat(seat_id, name, uid, density):
        return {"id": seat_id, "name": name, "positions": [[seat_id, 1]],
                "groups": [], "bound": uid, "patch": "alpha",
                "params": {"density": density, "label": "hi"}}

    state = {
        "schema": 1, "name": "Generator drawer verifier",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "seats": {"1": seat(1, "Freda", UIDS[0], .2),
                  "2": seat(2, "Sparks", UIDS[1], .8 if mixed else .2)},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path


ALL_DENSITY = ('.live-card[data-live-scope="all"] '
               'input[data-live-param][data-param-path="density"]')
ALL_ROW = ('.live-card[data-live-scope="all"] '
           '.live-param[data-param-path="density"]')
GEN_BUTTON = (ALL_ROW + ' [data-gen-mode="gen"]')
VALUE_BUTTON = (ALL_ROW + ' [data-gen-mode="value"]')
DRAWER = '.live-card[data-live-scope="all"] .live-param-gen'


def run(page, base_url, fleet_log_path, state_path, mixed):
    page.goto(base_url + "/facilitator")
    page.wait_for_selector('.live-card[data-live-scope="all"]')
    page.wait_for_function(
        "() => Object.keys(installation.devices||{}).length === 2")

    label = "mixed" if mixed else "agreeing"

    # --- 1. the switch exists on numeric rows only ---
    check(f"[{label}] numeric row carries a value/gen switch",
          page.locator(GEN_BUTTON).count() == 1)
    check(f"[{label}] string row carries no generator switch",
          page.locator('.live-card[data-live-scope="all"] '
                       '.live-param[data-param-path="label"] '
                       '[data-gen-mode]').count() == 0)
    check(f"[{label}] the switch is exactly two states",
          page.locator(ALL_ROW + " [data-gen-mode]").count() == 2)

    # --- 2. mixed aggregates are NOT disabled ---
    if mixed:
        check("[mixed] the aggregate row reports its mixed state",
              "mixed" in (page.locator(ALL_ROW).get_attribute("class") or ""))
        check("[mixed] the gen switch is NOT disabled by disagreement",
              not page.locator(GEN_BUTTON).is_disabled())

    # --- the drawer opens inline ---
    page.click(GEN_BUTTON)
    page.wait_for_selector(DRAWER)
    check(f"[{label}] gen opens an inline drawer",
          page.locator(DRAWER).count() == 1)
    check(f"[{label}] the drawer is a sibling of its row, not a popover",
          page.evaluate(
              "sel => { const d = document.querySelector(sel);"
              " return d.previousElementSibling?.classList"
              ".contains('live-param'); }", DRAWER))

    # --- 3. stop is inside the drawer, not a third switch state ---
    check(f"[{label}] stop is a control inside the drawer",
          page.locator(DRAWER + " [data-gen-stop]").count() == 1)
    check(f"[{label}] the switch gained no third state",
          page.locator(ALL_ROW + " [data-gen-mode]").count() == 2)

    # --- the builder is the ratified one: kinds, fields, preview ---
    kinds = page.eval_on_selector_all(
        DRAWER + " [data-gen-kind] option", "nodes => nodes.map(n => n.value)")
    check(f"[{label}] the drawer offers the generator kinds",
          kinds == ["fade", "loop", "lfo"], repr(kinds))
    check(f"[{label}] lfo fields and waveform preview render",
          page.locator(DRAWER + ' [data-param-lfo="shape"]').count() == 1
          and page.locator(DRAWER + " .show-param-preview").count() == 1)

    # --- the wire: a committed generator reaches the node as sec 3.2 args ---
    page.select_option(DRAWER + ' [data-param-lfo="shape"]', "tri")
    page.fill(DRAWER + ' [data-param-lfo="period"]', "2")
    page.click(DRAWER + " [data-gen-apply]")
    check(f"[{label}] applying runs the generator on the node",
          wait_ticking(fleet_log_path),
          "fleet log shows no ticking density: "
          + repr(density_ticks(fleet_log_path)[-6:]))
    check(f"[{label}] the node accepted the grammar",
          "grammar error" not in read_log(fleet_log_path))

    # --- committing sets ALL members, so the aggregate is no longer mixed ---
    became = page.wait_for_function(
        "() => Object.values(installation.automation || {})"
        ".filter(entry => entry.density).length === 2", timeout=8000)
    check(f"[{label}] the generator is recorded for every member seat",
          became is not None)

    # --- stop clears it again ---
    page.click(DRAWER + " [data-gen-stop]")
    before = len(density_ticks(fleet_log_path))
    time.sleep(1.5)
    settled = len(density_ticks(fleet_log_path))
    time.sleep(1.0)
    check(f"[{label}] stop halts the generator on the node",
          len(density_ticks(fleet_log_path)) == settled and settled >= before,
          f"ticks kept arriving after stop: {before} -> {settled} -> "
          f"{len(density_ticks(fleet_log_path))}")
    cleared = page.wait_for_function(
        "() => Object.values(installation.automation || {})"
        ".every(entry => !entry.density)", timeout=8000)
    check(f"[{label}] stop clears the recorded automation", cleared is not None)

    # --- switching back to value closes the drawer and stops nothing ---
    page.click(VALUE_BUTTON)
    check(f"[{label}] value closes the drawer",
          page.locator(DRAWER).count() == 0)
    check(f"[{label}] the underlying control is still usable",
          page.locator(ALL_DENSITY).count() == 1
          and not page.locator(ALL_DENSITY).is_disabled())


def main():
    for mixed in (False, True):
        prefix = "bopos-gen-drawer-"
        with tempfile.TemporaryDirectory(prefix=prefix) as temp:
            state_path = make_fixture(temp, mixed)
            assets = os.path.join(temp, "assets")
            patches = os.path.join(temp, "patches")
            state_dir = os.path.join(temp, "sim-state")
            http_port = free_port(socket.SOCK_STREAM)
            listen_port = free_port(socket.SOCK_DGRAM)
            send_port = free_port(socket.SOCK_DGRAM)
            base_url = f"http://127.0.0.1:{http_port}"
            fleet_log_path = os.path.join(temp, "fleet.log")
            server_log = open(os.path.join(temp, "server.log"), "w",
                              encoding="utf-8")
            fleet_log = open(fleet_log_path, "w", encoding="utf-8")
            server = fleet = None
            try:
                server = subprocess.Popen([
                    sys.executable,
                    os.path.join(REPO, "dashboard", "server.py"),
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
                    "--state-dir", state_dir, "--manifest",
                    os.path.join(patches, "alpha", "bopos.patch.json"),
                    "--patches-dir", patches, "--assets-dir", assets,
                ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width": 900,
                                                      "height": 1400})
                    page.set_default_timeout(10000)
                    errors, alerts = [], []
                    page.on("pageerror",
                            lambda error: errors.append(str(error)))
                    page.on("dialog",
                            lambda dialog: (alerts.append(dialog.message),
                                            dialog.dismiss()))
                    run(page, base_url, fleet_log_path, state_path, mixed)
                    label = "mixed" if mixed else "agreeing"
                    check(f"[{label}] no server rejection alert fired",
                          not alerts, repr(alerts))
                    check(f"[{label}] no page errors", not errors,
                          repr(errors))
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
    print("Generator drawer checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
