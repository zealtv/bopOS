#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for removing an installed asset pack
from a device via the Asset tab's catalog-row Remove control
(39-remove-installed-pack-from-device).

Distinct from the extra-row Remove already covered by 11b: here the pack lives
in the host catalog and is installed on the device, so Remove must surface on
the catalog row itself, converge the row back to absent, and reuse the
active-slot warning when the device's active patch still declares the slot.
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


def write_asset(root, name, payload):
    path = os.path.join(root, name)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "payload.bin"), "wb") as target:
        target.write(payload)


def write_patch(root, slots):
    path = os.path.join(root, "active-test")
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "main.bin"), "wb") as target:
        target.write(b"active patch")
    manifest = {
        "engine": "test", "entrypoint": "main.bin", "params": [],
        "caps": [], "slots": slots,
    }
    manifest_path = os.path.join(path, "bopos.patch.json")
    with open(manifest_path, "w", encoding="utf-8") as target:
        json.dump(manifest, target)
    return manifest_path


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


def row_state(page, slot):
    return page.locator(f'#tab-assets [data-slot="{slot}"]').get_attribute("data-state")


def wait_for_state(page, slot, state, timeout=12000):
    page.wait_for_function(
        "([slot, state]) => document.querySelector("
        "`#tab-assets [data-slot=\"${CSS.escape(slot)}\"]`)?.dataset.state === state",
        arg=[slot, state], timeout=timeout)


def catalog_remove(page, slot):
    return page.locator(
        f'#asset-catalog [data-slot="{slot}"] [data-asset-action="remove"]')


def device_assets(page, uid):
    return page.evaluate(
        "uid => (installation.devices?.[uid]?.assets || []).map(item => item.name).sort()",
        uid)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-assets-39-") as temp:
        state_path = os.path.join(temp, "installation.json")
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        for index, name in enumerate(("alpha", "beta", "gamma")):
            write_asset(assets, name, f"{name}-v1-{index}".encode())
        # active patch declares alpha (so removing it must warn) but not beta.
        manifest_path = write_patch(patches, ["alpha"])

        first_uid = "02:53:49:4d:00:01"
        second_uid = "02:53:49:4d:00:02"
        state = {
            "schema": 1, "name": "Catalog-remove browser rig",
            "seats": {
                "1": {"id": 1, "name": "Front", "positions": [[-1, 1]],
                      "params": {}, "groups": [], "bound": first_uid},
                "2": {"id": 2, "name": "Rear", "positions": [[1, -1]],
                      "params": {}, "groups": [], "bound": second_uid},
            },
        }
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
            server = start_dashboard(
                http_port, listen_port, send_port, state_path, assets, patches,
                base_url, server_log)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "2", "--unassigned", "0",
                "--target", "127.0.0.1", "--report-port", str(listen_port),
                "--cmd-port", str(send_port), "--hb-interval", "0.2",
                "--boot-secs", "1", "--fetch-seconds", "0.8", "--assets-dir", assets,
                "--patches-dir", patches, "--manifest", manifest_path,
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                page.set_default_timeout(10000)
                page_errors = []
                dialogs = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def accept_dialog(dialog):
                    dialogs.append((dialog.type, dialog.message))
                    if dialog.type == "prompt":
                        dialog.accept("verified")
                    else:
                        dialog.accept()

                page.on("dialog", accept_dialog)
                page.goto(base_url + "/#assets")
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "() => Object.keys(installation.devices||{}).length === 2")
                page.wait_for_function(
                    "uids => uids.every(uid => Array.isArray(installation.devices?.[uid]?.assets))",
                    arg=[first_uid, second_uid], timeout=30000)
                page.wait_for_function(
                    "uid => Array.isArray(installation.devices?.[uid]?.active_asset_slots)",
                    arg=first_uid, timeout=12000)
                page.select_option("#asset-target", first_uid)

                # An absent catalog pack offers Send and no Remove.
                check("absent catalog row offers Send and no Remove",
                      row_state(page, "beta") == "absent"
                      and page.locator(
                          '#asset-catalog [data-slot="beta"] [data-asset-action="send"]').count() == 1
                      and catalog_remove(page, "beta").count() == 0)

                # Install beta (a non-active catalog pack), then it must offer Remove.
                page.locator(
                    '#asset-catalog [data-slot="beta"] [data-asset-action="send"]').click()
                wait_for_state(page, "beta", "current")
                check("installed non-active catalog row surfaces Remove",
                      catalog_remove(page, "beta").count() == 1
                      and catalog_remove(page, "beta").get_attribute("class") == "danger")

                # Remove the non-active pack: no active warning, converges to absent.
                dialog_start = len(dialogs)
                catalog_remove(page, "beta").click()
                page.wait_for_function(
                    "uid => !(installation.devices?.[uid]?.assets || [])"
                    ".some(item => item.name === 'beta')",
                    arg=first_uid, timeout=12000)
                wait_for_state(page, "beta", "absent")
                remove_dialogs = dialogs[dialog_start:]
                check("non-active catalog Remove confirms plainly and converges to absent",
                      row_state(page, "beta") == "absent"
                      and catalog_remove(page, "beta").count() == 0
                      and page.locator(
                          '#asset-catalog [data-slot="beta"] [data-asset-action="send"]').count() == 1
                      and any(kind == "confirm" and "Remove asset slot" in message
                              and "declared by the active patch" not in message
                              for kind, message in remove_dialogs),
                      repr(remove_dialogs))
                check("catalog Remove only touched the selected device",
                      "beta" not in device_assets(page, first_uid)
                      and "beta" not in device_assets(page, second_uid),
                      repr((device_assets(page, first_uid),
                            device_assets(page, second_uid))))

                # Install alpha (declared by the active patch) then remove it:
                # the active-slot warning must fire from the catalog row.
                page.locator(
                    '#asset-catalog [data-slot="alpha"] [data-asset-action="send"]').click()
                wait_for_state(page, "alpha", "current")
                check("installed active catalog row also surfaces Remove",
                      catalog_remove(page, "alpha").count() == 1)
                dialog_start = len(dialogs)
                catalog_remove(page, "alpha").click()
                page.wait_for_function(
                    "uid => !(installation.devices?.[uid]?.assets || [])"
                    ".some(item => item.name === 'alpha')",
                    arg=first_uid, timeout=12000)
                wait_for_state(page, "alpha", "absent")
                active_dialogs = dialogs[dialog_start:]
                check("active catalog Remove warns about breaking the running patch",
                      row_state(page, "alpha") == "absent"
                      and any(kind == "confirm"
                              and "declared by the active patch" in message
                              and "can immediately break the running patch" in message
                              and "side-by-side generation" in message
                              for kind, message in active_dialogs),
                      repr(active_dialogs))

                page.screenshot(
                    path=os.path.join(HERE, "01-catalog-remove.png"), full_page=True)
                check("browser emitted no page errors", not page_errors,
                      repr(page_errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

        if FAILURES:
            with open(server_log_path, encoding="utf-8") as source:
                print("\nserver log tail:\n", source.read()[-5000:])
            with open(fleet_log_path, encoding="utf-8") as source:
                print("\nfleet log tail:\n", source.read()[-5000:])

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("Catalog-row Remove browser checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
