#!/usr/bin/env python3
"""Playwright verification for typed Monitor OSC sends."""

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
    for parent in Path(__file__).resolve().parents:
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
    while True:
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


def fixture(root):
    root = Path(root)
    patch = root / "patches" / "alpha"
    assets = root / "assets"
    state_dir = root / "sim-state"
    shows = root / "shows"
    for directory in (patch, assets, state_dir, shows):
        directory.mkdir(parents=True, exist_ok=True)
    (patch / "main.bin").write_bytes(b"monitor-send")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [], "cues": [], "caps": [], "slots": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    state_path = root / "installation.json"
    state_path.write_text(json.dumps({
        "schema": 1, "name": "Monitor send", "current_show": "monitor",
        "seats": {}, "groups": {}, "next_group_id": 0,
    }), encoding="utf-8")
    (shows / "monitor.json").write_text(json.dumps({
        "schema": 1, "name": "monitor", "items": [],
    }), encoding="utf-8")
    return patch.parent, assets, state_dir, manifest_path, state_path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-monitor-send-") as root:
        patches, assets, state_dir, manifest_path, state_path = fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log = Path(root, "server.log").open("w", encoding="utf-8")
        fleet_log = Path(root, "fleet.log").open("w", encoding="utf-8")
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
                page = browser.new_page(viewport={"width": 1100, "height": 850})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click('[data-monitor-tab="send"]')
                line = page.locator("[data-monitor-send-line]")
                feedback = page.locator("[data-monitor-send-feedback]")

                line.fill('/all/os/ping "monitor typed"')
                line.press("Enter")
                page.wait_for_function(
                    "() => document.querySelector('[data-monitor-send-feedback]').textContent === 'Sent.'")
                check("valid typed send succeeds", feedback.inner_text() == "Sent.")

                page.click('[data-monitor-tab="out"]')
                page.wait_for_function(
                    "() => document.querySelector('[data-console=\"out\"] "
                    "[data-console-log]').textContent.includes('monitor typed')")
                check("typed send echoes into Outgoing",
                      "/all/os/ping" in page.locator(
                          '[data-console="out"] [data-console-log]').inner_text())

                page.click('[data-monitor-tab="in"]')
                page.wait_for_function(
                    "() => document.querySelector('[data-console=\"in\"] "
                    "[data-console-log]').textContent.includes('monitor typed')")
                check("simfleet observed send and replied",
                      "/os/pong" in page.locator(
                          '[data-console="in"] [data-console-log]').inner_text())

                page.click('[data-monitor-tab="send"]')
                line.fill("not/an/address 1")
                line.press("Enter")
                check("malformed address fails inline",
                      "absolute path" in feedback.inner_text()
                      and "error" in (feedback.get_attribute("class") or ""))

                line.fill("/p/gain f:0.1234567")
                line.press("Enter")
                check("over-precision float fails inline",
                      "more than 6 significant figures" in feedback.inner_text())

                line.fill("")
                line.press("ArrowUp")
                check("up-arrow recalls session history",
                      line.input_value() == '/all/os/ping "monitor typed"')
                check("no browser errors", not errors, "; ".join(errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

        if FAILURES:
            print(f"\n{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
            return 1
        print("\n7/7 Monitor Send checks passed")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
