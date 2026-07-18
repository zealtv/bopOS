#!/usr/bin/env python3
"""Playwright verification for the compact (Ableton/QLab density) Show rows.

Asserts the 5b redesign: a seeded 20-step show fits a 768x1024 viewport
without scrolling, transport is driven by compact icon buttons, and message
pill colours hash stably from aliases (same alias => same colour, different
alias => different colour, unaliased => neutral).
"""

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


def seeded_steps():
    """20 steps + a divider; aliases arranged to test pill colour hashing."""
    items = []
    for index in range(20):
        uid = f"{index + 1:08d}"
        messages = []
        if index == 0:
            messages = [
                {"uid": "aaaa0001", "alias": "gain up", "address": "/p/gain",
                 "args": [{"type": "f", "value": 0.6}], "target": "all"},
                {"uid": "aaaa0002", "alias": None, "address": "/cue",
                 "args": [{"type": "s", "value": "snap"}], "target": "all"},
            ]
        elif index == 1:
            messages = [
                {"uid": "bbbb0001", "alias": "sparkle", "address": "/p/fx/sparkle",
                 "args": [{"type": "f", "value": 1.0}], "target": "0"},
            ]
        elif index == 5:
            messages = [
                {"uid": "eeee0001", "alias": "gain up", "address": "/p/gain",
                 "args": [{"type": "f", "value": 0.2}], "target": "all"},
            ]
        elif index % 3 == 0:
            messages = [
                {"uid": f"cccc{index:04d}", "alias": None, "address": "/p/gain",
                 "args": [{"type": "f", "value": 0.2}], "target": "all"},
            ]
        items.append({
            "kind": "step", "uid": uid,
            "alias": "intro drone" if index == 0 else f"step {index}",
            "messages": messages,
            "duration_s": 90.0, "play_count": 1,
            "then_actions": [{"type": "next_step"}], "forward_sync": False,
        })
        if index == 9:
            items.append({"kind": "divider", "uid": "dddd0001"})
    return items


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
    (patch / "main.bin").write_bytes(b"show-compact-verifier")
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
        "schema": 1, "name": "Show compact verifier",
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
    show = {"schema": 1, "name": "opening-set", "items": seeded_steps()}
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows_dir / "opening-set.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


def pill_colour(page, uid):
    return page.evaluate(
        """(uid) => {
          const pill = document.querySelector(`[data-show-message-focus="${uid}"]`);
          const style = getComputedStyle(pill);
          return `${style.borderColor} ${style.backgroundColor}`;
        }""", uid)


def main(screenshot_only=None):
    with tempfile.TemporaryDirectory(prefix="bopos-show-compact-") as root:
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
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                page.wait_for_selector('.show-step-row[data-show-step-row="00000001"]')

                if screenshot_only:
                    page.evaluate("window.scrollTo(0,0)")
                    page.screenshot(path=screenshot_only, full_page=False)
                    browser.close()
                    print(f"saved {screenshot_only}")
                    return 0

                check("all 20 rows and the divider render",
                      page.locator(".show-step-row").count() == 20
                      and page.locator(".show-divider-row").count() == 1)

                metrics = page.evaluate("""() => {
                    const rows = [...document.querySelectorAll('.show-step-row')];
                    const container = document.querySelector('.show-rows');
                    return {
                      maxRow: Math.max(...rows.map(row => row.getBoundingClientRect().height)),
                      bottom: container.getBoundingClientRect().bottom,
                      scrollY: window.scrollY,
                    };
                }""")
                check("every row fits the compact height budget (<= 40 px)",
                      metrics["maxRow"] <= 40, json.dumps(metrics))
                check("20 steps + divider fit the 768x1024 viewport unscrolled",
                      metrics["scrollY"] == 0 and metrics["bottom"] <= 1024,
                      json.dumps(metrics))

                play = page.locator(
                    '.show-step-row[data-show-step-row="00000001"] '
                    '[data-show-action="step_start"]')
                check("stopped row exposes a play icon button (no text label)",
                      play.count() == 1
                      and play.inner_text().strip() == ""
                      and play.locator(".show-glyph").count() == 1,
                      play.inner_text())
                target = page.evaluate("""() => {
                    const button = document.querySelector(
                      '.show-step-row[data-show-step-row="00000001"] [data-show-action="step_start"]');
                    const style = getComputedStyle(button, '::after');
                    const box = button.getBoundingClientRect();
                    const pad = parseFloat(style.top) || 0;
                    return {w: box.width - 2 * pad, h: box.height - 2 * pad};
                }""")
                check("icon button hit target is touch-sized (>= 40 px)",
                      target["w"] >= 40 and target["h"] >= 40, json.dumps(target))

                play.click()
                page.wait_for_function("""
                    () => window.__bopSentMessages.some(message =>
                      message.type === 'step_start' && message.data?.uid === '00000001')
                """)
                page.wait_for_selector(
                    '.show-step-row[data-show-step-row="00000001"].show-step-playing')
                row = page.locator('.show-step-row[data-show-step-row="00000001"]')
                check("playing row swaps to stop/pause/next icons and shows countdown",
                      row.locator('[data-show-action="step_stop"]').count() == 1
                      and row.locator('[data-show-action="step_pause"]').count() == 1
                      and row.locator('[data-show-action="step_trigger_next"]').count() == 1
                      and row.locator(".show-remaining").count() == 1,
                      row.inner_text())

                row.locator('[data-show-action="step_stop"]').click()
                page.wait_for_function("""
                    () => window.__bopSentMessages.some(message =>
                      message.type === 'step_stop' && message.data?.uid === '00000001')
                """)
                page.wait_for_selector(
                    '.show-step-row[data-show-step-row="00000001"].show-step-stopped')
                check("stop icon returns the row to stopped",
                      row.locator('[data-show-action="step_start"]').count() == 1)

                gain_a = pill_colour(page, "aaaa0001")
                gain_b = pill_colour(page, "eeee0001")
                sparkle = pill_colour(page, "bbbb0001")
                neutral = pill_colour(page, "aaaa0002")
                check("same alias hashes to the same pill colour across steps",
                      gain_a == gain_b, f"{gain_a} vs {gain_b}")
                check("different aliases hash to different pill colours",
                      gain_a != sparkle, f"{gain_a} vs {sparkle}")
                check("unaliased pills stay neutral",
                      neutral != gain_a and neutral != sparkle, neutral)

                page.locator('[data-show-message-focus="aaaa0001"]').click()
                check("pill click still focuses the message",
                      page.locator('[data-show-message-focus="aaaa0001"].focused').count() == 1
                      and page.locator(".show-inspector-shell").inner_text()
                          .lower().startswith("message inspector"))

                check("browser emitted no page errors", not page_errors, repr(page_errors))
                page.evaluate("window.scrollTo(0,0)")
                page.screenshot(path=str(HERE / "after-compact.png"), full_page=False)
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
