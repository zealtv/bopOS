#!/usr/bin/env python3
"""Playwright + 3-device simfleet verification for 5c multi-target messages.

Proves: the chip picker builds a selector-list target (seats + group mix),
the engine fans the sends out per selector (two seats reached, the third
not; then the group member too), a legacy single-string target still loads,
and saves normalize targets to lists.
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

SIM_MACS = {1: "02:53:49:4d:00:01", 2: "02:53:49:4d:00:02", 3: "02:53:49:4d:00:03"}


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
    (patch / "main.bin").write_bytes(b"show-target-verifier")
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

    def seat(seat_id, groups):
        return {"id": seat_id, "name": f"Seat {seat_id}",
                "positions": [[float(seat_id), 1.0]], "groups": groups,
                "bound": SIM_MACS[seat_id], "patch": "alpha", "params": {}}

    state = {
        "schema": 1, "name": "Show target verifier",
        "current_show": "opening-set",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "seats": {"1": seat(1, []), "2": seat(2, [9]), "3": seat(3, [])},
        "groups": {"9": {"id": 9, "name": "Rear"}},
        "next_group_id": 10,
    }
    show = {
        "schema": 1, "name": "opening-set",
        "items": [
            {"kind": "step", "uid": "11111111", "alias": "sweep",
             "messages": [
                 # Legacy single-string target on disk: must load + normalize.
                 {"uid": "aaaa0001", "alias": "gain up", "address": "/p/gain",
                  "args": [{"type": "f", "value": 0.77}], "target": "all"},
             ],
             "duration_s": 1.0, "play_count": 1,
             "then_actions": [], "forward_sync": False},
        ],
    }
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    show_path = shows_dir / "opening-set.json"
    show_path.write_text(json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path, show_path


def wait_for(predicate, timeout=10, label="condition"):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.1)
    return False


def device_lines(log_path, mark, device):
    # Log shape: "HH:MM:SS <hostname> id=<device_id> <message>" -- hostnames
    # follow the seat name after assignment, so match on the id token.
    text = log_path.read_text(encoding="utf-8")[mark:]
    return [line for line in text.splitlines() if f" id={device} " in line]


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-targets-") as root:
        (patches, assets, state_dir, manifest_path,
         state_path, show_path) = make_fixture(root)
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
                "--devices", "3", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.2", "--boot-secs", "0.2",
                "--state-dir", str(state_dir), "--manifest", str(manifest_path),
                "--patches-dir", str(patches), "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

            # Seat 2 is in group 9; the bridge syncs memberships on device
            # connect and the sim node persists them -- wait until sim2's
            # assignment file records the membership so the group datagram
            # will actually match.
            sim2_state = Path(state_dir, SIM_MACS[2].replace(":", "-") + ".json")

            def sim2_in_group():
                try:
                    return 9 in json.loads(sim2_state.read_text())["groups"]
                except (OSError, ValueError, KeyError):
                    return False

            check("sim2 acknowledged group 9 membership",
                  wait_for(sim2_in_group, timeout=15),
                  sim2_state.read_text() if sim2_state.exists() else "missing")

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

                page.locator('[data-show-message-focus="aaaa0001"]').click()
                page.wait_for_selector(".show-target-picker")
                check("legacy single-string target loads as All",
                      page.locator('[data-target-toggle="all"].on').count() == 1
                      and page.locator(".show-target-terse").inner_text() == "all"
                      and "-> all" in page.locator("#show-wire-preview").inner_text())

                page.locator(".show-target-picker summary").click()
                page.locator('[data-target-toggle="1"]').click()
                page.wait_for_function(
                    "() => document.querySelector('.show-target-terse')?.innerText === '1'")
                page.locator('[data-target-toggle="3"]').click()
                page.wait_for_function(
                    "() => document.querySelector('.show-target-terse')?.innerText === '1+3'")
                check("tapping seat chips builds a two-seat target and drops All",
                      page.locator('[data-target-toggle="all"].on').count() == 0
                      and page.locator('[data-target-toggle="1"].on').count() == 1
                      and page.locator('[data-target-toggle="3"].on').count() == 1
                      and "-> 1+3" in page.locator("#show-wire-preview").inner_text(),
                      page.locator("#show-wire-preview").inner_text())

                mark = len(fleet_log_path.read_text(encoding="utf-8"))
                page.locator(
                    '.show-step-row[data-show-step-row="11111111"] '
                    '[data-show-action="step_start"]').click()
                check("two-seat target reaches seat 1 and 3 but not seat 2",
                      wait_for(lambda: any("p/gain=0.77" in line
                                           for line in device_lines(fleet_log_path, mark, 1))
                               and any("p/gain=0.77" in line
                                       for line in device_lines(fleet_log_path, mark, 3)))
                      and not any("p/gain" in line
                                  for line in device_lines(fleet_log_path, mark, 2)),
                      repr(device_lines(fleet_log_path, mark, 2)))
                page.wait_for_selector(
                    '.show-step-row[data-show-step-row="11111111"].show-step-stopped')

                page.locator('[data-show-message-focus="aaaa0001"]').click()
                page.wait_for_selector(".show-target-picker")
                page.locator('[data-target-toggle="g9"]').click()
                page.wait_for_function(
                    "() => document.querySelector('.show-target-terse')?.innerText === '1+3+g9'")
                check("group chip joins the mix with removable summary chips",
                      page.locator(".show-target-summary [data-target-remove]").count() == 3
                      and "-> 1+3+g9" in page.locator("#show-wire-preview").inner_text(),
                      page.locator("#show-wire-preview").inner_text())

                mark = len(fleet_log_path.read_text(encoding="utf-8"))
                page.locator(
                    '.show-step-row[data-show-step-row="11111111"] '
                    '[data-show-action="step_start"]').click()
                check("adding the group fans the send out to its member too",
                      wait_for(lambda: any("p/gain=0.77" in line
                                           for line in device_lines(fleet_log_path, mark, 2))),
                      repr(device_lines(fleet_log_path, mark, 2)))
                page.wait_for_selector(
                    '.show-step-row[data-show-step-row="11111111"].show-step-stopped')

                def saved_target():
                    try:
                        doc = json.loads(show_path.read_text(encoding="utf-8"))
                        return doc["items"][0]["messages"][0]["target"]
                    except (OSError, ValueError, KeyError, IndexError):
                        return None

                check("saved show normalizes the target to a selector list",
                      wait_for(lambda: saved_target() == ["1", "3", "g9"]),
                      repr(saved_target()))

                page.locator('.show-target-summary [data-target-remove="g9"]').click()
                page.wait_for_function(
                    "() => document.querySelector('.show-target-terse')?.innerText === '1+3'")
                page.locator('.show-target-summary [data-target-remove="1"]').click()
                page.locator('.show-target-summary [data-target-remove="3"]').click()
                page.wait_for_function(
                    "() => document.querySelector('.show-target-terse')?.innerText === 'all'")
                check("removing every summary chip falls back to All",
                      page.locator('[data-target-toggle="all"].on').count() == 1)

                page.locator("#show-message-mode").select_option("cue")
                page.wait_for_selector(".show-target-picker.show-disabled-field")
                check("cue payloads grey the target picker",
                      page.locator(
                          ".show-target-picker.show-disabled-field "
                          '[data-target-toggle="all"]').is_disabled())

                check("browser emitted no page errors", not page_errors, repr(page_errors))
                page.screenshot(path=str(HERE / "target-picker.png"), full_page=False)
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
