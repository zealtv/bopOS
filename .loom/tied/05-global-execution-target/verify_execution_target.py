#!/usr/bin/env python3
"""Focused global execution-target browser/backend regression."""

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
while not os.path.isfile(os.path.join(REPO, "dashboard", "server.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent

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
    raise RuntimeError("cannot reserve localhost port")


def write_patch(root, name):
    path = os.path.join(root, name)
    os.makedirs(path)
    with open(os.path.join(path, "main.bin"), "wb") as target:
        target.write(name.encode())
    with open(os.path.join(path, "bopos.patch.json"), "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "params": [],
                   "caps": [], "slots": []}, target)


def wait_http(url, process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before HTTP startup")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not start")


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def pressed(page, target):
    return page.locator(f'[data-execution-target="{target}"]').get_attribute(
        "aria-pressed") == "true"


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-execution-target-") as root:
        assets, patches = os.path.join(root, "assets"), os.path.join(root, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        write_patch(patches, "alpha")
        write_patch(patches, "beta")
        state_path = os.path.join(root, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "target", "master": .37,
                       "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                                       "staged_at": 1},
                       "seats": {"0": {"id": 0, "name": "Seat 0",
                           "positions": [[1, 1]], "params": {}, "bound": None}}}, target)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM)
        engine_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = os.path.join(root, "dashboard.log")
        log = open(log_path, "w", encoding="utf-8")
        process = None
        try:
            process = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(command_port),
                "--state-file", state_path, "--assets-dir", assets,
                "--patches-dir", patches, "--sim-no-engine",
                "--sim-audio-backend", "none", "--sim-engine-port-base", str(engine_port),
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base_url, process)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1400, "height": 1000})
                dialogs, errors = [], []

                def handle_dialog(dialog):
                    dialogs.append((dialog.type, dialog.message))
                    dialog.accept()

                page.on("dialog", handle_dialog)
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "() => [...document.querySelectorAll('#editor-patch option')]"
                    ".some(option => option.value === 'beta')")
                labels = page.locator("[data-execution-target]").all_text_contents()
                check("header exposes the three authoritative execution targets",
                      labels == ["Live fleet", "Simulation", "Patch edit"], repr(labels))
                check("server mode selects Live fleet on entry",
                      pressed(page, "off")
                      and page.locator("#mode-status").inner_text().lower() == "live fleet")
                check("Seats keeps status only with no duplicate transition controls",
                      page.locator("#simulate-status").count() == 1
                      and page.locator("#simulate-toggle, #edit-sim-patch").count() == 0)

                before_dialogs = len(dialogs)
                page.evaluate("ws.send('set_simulation',{active:true,patch:'beta'})")
                page.wait_for_timeout(150)
                check("backend rejects unconfirmed Live to Simulation transition",
                      page.evaluate("installation.supervisor.mode") == "off"
                      and any(kind == "alert" and "Starting Simulation" in message
                              for kind, message in dialogs[before_dialogs:]))

                page.click('[data-execution-target="edit"]')
                page.wait_for_function("() => activeTab === 'patches'")
                check("Patch edit target navigates without guessing or launching",
                      page.evaluate("installation.supervisor.mode") == "off"
                      and not page.evaluate("installation.editor.active")
                      and pressed(page, "off"))
                page.select_option("#editor-patch", "beta")
                page.click('[data-execution-target="simulate"]')
                page.wait_for_function(
                    "() => installation.supervisor?.mode === 'simulate'"
                    " && installation.simulation?.patch === 'beta'")
                check("Simulation uses the contextual Patches selection",
                      pressed(page, "simulate")
                      and page.locator("#mode-status").inner_text().lower() == "simulation"
                      and page.evaluate("installation.fleet_patch.name") == "alpha")
                page.locator("header").screenshot(
                    path=os.path.join(HERE, "execution-target.png"))
                page.click("#tab-button-seats")
                check("Seats compact status reflects the active target and patch",
                      "running · beta" in page.locator("#simulate-status").inner_text())

                page.click('[data-execution-target="edit"]')
                page.wait_for_function(
                    "() => activeTab === 'patches' && installation.supervisor?.mode === 'off'")
                check("Simulation to Patch edit is guarded and stops before navigation",
                      any(kind == "confirm" and "choose a patch to edit" in message
                          for kind, message in dialogs)
                      and not page.evaluate("installation.editor.active"))

                before_dialogs = len(dialogs)
                page.evaluate("ws.send('set_edit',{active:true,patch:'beta'})")
                page.wait_for_timeout(150)
                check("backend rejects unconfirmed Live to Patch edit transition",
                      page.evaluate("installation.supervisor.mode") == "off"
                      and any(kind == "alert" and "Starting Patch edit" in message
                              for kind, message in dialogs[before_dialogs:]))

                page.click("#editor-launch")
                page.wait_for_function(
                    "() => installation.supervisor?.mode === 'edit'"
                    " && installation.editor?.patch === 'beta'")
                check("contextual launch visibly reasserts Patch edit target",
                      pressed(page, "edit")
                      and page.locator("#mode-status").inner_text().lower() == "patch edit")

                before_dialogs = len(dialogs)
                page.evaluate("ws.send('set_edit',{active:false})")
                page.wait_for_timeout(150)
                check("backend rejects unconfirmed Patch edit stop",
                      page.evaluate("installation.supervisor.mode") == "edit"
                      and any(kind == "alert" and "Stopping Patch edit" in message
                              for kind, message in dialogs[before_dialogs:]))

                before_dialogs = len(dialogs)
                page.evaluate("ws.send('set_simulation',{active:true,patch:'beta'})")
                page.wait_for_timeout(150)
                check("backend rejects unconfirmed Patch edit to Simulation transition",
                      page.evaluate("installation.supervisor.mode") == "edit"
                      and any(kind == "alert" and "requires confirmation" in message
                              for kind, message in dialogs[before_dialogs:]))

                page.click('[data-execution-target="simulate"]')
                page.wait_for_function("() => installation.supervisor?.mode === 'simulate'")
                check("confirmed Patch edit to Simulation preserves the edited patch",
                      page.evaluate("installation.simulation.patch") == "beta"
                      and any(kind == "confirm" and "hear \"beta\" in Simulation" in message
                              for kind, message in dialogs))

                page.click('[data-execution-target="off"]')
                page.wait_for_function("() => installation.supervisor?.mode === 'off'")
                check("Simulation to Live is guarded and reasserts Live fleet",
                      pressed(page, "off")
                      and any(kind == "confirm" and "return audio control" in message
                              for kind, message in dialogs))

                page.click('[data-execution-target="edit"]')
                page.click("#editor-launch")
                page.wait_for_function("() => installation.supervisor?.mode === 'edit'")
                page.click('[data-execution-target="off"]')
                page.wait_for_function("() => installation.supervisor?.mode === 'off'")
                check("Patch edit to Live is guarded and restores master/mute UI",
                      any(kind == "confirm" and "Stop Patch edit" in message
                          for kind, message in dialogs)
                      and page.locator("#master-out").evaluate("element => element.value") == "37%"
                      and not page.locator("#mute-all").get_attribute("class").endswith("active"))
                check("browser emitted no page errors", not errors, repr(errors))
                browser.close()
        finally:
            stop(process)
            log.close()
        server_log = open(log_path, encoding="utf-8").read()
        check("dashboard process exits cleanly",
              process is not None and process.returncode in (0, -15)
              and "Application shutdown complete" in server_log)
    total = 17
    print(f"\n{total - len(FAILURES)}/{total} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
