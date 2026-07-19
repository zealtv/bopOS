#!/usr/bin/env python3
"""Focused browser verification for PE-3 manifest authoring."""

import hashlib
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
from pythonosc import osc_message

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "dashboard", "server.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent

FAILURES = []
RESERVED_PORTS = set()
SENT_FRAMES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_port(kind):
    for _attempt in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        if port in RESERVED_PORTS:
            continue
        sock = socket.socket(socket.AF_INET, kind)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            sock.close()
            continue
        sock.close()
        RESERVED_PORTS.add(port)
        return port
    raise RuntimeError("cannot reserve a dynamic non-default loopback port")


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


def manifest_bytes(patch):
    with open(os.path.join(patch, "bopos.patch.json"), "rb") as source:
        return source.read()


def load_manifest(patch):
    with open(os.path.join(patch, "bopos.patch.json"), encoding="utf-8") as source:
        return json.load(source)


def seed_patch(patches):
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"non-PD verifier entrypoint")
    with open(os.path.join(patch, "bopos.patch.json"), "w", encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin",
            "params": [{
                "name": "gain", "type": "f", "min": 0, "max": 1,
                "default": .25, "group": "mix", "facilitator": True,
            }, {"name": "legacy_label", "type": "s", "group": "legacy"}],
            "cues": [{"id": "start", "label": "Start",
                      "description": "Original cue"}],
            "caps": ["audio", "edit"], "slots": ["samples"],
        }, target, indent=2)
        target.write("\n")
    return patch


def receive_value(capture, address, expected, timeout=3):
    deadline = time.monotonic() + timeout
    seen = []
    capture.settimeout(.2)
    while time.monotonic() < deadline:
        try:
            packet, _source = capture.recvfrom(65535)
        except socket.timeout:
            continue
        message = osc_message.OscMessage(packet)
        if message.address != address:
            continue
        values = list(message.params)
        seen.append(values)
        if values and abs(float(values[0]) - expected) < 1e-5:
            return values, seen
    return None, seen


def fill_param(row, *, name, kind="f", minimum="0", maximum="1",
               default="0", dashboard=False):
    row.locator('[data-manifest-field="name"]').fill(name)
    row.locator('[data-manifest-field="type"]').select_option(kind)
    row.locator('[data-manifest-field="min"]').fill(minimum)
    row.locator('[data-manifest-field="max"]').fill(maximum)
    row.locator('[data-manifest-field="default"]').fill(default)
    checkbox = row.locator('[data-manifest-field="dashboard"]')
    if dashboard:
        checkbox.check()
    else:
        checkbox.uncheck()


