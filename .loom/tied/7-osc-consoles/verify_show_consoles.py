#!/usr/bin/env python3
"""Playwright + simfleet verification for the Show tab OSC consoles.

Covers: the outgoing console shows a triggered step's sends, the incoming
console shows LAN traffic from simfleet, wildcard filters narrow, `!`
negation excludes (hide /sync noise), pause freezes the view while traffic
continues, and clear resets the buffer which then refills.
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
    (patch / "main.bin").write_bytes(b"show-console-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": .4, "facilitator": True},
        ],
        "cues": [{"id": "snap", "label": "Snap"}], "caps": [], "slots": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Show console verifier",
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
            {"kind": "step", "uid": "11111111", "alias": "console probe",
             "messages": [
                 {"uid": "aaaa0001", "alias": "gain up", "address": "/p/gain",
                  "args": [{"type": "f", "value": 0.61}], "target": ["all"]},
             ],
             "duration_s": 0.3, "play_count": 1,
             "then_actions": [], "forward_sync": False},
        ],
    }
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows_dir / "opening-set.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-consoles-") as root:
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
                page = context.new_page()
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                page.wait_for_selector('.show-step-row[data-show-step-row="11111111"]')

                check("both consoles render collapsed under the show table",
                      page.locator('[data-console="out"]').count() == 1
                      and page.locator('[data-console="in"]').count() == 1
                      and not page.locator('[data-console="out"]')
                          .evaluate("panel => panel.open")
                      and not page.locator('[data-console="in"]')
                          .evaluate("panel => panel.open"))

                def log_text(kind):
                    return page.locator(
                        f'[data-console="{kind}"] [data-console-log]').inner_text()

                def fill_filter(kind, value):
                    box = page.locator(f'[data-console="{kind}"] [data-console-filter]')
                    box.fill(value)

                page.locator('[data-console="out"] summary').click()
                page.locator('[data-console="in"] summary').click()

                # Outgoing: the sync plane broadcasts continuously; the
                # triggered step adds its /all/p/gain send.
                page.wait_for_function(
                    """() => document.querySelector(
                         '[data-console="out"] [data-console-log]'
                       ).textContent.includes('/sync/ping')""")
                page.locator(
                    '.show-step-row[data-show-step-row="11111111"] '
                    '[data-show-action="step_start"]').click()
                page.wait_for_function(
                    """() => document.querySelector(
                         '[data-console="out"] [data-console-log]'
                       ).textContent.includes('/all/p/gain')""")
                check("outgoing console shows the triggered step's send with args",
                      "0.61" in log_text("out") and "-> 127.0.0.1" in log_text("out"),
                      log_text("out")[-400:])

                # Incoming: simfleet heartbeats + /sync/pong replies.
                page.wait_for_function(
                    """() => document.querySelector(
                         '[data-console="in"] [data-console-log]'
                       ).textContent.includes('/sync/pong')""")
                check("incoming console shows simfleet traffic with a source",
                      "<- 127.0.0.1" in log_text("in"), log_text("in")[-400:])

                # Wildcard filter narrows the outgoing view.
                fill_filter("out", "/all/p/*")
                page.wait_for_function(
                    """() => {
                        const lines = document.querySelector(
                          '[data-console="out"] [data-console-log]'
                        ).textContent.split('\\n').filter(Boolean);
                        return lines.length > 0
                          && lines.every(line => line.includes('/all/p/'));
                    }""")
                check("wildcard filter narrows to matching sends", True)

                # Negation hides /sync noise but keeps other incoming lines.
                fill_filter("in", "!/sync*")
                page.wait_for_function(
                    """() => {
                        const lines = document.querySelector(
                          '[data-console="in"] [data-console-log]'
                        ).textContent.split('\\n').filter(Boolean);
                        return lines.length > 0
                          && lines.every(line => !line.includes('/sync/'));
                    }""")
                check("negation filter hides the /sync noise", True)
                fill_filter("in", "")

                # Pause freezes the view while traffic continues.
                page.locator('[data-console="in"] [data-console-pause]').click()
                frozen = log_text("in")
                page.wait_for_timeout(1200)
                check("pause freezes the incoming view under live traffic",
                      log_text("in") == frozen)
                page.locator('[data-console="in"] [data-console-pause]').click()
                page.wait_for_function(
                    """(before) => document.querySelector(
                         '[data-console="in"] [data-console-log]'
                       ).textContent !== before""", arg=frozen)
                check("resume catches the view back up", True)

                # Clear empties the buffer; live traffic refills it.
                page.locator('[data-console="in"] [data-console-clear]').click()
                cleared = page.evaluate(
                    """() => document.querySelector(
                         '[data-console="in"] [data-console-log]').textContent""")
                check("clear empties the console", cleared == "", repr(cleared[-200:]))
                page.wait_for_function(
                    """() => document.querySelector(
                         '[data-console="in"] [data-console-log]'
                       ).textContent.length > 0""")
                check("cleared console refills from live traffic", True)

                check("browser emitted no page errors", not page_errors, repr(page_errors))
                page.screenshot(path=str(HERE / "consoles.png"), full_page=True)
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
