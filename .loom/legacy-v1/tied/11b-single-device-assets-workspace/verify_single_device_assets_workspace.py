#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for the single-device Assets workspace."""

import json
import os
import random
import shutil
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


def device_assets(page, uid):
    return page.evaluate(
        "uid => (installation.devices?.[uid]?.assets || []).map(item => item.name).sort()",
        uid)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-assets-11b-") as temp:
        state_path = os.path.join(temp, "installation.json")
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        for index, name in enumerate(("alpha", "beta", "gamma", "delta", "epsilon")):
            write_asset(assets, name, f"{name}-v1-{index}".encode())
        write_asset(assets, "field-extra", b"temporary host source")
        manifest_path = write_patch(patches, ["alpha", "field-extra"])

        first_uid = "02:53:49:4d:00:01"
        second_uid = "02:53:49:4d:00:02"
        unassigned_uid = "02:53:49:4d:00:03"
        state = {
            "schema": 1, "name": "Single-device Assets browser rig",
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
                "--devices", "3", "--unassigned", "1",
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
                    "() => Object.keys(installation.devices||{}).length === 3")
                page.wait_for_timeout(1000)
                print("asset startup:", page.evaluate(
                    "() => Object.fromEntries(Object.entries(installation.devices||{})"
                    ".map(([uid, device]) => [uid, {id:device.id, online:device.online, "
                    "assets:Array.isArray(device.assets) ? device.assets.length : null}]))"),
                      flush=True)
                page.wait_for_function(
                    "uids => uids.every(uid => Array.isArray(installation.devices?.[uid]?.assets))",
                    arg=[first_uid, second_uid], timeout=30000)
                page.wait_for_function(
                    "uid => Array.isArray(installation.devices?.[uid]?.active_asset_slots)",
                    arg=first_uid, timeout=12000)

                check("Assets is an operational single-device workspace",
                      page.locator("#tab-assets:not([hidden]) #asset-target").count() == 1
                      and page.locator("#asset-catalog [data-slot]").count() == 6)
                catalog_names = page.locator(
                    "#asset-catalog [data-slot] .asset-row-main > strong").all_inner_texts()
                check("host catalog exposes files, size, modified time and abbreviated identity",
                      catalog_names == ["alpha", "beta", "delta", "epsilon",
                                        "field-extra", "gamma"]
                      and page.locator("#asset-catalog .asset-facts").count() == 6
                      and all(text.endswith("…") for text in page.locator(
                          "#asset-catalog .asset-facts code").all_inner_texts()),
                      repr(catalog_names))
                option_values = page.locator("#asset-target option").evaluate_all(
                    "options => options.map(option => ({value: option.value, disabled: option.disabled, text: option.textContent}))")
                check("target selector offers assigned physical devices but disables unassigned",
                      {item["value"] for item in option_values if not item["disabled"]}
                      == {first_uid, second_uid}
                      and any(item["value"] == unassigned_uid and item["disabled"]
                              and "unassigned" in item["text"] for item in option_values),
                      repr(option_values))
                check("Assets has no fleet-wide controls",
                      page.locator("#tab-assets [data-all], #tab-assets #sync-all, "
                                   "#tab-assets [id*=fleet]").count() == 0
                      and "sync all" not in page.locator("#tab-assets").inner_text().lower()
                      and "all devices" not in page.locator("#tab-assets").inner_text().lower())

                # Guard copy for offline and simulation is exercised without
                # teaching the server fixture identities which do not exist on wire.
                page.evaluate("""() => {
                    installation.devices['offline-fixture'] = {
                      uid:'offline-fixture', hostname:'offline-fixture', virtual:false,
                      online:false, assets:[]};
                    installation.devices['simulation-fixture'] = {
                      uid:'simulation-fixture', hostname:'simulation-fixture', virtual:true,
                      online:true, assets:[]};
                    renderAssets();
                }""")
                guarded = page.locator("#asset-target option").evaluate_all(
                    "options => options.map(option => ({value: option.value, disabled: option.disabled, text: option.textContent}))")
                check("offline and simulated targets are visibly guarded",
                      any(item["value"] == "offline-fixture" and item["disabled"]
                              and "offline" in item["text"] for item in guarded)
                      and any(item["value"] == "simulation-fixture" and item["disabled"]
                              and "simulation" in item["text"] for item in guarded),
                      repr(guarded))
                page.evaluate("""() => {
                    delete installation.devices['offline-fixture'];
                    delete installation.devices['simulation-fixture'];
                    renderAssets();
                }""")

                page.select_option("#asset-target", first_uid)
                check("observed empty inventory renders host slots absent with Send",
                      row_state(page, "beta") == "absent"
                      and page.locator('[data-slot="beta"] [data-asset-action="send"]').count() == 1)
                page.locator('[data-slot="beta"] [data-asset-action="send"]').click()
                page.wait_for_function(
                    "() => ['queued','fetching'].includes(document.querySelector("
                    "'[data-slot=\"beta\"]')?.dataset.state)")
                check("send exposes queued or fetching live feedback",
                      row_state(page, "beta") in {"queued", "fetching"})
                wait_for_state(page, "beta", "current")
                check("Send converges from inventory to current", True)
                check("single-target Send leaves the other assigned device unchanged",
                      "beta" in device_assets(page, first_uid)
                      and "beta" not in device_assets(page, second_uid),
                      repr((device_assets(page, first_uid),
                            device_assets(page, second_uid))))

                # Forged actions exercise backend enforcement independently of
                # disabled options. Neither request may mutate the unassigned node.
                page.evaluate(
                    "([uid]) => ws.send('send_distribution', "
                    "{uid,kind:'asset',name:'gamma',confirmed_active:false})",
                    [unassigned_uid])
                page.evaluate(
                    "() => ws.send('send_distribution', "
                    "{uid:'missing-offline',kind:'asset',name:'gamma',confirmed_active:false})")
                page.wait_for_timeout(1200)
                check("backend rejects forged unassigned and offline delivery targets",
                      "gamma" not in device_assets(page, unassigned_uid))

                # Seed a later device-only row through the real single-target path.
                page.locator('[data-slot="field-extra"] [data-asset-action="send"]').click()
                wait_for_state(page, "field-extra", "current")
                shutil.rmtree(os.path.join(assets, "field-extra"))
                page.click("#asset-refresh")
                page.wait_for_function(
                    "() => document.querySelector('#asset-catalog-summary')?.innerText.startsWith('5 host slots')"
                    " && document.querySelector('#asset-extras [data-slot=\"field-extra\"]')?.dataset.state === 'extra'")
                check("device-only inventory appears beneath the five host rows",
                      page.locator("#asset-catalog [data-slot]").count() == 5
                      and page.locator(
                          '#asset-extras [data-slot="field-extra"] [data-asset-action="remove"]').count() == 1)
                dialog_start = len(dialogs)
                page.locator(
                    '#asset-extras [data-slot="field-extra"] [data-asset-action="remove"]').click()
                page.wait_for_function(
                    "uid => !(installation.devices?.[uid]?.assets || [])"
                    ".some(item => item.name === 'field-extra')",
                    arg=first_uid, timeout=12000)
                extra_remove_dialogs = dialogs[dialog_start:]
                check("active extra-slot Remove warns and converges from fresh inventory",
                      page.locator('#asset-extras [data-slot="field-extra"]').count() == 0
                      and any(kind == "confirm"
                              and "declared by the active patch" in message
                              and "can immediately break the running patch" in message
                              and "side-by-side generation" in message
                              for kind, message in extra_remove_dialogs),
                      repr(extra_remove_dialogs))

                # Install active alpha, then change the host copy to create stale.
                page.locator('[data-slot="alpha"] [data-asset-action="send"]').click()
                wait_for_state(page, "alpha", "current")
                with open(os.path.join(assets, "alpha", "payload.bin"), "wb") as target:
                    target.write(b"alpha-v2-host-edit")
                page.click("#asset-refresh")
                wait_for_state(page, "alpha", "stale")
                dialog_start = len(dialogs)
                page.locator('[data-slot="alpha"] [data-asset-action="update"]').click()
                page.wait_for_function(
                    "() => ['queued','fetching'].includes(document.querySelector("
                    "'[data-slot=\"alpha\"]')?.dataset.state)")
                wait_for_state(page, "alpha", "current")
                update_dialogs = dialogs[dialog_start:]
                check("active-slot Update warns, allows continuation, and converges",
                      any(kind == "confirm" and "declared by the active patch" in message
                              and "partial update or broken files" in message
                              and "side-by-side generation" in message
                              for kind, message in update_dialogs), repr(update_dialogs))

                # A dashboard restart must rebuild current from node inventory.
                receipt_before = page.evaluate(
                    "uid => installation.devices?.[uid]?.distribution?.alpha", first_uid)
                stop(server)
                server = start_dashboard(
                    http_port, listen_port, send_port, state_path, assets, patches,
                    base_url, server_log)
                page.reload()
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "uid => (installation.devices?.[uid]?.assets || [])"
                    ".some(item => item.name === 'alpha')",
                    arg=first_uid, timeout=12000)
                page.select_option("#asset-target", first_uid)
                page.wait_for_function(
                    "() => document.querySelector('[data-slot=\"alpha\"]')?.dataset.state === 'current'",
                    timeout=12000)
                receipt_after = page.evaluate(
                    "uid => installation.devices?.[uid]?.distribution?.alpha || null", first_uid)
                check("dashboard restart derives current state from inventory, not receipts",
                      bool(receipt_before) and receipt_after is None
                      and row_state(page, "alpha") == "current",
                      repr((receipt_before, receipt_after)))

                page.screenshot(
                    path=os.path.join(HERE, "01-assets-workspace.png"),
                    full_page=True)
                page.click("#tab-button-devices")
                page.select_option("#device-filter", "bound")
                page.locator("#device-roster .device-row").first.click()
                page.wait_for_selector("#detail .device-assets-summary")
                check("Devices retains observation and hand-off but no asset actions",
                      page.locator("#detail .device-assets-summary #device-open-assets").count() == 1
                      and page.locator("#tab-devices [data-asset-action], "
                                       "#tab-devices #distribution, "
                                       "#tab-devices #sync-all").count() == 0)

                page.click("#tab-button-assets")
                page.set_viewport_size({"width": 390, "height": 844})
                page.wait_for_timeout(150)
                page.locator('[data-slot="gamma"]').scroll_into_view_if_needed()
                action_box = page.locator(
                    '[data-slot="gamma"] [data-asset-action]').bounding_box()
                check("narrow Assets layout stays within viewport with touch-sized actions",
                      page.evaluate("() => document.documentElement.scrollWidth <= innerWidth")
                      and action_box is not None and action_box["height"] >= 44
                      and action_box["width"] >= 44, repr(action_box))
                page.screenshot(
                    path=os.path.join(HERE, "02-assets-narrow.png"),
                    full_page=True)
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
    print("Single-device Assets workspace browser checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
