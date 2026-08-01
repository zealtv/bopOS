#!/usr/bin/env python3
"""Real dashboard + simfleet browser verification for Monitor's base frame."""

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
    root = Path(root)
    patches = root / "patches"
    assets = root / "assets"
    state_dir = root / "sim-state"
    shows = root / "shows"
    patch = patches / "alpha"
    for directory in (patch, assets, state_dir, shows):
        directory.mkdir(parents=True, exist_ok=True)
    (patch / "main.bin").write_bytes(b"monitor-frame")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [{"name": "gain", "type": "f", "min": 0, "max": 1,
                    "default": .4, "dashboard": True}],
        "cues": [], "caps": [], "slots": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    state = {
        "schema": 1, "name": "Monitor verifier", "current_show": "monitor",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "seats": {"0": {"id": 0, "name": "Front", "positions": [[1, 1]],
                        "groups": [], "bound": None, "patch": "alpha",
                        "params": {}}},
        "groups": {}, "next_group_id": 0,
    }
    show = {
        "schema": 1, "name": "monitor",
        "items": [{"kind": "step", "uid": "11111111", "alias": "Monitor",
                   "messages": [], "duration_s": 1, "play_count": 1,
                   "then_actions": [], "forward_sync": False}],
    }
    state_path = root / "installation.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows / "monitor.json").write_text(json.dumps(show), encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-monitor-frame-") as root:
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
                context = browser.new_context(viewport={"width": 1100, "height": 850})
                page = context.new_page()
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.wait_for_selector("#monitor-dock")

                check("one app-level Monitor frame is mounted",
                      page.locator("#monitor-dock").count() == 1
                      and page.locator("#show-root #monitor-dock").count() == 0)
                check("Monitor defaults collapsed with one collapse control",
                      "is-collapsed" in page.locator("#monitor-dock")
                          .get_attribute("class")
                      and page.locator("[data-monitor-collapse]").count() == 1)

                page.click("[data-monitor-collapse]")
                page.wait_for_function(
                    "() => !document.querySelector('#monitor-dock').classList.contains('is-collapsed')")
                check("one active traffic panel is visible",
                      page.locator(".monitor-panel:not([hidden])").count() == 1)

                page.wait_for_function(
                    "() => document.querySelector('[data-console=\"out\"] "
                    "[data-console-log]').textContent.includes('/sync/ping')")
                out_text = page.locator(
                    '[data-console="out"] [data-console-log]').inner_text()
                check("Outgoing retains the live OSC stream", "/sync/ping" in out_text)

                page.click('[data-monitor-tab="in"]')
                page.wait_for_function(
                    "() => document.querySelector('[data-console=\"in\"] "
                    "[data-console-log]').textContent.includes('/sync/pong')")
                in_text = page.locator(
                    '[data-console="in"] [data-console-log]').inner_text()
                check("Incoming retains the live OSC stream",
                      "/sync/pong" in in_text and "<- 127.0.0.1" in in_text)

                page.locator(
                    '[data-console="in"] [data-console-filter]').fill("/sync/pong")
                filtered_in = page.locator(
                    '[data-console="in"] [data-console-log]').inner_text()
                page.click('[data-monitor-tab="out"]')
                check("filters remain independent per stream",
                      "/sync/pong" in filtered_in
                      and page.locator(
                          '[data-console="out"] [data-console-filter]').input_value() == "")

                page.evaluate(
                    "() => { window.__monitorRow = document.querySelector('.show-step-row'); }")
                time.sleep(.5)
                check("traffic does not replace Show row DOM",
                      page.evaluate(
                          "() => window.__monitorRow === document.querySelector('.show-step-row')"))

                page.click("#tab-button-devices")
                check("Monitor remains mounted across app tabs",
                      page.locator("#monitor-dock").is_visible())

                page.click("[data-monitor-collapse]")
                page.reload()
                page.wait_for_selector("#monitor-dock")
                check("collapse state persists across reload",
                      "is-collapsed" in page.locator("#monitor-dock")
                          .get_attribute("class"))

                check("no browser errors", not page_errors, "; ".join(page_errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

        if FAILURES:
            print(f"\n{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
            print(server_log_path.read_text(encoding="utf-8")[-3000:])
            return 1
        print("\n10/10 Monitor frame checks passed")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
