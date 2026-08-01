#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for device-scoped patch targeting
(thread 37, bite 2 — 2-device-patch-targeting).

Proves the ratified first bite end to end against the live wire:
  * the Patches-tab target picker offers the whole fleet or one device, and the
    Deploy button becomes "Pin to device" for a single target;
  * pinning one device converges only that device to its pinned patch, on its own
    generation track, while the rest hold the fleet patch;
  * the pin is a separate axis from the convergence badge (roster pin marker);
  * a subsequent whole-fleet deploy leaves the pin intact (the crucial
    correctness property — a fleet deploy is a bulk-set over the unpinned
    remainder), converging only the unpinned device;
  * "follow fleet" clears the pin and re-converges the device to the fleet;
  * the pin persists across a page reload (durable UID registry).

Homed in tests/ by code surface per the thread-27 durable-tests policy, not a
tied guard. Non-hardware: simfleet is protocol-reactive and models per-device
patches, so a singleton-targeted convergence reaches only that device unmodified.
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
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""),
          flush=True)
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


def write_patch(root, name, payload):
    path = os.path.join(root, name)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "main.bin"), "wb") as target:
        target.write(payload)
    with open(os.path.join(path, "bopos.patch.json"), "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "params": [],
                   "caps": [], "slots": []}, target)


