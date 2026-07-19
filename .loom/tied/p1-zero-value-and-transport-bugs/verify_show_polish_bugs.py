#!/usr/bin/env python3
"""Real Dashboard + simfleet verification for Show polish bug fixes (p1)."""

import json
import random
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


def make_fixture(root):
    patches = Path(root, "patches")
    assets = Path(root, "assets")
    state_dir = Path(root, "sim-state")
    shows_dir = Path(root, "shows")
    patch = patches / "alpha"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows_dir.mkdir()
    (patch / "main.bin").write_bytes(b"show-polish-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": 0.4, "facilitator": True},
        ],
        "cues": [], "caps": [], "slots": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Show polish verifier",
        "current_show": "opening-set",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "seats": {
            "0": {"id": 0, "name": "Front", "positions": [[1, 1]],
                  "groups": [], "bound": None, "patch": "alpha", "params": {}},
        },
        "groups": {}, "next_group_id": 0,
    }
    show = {
        "schema": 1, "name": "opening-set",
        "items": [
            {"kind": "step", "uid": "11111111", "alias": "intro drone",
             "messages": [
                 {"uid": "aaaa0001", "alias": "gain up", "address": "/p/gain",
                  "args": [{"type": "f", "value": 0.6}], "target": ["all"]},
             ],
             "duration_s": 60.0, "play_count": 1,
             "then_actions": [{"type": "stop"}], "forward_sync": False},
        ],
    }
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows_dir / "opening-set.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-polish-") as root:
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
                page = browser.new_page(viewport={"width": 1100, "height": 900})
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def handle_dialog(dialog):
                    if dialog.type == "prompt":
                        dialog.accept("")
                    else:
                        dialog.accept()

                page.on("dialog", handle_dialog)
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                row = '.show-step-row[data-show-step-row="11111111"]'
                page.wait_for_selector(row)

                # 1. A stored numeric zero must survive the edit round-trip.
                page.click('[data-show-message-focus="aaaa0001"]')
                page.wait_for_selector("#show-param-value")
                page.locator("#show-param-value").fill("0")
                page.locator("#show-param-value").press("Tab")
                page.wait_for_function(
                    "() => document.querySelector('#show-wire-preview')?.textContent.includes('f:0')"
                    " && document.querySelector('#show-param-value')?.value === '0'")
                check("zero value sticks in preview and re-rendered input",
                      "f:0" in page.locator("#show-wire-preview").inner_text()
                      and page.locator("#show-param-value").input_value() == "0")

                # 2. The second click must hit the optimistically rendered Stop button.
                first_transport = f"{row} .show-step-transport .show-icon-button:first-child"
                page.locator(first_transport).click()
                page.locator(first_transport).click()
                page.wait_for_function(
                    "() => document.querySelector('#show-playing-indicator')"
                    "?.textContent.trim() === '0 playing'")
                stopped_now = page.locator("#show-playing-indicator").inner_text().strip()
                time.sleep(1)
                stopped_later = page.locator("#show-playing-indicator").inner_text().strip()
                check("rapid play then stop remains stopped",
                      stopped_now == "0 playing" and stopped_later == "0 playing",
                      f"now={stopped_now!r}, later={stopped_later!r}")

                # 3. The local DOM changes before a playback broadcast is required.
                page.locator(first_transport).click()
                optimistic_action = page.locator(first_transport).get_attribute(
                    "data-show-action")
                check("play click optimistically renders Stop",
                      optimistic_action == "step_stop", repr(optimistic_action))
                page.locator(first_transport).click()
                page.wait_for_function(
                    "() => document.querySelector('#show-playing-indicator')"
                    "?.textContent.trim() === '0 playing'")

                # 4. Reserving three transport buttons keeps the alias column fixed.
                page.evaluate("window.scrollTo(0, 0)")
                stopped_x = page.locator(f"{row} .show-step-alias").bounding_box()["x"]
                page.locator(first_transport).click()
                page.wait_for_selector(f"{row}.show-step-playing")
                page.evaluate("window.scrollTo(0, 0)")
                playing_x = page.locator(f"{row} .show-step-alias").bounding_box()["x"]
                check("step title x is stable", stopped_x == playing_x,
                      f"stopped={stopped_x}, playing={playing_x}")
                page.locator(first_transport).click()
                page.wait_for_function(
                    "() => document.querySelector('#show-playing-indicator')"
                    "?.textContent.trim() === '0 playing'")

                # 5. The playing row exposes a visibly wider, distinct next glyph.
                page.locator(first_transport).click()
                next_button = page.locator(f'{row} [data-show-action="step_trigger_next"]')
                next_button.wait_for()
                glyph = next_button.locator(".show-glyph-next")
                glyph_box = glyph.bounding_box()
                glyph_classes = glyph.get_attribute("class") or ""
                check("next control has a distinct legible glyph",
                      next_button.count() == 1 and glyph_box["width"] >= 10
                      and "show-glyph-next" in glyph_classes
                      and "show-glyph-play" not in glyph_classes,
                      f"classes={glyph_classes!r}, width={glyph_box['width']}")
                page.locator(first_transport).click()

                # 6. Console exceptions invalidate the UI checks above.
                check("browser emitted no page errors", not page_errors,
                      repr(page_errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

        if FAILURES:
            print("\nserver log tail:\n", server_log_path.read_text(encoding="utf-8")[-4000:])
            print("\nfleet log tail:\n", fleet_log_path.read_text(encoding="utf-8")[-4000:])

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
