#!/usr/bin/env python3
"""Does a heartbeat re-render discard a preset name the operator is typing?

`control-surface.js:356` emits the drawer's name field as
`<input type="text" data-preset-name value="${esc(name)}">`, where `name` comes
from the `openSaveDrawers` entry. Nothing writes what is typed back into that
entry, and the drawer's HTML is regenerated wholesale on every render. Text
inputs are not covered by the `interacting` guard either — that covers ranges,
toggles, enums (pointer) and event boxes (focus), not this field.

If that reading is right, an operator who types a preset name and pauses loses
it on the next heartbeat, and `commit` then sees an empty name and saves
nothing. Reports, does not assert.
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
    raise RuntimeError("no free port")


def wait_http(url, process):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited early")
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
        target.write(b"drawer-typing-probe")
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin",
            "params": [{"name": "density", "kind": "float", "min": 0,
                        "max": 1, "default": .2, "dashboard": True}],
            "events": [], "caps": [], "slots": [],
        }, target)
    state = {
        "schema": 1, "name": "Drawer typing probe",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha", "groups": {},
        "seats": {"1": {"id": 1, "name": "Seat 1", "pos": [1, 1]}},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path, patches, assets


def main():
    temp = tempfile.TemporaryDirectory()
    state_path, patches, assets = make_fixture(temp.name)
    http_port = free_port(socket.SOCK_STREAM)
    listen_port = free_port(socket.SOCK_DGRAM)
    send_port = free_port(socket.SOCK_DGRAM)
    log = open(os.path.join(temp.name, "d.log"), "w", encoding="utf-8")
    dashboard = subprocess.Popen([
        sys.executable, os.path.join(REPO, "dashboard", "server.py"),
        "--port", str(http_port), "--listen-port", str(listen_port),
        "--send-port", str(send_port), "--osc-target", "127.0.0.1",
        "--state-file", state_path, "--patches-dir", patches,
        "--assets-dir", assets,
    ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
    fleet = None
    base = f"http://127.0.0.1:{http_port}"
    try:
        wait_http(base + "/", dashboard)
        fleet_log = open(os.path.join(temp.name, "f.log"), "w",
                         encoding="utf-8")
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
            "--devices", "1", "--target", "127.0.0.1",
            "--report-port", str(listen_port), "--cmd-port", str(send_port),
            "--hb-interval", "0.5", "--boot-secs", "0.2",
            "--patches-dir", patches, "--assets-dir", assets,
            "--manifest", os.path.join(patches, "alpha",
                                       "bopos.patch.json"),
        ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1200})
            page.set_default_timeout(15000)
            page.goto(base + "#control")
            page.wait_for_selector("#ws-status.online")
            host = "#control-column-host"
            page.locator(f'{host} .live-card[data-live-scope="all"]').wait_for()

            disclosure = page.locator(f"{host} .live-preset-authoring").first
            page.wait_for_function(
                "() => !!document.querySelector"
                "('#control-column-host .live-preset-authoring')?.ontoggle")
            disclosure.locator("summary").click()
            page.wait_for_function(
                "() => !!document.querySelector('#control-column-host"
                ' [data-preset-action="new"]\')?.onclick')
            page.locator(f'{host} [data-preset-action="new"]').first.click()

            field = page.locator(f"{host} [data-preset-drawer] "
                                 "[data-preset-name]")
            field.wait_for()
            if os.environ.get("PROBE_WAIT_FOR_BINDING"):
                # Gotcha 16 candidate: the drawer's focus guard is assigned by
                # `bindPresets` AFTER the drawer's markup exists. A `fill` that
                # lands first fires `focusin` at an unbound node, so nothing
                # holds the render guard.
                page.wait_for_function(
                    "() => !!document.querySelector('#control-column-host"
                    " [data-preset-drawer]')?.onfocusin")
            field.fill("Dawn")
            typed = field.input_value()
            # Mark the node so we can tell replacement from a value reset, and
            # record where focus actually is — `drawer.onfocusin` is supposed
            # to be holding the render guard for exactly this.
            page.evaluate("""() => {
              const input = document.querySelector('#control-column-host'
                + ' [data-preset-drawer] [data-preset-name]');
              input.dataset.probeMark = 'original';
              window.__focus = () => {
                const active = document.activeElement;
                return active ? active.tagName + '/'
                  + (active.dataset?.presetName !== undefined
                     ? 'preset-name' : (active.className || 'n/a')) : 'none';
              };
            }""")
            focus_after_fill = page.evaluate("() => window.__focus()")
            guard_after_fill = page.evaluate("() => window.__probeInteracting?.()")

            # Let several heartbeats land, as a human pause would.
            page.wait_for_timeout(3000)
            live = page.locator(f"{host} [data-preset-drawer] "
                                "[data-preset-name]")
            after = live.input_value()
            replaced = page.evaluate(
                """() => document.querySelector('#control-column-host'
                   + ' [data-preset-drawer] [data-preset-name]')
                   ?.dataset.probeMark !== 'original'""")
            focus_after_wait = page.evaluate("() => window.__focus()")
            guard_after_wait = page.evaluate("() => window.__probeInteracting?.()")

            trace = page.evaluate("() => window.__trace || []")
            print("  --- trace (ms, event, extra, focus) ---")
            for entry in trace:
                print(f"    {entry['t']:>6}  {entry['what']:<16}"
                      f" {str(entry.get('extra')):<10} focus={entry['focus']}")
            print(f"  typed into the field: {typed!r}")
            print(f"  focus right after fill: {focus_after_fill}")
            print(f"  interacting guard after fill: {guard_after_fill}")
            print(f"  still there after ~3s of heartbeats: {after!r}")
            print(f"  focus after the wait: {focus_after_wait}")
            print(f"  interacting guard after wait: {guard_after_wait}")
            print(f"  input node was replaced: {replaced}")
            print("  VERDICT:", "SURVIVES" if after == typed
                  else "DISCARDED by re-render")
            browser.close()
    finally:
        for process in (fleet, dashboard):
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        log.close()
        temp.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