def wait_manifest_result(page):
    try:
        page.wait_for_function(
            "() => { const text=document.querySelector('#manifest-feedback')"
            "?.textContent||''; const lower=text.toLowerCase();"
            " return !text.includes('Saving manifest')"
            " && (lower.includes('saved') || text.startsWith('Not saved:')); }",
            timeout=5000)
    except Exception as error:
        state = page.evaluate("() => ({feedback:document.querySelector('#manifest-feedback')?.textContent, disabled:document.querySelector('#manifest-save')?.disabled, draft:manifestDraft})")
        raise RuntimeError(
            f"manifest save did not settle: {state}; sent={SENT_FRAMES[-4:]}") from error
    return page.locator("#manifest-feedback").inner_text()


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-pe3-") as temp:
        patches = os.path.join(temp, "patches")
        assets = os.path.join(temp, "assets")
        template_dir = os.path.join(patches, ".templates")
        os.makedirs(template_dir)
        os.makedirs(assets)
        alpha = seed_patch(patches)
        bob_template = os.path.join(REPO, "patches", ".templates",
                                    "bopos-template.pd")
        temp_template = os.path.join(template_dir, "bopos-template.pd")
        shutil.copyfile(bob_template, temp_template)

        state_path = os.path.join(temp, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "pe3", "seats": {}}, target)

        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM)
        engine_port = free_port(socket.SOCK_DGRAM)
        capture = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        capture.bind(("127.0.0.1", engine_port))
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = os.path.join(temp, "dashboard.log")
        log = open(log_path, "w", encoding="utf-8")
        server = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port),
                "--send-port", str(command_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", assets, "--patches-dir", patches,
                "--sim-no-engine", "--sim-audio-backend", "none",
                "--sim-engine-port-base", str(engine_port),
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1200})
                page.on("pageerror", lambda error: print(f"[BROWSER ERROR] {error}"))
                page.on("websocket", lambda websocket: websocket.on(
                    "framesent", lambda payload: SENT_FRAMES.append(payload)))
                prompt_value = {"value": ""}
                dialogs = []

                def handle_dialog(dialog):
                    dialogs.append((dialog.type, dialog.message))
                    if dialog.type == "prompt":
                        dialog.accept(prompt_value["value"])
                    else:
                        dialog.accept()

                page.on("dialog", handle_dialog)
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-patches")
                page.select_option("#editor-patch", "alpha")
                page.click("#editor-launch")
                page.wait_for_function(
                    "() => installation.supervisor?.mode === 'edit'"
                    " && installation.editor?.patch === 'alpha'",
                    timeout=10000)
                page.wait_for_selector("#manifest-editor:not([hidden])")

                readonly = page.locator("#manifest-readonly")
                readonly_text = readonly.inner_text().lower()
                check("engine, entrypoint, caps, and slots render read-only",
                      all(value in readonly_text for value in
                          ("test", "main.bin", "audio", "edit", "samples"))
                      and readonly.locator("input, select, textarea").count() == 0,
                      readonly_text)
                legacy_row = page.locator(".manifest-param").nth(1)
                check("legacy string parameter renders honestly and read-only",
                      legacy_row.locator('[data-manifest-field="type"]').input_value() == "s"
                      and legacy_row.locator('[data-manifest-field="name"]').is_disabled()
                      and "read-only" in legacy_row.inner_text().lower())

                generation = page.evaluate("installation.editor.generation")
                page.click("#manifest-add-param")
                new_param = page.locator(".manifest-param").last
                fill_param(new_param, name="tone", minimum="100", maximum="1000",
                           default="440", dashboard=True)

                # Cue create and update are persisted in the same atomic save.
                first_cue = page.locator(".manifest-cue").first
                first_cue.locator('[data-manifest-field="label"]').fill("Begin")
                page.click("#manifest-add-cue")
                new_cue = page.locator(".manifest-cue").last
                new_cue.locator('[data-manifest-field="id"]').fill("stop")
                new_cue.locator('[data-manifest-field="label"]').fill("Stop")
                new_cue.locator('[data-manifest-field="description"]').fill(
                    "Stop the piece")
                page.click("#manifest-save")
                first_feedback = wait_manifest_result(page)
                saved = load_manifest(alpha)
                check("parameter add and cue create/update save atomically",
                      [item["name"] for item in saved["params"]]
                      == ["gain", "legacy_label", "tone"]
                      and [(cue["id"], cue.get("label")) for cue in saved["cues"]]
                      == [("start", "Begin"), ("stop", "Stop")]
                      and "Manifest saved" in first_feedback,
                      first_feedback + " " + repr(saved))
                check("manifest save refreshes live controls without restart",
                      page.locator('[data-editor-param="tone"]').count() == 1
                      and page.evaluate("installation.editor.generation") == generation
                      and page.evaluate("installation.editor.active"))

                tone = page.locator('[data-editor-param="tone"]')
                tone.evaluate(
                    "el => { el.value='523';"
                    " el.dispatchEvent(new Event('input', {bubbles:true})); }")
                delivered, seen = receive_value(capture, "/p/tone", 523)
                check("new live control reaches the no-engine relay",
                      delivered is not None, repr(seen))

                # Rename and remove together must produce the explicit PD warning.
                gain_row = page.locator(".manifest-param").first
                gain_row.locator('[data-manifest-field="name"]').fill("level")
                page.locator(".manifest-param").last.locator(
                    '[data-remove-param]').click()
                page.click("#manifest-save")
                wait_manifest_result(page)
                warning = page.locator("#manifest-feedback").inner_text().lower()
                check("parameter rename/removal warns that engine routes must follow",
                      "engine routes" in warning and "gain" in warning,
                      warning)

                # Cue deletion completes CRUD and re-renders from disk.
                page.locator(".manifest-cue").first.locator(
                    '[data-remove-cue]').click()
                page.click("#manifest-save")
                wait_manifest_result(page)
                saved = load_manifest(alpha)
                check("cue delete persists and refreshes the cue editor",
                      [cue["id"] for cue in saved["cues"]] == ["stop"]
                      and page.locator(".manifest-cue").count() == 1,
                      repr(saved["cues"]))

                before_invalid = manifest_bytes(alpha)
                page.locator(".manifest-param").first.locator(
                    '[data-manifest-field="name"]').fill("bad name")
                page.click("#manifest-save")
                wait_manifest_result(page)
                check("invalid browser edit is rejected with manifest bytes untouched",
                      manifest_bytes(alpha) == before_invalid
                      and any(kind == "alert" for kind, _message in dialogs),
                      repr(dialogs[-3:]))

                prompt_value["value"] = "from-template"
                page.click("#editor-new-patch")
                created = os.path.join(patches, "from-template")
                page.wait_for_function(
                    "() => document.querySelector('#manifest-feedback')"
                    ".textContent.includes('verbatim copy')")
                page.wait_for_function(
                    "() => document.querySelector('#editor-patch')?.value === 'from-template'")
                copied = os.path.join(created, "main.pd")
                source_hash = hashlib.sha256(open(temp_template, "rb").read()).hexdigest()
                copied_hash = hashlib.sha256(open(copied, "rb").read()).hexdigest()
                created_manifest = load_manifest(created)
                check("New Patch copies Bob's template byte-identically",
                      source_hash == copied_hash, copied_hash)
                check("template-backed New Patch has a valid minimal manifest",
                      created_manifest == {
                          "engine": "pd", "entrypoint": "main.pd", "params": [],
                          "cues": [], "caps": [], "slots": [],
                      }
                      and page.locator('#editor-patch option[value="from-template"]')
                      .count() == 1
                      and page.locator("#editor-patch").input_value() == "from-template",
                      repr(created_manifest))

                # Removing only the temporary copy exercises the honest fallback;
                # Bob's repository template remains untouched.
                os.rename(temp_template, temp_template + ".held")
                prompt_value["value"] = "manifest-only"
                page.click("#editor-new-patch")
                manifest_only = os.path.join(patches, "manifest-only")
                page.wait_for_function(
                    "() => document.querySelector('#manifest-feedback')"
                    ".textContent.toLowerCase().includes('add main.pd')")
                fallback_text = page.locator("#manifest-feedback").inner_text().lower()
                fallback_manifest = load_manifest(manifest_only)
                check("New Patch without template succeeds manifest-only",
                      os.path.isfile(os.path.join(manifest_only, "bopos.patch.json"))
                      and not os.path.exists(os.path.join(manifest_only, "main.pd"))
                      and fallback_manifest["entrypoint"] == "main.pd")
                check("manifest-only fallback is honest in the UI",
                      "no template" in fallback_text or "add main.pd" in fallback_text,
                      fallback_text)
                browser.close()
        finally:
            stop(server)
            capture.close()
            log.close()
            if server is not None and server.returncode not in (0, -15):
                with open(log_path, encoding="utf-8") as source:
                    print("\n--- dashboard log ---\n" + source.read())

    total = 12
    print(f"\n{total - len(FAILURES)}/{total} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
