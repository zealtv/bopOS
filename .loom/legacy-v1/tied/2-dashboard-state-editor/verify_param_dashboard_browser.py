#!/usr/bin/env python3
"""Real-dashboard Playwright verification for nested parameter authoring."""

import json
import os
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright
from pythonosc import osc_message

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "dashboard" / "server.py").is_file():
            return candidate
    raise RuntimeError("cannot locate repository")


REPO = repo_root()
FAILURES = []
RESERVED = set()


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
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
    raise RuntimeError("cannot reserve loopback port")


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


def receive(capture, address, expected, timeout=3):
    capture.settimeout(.2)
    deadline = time.monotonic() + timeout
    seen = []
    while time.monotonic() < deadline:
        try:
            packet, _source = capture.recvfrom(65535)
        except socket.timeout:
            continue
        message = osc_message.OscMessage(packet)
        seen.append((message.address, list(message.params)))
        if (message.address == address and message.params
                and abs(float(message.params[0]) - expected) < 1e-5):
            return True, seen
    return False, seen


def wait_saved(page):
    page.wait_for_function(
        "() => {const text=document.querySelector('#manifest-feedback')?.textContent||'';"
        "return !text.includes('Saving manifest') && "
        "(text.toLowerCase().includes('saved') || text.startsWith('Not saved:'));}",
        timeout=5000)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-param-browser-") as root:
        patches = Path(root, "patches")
        assets = Path(root, "assets")
        patch = patches / "alpha"
        patch.mkdir(parents=True)
        assets.mkdir()
        (patch / "main.bin").write_bytes(b"browser nested verifier")
        manifest_path = patch / "bopos.patch.json"
        manifest_path.write_text(json.dumps({
            "engine": "test", "entrypoint": "main.bin",
            "params": [
                {"path": ["synth", "voice"], "name": "gain", "type": "f",
                 "min": 0, "max": 1, "default": .25},
                {"path": ["fx", "reverb"], "name": "gain", "type": "f",
                 "min": 0, "max": 1, "default": .75},
                {"name": "level", "type": "f", "min": 0, "max": 1,
                 "default": .5, "group": "mix"},
            ], "cues": [], "caps": [], "slots": [],
        }, indent=2) + "\n")
        state_path = Path(root, "installation.json")
        state_path.write_text(json.dumps({"schema": 1, "name": "nested", "seats": {}}))

        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM)
        engine_port = free_port(socket.SOCK_DGRAM)
        capture = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        capture.bind(("127.0.0.1", engine_port))
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = Path(root, "dashboard.log")
        log = log_path.open("w")
        server = None
        try:
            server = subprocess.Popen([
                sys.executable, str(REPO / "dashboard" / "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(command_port),
                "--osc-target", "127.0.0.1", "--state-file", str(state_path),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--sim-no-engine", "--sim-audio-backend", "none",
                "--sim-engine-port-base", str(engine_port),
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1200})
                page_errors = []
                dialogs = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def accept_dialog(dialog):
                    dialogs.append((dialog.type, dialog.message))
                    dialog.accept()

                page.on("dialog", accept_dialog)
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-patches")
                page.select_option("#editor-patch", "alpha")
                page.click("#editor-launch")
                page.wait_for_function(
                    "() => installation.supervisor?.mode==='edit'"
                    " && installation.editor?.patch==='alpha'", timeout=10000)
                page.wait_for_selector('[data-editor-param="synth/voice/gain"]')

                paths = page.locator('[data-manifest-field="path"]')
                check("manifest renders slash-separated path arrays",
                      paths.nth(0).input_value() == "synth/voice"
                      and paths.nth(1).input_value() == "fx/reverb")
                check("legacy group inputs are absent and flat paths stay editable",
                      page.locator('[data-manifest-field="group"]').count() == 0
                      and not paths.nth(2).is_disabled())
                check("nested editor renders duplicate leaves in distinct branches",
                      page.locator('[data-param-path="synth/voice"]').count() == 1
                      and page.locator('[data-param-path="fx/reverb"]').count() == 1
                      and page.locator('[data-editor-param$="/gain"]').count() == 2)

                synth = page.locator('[data-editor-param="synth/voice/gain"]')
                synth.evaluate("el=>{el.value='.4';el.dispatchEvent(new Event('input',{bubbles:true}));}")
                ok, seen = receive(capture, "/p/synth/voice/gain", .4)
                check("nested editor control sends its qualified OSC address", ok, repr(seen))
                reverb = page.locator('[data-editor-param="fx/reverb/gain"]')
                reverb.evaluate("el=>{el.value='.6';el.dispatchEvent(new Event('input',{bubbles:true}));}")
                ok, seen = receive(capture, "/p/fx/reverb/gain", .6)
                check("duplicate leaf control stays bound to its own branch", ok, repr(seen))

                # Legacy presentation groups normalize away on load.
                paths.nth(2).fill("mix/main")
                paths.nth(2).press("Tab")
                paths.nth(0).fill("synth/main")
                page.click("#manifest-save")
                wait_saved(page)
                saved = json.loads(manifest_path.read_text())
                check("path updates serialize as arrays after group normalization",
                      saved["params"][0]["path"] == ["synth", "main"]
                      and saved["params"][2]["path"] == ["mix", "main"]
                      and "group" not in saved["params"][2], repr(saved["params"]))
                feedback = page.locator("#manifest-feedback").inner_text()
                check("path move warns with exact old engine identities",
                      "/p/synth/voice/gain" in feedback and "/p/level" in feedback,
                      feedback)
                check("path move is remove/add and rebinds the editor tree",
                      page.locator('[data-editor-param="synth/voice/gain"]').count() == 0
                      and page.locator('[data-editor-param="synth/main/gain"]').count() == 1
                      and page.locator('[data-editor-param="mix/main/level"]').count() == 1)

                # Create and delete a path-bearing declaration through the UI.
                page.click("#manifest-add-param")
                row = page.locator(".manifest-param").last
                row.locator('[data-manifest-field="name"]').fill("tone")
                row.locator('[data-manifest-field="default"]').fill(".2")
                row.locator('[data-manifest-field="path"]').fill("new/branch")
                row.locator('[data-manifest-field="path"]').press("Tab")
                page.click("#manifest-save")
                wait_saved(page)
                saved = json.loads(manifest_path.read_text())
                created_count = page.locator(
                    '[data-editor-param="new/branch/tone"]').count()
                check("path declaration create persists and renders",
                      saved["params"][-1]["path"] == ["new", "branch"]
                      and created_count == 1,
                      repr((saved["params"][-1], created_count,
                            page.evaluate("installation.editor"))))
                page.locator(".manifest-param").last.locator("[data-remove-param]").click()
                page.click("#manifest-save")
                wait_saved(page)
                saved = json.loads(manifest_path.read_text())
                check("path declaration delete persists and prunes editor control",
                      all(item["name"] != "tone" for item in saved["params"])
                      and page.locator('[data-editor-param="new/branch/tone"]').count() == 0)
                check("browser emitted no page errors", not page_errors, repr(page_errors))
                check("identity-changing saves were explicitly confirmed",
                      any(kind == "confirm" and "/p/synth/voice/gain" in message
                          for kind, message in dialogs), repr(dialogs))
                browser.close()
        finally:
            stop(server)
            capture.close()
            log.close()
            if server is not None and server.returncode not in (0, -15):
                print("\n--- dashboard log ---\n" + log_path.read_text())

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
