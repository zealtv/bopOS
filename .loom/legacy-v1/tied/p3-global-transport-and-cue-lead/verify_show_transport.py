#!/usr/bin/env python3
"""Real Dashboard + simfleet verification for global Show transport and cue lead."""

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
    (patch / "main.bin").write_bytes(b"show-transport-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin", "params": [],
        "cues": [{"id": "cueA", "label": "Cue A"}], "caps": [], "slots": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Show transport verifier", "current_show": "legacy-set",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha", "seats": {}, "groups": {}, "next_group_id": 0,
    }
    show = {
        "schema": 1, "name": "legacy-set", "items": [
            {"kind": "step", "uid": "aaaaaaaa", "alias": "A",
             "messages": [{"uid": "aaaa0001", "alias": "cue A", "address": "/cue",
                           "args": [{"type": "s", "value": "cueA"}], "target": ["all"]}],
             "duration_s": 8.0, "play_count": 1,
             "then_actions": [{"type": "goto", "target_uid": "bbbbbbbb"}],
             "forward_sync": True},
            {"kind": "divider", "uid": "dddddddd"},
            {"kind": "step", "uid": "bbbbbbbb", "alias": "B", "messages": [],
             "duration_s": 8.0, "play_count": 1,
             "then_actions": [{"type": "goto", "target_uid": "aaaaaaaa"}],
             "forward_sync": False},
        ],
    }
    state_path = Path(root, "installation.json")
    show_path = shows_dir / "legacy-set.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    show_path.write_text(json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path, show_path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-transport-") as root:
        patches, assets, state_dir, manifest_path, state_path, show_path = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log_path = Path(root, "server.log")
        fleet_log_path = Path(root, "fleet.log")
        server_log = server_log_path.open("w", encoding="utf-8")
        fleet_log = fleet_log_path.open("w", encoding="utf-8")
        server = fleet = None

        def start_server():
            process = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard" / "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", str(state_path),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base_url,
            ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, process)
            return process

        try:
            server = start_server()
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
                page = browser.new_page(viewport={"width": 1180, "height": 900})
                page2 = browser.new_page(viewport={"width": 1180, "height": 900})
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page2.on("pageerror", lambda error: page_errors.append(str(error)))

                def handle_dialog(dialog):
                    dialog.accept("") if dialog.type == "prompt" else dialog.accept()

                page.on("dialog", handle_dialog)
                page2.on("dialog", handle_dialog)
                for client in (page, page2):
                    client.goto(base_url)
                    client.wait_for_selector("#ws-status.online")
                    client.click("#tab-button-show")
                    client.wait_for_selector('[data-show-step-row="aaaaaaaa"]')
                page.bring_to_front()

                row_a = '[data-show-step-row="aaaaaaaa"]'
                row_b = '[data-show-step-row="bbbbbbbb"]'
                actions = ".show-transport-actions"

                # 1. No focus falls back to the first step; progress is CSS-smooth.
                page.locator(f'{actions} [data-show-action="step_start"]').click()
                page.wait_for_selector(f"{row_a}.show-step-playing")
                check("global play with no focus starts first step",
                      page.locator(f"{row_a}.active").count() == 1)
                progress = page.locator(f"{row_a} .show-step-progress")
                progress_handle = progress.element_handle()
                before_width = progress.evaluate("el => el.getBoundingClientRect().width")
                animation = progress.evaluate("el => ({name:getComputedStyle(el).animationName,duration:getComputedStyle(el).animationDuration,state:getComputedStyle(el).animationPlayState,row:el.parentElement.getBoundingClientRect().width})")
                page.wait_for_timeout(650)
                after_width = progress_handle.evaluate(
                    "el => el.getBoundingClientRect().width")
                check("progress uses a continuous CSS animation",
                      animation["name"] == "show-step-progress-fill"
                      and progress_handle.evaluate("el => el.isConnected")
                      and after_width > before_width,
                      repr((animation, before_width, after_width)))
                page.locator(f'{actions} [data-show-action="step_stop"]').click()
                page.wait_for_selector(f"{row_a}.show-step-stopped")
                check("global stop stops the active step",
                      page.locator(".show-step-row.active").count() == 0)

                # 2. Focused B starts; the same global button pauses and resumes B.
                page.locator(row_b).click()
                page.locator(f'{actions} [data-show-action="step_start"]').click()
                page.wait_for_selector(f"{row_b}.show-step-playing")
                check("focused row makes global play start B",
                      page.locator(f"{row_a}.active").count() == 0
                      and page.locator(f"{row_b}.active").count() == 1)
                page.locator(f'{actions} [data-show-action="step_pause"]').click()
                page.wait_for_selector(f"{row_b}.show-step-paused")
                check("global play-pause pauses B",
                      page.locator(f"{row_b}.show-step-paused").count() == 1)
                page.wait_for_timeout(150)
                resume = page.locator(f'{actions} [data-show-action="step_resume"]').element_handle()
                page.wait_for_timeout(650)
                resume_stable = resume.evaluate("el => el.isConnected")
                resume.click()
                page.wait_for_selector(f"{row_b}.show-step-playing")
                check("paused Resume remains stable and immediately clickable",
                      resume_stable and page.locator(f"{row_b}.show-step-playing").count() == 1)

                # 3. B's immediate then-action goes to A.
                page.locator(f'{actions} [data-show-action="step_trigger_next"]').click()
                page.wait_for_selector(f"{row_a}.show-step-playing")
                check("global next resolves the active then-action now",
                      page.locator(f"{row_b}.active").count() == 0)

                # 4. Exclusive playback needs one Stop and no playing count.
                check("redundant stop-all and playing-count UI are absent",
                      page.locator("#show-stop-all, #show-playing-indicator").count() == 0
                      and page.locator(
                          f'{actions} [data-show-action="step_stop"]').count() == 1)
                grip_x = page.locator(f"{row_a} .show-drag-handle").bounding_box()["x"]
                divider_x = page.locator(
                    '[data-show-divider-row="dddddddd"] .show-divider-drag').bounding_box()["x"]
                check("divider grip is left-aligned with step grips",
                      abs(grip_x - divider_x) <= 1, repr((grip_x, divider_x)))
                page.locator(f'{actions} [data-show-action="step_stop"]').click()
                page.wait_for_function(
                    "() => document.querySelectorAll('.show-step-row.active').length === 0")

                # 5. Persisted lead broadcasts to page2 and schedules the cue near +1200 ms.
                page.fill("#show-cue-lead", "1200")
                page.locator("#show-cue-lead").press("Tab")
                page2.wait_for_function(
                    "() => document.querySelector('#show-cue-lead')?.value === '1200'")
                check("cue lead broadcasts to a second client",
                      page2.locator("#show-cue-lead").input_value() == "1200")
                page.locator(row_a).click()
                fleet_mark = len(fleet_log_path.read_text(encoding="utf-8"))
                before_ns = time.monotonic_ns()
                page.locator(f'{actions} [data-show-action="step_start"]').click()
                deadline = time.monotonic() + 4
                shared_ns = None
                while time.monotonic() < deadline:
                    match = re.search(r"cue-recv id=cueA .*raw='(\d+)'",
                                      fleet_log_path.read_text(encoding="utf-8")[fleet_mark:])
                    if match:
                        shared_ns = int(match.group(1))
                        break
                    time.sleep(.05)
                delta_ms = (shared_ns - before_ns) / 1_000_000 if shared_ns else None
                check("Show cue uses configured forward-sync lead",
                      delta_ms is not None and 800 <= delta_ms <= 1600,
                      repr(delta_ms))
                time.sleep(1.2)
                stop(server)
                server = start_server()
                page.reload()
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                page.wait_for_selector("#show-cue-lead")
                check("cue lead survives server restart",
                      page.locator("#show-cue-lead").input_value() == "1200",
                      page.locator("#show-cue-lead").input_value())

                # 6. Legacy flags loaded, inspector omits them, and a save drops them.
                page.locator(row_a).click()
                check("legacy show loads with no forward-sync control",
                      page.locator("#show-forward-sync").count() == 0
                      and page.locator(".show-sync-hint").count() == 0)
                page.fill("#show-step-alias", "A saved")
                page.locator("#show-step-alias").press("Tab")
                deadline = time.monotonic() + 3
                saved = None
                while time.monotonic() < deadline:
                    saved = json.loads(show_path.read_text(encoding="utf-8"))
                    if saved["items"][0].get("alias") == "A saved":
                        break
                    time.sleep(.05)
                serialized = json.dumps(saved)
                check("saving legacy show drops forward_sync keys",
                      "forward_sync" not in serialized, serialized)

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
