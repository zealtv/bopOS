#!/usr/bin/env python3
from project_fixture import project_path, data_root
"""Real dashboard + simfleet journey for the Patches tab (66-projects/6).

The project's patches as sidebar + detail (mockups 1-3): the list with its
Live tag and filter, New Version copying the Patch under a bumped name, Set
Live switching the fleet to it, and Add Existing bringing in a catalog
folder. BOPOS_PATCHES_TAB_SCREENSHOT=<path> saves a screenshot of the tab.
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


def patch_bytes(root):
    return {name: open(os.path.join(root, name), "rb").read()
            for name in sorted(os.listdir(root))}


def listed(page):
    return page.evaluate(
        "() => [...document.querySelectorAll('#patch-list .patch-item')]"
        ".map(item => ({name: item.dataset.patch,"
        " live: !!item.querySelector('.patch-live-tag'),"
        " selected: item.classList.contains('selected')}))")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-patches-tab-") as temp:
        state_path = str(project_path(temp))
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        for name in ("demo-pd", "kite-v1", "kite-v2", "kite-sketch"):
            write_patch(patches, name, name.encode())
        # A project stored with a Patch and one earlier version listed.
        state = {"schema": 1, "name": "Kite Choir", "patches": ["kite-v1"],
                 "fleet_patch": {"name": "kite-v2"}, "seats": {
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
                "--osc-target", "127.0.0.1", "--data-dir", data_root(state_path),
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
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.set_default_timeout(15000)
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.wait_for_function(
                    "() => Object.keys(installation.devices||{}).length === 2")
                page.click("#tab-button-patches")
                page.wait_for_function(
                    "() => document.querySelectorAll('#patch-list .patch-item').length === 2")

                # --- the list: the project's patches, the Patch tagged Live ---
                rows = listed(page)
                check("the list is the project's patches, seeded with the Patch",
                      [row["name"] for row in rows] == ["kite-v1", "kite-v2"], repr(rows))
                check("only the Patch carries the Live tag",
                      [row["name"] for row in rows if row["live"]] == ["kite-v2"], repr(rows))
                check("the Patch is selected first",
                      [row["name"] for row in rows if row["selected"]] == ["kite-v2"], repr(rows))
                check("the live patch offers Edit and Push",
                      page.locator("#patch-edit").inner_text() == "Edit"
                      and page.locator("#patch-deploy").inner_text() == "Push")
                check("the old fleet-patch and host-patch pickers are gone",
                      page.locator("#patch-select, #patch-switch, #editor-patch").count() == 0)
                check("Remote device commands sit in the Patches sidebar",
                      page.locator(".patch-sidebar #remote-command-editor").count() == 1)

                page.fill("#patch-filter", "V1")
                page.wait_for_function(
                    "() => document.querySelectorAll('#patch-list .patch-item').length === 1")
                check("the filter narrows the list, ignoring case",
                      [row["name"] for row in listed(page)] == ["kite-v1"])
                page.fill("#patch-filter", "")
                page.wait_for_function(
                    "() => document.querySelectorAll('#patch-list .patch-item').length === 2")

                page.click('#patch-list [data-patch="kite-v1"]')
                page.wait_for_function(
                    "() => document.querySelector('#patch-deploy')?.innerText === 'Set Live'")
                check("another version offers Edit and Set Live",
                      page.locator("#patch-edit").inner_text() == "Edit")

                # --- New Version: suggested name, refusal, copy ---
                suggestions = page.evaluate("""() => [
                  nextVersionName('kite-v2', new Set()),
                  nextVersionName('kite-v09', new Set()),
                  nextVersionName('kite', new Set()),
                  nextVersionName('kite-v2', new Set(['kite-v3']))]""")
                check("suggested names bump the trailing number or append -v2",
                      suggestions == ["kite-v3", "kite-v10", "kite-v2", "kite-v4"],
                      repr(suggestions))
                page.click("#patch-new-version")
                page.wait_for_selector("#patch-version-dialog[open]")
                check("New Version suggests the next name after the Patch",
                      page.input_value("#patch-version-name") == "kite-v3")
                page.fill("#patch-version-name", "kite-v1")
                check("an existing name is refused",
                      page.locator("#patch-version-create").is_disabled()
                      and "already exists" in page.locator("#patch-version-error").inner_text())
                page.fill("#patch-version-name", "kite-v3")
                page.click("#patch-version-create")
                page.wait_for_function(
                    "() => (installation.patches||[]).includes('kite-v3')"
                    " && document.querySelector('#patch-list .patch-item.selected')?.dataset.patch === 'kite-v3'")
                check("New Version copies the Patch folder byte for byte",
                      patch_bytes(os.path.join(patches, "kite-v3"))
                      == patch_bytes(os.path.join(patches, "kite-v2")))
                check("the fleet keeps running the Patch",
                      page.evaluate("() => installation.fleet_patch?.name") == "kite-v2")

                # --- Set Live: the new version goes to the whole fleet ---
                page.click("#patch-deploy")
                page.wait_for_function(
                    "() => installation.fleet_patch?.name === 'kite-v3'"
                    " && document.querySelector('#fleet-patch-summary')?.innerText.includes('2 current')",
                    timeout=20000)
                rows = listed(page)
                check("Set Live moves the Live tag and keeps the old Patch as a version",
                      [row["name"] for row in rows] == ["kite-v1", "kite-v2", "kite-v3"]
                      and [row["name"] for row in rows if row["live"]] == ["kite-v3"],
                      repr(rows))
                check("both devices converge on the new Patch",
                      page.evaluate("() => Object.values(installation.devices).every("
                                    "d => d.report?.patch === 'kite-v3' && d.patch_badge === 'current')"))
                shot = os.environ.get("BOPOS_PATCHES_TAB_SCREENSHOT")
                if shot:
                    page.screenshot(path=shot)

                # --- Set Live outside the project is refused (proposal sec 3) ---
                page.evaluate("ws.send('set_fleet_patch', {patch: 'kite-sketch', confirmed: true})")
                time.sleep(.5)
                check("Set Live refuses a patch outside the project",
                      page.evaluate("() => installation.fleet_patch?.name") == "kite-v3"
                      and "kite-sketch" not in page.evaluate("() => installation.patches"))

                # --- Add Existing: a catalog folder joins the project ---
                page.click("#patch-add-existing")
                page.wait_for_selector("#patch-add-dialog[open]")
                options = page.evaluate(
                    "() => [...document.querySelectorAll('#patch-add-select option')].map(o => o.value)")
                check("Add Existing offers only catalog folders outside the project",
                      options == ["demo-pd", "kite-sketch"], repr(options))
                page.select_option("#patch-add-select", "kite-sketch")
                page.click("#patch-add-confirm")
                page.wait_for_function(
                    "() => document.querySelector('#patch-list .patch-item.selected')?.dataset.patch === 'kite-sketch'")
                check("the added patch is listed and selected, not live",
                      page.evaluate("() => installation.fleet_patch?.name") == "kite-v3"
                      and page.locator("#patch-deploy").inner_text() == "Set Live")

                deadline = time.monotonic() + 5
                saved = None
                while time.monotonic() < deadline:
                    with open(state_path, encoding="utf-8") as source:
                        saved = json.load(source).get("patches")
                    if saved == ["kite-sketch", "kite-v1", "kite-v2", "kite-v3"]:
                        break
                    time.sleep(.2)
                check("project.json keeps the project's patches", saved
                      == ["kite-sketch", "kite-v1", "kite-v2", "kite-v3"], repr(saved))
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
    print("Patches tab browser checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
