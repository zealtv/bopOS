#!/usr/bin/env python3
"""Real-dashboard integration pass for durable physical-device aliases."""

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
PASSED = 0


def check(label, condition, detail=""):
    global PASSED
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    PASSED += 1
    print(f"PASS {label}")


def free_port(kind):
    for _ in range(256):
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
    raise RuntimeError("could not reserve local port")


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


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-alias-integration-") as temp:
        state = os.path.join(temp, "installation.json")
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        with open(state, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "Alias integration rig", "seats": {}}, target)

        http = free_port(socket.SOCK_STREAM)
        listen = free_port(socket.SOCK_DGRAM)
        send = free_port(socket.SOCK_DGRAM)
        base = f"http://127.0.0.1:{http}"
        log_path = os.path.join(temp, "run.log")
        log = open(log_path, "w", encoding="utf-8")
        server = fleet = None

        def start_server():
            process = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http),
                "--listen-port", str(listen), "--send-port", str(send),
                "--osc-target", "127.0.0.1", "--state-file", state,
                "--assets-dir", assets, "--patches-dir", patches,
                "--public-url", base,
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base, process)
            return process

        try:
            server = start_server()
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "2", "--unassigned", "2",
                "--target", "127.0.0.1", "--report-port", str(listen),
                "--cmd-port", str(send), "--hb-interval", "0.2",
                "--patches-dir", patches,
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.set_default_timeout(25000)
                errors, dialogs = [], []
                prompt_values = []
                page.on("pageerror", lambda error: errors.append(str(error)))

                def accept_dialog(dialog):
                    dialogs.append((dialog.type, dialog.message))
                    if dialog.type == "prompt":
                        dialog.accept(prompt_values.pop(0) if prompt_values else "Alias-venue")
                    else:
                        dialog.accept()

                page.on("dialog", accept_dialog)
                page.goto(base + "/#devices")
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "() => Object.keys(installation.devices||{}).length === 2")
                page.wait_for_function(
                    "() => Object.keys(installation.device_registry||{}).length === 2")
                page.click("#tab-button-devices")
                rows = page.locator("#device-roster .device-row")
                uids = rows.evaluate_all("nodes => nodes.map(node => node.dataset.uid).sort()")
                uid1, uid2 = uids
                aliases = page.evaluate(
                    "uids => uids.map(uid => installation.device_registry[uid].alias)", uids)
                alias1, alias2 = aliases
                check("discovery allocates two distinct generated aliases",
                      alias1 != alias2 and all(len(alias.split()) == 2 for alias in aliases))

                # Report hydration provides a real hostname for the selected-detail boundary.
                page.locator(f'#device-roster [data-uid="{uid1}"]').click()
                page.click("#refresh-report")
                page.wait_for_function(
                    "uid => installation.devices?.[uid]?.hostname === 'sim1'", arg=uid1)
                selected_text = page.locator("#detail").inner_text()
                roster_text = page.locator("#device-roster").inner_text()
                check("selected Device detail alone exposes hostname and full UID",
                      "sim1" in selected_text and uid1 in selected_text
                      and "sim1" not in roster_text and uid1 not in roster_text)
                check("Devices roster uses aliases without UID or hostname",
                      alias1 in roster_text and alias2 in roster_text
                      and not any(value in roster_text for value in (uid1, uid2, "sim1", "sim2")))

                page.fill("#device-alias", "Freda Sparks")
                page.click("#device-alias-save")
                page.wait_for_function(
                    "uid => installation.device_registry[uid].alias === 'Freda Sparks'", arg=uid1)
                check("Rename converges roster and selected detail",
                      page.locator(f'#device-roster [data-uid="{uid1}"] strong').inner_text()
                      == "Freda Sparks"
                      and page.locator("#detail h2").first.inner_text().startswith("Freda Sparks"))

                page.locator(f'#device-roster [data-uid="{uid2}"]').click()
                page.fill("#device-alias", "freda sparks")
                page.click("#device-alias-save")
                page.wait_for_timeout(250)
                check("case-insensitive duplicate rename is rejected in the real UI",
                      page.evaluate("uid => installation.device_registry[uid].alias", uid2) == alias2
                      and any("already used" in message.lower()
                              for kind, message in dialogs if kind == "alert"))

                # Bind uid1 so all everyday identity consumers can be inspected.
                page.click("#tab-button-seats")
                page.click("#seat-add")
                page.wait_for_selector("#seat-device")
                seat_options = page.locator("#seat-device").inner_text()
                check("Seats picker uses aliases without technical identity",
                      "Freda Sparks" in seat_options and alias2 in seat_options
                      and not any(value in seat_options for value in (uid1, uid2, "sim1", "sim2")))
                page.select_option("#seat-device", uid1)
                page.click("#seat-bind")
                page.wait_for_function("uid => installation.seats['0'].bound === uid", arg=uid1)
                binding_text = page.locator(".seat-binding-note").inner_text()
                check("Seat binding note uses the alias alone as device identity",
                      "Freda Sparks" in binding_text and uid1 not in binding_text and "sim1" not in binding_text)

                page.click("#tab-button-assets")
                asset_options = page.locator("#asset-target").inner_text()
                check("Assets selector uses aliases without technical identity",
                      "Freda Sparks" in asset_options and alias2 in asset_options
                      and not any(value in asset_options for value in (uid1, uid2, "sim1", "sim2")))

                page.click("#tab-button-dashboard")
                frame = page.frame_locator("#dashboard-live-view")
                frame.locator(".card").wait_for()
                card_text = frame.locator(".card").inner_text()
                check("Dashboard card retains Seat primary and alias secondary only",
                      "Seat 0" in card_text and "Freda Sparks" in card_text
                      and uid1 not in card_text and "sim1" not in card_text)

                # Venue snapshots must not roll back host-global alias identity.
                page.click("#tab-button-seats")
                prompt_values.append("Alias-venue")
                page.click("#venue-save")
                page.wait_for_function("() => venues.venues.includes('Alias-venue')")
                page.click("#tab-button-devices")
                page.locator(f'#device-roster [data-uid="{uid1}"]').click()
                page.fill("#device-alias", "Mira Velvet")
                page.click("#device-alias-save")
                page.wait_for_function(
                    "uid => installation.device_registry[uid].alias === 'Mira Velvet'", arg=uid1)
                page.click("#tab-button-seats")
                page.select_option("#venue-select", "Alias-venue")
                page.click("#venue-load")
                page.wait_for_function("() => venues.current === 'Alias-venue'")
                check("venue load preserves the host-global alias registry",
                      page.evaluate("uid => installation.device_registry[uid].alias", uid1)
                      == "Mira Velvet")

                # A real dashboard process restart must reload the same resolved aliases.
                stop(server)
                server = None
                page.wait_for_selector("#ws-status.offline")
                server = start_server()
                page.reload()
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "uid => installation.device_registry?.[uid]?.alias === 'Mira Velvet'", arg=uid1)
                check("dashboard restart preserves custom and generated aliases",
                      page.evaluate("uid => installation.device_registry[uid].alias", uid1)
                      == "Mira Velvet"
                      and page.evaluate("uid => installation.device_registry[uid].alias", uid2)
                      == alias2)

                page.click("#tab-button-devices")
                page.locator(f'#device-roster [data-uid="{uid1}"]').click()
                page.click("#device-alias-reset")
                page.wait_for_function(
                    "uid => installation.device_registry[uid].source === 'generated'", arg=uid1)
                reset_alias = page.evaluate("uid => installation.device_registry[uid].alias", uid1)
                check("Reset restores a generated globally unique alias",
                      reset_alias != "Mira Velvet" and reset_alias != alias2)

                page.locator(f'#device-roster [data-uid="{uid2}"]').click()
                page.fill("#device-alias", "Rina Vinyl")
                page.click("#device-alias-save")
                page.wait_for_function(
                    "uid => installation.device_registry[uid].alias === 'Rina Vinyl'", arg=uid2)

                # The identity hierarchy and controls remain usable at phone width.
                page.set_viewport_size({"width": 375, "height": 812})
                page.click("#tab-button-devices")
                page.locator(f'#device-roster [data-uid="{uid2}"]').click()
                narrow = page.evaluate("""() => ({
                    overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
                    aliasVisible: !!document.querySelector('#device-alias')?.offsetParent,
                    saveVisible: !!document.querySelector('#device-alias-save')?.offsetParent,
                    resetVisible: !!document.querySelector('#device-alias-reset')?.offsetParent,
                    inputHeight: document.querySelector('#device-alias')?.getBoundingClientRect().height || 0,
                    saveHeight: document.querySelector('#device-alias-save')?.getBoundingClientRect().height || 0,
                    resetHeight: document.querySelector('#device-alias-reset')?.getBoundingClientRect().height || 0,
                    rosterWidth: document.querySelector('.device-sidebar')?.getBoundingClientRect().width || 0,
                    viewport: document.documentElement.clientWidth,
                })""")
                check("narrow Devices layout keeps accessible Rename/Reset controls without overflow",
                      not narrow["overflow"] and narrow["aliasVisible"] and narrow["saveVisible"]
                      and narrow["resetVisible"] and narrow["inputHeight"] >= 44
                      and narrow["saveHeight"] >= 44 and narrow["resetHeight"] >= 44
                      and narrow["rosterWidth"] <= narrow["viewport"], repr(narrow))
                page.set_viewport_size({"width": 1280, "height": 900})

                # Let the real offline sweep fire, then verify aliases remain usable.
                stop(fleet)
                fleet = None
                page.wait_for_function(
                    "() => Object.values(installation.devices||{}).length === 2"
                    " && Object.values(installation.devices).every(device => !device.online)",
                    timeout=38000)
                offline_roster = page.locator("#device-roster").inner_text()
                check("offline transition retains aliases and hides technical identity",
                      reset_alias in offline_roster and "Rina Vinyl" in offline_roster
                      and not any(value in offline_roster for value in (uid1, uid2, "sim1", "sim2")))

                # Forget is genuine deletion: both runtime row and durable registry entry vanish.
                page.locator(f'#device-roster [data-uid="{uid2}"]').click()
                page.click("#device-forget")
                page.wait_for_function(
                    "uid => !installation.devices?.[uid] && !installation.device_registry?.[uid]", arg=uid2)
                check("Forget removes the offline device and its custom registry entry", True)
                with open(state, encoding="utf-8") as source:
                    persisted = json.load(source)
                check("Forget deletion is durable on disk", uid2 not in persisted["device_registry"])

                stop(server)
                server = None
                server = start_server()
                page.reload()
                page.wait_for_selector("#ws-status.online")
                check("forgotten alias stays deleted after dashboard restart",
                      page.evaluate("uid => !(uid in (installation.device_registry||{}))", uid2))
                check("browser emitted no page errors", not errors, repr(errors))
                browser.close()
        except Exception:
            log.flush()
            with open(log_path, encoding="utf-8") as source:
                print("\n--- dashboard/simfleet log ---\n" + source.read(), file=sys.stderr)
            raise
        finally:
            stop(fleet)
            stop(server)
            log.close()

    check_count = 18
    if PASSED != check_count:
        raise AssertionError(f"browser verifier count drift: {PASSED} != {check_count}")
    print(f"\n{PASSED}/{check_count} browser checks passed")


if __name__ == "__main__":
    main()
