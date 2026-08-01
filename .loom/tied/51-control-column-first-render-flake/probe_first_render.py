#!/usr/bin/env python3
"""Instrumented reproduction for 51-control-column-first-render-flake.

Hypothesis under test: the Control tab's first paint is lost when the initial
`state` message is delivered in the window between `dashboard.js` registering
`ws.on("state", ...)` and `control-host.js` registering its own.

`ws.js` buffers a message only while a type has NO handlers at all
(`emit`: `if (!handlers.length) { pending.push(data); return; }`), so once
`dashboard.js` has registered, nothing is buffered for the later handler. It
never fires, `venueKnown` stays false, and `renderAll` returns early forever —
including on every `device_update` heartbeat.

The two scripts are separate classic `<script>` tags. Between them the browser
must FETCH five more files, and the event loop is free during those fetches, so
the window is real and is exactly network-latency wide. This probe widens it
deliberately with `page.route` instead of chasing it under load.

Run standalone. Reports, it does not assert.
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


def free_port():
    for _attempt in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        if port in RESERVED:
            continue
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            probe.close()
            continue
        probe.close()
        RESERVED.add(port)
        return port
    raise RuntimeError("no free port")


def free_udp():
    for _attempt in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        if port in RESERVED:
            continue
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            probe.close()
            continue
        probe.close()
        RESERVED.add(port)
        return port
    raise RuntimeError("no free port")


def wait_http(url, process):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before serving HTTP")
        try:
            urllib.request.urlopen(url, timeout=1).read()
            return
        except OSError:
            time.sleep(.2)
    raise RuntimeError("dashboard did not serve HTTP")


def make_fixture(root):
    patches = os.path.join(root, "patches")
    patch = os.path.join(patches, "alpha")
    assets = os.path.join(root, "assets")
    os.makedirs(patch)
    os.makedirs(assets)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"first-render-probe")
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin",
            "params": [{"name": "density", "kind": "float", "min": 0,
                        "max": 1, "default": .2, "dashboard": True}],
            "events": [], "caps": [], "slots": [],
        }, target)
    state = {
        "schema": 1, "name": "First render probe",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha", "groups": {},
        "seats": {"1": {"id": 1, "name": "Seat 1", "pos": [1, 1]}},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path, patches, assets


def run(delay_host_js):
    """Load the Control tab; optionally stall `control-host.js`'s fetch."""
    temp = tempfile.TemporaryDirectory()
    state_path, patches, assets = make_fixture(temp.name)
    http_port, listen, send = free_port(), free_udp(), free_udp()
    log = open(os.path.join(temp.name, "dash.log"), "w", encoding="utf-8")
    dashboard = subprocess.Popen([
        sys.executable, os.path.join(REPO, "dashboard", "server.py"),
        "--port", str(http_port), "--listen-port", str(listen),
        "--send-port", str(send), "--osc-target", "127.0.0.1",
        "--state-file", state_path, "--patches-dir", patches,
        "--assets-dir", assets,
    ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{http_port}"
    try:
        wait_http(base + "/", dashboard)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1200})
            page.set_default_timeout(8000)

            if delay_host_js:
                # Stall ONLY the last script, so the initial `state` lands
                # while `dashboard.js` is the sole registered handler. This is
                # what a slow fetch does on its own; the route just makes the
                # timing deterministic.
                def stall(route):
                    time.sleep(delay_host_js)
                    route.continue_()
                page.route("**/js/control-host.js", stall)

            page.goto(base + "#control")
            page.wait_for_selector("#ws-status.online")

            painted = True
            try:
                page.locator(
                    '#control-column-host .live-card[data-live-scope="all"]'
                ).wait_for(timeout=8000)
            except Exception:
                painted = False

            # Ask the page what it actually saw, rather than inferring.
            observed = page.evaluate("""() => ({
              stateHandlers: (ws && ws.handlers && ws.handlers.state
                              || []).length,
              pendingState: !!(ws && ws.pending && ws.pending.state),
              columnHtml: (document.querySelector('#control-column-host')
                           || {}).innerHTML?.length || 0,
              cards: document.querySelectorAll(
                '#control-column-host .live-card').length,
            })""")

            # Does a later `state` broadcast rescue it? It must be a verb that
            # actually broadcasts `state` — most do not. `create_show` routes
            # through `set_current_show`, which does (thread 50/4).
            page.evaluate("() => ws.send('create_show', {name: 'rescue'})")
            rescued = True
            try:
                page.locator(
                    '#control-column-host .live-card[data-live-scope="all"]'
                ).wait_for(timeout=8000)
            except Exception:
                rescued = False

            browser.close()
            return {"painted": painted, "rescued_by_later_state": rescued,
                    **observed}
    finally:
        dashboard.terminate()
        try:
            dashboard.wait(timeout=5)
        except subprocess.TimeoutExpired:
            dashboard.kill()
        log.close()
        temp.cleanup()


def main():
    for label, delay in (("no delay (control)", 0), ("control-host.js stalled 1.5s", 1.5)):
        result = run(delay)
        print(f"\n=== {label} ===")
        for key, value in result.items():
            print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
