#!/usr/bin/env python3
"""Focused p7 manifest normalization and Patch-tab browser checks."""

import json
import os
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "dashboard", "server.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate repo")
    REPO = parent
sys.path.insert(0, REPO)

from playwright.sync_api import sync_playwright  # noqa: E402
from python import manifest  # noqa: E402

FAILURES = []
RESERVED_PORTS = set()


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}" +
          (f" -- {detail}" if detail and not condition else ""))
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
    raise RuntimeError("cannot reserve port")


def wait_http(url, process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited early")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not serve HTTP")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-p7-") as root:
        patches = os.path.join(root, "patches")
        assets = os.path.join(root, "assets")
        patch = os.path.join(patches, "alpha")
        os.makedirs(patch)
        os.makedirs(assets)
        with open(os.path.join(patch, "main.bin"), "wb") as target:
            target.write(b"p7 verifier")
        legacy = {
            "engine": "test", "entrypoint": "main.bin",
            "params": [{"name": "gain", "type": "f", "min": 0,
                        "max": 1, "default": .5, "group": "mix",
                        "facilitator": True}],
            "cues": [], "caps": [], "slots": [],
        }
        with open(os.path.join(patch, manifest.MANIFEST_NAME), "w",
                  encoding="utf-8") as target:
            json.dump(legacy, target)

        loaded, error = manifest.load(patch)
        declaration = loaded["params"][0] if loaded else {}
        check("legacy promotion key normalizes to dashboard",
              error is None and declaration.get("dashboard") is True
              and "facilitator" not in declaration, str(error))
        check("legacy presentation group is ignored on load",
              error is None and "group" not in declaration, repr(declaration))

        same, same_error = manifest.validate(dict(
            legacy, params=[dict(legacy["params"][0], dashboard=True)]), patch)
        check("matching dual promotion keys normalize",
              same_error is None and same["params"][0].get("dashboard") is True)
        conflict, conflict_error = manifest.validate(dict(
            legacy, params=[dict(legacy["params"][0], dashboard=False)]), patch)
        check("conflicting dual promotion keys reject",
              conflict is None and "conflict" in (conflict_error or ""),
              str(conflict_error))

        saved, save_error = manifest.write_atomic(patch, legacy)
        disk = json.load(open(os.path.join(patch, manifest.MANIFEST_NAME),
                              encoding="utf-8"))
        check("save writes only canonical presentation fields",
              save_error is None and disk["params"][0].get("dashboard") is True
              and "facilitator" not in disk["params"][0]
              and "group" not in disk["params"][0], repr(disk))

        state_path = os.path.join(root, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({
                "schema": 1, "name": "p7", "params_patch": "alpha",
                "seats": {"1": {
                    "id": 1, "name": "One", "positions": [[1, 1]],
                    "groups": [], "bound": None, "patch": "alpha",
                    "params": {"gain": .5},
                }},
            }, target)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM)
        engine_port = free_port(socket.SOCK_DGRAM)
        log_path = os.path.join(root, "dashboard.log")
        log = open(log_path, "w", encoding="utf-8")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard", "server.py"),
            "--host", "127.0.0.1", "--port", str(http_port),
            "--listen-port", str(listen_port), "--send-port", str(command_port),
            "--osc-target", "127.0.0.1", "--state-file", state_path,
            "--assets-dir", assets, "--patches-dir", patches,
            "--sim-no-engine", "--sim-audio-backend", "none",
            "--sim-engine-port-base", str(engine_port),
        ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
        base_url = f"http://127.0.0.1:{http_port}"
        try:
            wait_http(base_url, server)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1400, "height": 1000})
                page.set_default_timeout(10000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-patches")
                page.select_option("#editor-patch", "alpha")
                page.click("#editor-launch")
                page.wait_for_selector("#manifest-editor:not([hidden])")
                patch_text = page.locator("#tab-patches").inner_text().lower()
                check("Patch tab renders no facilitator terminology",
                      "facilitator" not in patch_text, patch_text)
                check("legacy group input is absent",
                      page.locator('[data-manifest-field="group"]').count() == 0)
                path = page.locator('[data-manifest-field="path"]').first
                check("path hint is unmistakably an example",
                      path.get_attribute("placeholder") ==
                      "e.g. instrument/marimba")
                dashboard = page.locator('[data-manifest-field="dashboard"]').first
                check("Dashboard promotion control reflects normalized payload",
                      dashboard.is_checked()
                      and "dashboard" in dashboard.locator("xpath=..").inner_text().lower())
                page.goto(base_url + "/facilitator")
                page.wait_for_selector('[data-live-param][data-param-path="gain"]')
                check("normalized promotion reaches the live Dashboard surface",
                      page.locator(
                          '[data-live-param][data-live-scope="all"]'
                          '[data-param-path="gain"]').count() == 1)
                check("browser reports no page errors", not errors, repr(errors))
                browser.close()
        finally:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)
            log.close()

    tracked = subprocess.run(
        ["git", "ls-files", "patches/*/bopos.patch.json"], cwd=REPO,
        check=True, capture_output=True, text=True).stdout.splitlines()
    tracked_groups = [path for path in tracked
                      if '"group"' in open(os.path.join(REPO, path),
                                           encoding="utf-8").read()]
    check("tracked demo manifests carry no presentation group", not tracked_groups,
          repr(tracked_groups))

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        return 1
    print("all 12 checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
