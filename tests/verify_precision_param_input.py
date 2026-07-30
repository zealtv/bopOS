#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for precision typed parameter entry
(40-precision-param-input).

Phase A (engine alive): the facilitator live-control surface. Typing an exact
value into a slider's readout must reach the wire with full precision, clamp to
the manifest min/max, round integers, revert on Escape, and round-trip into UI
state. Wire capture is the simfleet fleet log (`p/<name>=<value>` via %g).

Phase B (--sim-no-engine): the patch-editor control panel. Best-effort edit-mode
entry (like the tied editor-toggle verify); when reached, typed editor param and
master values round-trip through the same shared PrecisionField helper.
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


def make_fixture(root):
    patches = os.path.join(root, "patches")
    assets = os.path.join(root, "assets")
    state_dir = os.path.join(root, "sim-state")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(assets)
    os.makedirs(state_dir)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"precision-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"path": ["synth", "voice"], "name": "density", "kind": "float",
             "min": 0, "max": 1, "default": .2, "dashboard": True},
            {"name": "steps", "kind": "int", "min": 0, "max": 10,
             "default": 2, "dashboard": True},
        ], "caps": [], "slots": [],
    }
    manifest_path = os.path.join(patch, "bopos.patch.json")
    with open(manifest_path, "w", encoding="utf-8") as target:
        json.dump(manifest, target, indent=2)
    uids = ["02:53:49:4d:00:01", "02:53:49:4d:00:02"]

    def seat(seat_id, name, uid):
        # Both seats share identical values so the All aggregate is non-mixed
        # and therefore exposes the precise (click-to-type) readout.
        return {"id": seat_id, "name": name, "positions": [[seat_id, 1]],
                "groups": [], "bound": uid, "patch": "alpha",
                "params": {"synth/voice/density": .2, "steps": 2}}

    state = {
        "schema": 1, "name": "Precision verifier",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "seats": {"1": seat(1, "Freda", uids[0]),
                  "2": seat(2, "Sparks", uids[1])},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return patches, assets, state_dir, manifest_path, state_path, uids


def start_dashboard(http_port, listen_port, send_port, state_path, assets,
                    patches, base_url, log):
    process = subprocess.Popen([
        sys.executable, os.path.join(REPO, "dashboard", "server.py"),
        "--host", "127.0.0.1", "--port", str(http_port),
        "--listen-port", str(listen_port), "--send-port", str(send_port),
        "--osc-target", "127.0.0.1", "--state-file", state_path,
        "--assets-dir", assets, "--patches-dir", patches,
        "--public-url", base_url,
    ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
    wait_http(base_url, process)
    return process


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


def precise_type(page, label_selector, value, commit="Enter"):
    output = page.locator(f'{label_selector} output[data-precise="true"]')
    output.click()
    field = page.locator(f'{label_selector} input.precise-input')
    field.wait_for(state="visible", timeout=4000)
    field.fill(str(value))
    field.press(commit)


def phase_a(temp, uids):
    """Facilitator live surface: wire-precise typed entry."""
    state_path = os.path.join(temp, "installation.json")
    assets = os.path.join(temp, "assets")
    patches = os.path.join(temp, "patches")
    state_dir = os.path.join(temp, "sim-state")
    http_port = free_port(socket.SOCK_STREAM)
    listen_port = free_port(socket.SOCK_DGRAM)
    send_port = free_port(socket.SOCK_DGRAM)
    base_url = f"http://127.0.0.1:{http_port}"
    server_log_path = os.path.join(temp, "server-a.log")
    fleet_log_path = os.path.join(temp, "fleet-a.log")
    server_log = open(server_log_path, "w", encoding="utf-8")
    fleet_log = open(fleet_log_path, "w", encoding="utf-8")
    server = fleet = None
    try:
        server = start_dashboard(http_port, listen_port, send_port, state_path,
                                 assets, patches, base_url, server_log)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
            "--devices", "2", "--target", "127.0.0.1",
            "--report-port", str(listen_port), "--cmd-port", str(send_port),
            "--hb-interval", "0.2", "--boot-secs", "0.2",
            "--state-dir", state_dir, "--manifest",
            os.path.join(patches, "alpha", "bopos.patch.json"),
            "--patches-dir", patches, "--assets-dir", assets,
        ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 900, "height": 1200})
            page.set_default_timeout(10000)
            page_errors = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(base_url + "/facilitator")
            page.wait_for_selector('.live-card[data-live-scope="all"]')
            page.wait_for_function(
                "() => Object.keys(installation.devices||{}).length === 2")
            page.wait_for_function(
                "() => (installation.devices['02:53:49:4d:00:01']||{}).engine_alive !== 0")

            all_density = ('.live-card[data-live-scope="all"] '
                           '.live-param[data-param-path="synth/voice/density"]')
            all_steps = ('.live-card[data-live-scope="all"] '
                         '.live-param[data-param-path="steps"]')

            check("plain numeric readout is a click-to-type precision field",
                  page.locator(f'{all_density} output[data-precise="true"]').count() == 1
                  and page.locator(f'{all_steps} output[data-precise="true"]').count() == 1)

            # --- exact float survives to the wire ---
            precise_type(page, all_density, "0.137913")
            check("typed float reaches the wire with full precision",
                  wait_log(fleet_log_path, r"p/synth/voice/density=0\.137913"),
                  "fleet log missing precise density write")
            page.wait_for_function(
                "() => Math.abs((installation.seats['1'].params['synth/voice/density'])"
                " - 0.137913) < 1e-9")
            check("typed float round-trips into UI state for every scoped seat",
                  page.evaluate(
                      "() => installation.seats['1'].params['synth/voice/density'] === 0.137913"
                      " && installation.seats['2'].params['synth/voice/density'] === 0.137913"))

            # --- above-max input clamps to the manifest bound ---
            precise_type(page, all_density, "2.5")
            check("out-of-range typed value clamps to max on the wire",
                  wait_log(fleet_log_path, r"p/synth/voice/density=1(\b|\.)")
                  and page.evaluate(
                      "() => installation.seats['1'].params['synth/voice/density'] === 1"))

            # --- integer control rounds a typed fraction ---
            precise_type(page, all_steps, "6.7")
            check("integer control rounds a typed fraction on the wire",
                  wait_log(fleet_log_path, r"p/steps=7(\b|\.)")
                  and page.evaluate("() => installation.seats['1'].params.steps === 7"))

            # --- Escape reverts without sending ---
            before = page.evaluate(
                "() => installation.seats['1'].params['synth/voice/density']")
            precise_type(page, all_density, "0.5", commit="Escape")
            page.wait_for_timeout(300)
            check("Escape reverts the field and sends nothing",
                  page.evaluate(
                      "() => installation.seats['1'].params['synth/voice/density']") == before
                  and not wait_log(fleet_log_path, r"p/synth/voice/density=0\.5\b", timeout=1))

            # --- the shared rounding contract (house =<6 sig figs) ---
            check("PrecisionField.round honours 6 significant figures and integers",
                  page.evaluate(
                      "() => window.PrecisionField.round(0.12345678, false) === 0.123457"
                      " && window.PrecisionField.round(3.7, true) === 4"))

            page.screenshot(path=os.path.join(temp, "01-facilitator-precision.png"))
            check("facilitator emitted no page errors", not page_errors, repr(page_errors))
            browser.close()
    finally:
        stop(fleet)
        stop(server)
        server_log.close()
        fleet_log.close()
    if FAILURES:
        with open(fleet_log_path, encoding="utf-8") as source:
            print("\nphase A fleet log tail:\n", source.read()[-4000:])


def phase_b(temp, uids):
    """Patch-editor control panel: best-effort edit-mode precision round-trip."""
    state_path = os.path.join(temp, "installation.json")
    assets = os.path.join(temp, "assets")
    patches = os.path.join(temp, "patches")
    state_dir = os.path.join(temp, "sim-state")
    http_port = free_port(socket.SOCK_STREAM)
    listen_port = free_port(socket.SOCK_DGRAM)
    send_port = free_port(socket.SOCK_DGRAM)
    base_url = f"http://127.0.0.1:{http_port}"
    server_log_path = os.path.join(temp, "server-b.log")
    fleet_log_path = os.path.join(temp, "fleet-b.log")
    server_log = open(server_log_path, "w", encoding="utf-8")
    fleet_log = open(fleet_log_path, "w", encoding="utf-8")
    engine_port = free_port(socket.SOCK_STREAM)
    server = fleet = None
    try:
        # Edit mode reaches real edit/simulate supervisor.mode without spawning
        # Pure Data: the sim-no-engine flags belong to the dashboard supervisor.
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard", "server.py"),
            "--host", "127.0.0.1", "--port", str(http_port),
            "--listen-port", str(listen_port), "--send-port", str(send_port),
            "--osc-target", "127.0.0.1", "--state-file", state_path,
            "--assets-dir", assets, "--patches-dir", patches,
            "--public-url", base_url,
            "--sim-audio-backend", "none", "--sim-no-engine",
            "--sim-engine-port-base", str(engine_port),
        ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
        wait_http(base_url, server)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
            "--devices", "2", "--target", "127.0.0.1",
            "--report-port", str(listen_port), "--cmd-port", str(send_port),
            "--hb-interval", "0.2", "--boot-secs", "0.2",
            "--state-dir", state_dir, "--manifest",
            os.path.join(patches, "alpha", "bopos.patch.json"),
            "--patches-dir", patches, "--assets-dir", assets,
        ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1200, "height": 1000})
            page.set_default_timeout(10000)
            page_errors = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(base_url)
            page.wait_for_function(
                "() => Object.keys(installation.devices||{}).length === 2")

            check("PrecisionField helper is loaded on the dashboard page",
                  page.evaluate("() => typeof window.PrecisionField?.attach === 'function'"))

            # The patch editor now renders the shared ControlSurface
            # (component-unification/06), so probe that component's markup
            # contract directly. The focused editor journey covers the real
            # edit-mode wire; this test owns PrecisionField semantics.
            markup = page.evaluate(
                """() => {
                  const control=(declaration,value) => {
                    declaration={
                      ...declaration,
                      identity:[...(declaration.path||[]),declaration.name]
                        .join('/'),
                    };
                    const state={
                      automation:{},
                      live_controls:{declarations:[declaration]},
                    };
                    const surface=window.ControlSurface.create({
                      getState:()=>state, send:()=>{},
                    });
                    return surface.control(
                      'editor',null,
                      [{id:0,params:{[declaration.identity]:value}}],
                      declaration,false);
                  };
                  return {
                    float:control(
                      {name:'d',kind:'float',min:0,max:1,
                       path:['synth','voice']},0.2),
                    intRange:control(
                      {name:'steps',kind:'int',min:0,max:10,path:[]},2),
                    toggle:control(
                      {name:'gate',kind:'toggle',min:0,max:1,path:[]},0),
                    text:control(
                      {name:'word',kind:'text',path:[]},'hi'),
                  };
                }""")
            check("editor numeric readouts are precise, but toggles/strings are not",
                  'data-precise="true"' in markup["float"]
                  and 'type="range"' in markup["float"]
                  and 'data-precise="true"' in markup["intRange"]
                  and 'data-precise' not in markup["toggle"]
                  and 'aria-pressed="false"' in markup["toggle"]
                  and 'data-precise' not in markup["text"],
                  repr(markup))

            # DOM-contract probe: attach the shared helper to a synthetic readout
            # with a commit spy and drive it like a user would.
            page.evaluate(
                "() => { window.__commits = [];"
                " const out = document.createElement('output');"
                " out.id = 'pf-probe'; out.textContent = '0.2';"
                " document.body.appendChild(out);"
                " window.PrecisionField.attach(out,"
                " {min:0, max:1, integer:false, value:0.2, label:'probe', disabled:false},"
                " v => window.__commits.push(v)); }")
            page.locator('#pf-probe').click()
            probe = page.locator('input.precise-input')
            probe.wait_for(state="visible", timeout=4000)
            probe.fill("2.5")
            probe.press("Enter")
            page.wait_for_function("() => window.__commits.length === 1")
            check("shared helper clamps an over-max typed value to the bound on commit",
                  page.evaluate("() => window.__commits[0] === 1"),
                  page.evaluate("() => JSON.stringify(window.__commits)"))

            page.locator('#pf-probe').click()
            probe = page.locator('input.precise-input')
            probe.wait_for(state="visible", timeout=4000)
            probe.fill("0.5")
            probe.press("Escape")
            page.wait_for_timeout(200)
            check("shared helper commits nothing on Escape",
                  page.evaluate("() => window.__commits.length === 1"))

            check("dashboard emitted no page errors", not page_errors, repr(page_errors))
            browser.close()
    finally:
        stop(fleet)
        stop(server)
        server_log.close()
        fleet_log.close()
    if FAILURES:
        with open(server_log_path, encoding="utf-8") as source:
            print("\nphase B server log tail:\n", source.read()[-3000:])


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-precision-") as temp:
        _p, _a, _s, _m, _sp, uids = make_fixture(temp)
        phase_a(temp, uids)
        phase_b(temp, uids)
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("Precision param input browser checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
