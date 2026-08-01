#!/usr/bin/env python3
"""Evidence for the one open question in 09: `<select>` or `TargetPicker`?

The stitch says Bob was unsure the picker is the right object for the deploy
target, and asks for evidence rather than a forced component. The deliverable is
a SINGLE LINE holding patch, target and buttons, so the question is really
about geometry: what does each object cost that line, and what does it do to it
when used?

Measures the real running app: the Patches tab's existing `<select>`s against
the Assets tab's device-domain `TargetPicker`, which is the component's only
existing device consumer and therefore the honest comparison.

Reports, does not assert.
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
    assets = os.path.join(root, "assets")
    os.makedirs(assets)
    for name in ("alpha", "beta"):
        patch = os.path.join(patches, name)
        os.makedirs(patch)
        with open(os.path.join(patch, "main.bin"), "wb") as target:
            target.write(b"deploy-row-probe")
        with open(os.path.join(patch, "bopos.patch.json"), "w",
                  encoding="utf-8") as target:
            json.dump({
                "engine": "test", "entrypoint": "main.bin",
                "params": [{"name": "density", "kind": "float", "min": 0,
                            "max": 1, "default": .2, "dashboard": True}],
                "events": [], "caps": [], "slots": [],
            }, target)
    uids = ["b8:27:eb:00:00:01", "b8:27:eb:00:00:02"]
    state = {
        "schema": 1, "name": "Deploy row rig",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha", "groups": {},
        "seats": {
            str(index + 1): {
                "id": index + 1, "name": name, "positions": [[index + 1, 1]],
                "groups": [], "bound": uid, "patch": "alpha", "params": {},
            }
            for index, (name, uid) in enumerate(
                zip(("Freda", "Sparks"), uids))
        },
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path, patches, assets, uids


def main():
    temp = tempfile.TemporaryDirectory()
    state_path, patches, assets, _uids = make_fixture(temp.name)
    http_port = free_port(socket.SOCK_STREAM)
    listen_port = free_port(socket.SOCK_DGRAM)
    send_port = free_port(socket.SOCK_DGRAM)
    log = open(os.path.join(temp.name, "d.log"), "w", encoding="utf-8")
    fleet_log = open(os.path.join(temp.name, "f.log"), "w", encoding="utf-8")
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
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
            "--devices", "2", "--target", "127.0.0.1",
            "--report-port", str(listen_port), "--cmd-port", str(send_port),
            "--hb-interval", "0.5", "--boot-secs", "0.2",
            "--patches-dir", patches, "--assets-dir", assets,
            "--manifest", os.path.join(patches, "alpha", "bopos.patch.json"),
        ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.set_default_timeout(15000)
            page.goto(base + "#patches")
            page.wait_for_selector("#ws-status.online")
            page.wait_for_function(
                "() => document.querySelectorAll('#patch-select option')"
                ".length >= 2")

            def box(selector):
                return page.evaluate(
                    """selector => {
                      const node = document.querySelector(selector);
                      if (!node) return null;
                      const rect = node.getBoundingClientRect();
                      return {w: Math.round(rect.width),
                              h: Math.round(rect.height)};
                    }""", selector)

            print("=== Patches tab, as shipped ===")
            for label, selector in (
                    ("deploy row  ", ".fleet-patch-deploy"),
                    ("  patch <select>", "#patch-select"),
                    ("  target <select>", "#patch-target"),
                    ("  actions", ".fleet-patch-actions"),
                    ("editor-launch row", ".editor-launch"),
            ):
                print(f"  {label:<18} {box(selector)}")

            # The sweep the stitch asks for: any container in this tab whose
            # form controls wrap onto more than one row while the tab is wide.
            # Reported by measurement rather than by reading the markup.
            print("\n=== stacking sweep: Patches tab at 1280 ===")
            stacked = page.evaluate("""() => {
              // A container "stacks" when its own height is much greater than
              // its tallest control, i.e. the controls sit on separate LINES.
              // Distinct `top` values are not the test: vertical centring gives
              // a short button a different top on the same line.
              const out = [];
              document.querySelectorAll('#tab-patches *').forEach(node => {
                const controls = [...node.children].filter(child =>
                  /^(SELECT|BUTTON|INPUT|TEXTAREA)$/.test(child.tagName)
                  || child.querySelector?.('select,button,input,textarea'));
                if (controls.length < 2) return;
                const rect = node.getBoundingClientRect();
                if (!rect.width || !rect.height) return;
                const tallest = Math.max(...controls.map(child =>
                  child.getBoundingClientRect().height));
                if (!tallest || rect.height < tallest * 1.6) return;
                out.push({
                  node: node.id ? '#' + node.id
                        : '.' + String(node.className || node.tagName)
                                 .split(' ')[0],
                  controls: controls.length,
                  h: Math.round(rect.height),
                  tallest: Math.round(tallest),
                  w: Math.round(rect.width),
                });
              });
              return out;
            }""")
            if not stacked:
                print("  nothing stacks")
            for entry in stacked:
                print(f"  {entry['node']:<28} {entry['controls']} controls,"
                      f" box {entry['w']}x{entry['h']},"
                      f" tallest control {entry['tallest']}")

            # Flat, not a subdirectory: `loom.sh` reads any directory inside a
            # stitch as a child stitch and refuses to tie the parent.
            shots = HERE
            for width, tag in ((1280, "desktop"), (800, "tight"), (700, "narrow")):
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_timeout(200)
                page.locator("#fleet-patch-panel").screenshot(
                    path=os.path.join(shots, f"deploy-row-{tag}.png"))
            print("\n=== the row just above the 760px breakpoint ===")
            for width in (1280, 900, 800, 780):
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_timeout(150)
                print(f"  {width:>5}px viewport -> deploy row"
                      f" {box('.fleet-patch-deploy')},"
                      f" target {box('#patch-target')}")
            page.set_viewport_size({"width": 1280, "height": 900})
            print(f"\n  shots written to {shots}")

            # The Assets tab is the component's only device consumer.
            page.goto(base + "#assets")
            page.wait_for_selector("#tab-assets:not([hidden])")
            page.wait_for_selector("#asset-target-host .target-picker")
            print("\n=== Assets tab, the device-domain TargetPicker ===")
            print(f"  picker CLOSED     {box('#asset-target-host .target-picker')}")
            summary = box("#asset-target-host .target-picker > summary")
            print(f"  its summary row   {summary}")
            page.evaluate(
                "() => document.querySelector('#asset-target-host"
                " .target-picker').open = true")
            page.wait_for_timeout(150)
            print(f"  picker OPEN       {box('#asset-target-host .target-picker')}")
            print("  chips when open  ", page.evaluate(
                "() => document.querySelectorAll('#asset-target-host"
                " .target-picker .target-chip').length"))
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
        fleet_log.close()
        temp.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
