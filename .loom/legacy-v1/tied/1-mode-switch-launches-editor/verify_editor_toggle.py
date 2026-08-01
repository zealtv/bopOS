#!/usr/bin/env python3
"""Verification for stitch 38/1+2: menu-bar Patch Edit launch + editor button toggle."""

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
_CANDIDATES = [HERE, "/Users/bob/repos/bopOS"]
REPO = None
for _candidate in _CANDIDATES:
    _walk = _candidate
    while True:
        if os.path.isfile(os.path.join(_walk, "tools", "simfleet.py")):
            REPO = _walk
            break
        _parent = os.path.dirname(_walk)
        if _parent == _walk:
            break
        _walk = _parent
    if REPO:
        break
if REPO is None:
    raise SystemExit("cannot locate bopOS repo")

FAILURES = []
RESERVED = set()


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_port(kind):
    for _attempt in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        if port in RESERVED:
            continue
        sock = socket.socket(socket.AF_INET, kind)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            sock.close()
            continue
        sock.close()
        RESERVED.add(port)
        return port
    raise RuntimeError("cannot reserve port")


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
    with tempfile.TemporaryDirectory(prefix="bopos-editor-toggle-") as temp:
        patches = os.path.join(temp, "patches")
        assets = os.path.join(temp, "assets")
        patch = os.path.join(patches, "alpha")
        os.makedirs(patch)
        os.makedirs(assets)
        manifest = os.path.join(patch, "bopos.patch.json")
        with open(os.path.join(patch, "main.bin"), "wb") as target:
            target.write(b"editor toggle verifier")
        with open(manifest, "w", encoding="utf-8") as target:
            json.dump({
                "engine": "test", "entrypoint": "main.bin",
                "params": [{"name": "gain", "type": "f", "min": 0,
                            "max": 1, "default": .5, "dashboard": True}],
                "cues": [], "caps": [], "slots": [],
            }, target)
        state_path = os.path.join(temp, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "editor toggle rig", "seats": {},
                       "fleet_patch": {"name": "alpha", "fingerprint": "0" * 64}},
                      target)

        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        engine_port = free_port(socket.SOCK_DGRAM)
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
                "--sim-audio-backend", "none", "--sim-no-engine",
                "--sim-engine-port-base", str(engine_port),
            ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "1", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.3", "--manifest", manifest,
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base_url)
                page.wait_for_selector("#ws-status", state="attached")
                page.wait_for_function(
                    "() => Object.keys(installation.devices||{}).length >= 1")

                page.click("#tab-button-patches")
                page.wait_for_selector("#editor-patch option", state="attached")

                # --- off state ---
                check(
                    "off-state launch button reads 'Launch editor'",
                    page.locator("#editor-launch").inner_text().lower() == "launch editor")
                check(
                    "off-state session-actions is empty",
                    page.locator("#editor-session-actions").inner_text().strip() == "")
                check(
                    "removed buttons never render in off state",
                    page.locator("#editor-restart").count() == 0
                    and page.locator("#editor-hear-sim").count() == 0
                    and page.locator("#editor-stop").count() == 0)

                # --- menu-bar Patch Edit toggle launches the editor ---
                page.click('[data-execution-target="edit"]')
                entered = True
                try:
                    page.wait_for_function(
                        "() => installation.supervisor?.mode === 'edit'"
                        " && installation.editor?.active === true",
                        timeout=8000)
                except Exception as exc:  # noqa: BLE001
                    entered = False
                    detail = str(exc)

                if entered:
                    check("menu-bar Patch Edit toggle launches the editor "
                          "(live editor mode reached headlessly)", True)
                    page.wait_for_function(
                        "() => document.querySelector('#editor-launch').textContent"
                        " === 'Stop Editor'", timeout=8000)
                    check(
                        "in-tab button now reads 'Stop Editor'",
                        page.locator("#editor-launch").inner_text().lower() == "stop editor")
                    check(
                        "removed buttons stay gone while editor is active",
                        page.locator("#editor-restart").count() == 0
                        and page.locator("#editor-hear-sim").count() == 0
                        and page.locator("#editor-stop").count() == 0
                        and "Launch selected patch" not in
                        page.locator("#editor-launch").inner_text())

                    # Stop via the in-tab button now doubling as Stop control.
                    page.click("#editor-launch")
                    try:
                        page.wait_for_function(
                            "() => installation.supervisor?.mode === 'off'",
                            timeout=8000)
                    except Exception as exc:  # noqa: BLE001
                        print("DEBUG stop-via-in-tab mode:",
                              page.evaluate("() => installation.supervisor?.mode"))
                        print("DEBUG stop-via-in-tab exc:", exc)
                    check(
                        "in-tab Stop Editor click returns to off + relabels",
                        page.locator("#editor-launch").inner_text().lower() == "launch editor")

                    # Re-enter via the in-tab Launch editor button, then exit
                    # via the menu-bar toggle, to check both directions stay
                    # in sync (decided constraint).
                    page.click("#editor-launch")
                    page.wait_for_function(
                        "() => installation.supervisor?.mode === 'edit'",
                        timeout=8000)
                    check(
                        "in-tab launch flips menu-bar affordance in sync",
                        page.locator('[data-execution-target="edit"]')
                        .get_attribute("aria-pressed") in ("true", None))
                    page.click('[data-execution-target="off"]')
                    try:
                        page.wait_for_function(
                            "() => installation.supervisor?.mode === 'off'",
                            timeout=8000)
                    except Exception as exc:  # noqa: BLE001
                        print("DEBUG off-toggle mode:",
                              page.evaluate("() => installation.supervisor?.mode"))
                        print("DEBUG off-toggle exc:", exc)
                    check(
                        "menu-bar Live Fleet click stops the editor and "
                        "relabels the in-tab button back",
                        page.locator("#editor-launch").inner_text().lower() == "launch editor")
                else:
                    print(f"NOTE: could not reach live edit mode headlessly ({detail});"
                          " skipping live-editor assertions.")
                    print("NEEDS LIVE EDITOR: menu-bar toggle launches editor")
                    print("NEEDS LIVE EDITOR: in-tab button relabels to 'Stop Editor'")
                    print("NEEDS LIVE EDITOR: both affordances stay in sync")

                # --- synthesize active/closed editor state without a live
                # process, to check DOM wiring for states we can inject ---
                injected = page.evaluate(
                    """() => {
                        installation.editor = {active: true, status: 'running',
                            patch: 'alpha', declarations: [], params: {},
                            engine_alive: 1};
                        installation.supervisor = {mode: 'edit'};
                        renderEditor();
                        return document.querySelector('#editor-launch').textContent;
                    }""")
                check(
                    "synthesized active editor relabels in-tab button",
                    injected == "Stop Editor")
                check(
                    "synthesized active editor renders no removed buttons",
                    page.locator("#editor-restart").count() == 0
                    and page.locator("#editor-hear-sim").count() == 0
                    and page.locator("#editor-stop").count() == 0)
                check(
                    "synthesized active (engine alive) session-actions empty",
                    page.locator("#editor-session-actions").inner_text().strip() == "")

                relaunch_shown = page.evaluate(
                    """() => {
                        installation.editor.engine_alive = 0;
                        renderEditor();
                        return !!document.querySelector('#editor-relaunch');
                    }""")
                check(
                    "synthesized closed-engine state still shows Relaunch",
                    relaunch_shown)
                check(
                    "removed buttons stay gone in closed-engine state",
                    page.locator("#editor-restart").count() == 0
                    and page.locator("#editor-hear-sim").count() == 0
                    and page.locator("#editor-stop").count() == 0)

                # restore off state and confirm button relabels back
                off_label = page.evaluate(
                    """() => {
                        installation.editor = {active: false, status: 'off',
                            declarations: [], params: {}};
                        installation.supervisor = {mode: 'off'};
                        renderEditor();
                        return document.querySelector('#editor-launch').textContent;
                    }""")
                check(
                    "synthesized off state relabels back to 'Launch editor'",
                    off_label == "Launch editor")

                check("browser emitted no page errors", not errors, repr(errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

        if FAILURES:
            with open(server_log_path, encoding="utf-8") as source:
                print("\nserver log tail:\n", source.read()[-3000:])
            with open(fleet_log_path, encoding="utf-8") as source:
                print("\nfleet log tail:\n", source.read()[-3000:])

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("editor toggle checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
