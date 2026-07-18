#!/usr/bin/env python3
"""Real Dashboard + simfleet Playwright verification for the Show inspector."""

import json
import random
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "tools" / "simfleet.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
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


def wait_http(url, process):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before serving HTTP")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not serve HTTP")


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def log_contains(path, pattern):
    try:
        return re.search(pattern, path.read_text(encoding="utf-8")) is not None
    except OSError:
        return False


def wait_log(path, pattern, timeout=6):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if log_contains(path, pattern):
            return True
        time.sleep(.1)
    return False


def make_fixture(root):
    patches = Path(root, "patches")
    assets = Path(root, "assets")
    state_dir = Path(root, "sim-state")
    patch = patches / "alpha"
    shows_dir = Path(root, "shows")
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows_dir.mkdir()
    (patch / "main.bin").write_bytes(b"show-inspector-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"path": ["fx"], "name": "sparkle", "type": "f",
             "min": 0, "max": 1, "default": 0.2, "facilitator": True},
            {"path": ["voice", "env"], "name": "gate", "type": "i",
             "min": 0, "max": 1, "default": 0, "facilitator": True},
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": 0.4, "facilitator": True},
        ],
        "cues": [
            {"id": "snap", "label": "Snap"},
            {"id": "blackout", "label": "Blackout"},
        ],
        "caps": [], "slots": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Show inspector verifier",
        "current_show": "opening-set",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "seats": {
            "0": {"id": 0, "name": "Front", "positions": [[1, 1]],
                  "groups": [0], "bound": None, "patch": "alpha", "params": {}},
            "1": {"id": 1, "name": "Back", "positions": [[2, 1]],
                  "groups": [], "bound": None, "patch": "alpha", "params": {}},
        },
        "groups": {"0": {"id": 0, "name": "Main"}},
        "next_group_id": 1,
    }
    show = {
        "schema": 1, "name": "opening-set",
        "items": [
            {"kind": "step", "uid": "11111111", "alias": "intro drone",
             "messages": [
                 {"uid": "aaaa0001", "alias": "gain up", "address": "/p/gain",
                  "args": [{"type": "f", "value": 0.6}], "target": "all"},
                 {"uid": "aaaa0002", "alias": None, "address": "/cue",
                  "args": [{"type": "s", "value": "snap"}], "target": "all"},
             ],
             "duration_s": 60.0, "play_count": 1,
             "then_actions": [{"type": "next_step"}], "forward_sync": False},
            {"kind": "step", "uid": "22222222", "alias": "landing",
             "messages": [], "duration_s": 12.0, "play_count": 3,
             "then_actions": [{"type": "stop"}], "forward_sync": False},
        ],
    }
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows_dir / "opening-set.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-inspector-") as root:
        patches, assets, state_dir, manifest_path, state_path = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log_path = Path(root, "server.log")
        fleet_log_path = Path(root, "fleet.log")
        server_log = server_log_path.open("w", encoding="utf-8")
        fleet_log = fleet_log_path.open("w", encoding="utf-8")
        server = fleet = None
        try:
            server = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard" / "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", str(state_path),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base_url,
            ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, str(ROOT / "tools" / "simfleet.py"),
                "--devices", "1", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.2", "--boot-secs", "0.2",
                "--state-dir", str(state_dir), "--manifest", str(manifest_path),
                "--patches-dir", str(patches), "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 900, "height": 1100}, has_touch=True,
                    is_mobile=True, device_scale_factor=1,
                )
                page = context.new_page()
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept(""))

                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                page.wait_for_selector('.show-step-row[data-show-step-row="11111111"]')

                page.locator('.show-step-row[data-show-step-row="11111111"]').click()
                page.fill("#show-step-alias", "edited intro")
                page.locator("#show-step-alias").press("Tab")
                page.locator('[data-duration-part="h"]').fill("1")
                page.locator('[data-duration-part="h"]').press("Tab")
                page.locator('[data-duration-part="m"]').fill("2")
                page.locator('[data-duration-part="m"]').press("Tab")
                page.locator('[data-duration-part="s"]').fill("3")
                page.locator('[data-duration-part="s"]').press("Tab")
                page.fill("#show-play-count", "2")
                page.locator("#show-play-count").press("Tab")
                page.click("[data-add-then-action]")
                page.wait_for_selector('.show-then-row:nth-child(2) [data-then-type="1"]')
                page.select_option('[data-then-type="1"]', "goto")
                page.wait_for_selector('[data-then-goto="1"]')
                page.select_option('[data-then-goto="1"]', "22222222")
                page.click("#show-forward-sync")
                page.wait_for_selector(".show-sync-hint")

                page.click("#show-play-forever")
                page.fill('[data-duration-part="h"]', "0")
                page.fill('[data-duration-part="m"]', "0")
                page.fill('[data-duration-part="s"]', "0")
                page.locator('[data-duration-part="s"]').press("Tab")
                page.wait_for_selector(".show-field-error")
                check("duration-zero validation is surfaced near the field",
                      page.locator(".show-field-error").inner_text().strip()
                      == "Duration 0 needs a finite play count.")
                page.click("#show-play-forever")
                page.fill("#show-play-count", "2")
                page.locator("#show-play-count").press("Tab")
                page.fill('[data-duration-part="h"]', "1")
                page.fill('[data-duration-part="m"]', "2")
                page.fill('[data-duration-part="s"]', "3")
                page.locator('[data-duration-part="s"]').press("Tab")

                page.reload()
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                page.wait_for_selector('.show-step-row[data-show-step-row="11111111"]')
                # 5b compact rows: the row shows alias + terse duration only;
                # play count and then-actions moved to the inspector.
                row_text = page.locator('.show-step-row[data-show-step-row="11111111"]').inner_text().lower()
                page.locator('.show-step-row[data-show-step-row="11111111"]').click()
                page.wait_for_selector('[data-then-goto="1"]')
                check("step inspector edits persisted across reload",
                      "edited intro" in row_text and "1h2m3" in row_text
                      and page.locator("#show-play-count").input_value() == "2"
                      and page.locator('[data-then-goto="1"]').input_value() == "22222222",
                      row_text)
                check("forward-sync persisted and skew hint renders",
                      page.locator("#show-forward-sync").is_checked()
                      and page.locator(".show-sync-hint").is_visible())

                page.locator('[data-show-message-focus="aaaa0001"]').click()
                page.wait_for_selector("#show-param-picker")
                page.select_option("#show-param-picker", "fx/sparkle")
                page.wait_for_function("""
                    () => document.querySelector('#show-wire-preview')?.textContent.includes('/p/fx/sparkle')
                """)
                page.fill("#show-param-value", "0.72")
                page.locator("#show-param-value").press("Tab")
                page.wait_for_function("""
                    () => document.querySelector('#show-wire-preview')?.textContent
                      === '/p/fx/sparkle [f:0.72] -> all'
                """)
                check("param builder preview is exact",
                      page.locator("#show-wire-preview").inner_text()
                      == "/p/fx/sparkle [f:0.72] -> all")

                page.locator('[data-show-message-focus="aaaa0002"]').click()
                page.wait_for_selector("#show-cue-picker")
                page.select_option("#show-cue-picker", "blackout")
                page.wait_for_function("""
                    () => document.querySelector('#show-wire-preview')?.textContent
                      === '/cue [s:blackout] -> all'
                """)
                check("cue builder preview is exact and target is greyed",
                      page.locator("#show-wire-preview").inner_text()
                      == "/cue [s:blackout] -> all"
                      # 5c: the target dropdown became a chip picker; greyed
                      # now means the disabled picker section.
                      and page.locator(
                          ".show-target-picker.show-disabled-field "
                          '[data-target-toggle="all"]').is_disabled())

                page.locator('.show-step-row[data-show-step-row="11111111"]').click()
                before_pills = page.locator(
                    '.show-step-row[data-show-step-row="11111111"] .show-message-pill').count()
                page.click("#show-add-message")
                page.wait_for_function(
                    "(count) => document.querySelectorAll('[data-show-message-focus]').length > count",
                    arg=before_pills)
                check("add-message creates and focuses the new pill",
                      page.locator(".show-message-pill.focused").count() == 1
                      and page.locator(".show-inspector-shell").inner_text().lower().startswith("message inspector"))

                page.locator(
                    '.show-step-row[data-show-step-row="11111111"] '
                    '[data-show-action="step_start"]').click()
                check("simfleet received built param message",
                      wait_log(fleet_log_path, r"p/fx/sparkle=0\.72\b"))
                check("simfleet received built cue message",
                      wait_log(fleet_log_path, r"cue blackout fired"))
                check("browser emitted no page errors", not page_errors, repr(page_errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

        if FAILURES:
            print("\nserver log tail:\n", server_log_path.read_text(encoding="utf-8")[-4000:])
            print("\nfleet log tail:\n", fleet_log_path.read_text(encoding="utf-8")[-4000:])

    failed = len(FAILURES)
    print(f"\n{failed} failure(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
