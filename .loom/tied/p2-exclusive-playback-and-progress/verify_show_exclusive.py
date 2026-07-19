#!/usr/bin/env python3
"""Real Dashboard + simfleet verification for exclusive Show playback (p2)."""

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
    (patch / "main.bin").write_bytes(b"show-exclusive-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [], "cues": [], "caps": [], "slots": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Show exclusive verifier",
        "current_show": "exclusive-set",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha", "seats": {}, "groups": {}, "next_group_id": 0,
    }
    show = {
        "schema": 1, "name": "exclusive-set",
        "items": [
            {"kind": "step", "uid": "aaaaaaaa", "alias": "A",
             "messages": [], "duration_s": 8.0, "play_count": 1,
             "then_actions": [{"type": "goto", "target_uid": "cccccccc"}],
             "forward_sync": False},
            {"kind": "step", "uid": "bbbbbbbb", "alias": "B",
             "messages": [], "duration_s": 8.0, "play_count": 1,
             "then_actions": [
                 {"type": "goto", "target_uid": "aaaaaaaa"},
                 {"type": "goto", "target_uid": "cccccccc"},
             ], "forward_sync": False},
            {"kind": "step", "uid": "cccccccc", "alias": "C",
             "messages": [], "duration_s": 8.0, "play_count": 1,
             "then_actions": [], "forward_sync": False},
        ],
    }
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows_dir / "exclusive-set.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-exclusive-") as root:
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

                row_a = '.show-step-row[data-show-step-row="aaaaaaaa"]'
                row_b = '.show-step-row[data-show-step-row="bbbbbbbb"]'
                row_c = '.show-step-row[data-show-step-row="cccccccc"]'
                page.wait_for_selector(row_a)

                def action(row, name):
                    page.locator(f'{row} [data-show-action="{name}"]').click()

                def active_count():
                    return page.locator(".show-step-row.active").count()

                # 1. A manual start replaces the prior playing step.
                action(row_a, "step_start")
                page.wait_for_selector(f"{row_a}.show-step-playing")
                action(row_b, "step_start")
                page.wait_for_selector(f"{row_b}.show-step-playing")
                page.wait_for_selector(f"{row_a}.show-step-stopped")
                check("manual start stops A and plays B",
                      "active" not in (page.locator(row_a).get_attribute("class") or "").split()
                      and "active" in (page.locator(row_b).get_attribute("class") or "").split())
                time.sleep(.55)
                check("manual exclusivity remains exactly one active row",
                      active_count() == 1, str(active_count()))

                # 2. Immediate then-action resolution hops exclusively A -> C.
                action(row_a, "step_start")
                page.wait_for_selector(f"{row_a}.show-step-playing")
                action(row_a, "step_trigger_next")
                page.wait_for_selector(f"{row_c}.show-step-playing")
                check("then-action hop leaves only C playing",
                      active_count() == 1
                      and "active" in (page.locator(row_c).get_attribute("class") or "").split(),
                      str(active_count()))

                # 3. Progress grows while playing and freezes while paused.
                action(row_a, "step_start")
                page.wait_for_selector(f"{row_a}.show-step-playing .show-step-progress")
                time.sleep(.55)
                first = float(page.locator(f"{row_a} .show-step-progress").evaluate(
                    "node => parseFloat(node.style.width)"))
                time.sleep(1.2)
                second = float(page.locator(f"{row_a} .show-step-progress").evaluate(
                    "node => parseFloat(node.style.width)"))
                check("progress fill grows", second > first, f"first={first}, second={second}")
                action(row_a, "step_pause")
                page.wait_for_selector(f"{row_a}.show-step-paused")
                time.sleep(.55)
                paused_first = float(page.locator(f"{row_a} .show-step-progress").evaluate(
                    "node => parseFloat(node.style.width)"))
                time.sleep(1.1)
                paused_second = float(page.locator(f"{row_a} .show-step-progress").evaluate(
                    "node => parseFloat(node.style.width)"))
                check("paused progress fill freezes",
                      abs(paused_second - paused_first) < .001,
                      f"first={paused_first}, second={paused_second}")

                # 4. Deterministic A -> C arms C; stopping clears it.
                check("goto target C has armed pulse class",
                      "show-step-armed" in (page.locator(row_c).get_attribute("class") or "").split())
                action(row_a, "step_stop")
                page.wait_for_selector(f"{row_a}.show-step-stopped")
                page.wait_for_function(
                    "() => !document.querySelector('.show-step-row.show-step-armed')")
                check("stopping active step clears armed class",
                      page.locator(".show-step-row.show-step-armed").count() == 0)

                # Multiple then-actions remain unresolved and arm no row.
                action(row_b, "step_start")
                page.wait_for_selector(f"{row_b}.show-step-playing")
                check("multiple then-actions arm nothing",
                      page.locator(".show-step-row.show-step-armed").count() == 0)
                action(row_b, "step_stop")

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

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
