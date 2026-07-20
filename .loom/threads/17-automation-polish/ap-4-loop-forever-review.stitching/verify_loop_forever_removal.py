#!/usr/bin/env python3
"""Loop-forever checkbox is gone; legacy null play_count and play_again loop."""

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
    patches, assets = root / "patches", root / "assets"
    state_dir, shows = root / "fleet-state", root / "shows"
    patch = patches / "loops"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"loops")
    manifest = {"engine": "test", "entrypoint": "main.bin", "caps": [],
                "slots": [], "params": [
                    {"name": "gain", "type": "f", "min": 0, "max": 1,
                     "default": 0, "dashboard": True}], "cues": []}
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    uid = "02:53:49:4d:00:01"
    devices_path = root / "devices.csv"
    devices_path.write_text(f"mac,hostname,id\n{uid},sim0,0\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Loop removal verifier",
        "current_show": "loops", "params_patch": "loops",
        "fleet_patch": {"name": "loops", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "seats": {"0": {"id": 0, "name": "Zero", "positions": [[1, 1]],
                        "groups": [], "bound": uid, "patch": "loops",
                        "params": {"gain": 0}}},
        "groups": {}, "next_group_id": 0,
    }
    message = {"uid": "aaaa0001", "alias": "ping", "address": "/p/gain",
               "target": ["0"], "args": [{"type": "f", "value": .5}]}
    show = {"schema": 1, "name": "loops", "items": [
        {"kind": "step", "uid": "11111111", "alias": "legacy-forever",
         "messages": [message], "duration_s": 1, "play_count": None,
         "then_actions": [{"type": "stop"}]},
        {"kind": "step", "uid": "22222222", "alias": "again-loop",
         "messages": [dict(message, uid="aaaa0002")], "duration_s": 1,
         "play_count": 1, "then_actions": [{"type": "play_again"}]},
    ]}
    state_path = root / "installation.json"
    (shows / "loops.json").write_text(json.dumps(show, indent=2) + "\n",
                                      encoding="utf-8")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path, devices_path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-loop-removal-") as root:
        (patches, assets, state_dir, manifest_path, state_path,
         devices_path) = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        fleet_port = free_port(socket.SOCK_DGRAM)
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
                "--listen-port", str(listen_port), "--send-port", str(fleet_port),
                "--osc-target", "127.0.0.1", "--state-file", str(state_path),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base_url,
            ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, str(ROOT / "tools" / "simfleet.py"),
                "--devices", "1", "--devices-file", str(devices_path),
                "--target", "127.0.0.1", "--report-port", str(listen_port),
                "--cmd-port", str(fleet_port), "--hb-interval", "0.2",
                "--boot-secs", "0.2", "--state-dir", str(state_dir),
                "--manifest", str(manifest_path), "--patches-dir", str(patches),
                "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: errors.append(message.text)
                        if message.type == "error" else None)
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="11111111"]')
                check("legacy show with play_count null loads",
                      page.locator("[data-show-step-row]").count() == 2)

                page.locator('[data-show-step-row="11111111"]').click()
                page.wait_for_selector("#show-play-count")
                check("loop forever checkbox is gone",
                      page.locator("#show-play-forever").count() == 0)
                placeholder = page.locator("#show-play-count") \
                    .get_attribute("placeholder")
                check("legacy forever renders as the ∞ placeholder",
                      placeholder is not None and "legacy" in placeholder,
                      repr(placeholder))
                check("play count input is enabled",
                      page.locator("#show-play-count").is_enabled())

                # Legacy forever step still loops: playing well past 2x its
                # 1s duration.
                page.evaluate("() => ws.send('step_start', {uid: '11111111'})")
                page.wait_for_selector(
                    '[data-show-step-row="11111111"].active')
                time.sleep(2.6)
                check("legacy forever step is still playing after 2+ cycles",
                      page.locator('[data-show-step-row="11111111"].active')
                      .count() == 1)
                page.evaluate("() => ws.send('step_stop', {uid: '11111111'})")
                page.wait_for_function(
                    "() => !document.querySelector('[data-show-step-row=\"11111111\"].active')")
                check("transport stop halts the legacy forever step", True)

                # play_again self-loop: the ratified replacement idiom.
                page.evaluate("() => ws.send('step_start', {uid: '22222222'})")
                page.wait_for_selector(
                    '[data-show-step-row="22222222"].active')
                time.sleep(2.6)
                check("play_again step is still looping after 2+ cycles",
                      page.locator('[data-show-step-row="22222222"].active')
                      .count() == 1)
                page.evaluate("() => ws.send('step_stop', {uid: '22222222'})")
                page.wait_for_function(
                    "() => !document.querySelector('[data-show-step-row=\"22222222\"].active')")
                check("transport stop halts the play_again loop", True)

                # Typing a number converts a legacy forever step.
                page.locator('[data-show-step-row="11111111"]').click()
                page.wait_for_selector("#show-play-count")
                page.fill("#show-play-count", "3")
                page.dispatch_event("#show-play-count", "change")
                show_file = Path(root) / "shows" / "loops.json"
                deadline = time.monotonic() + 6
                converted = False
                while time.monotonic() < deadline and not converted:
                    doc = json.loads(show_file.read_text(encoding="utf-8"))
                    step = next(item for item in doc["items"]
                                if item["uid"] == "11111111")
                    converted = step["play_count"] == 3
                    if not converted:
                        time.sleep(.2)
                check("typing a count converts the legacy step", converted)

                check("browser emitted no console errors", not errors,
                      repr(errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

        if FAILURES:
            print("\nserver log tail:\n",
                  server_log_path.read_text(encoding="utf-8")[-4000:])
            print("\nfleet log tail:\n",
                  fleet_log_path.read_text(encoding="utf-8")[-4000:])

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
        raise SystemExit(1)
    print("\nAll loop-forever removal checks passed.")


if __name__ == "__main__":
    main()