def deploy_fleet(page, name):
    page.select_option("#patch-target", "all")
    page.select_option("#patch-select", name)
    page.click("#patch-switch")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-device-patch-") as temp:
        state_path = os.path.join(temp, "installation.json")
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        write_patch(patches, "demo-pd", b"demo")
        write_patch(patches, "alpha", b"alpha-bytes")
        write_patch(patches, "beta", b"beta-bytes")
        state = {"schema": 1, "name": "Device patch targeting rig", "seats": {
            "1": {"id": 1, "name": "Finn", "positions": [[1, 1]],
                  "params": {}, "bound": UID_A},
            "2": {"id": 2, "name": "Ciro", "positions": [[2, 1]],
                  "params": {}, "bound": UID_B},
        }}
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump(state, target)

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
                "--public-url", base_url,
            ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "2", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.2", "--fetch-seconds", "0.3",
                "--patches-dir", patches,
                "--manifest", os.path.join(patches, "demo-pd", "bopos.patch.json"),
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "() => Object.keys(installation.devices||{}).length === 2")
                page.wait_for_function(
                    "uid => Array.isArray(installation.devices?.[uid]?.patches)",
                    arg=UID_A)
                page.wait_for_function(
                    "uid => Array.isArray(installation.devices?.[uid]?.patches)",
                    arg=UID_B)

                page.click("#tab-button-patches")
                page.wait_for_selector("#tab-patches:not([hidden]) #fleet-patch-panel")
                page.wait_for_function(
                    "() => [...document.querySelectorAll('#patch-select option')]"
                    ".some(option => option.value === 'beta')")

                # --- one line: patch, target, buttons (09) ---
                # Bob, 2026-07-30: "it would make a lot more sense for those to
                # be side by side so that the patch, the target, and the buttons
                # are all in a single line." They used to stack, at 74px.
                #
                # Measured as "the row is no taller than its tallest control",
                # NOT as "the three share a `top`": the buttons are shorter than
                # the selects and are centred against them, so equal tops is the
                # wrong test and would fail on a correct layout.
                row = page.evaluate("""() => {
                  const box = node => node.getBoundingClientRect();
                  const deploy = document.querySelector('.fleet-patch-deploy');
                  const parts = ['#patch-select', '#patch-target',
                                 '.fleet-patch-actions']
                    .map(selector => document.querySelector(selector));
                  if (!deploy || parts.some(part => !part)) return null;
                  const rect = box(deploy);
                  const tallest = Math.max(...parts.map(part => box(part).height));
                  const centres = parts.map(part =>
                    Math.round(box(part).top + box(part).height / 2));
                  return {height: Math.round(rect.height),
                          tallest: Math.round(tallest),
                          centreSpread: Math.max(...centres) - Math.min(...centres)};
                }""")
                check("the deploy row is a single line",
                      row and row["height"] <= row["tallest"] + 2, repr(row))
                check("patch, target and actions share one vertical centre",
                      row and row["centreSpread"] <= 1, repr(row))

                # --- target picker shape ---
                target_options = page.evaluate(
                    "() => [...document.querySelectorAll('#patch-target option')]"
                    ".map(o => o.value)")
                check("target picker offers whole fleet plus each online device",
                      target_options[0] == "all"
                      and UID_A in target_options and UID_B in target_options
                      and len(target_options) == 3, repr(target_options))
                page.select_option("#patch-target", UID_B)
                check("selecting one device relabels Deploy to Pin to device",
                      "pin to device" in page.locator("#patch-switch").inner_text().lower())
                page.select_option("#patch-target", "all")
                check("selecting the whole fleet restores the fleet deploy label",
                      "fleet patch" in page.locator("#patch-switch").inner_text().lower())

                # --- deploy alpha to the whole fleet: both converge ---
                deploy_fleet(page, "alpha")
                page.wait_for_function(
                    "() => installation.fleet_patch?.name === 'alpha'"
                    " && document.querySelector('#fleet-patch-summary')?.innerText.includes('2 current')",
                    timeout=15000)
                check("whole-fleet deploy converges both assigned devices",
                      page.evaluate("uid => installation.devices[uid].patch_badge", arg=UID_A) == "current"
                      and page.evaluate("uid => installation.devices[uid].patch_badge", arg=UID_B) == "current")

                # --- pin device B to beta: only B converges to beta ---
                page.select_option("#patch-target", UID_B)
                page.select_option("#patch-select", "beta")
                page.click("#patch-switch")
                page.wait_for_function(
                    "uid => installation.devices[uid]?.patch_pinned === true"
                    " && installation.devices[uid]?.pinned_patch === 'beta'",
                    arg=UID_B, timeout=15000)
                page.wait_for_function(
                    "uid => installation.devices[uid]?.patch_badge === 'current'",
                    arg=UID_B, timeout=15000)
                check("pinning one device leaves the other unpinned on the fleet patch",
                      page.evaluate("uid => !!installation.devices[uid].patch_pinned", arg=UID_A) is False
                      and page.evaluate("uid => installation.devices[uid].patch_badge", arg=UID_A) == "current")
                check("pinned device reports its pin as a separate axis from the badge",
                      page.evaluate("uid => installation.devices[uid].pinned_patch", arg=UID_B) == "beta"
                      and page.evaluate("uid => installation.devices[uid].patch_badge", arg=UID_B) == "current")
                check("fleet-patch summary counts the pin",
                      "1 pinned" in page.locator("#fleet-patch-summary").inner_text())

                # --- roster pin marker (Devices tab) ---
                page.click("#tab-button-devices")
                page.wait_for_selector("#tab-devices:not([hidden])")
                page.wait_for_function(
                    "() => document.querySelectorAll('#device-roster .patch-pin').length === 1")
                check("exactly one roster row shows the pin marker",
                      page.locator("#device-roster .patch-pin").count() == 1)
                check("the pin marker names the pinned patch",
                      "beta" in (page.locator("#device-roster .patch-pin").first
                                 .get_attribute("title") or ""))

                # --- the crucial property: a whole-fleet deploy leaves the pin intact ---
                page.click("#tab-button-patches")
                page.wait_for_selector("#tab-patches:not([hidden]) #fleet-patch-panel")
                deploy_fleet(page, "demo-pd")
                page.wait_for_function(
                    "() => installation.fleet_patch?.name === 'demo-pd'", timeout=15000)
                page.wait_for_function(
                    "uid => installation.devices[uid]?.patch_badge === 'current'"
                    " && installation.devices[uid]?.patch_pinned !== true",
                    arg=UID_A, timeout=15000)
                check("a fleet deploy converges only the unpinned device",
                      page.evaluate("uid => installation.devices[uid].patch_badge", arg=UID_A) == "current"
                      and page.evaluate("uid => !!installation.devices[uid].patch_pinned", arg=UID_A) is False)
                check("a fleet deploy leaves the pinned device pinned to its own patch",
                      page.evaluate("uid => !!installation.devices[uid].patch_pinned", arg=UID_B) is True
                      and page.evaluate("uid => installation.devices[uid].pinned_patch", arg=UID_B) == "beta"
                      and page.evaluate("uid => installation.devices[uid].patch_badge", arg=UID_B) == "current")

                # --- the pin persists across a page reload (durable registry) ---
                page.reload()
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "uid => installation.devices?.[uid]?.patch_pinned === true",
                    arg=UID_B, timeout=15000)
                check("the pin survives a page reload (durable UID registry)",
                      page.evaluate("uid => installation.devices[uid].pinned_patch", arg=UID_B) == "beta")

                # --- follow fleet clears the pin and re-converges to the fleet ---
                page.click("#tab-button-devices")
                page.wait_for_selector("#tab-devices:not([hidden])")
                page.click(f'#device-roster .device-row[data-uid="{UID_B}"]')
                page.wait_for_selector("#patch-follow-fleet")
                page.click("#patch-follow-fleet")
                page.wait_for_function(
                    "uid => installation.devices[uid]?.patch_pinned !== true",
                    arg=UID_B, timeout=15000)
                page.wait_for_function(
                    "uid => installation.devices[uid]?.patch_badge === 'current'",
                    arg=UID_B, timeout=15000)
                check("follow fleet clears the pin and re-converges to the fleet patch",
                      page.evaluate("uid => !!installation.devices[uid].patch_pinned", arg=UID_B) is False
                      and page.evaluate("uid => installation.devices[uid].patch_badge", arg=UID_B) == "current")

                check("no page errors during the run", not page_errors, repr(page_errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()
        if FAILURES:
            with open(fleet_log_path, encoding="utf-8") as source:
                print("\nfleet log tail:\n", source.read()[-3000:])
            with open(server_log_path, encoding="utf-8") as source:
                print("\nserver log tail:\n", source.read()[-3000:])
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("Device-scoped patch targeting browser checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
