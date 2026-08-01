#!/usr/bin/env python3
"""Real Dashboard + simfleet Playwright verification for the Show tab UI."""

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
HERE = Path(__file__).resolve().parent
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
    patch = patches / "alpha"
    shows_dir = Path(root, "shows")
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows_dir.mkdir()
    (patch / "main.bin").write_bytes(b"show-tab-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"path": ["fx"], "name": "sparkle", "type": "f",
             "min": 0, "max": 1, "default": 0, "facilitator": True},
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": .4, "facilitator": True},
        ],
        "cues": [{"id": "snap", "label": "Snap"}], "caps": [], "slots": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Show verifier",
        "current_show": "opening-set",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "seats": {
            "0": {"id": 0, "name": "Front", "positions": [[1, 1]],
                  "groups": [], "bound": None, "patch": "alpha", "params": {}},
        },
        "groups": {},
        "next_group_id": 0,
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
            {"kind": "step", "uid": "22222222", "alias": None,
             "messages": [
                 {"uid": "bbbb0001", "alias": "sparkle", "address": "/p/fx/sparkle",
                  "args": [{"type": "f", "value": 1.0}], "target": "0"},
             ],
             "duration_s": 12.0, "play_count": 3,
             "then_actions": [{"type": "stop"}], "forward_sync": False},
            {"kind": "divider", "uid": "dddd0001"},
            {"kind": "step", "uid": "33333333", "alias": "second section",
             "messages": [
                 {"uid": "cccc0001", "alias": None, "address": "/p/gain",
                  "args": [{"type": "f", "value": 0.2}], "target": "all"},
             ],
             "duration_s": 8.0, "play_count": 1,
             "then_actions": [{"type": "play_again"}], "forward_sync": False},
            {"kind": "step", "uid": "44444444", "alias": "outro",
             "messages": [],
             "duration_s": 5.0, "play_count": 1,
             "then_actions": [], "forward_sync": False},
        ],
    }
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows_dir / "opening-set.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-tab-") as root:
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
                    viewport={"width": 768, "height": 1024}, has_touch=True,
                    is_mobile=True, device_scale_factor=1,
                )
                context.add_init_script("""
                    (() => {
                      window.__bopSentMessages = [];
                      const original = WebSocket.prototype.send;
                      WebSocket.prototype.send = function(payload) {
                        try { window.__bopSentMessages.push(JSON.parse(payload)); }
                        catch (_error) {}
                        return original.call(this, payload);
                      };
                    })();
                """)
                page = context.new_page()
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def on_dialog(dialog):
                    if dialog.type == "prompt":
                        dialog.accept("")
                    else:
                        dialog.accept()

                page.on("dialog", on_dialog)
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function("() => window.show !== undefined || document.querySelector('#show-root')")

                tab_text = page.locator("#tab-button-show").inner_text().strip().lower()
                check("tab button says Show", tab_text == "show", tab_text)
                page.evaluate("window.scrollTo(0,0)")
                page.click("#tab-button-show")
                check("Show panel is reachable",
                      page.locator("#tab-show").is_visible()
                      and page.locator("#tab-sequencer").count() == 0)
                page.wait_for_selector('.show-step-row[data-show-step-row="11111111"]')
                check("steps, divider, and message pills render from seeded show",
                      page.locator(".show-step-row").count() == 4
                      and page.locator(".show-divider-row").count() == 1
                      and page.locator(".show-message-pill").count() >= 4
                      and "intro drone" in page.locator(".show-rows").inner_text().lower())

                page.evaluate("window.scrollTo(0,0)")
                page.locator(
                    '.show-step-row[data-show-step-row="11111111"] '
                    '[data-show-action="step_start"]').click()
                page.wait_for_function("""
                    () => window.__bopSentMessages.some(message =>
                      message.type === 'step_start' && message.data?.uid === '11111111')
                """)
                page.wait_for_selector('.show-step-row[data-show-step-row="11111111"].show-step-playing')
                # 5b compact rows: the playing state is shown structurally
                # (icon swap + countdown), not as row text.
                playing_row = page.locator('.show-step-row[data-show-step-row="11111111"]')
                check("trigger click sends step_start and row reflects playing playback",
                      playing_row.locator(".show-remaining").count() == 1
                      and playing_row.locator('[data-show-action="step_stop"]').count() == 1
                      and playing_row.locator('[data-show-action="step_pause"]').count() == 1,
                      playing_row.inner_text())

                page.evaluate("window.scrollTo(0,0)")
                page.click("#show-stop-all")
                page.wait_for_function("""
                    () => window.__bopSentMessages.some(message =>
                      message.type === 'stop_all_steps')
                """)
                page.wait_for_selector('.show-step-row[data-show-step-row="11111111"].show-step-stopped')
                check("stop-all stops the playing step",
                      page.locator("#show-playing-indicator").inner_text().strip().lower()
                      == "0 playing")

                page.locator('.show-step-row[data-show-step-row="22222222"]').click()
                check("clicking a step applies the single focus highlight",
                      page.locator('.show-step-row[data-show-step-row="22222222"].focused').count() == 1
                      and page.locator(".show-message-pill.focused").count() == 0)
                page.locator('[data-show-message-focus="aaaa0001"]').click()
                check("clicking a message pill applies the focus highlight",
                      page.locator('[data-show-message-focus="aaaa0001"].focused').count() == 1
                      and page.locator(".show-step-row.focused").count() == 0)
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
