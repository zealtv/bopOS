#!/usr/bin/env python3
"""Real Dashboard + simfleet Playwright verification for live controls."""

import json
import os
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
        if (parent / "dashboard" / "server.py").is_file():
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
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    (patch / "main.bin").write_bytes(b"live-browser-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"path": ["synth", "voice"], "name": "density", "type": "f",
             "min": 0, "max": 1, "default": .25, "dashboard": True},
            {"name": "gate", "type": "i", "min": 0, "max": 1,
             "default": 0, "dashboard": True},
            {"path": ["labels"], "name": "word", "type": "s",
             "dashboard": True},
            {"name": "hidden", "type": "f", "min": 0, "max": 1,
             "default": .4, "dashboard": False},
        ], "cues": [], "caps": [], "slots": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    uids = ["02:53:49:4d:00:01", "02:53:49:4d:00:02"]

    def seat(seat_id, name, uid, density, gate, word, groups):
        return {"id": seat_id, "name": name, "positions": [[seat_id, 1]],
                "groups": groups, "bound": uid, "patch": "alpha",
                "params": {"synth/voice/density": density, "gate": gate,
                           "labels/word": word, "hidden": .4}}

    state = {
        "schema": 1, "name": "Live browser verifier",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "groups": {"0": {"id": 0, "name": "Front"},
                   "1": {"id": 1, "name": "Empty"}},
        "next_group_id": 2,
        "seats": {
            "1": seat(1, "Freda", uids[0], .2, 0, "warm", [0]),
            "2": seat(2, "Sparks", uids[1], .8, 1, "cool", [0]),
        },
    }
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path, uids


def set_range(page, selector, value):
    page.eval_on_selector(selector, """(input, value) => {
        input.value = value;
        input.dispatchEvent(new Event('input', {bubbles: true}));
        input.dispatchEvent(new Event('change', {bubbles: true}));
    }""", str(value))


def set_checkbox(page, selector, checked):
    page.eval_on_selector(selector, """(input, checked) => {
        input.indeterminate = false;
        input.checked = checked;
        input.dispatchEvent(new Event('change', {bubbles: true}));
    }""", bool(checked))


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-live-browser-") as root:
        patches, assets, state_dir, manifest_path, state_path, uids = make_fixture(root)
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
                "--devices", "2", "--target", "127.0.0.1",
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
                page.goto(base_url + "/facilitator")
                page.wait_for_selector(".live-card[data-live-scope=all]")
                page.wait_for_function("() => Object.keys(installation.devices||{}).length === 2")

                check("Dashboard renders Seat-owned All, Group, and Seat cards",
                      page.locator('.live-card[data-live-scope="all"]').count() == 1
                      and page.locator('.live-card[data-live-scope="group"]').count() == 2
                      and page.locator('.live-card[data-live-scope="seat"]').count() == 2
                      and page.locator(".card[data-uid]").count() == 0)
                check("flat and nested promoted identities coexist without flattening",
                      page.locator('[data-live-param][data-param-path="gate"]').count() == 5
                      and page.locator(
                          '[data-live-param][data-param-path="synth/voice/density"]').count() == 5
                      and page.locator('[data-param-branch="synth/voice"]').count() == 5
                      and page.locator('[data-param-path="hidden"]').count() == 0)
                check("All and populated Group expose clear mixed aggregate state",
                      page.locator('.live-card[data-live-scope="all"] .live-param.mixed').count() == 3
                      and page.locator(
                          '.live-card[data-live-scope="group"][data-live-id="0"] .live-param.mixed').count() == 3)
                empty = page.locator(
                    '.live-card.empty-group[data-live-scope="group"][data-live-id="1"]')
                check("empty Group is visible but cannot emit parameter writes",
                      empty.count() == 1
                      and empty.locator("[data-live-param]").count() == 3
                      and all(empty.locator("[data-live-param]").nth(index).is_disabled()
                              for index in range(3)))
                check("Send all exists only for All and each Seat",
                      page.locator('[data-replay-live][data-live-scope="all"]').count() == 1
                      and page.locator('[data-replay-live][data-live-scope="seat"]').count() == 2
                      and page.locator('[data-replay-live][data-live-scope="group"]').count() == 0)

                all_density = ('[data-live-param][data-live-scope="all"]'
                               '[data-param-path="synth/voice/density"]')
                set_range(page, all_density, .6)
                page.wait_for_function(
                    "() => [...document.querySelectorAll("
                    "'.live-card:not(.empty-group) [data-live-param]"
                    "[data-param-path=\"synth/voice/density\"]')]"
                    ".every(input => Math.abs(Number(input.value)-.6)<.0001)")
                density_values = page.locator(
                    '.live-card:not(.empty-group) [data-live-param]'
                    '[data-param-path="synth/voice/density"]').evaluate_all(
                        "inputs => inputs.map(input => Number(input.value))")
                check("All edit converges each Seat card and Group aggregate",
                      all(abs(value - .6) < .001 for value in density_values),
                      repr(density_values))

                all_gate = ('[data-live-param][data-live-scope="all"]'
                            '[data-param-path="gate"]')
                set_checkbox(page, all_gate, False)
                page.wait_for_function(
                    "() => [...document.querySelectorAll("
                    "'.live-card:not(.empty-group) [data-live-param][data-param-path=gate]')]"
                    ".every(input => !input.checked && !input.indeterminate)")
                seat_gate = ('[data-live-param][data-live-scope="seat"][data-live-id="1"]'
                             '[data-param-path="gate"]')
                page.locator(seat_gate).check()
                page.wait_for_function(
                    "() => document.querySelector("
                    "'.live-card[data-live-scope=all] [data-param-path=gate]')"
                    "?.classList.contains('mixed')")
                check("Seat edit makes All and Group mixed without changing the other Seat",
                      page.locator(
                          '.live-card[data-live-scope="all"] [data-param-path="gate"].mixed').count() == 1
                      and page.locator(
                          '.live-card[data-live-scope="group"][data-live-id="0"] '
                          '[data-param-path="gate"].mixed').count() == 1
                      and page.locator(
                          '[data-live-param][data-live-scope="seat"][data-live-id="2"]'
                          '[data-param-path="gate"]').is_checked() is False)

                # Touch activation must work for replay buttons without adding help copy.
                page.locator('[data-replay-live][data-live-scope="seat"][data-live-id="1"]').tap()
                page.locator('[data-replay-live][data-live-scope="all"]').tap()
                page.wait_for_timeout(150)
                body = page.locator("body").inner_text().lower()
                check("live surface adds no explanatory prose",
                      all(phrase not in body for phrase in (
                          "choose a target", "replay the snapshot", "parameter snapshot",
                          "mute is device-owned", "send all will")), body)
                dimensions = page.locator("[data-replay-live], .live-param").evaluate_all(
                    "els => els.map(el => ({w:el.getBoundingClientRect().width,"
                    "h:el.getBoundingClientRect().height}))")
                check("iPad-width touch rows and replay actions meet 44px targets",
                      dimensions and all(item["w"] >= 44 and item["h"] >= 44
                                         for item in dimensions), repr(dimensions))
                check("narrow live surface has no horizontal overflow",
                      page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"),
                      str(page.evaluate("[document.documentElement.scrollWidth,innerWidth]")))
                page.screenshot(path=str(HERE / "live-controls-ipad.png"), full_page=True)

                # Main Devices tab: roster indication and selected-detail action.
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function("() => Object.keys(installation.devices||{}).length === 2")
                page.click("#tab-button-devices")
                page.wait_for_selector("#device-roster .device-row")
                indicators = page.locator("#device-roster [data-device-mute-indicator]")
                check("every physical-device roster row carries one accessible mute indicator",
                      indicators.count() == 2
                      and all(indicators.nth(index).get_attribute("aria-label")
                              for index in range(2)))
                page.locator(f'#device-roster .device-row[data-uid="{uids[0]}"]').click()
                page.wait_for_selector("#device-mute-toggle")
                check("selected Device exposes terse mute action and state",
                      page.locator("#device-mute-toggle").inner_text() == "Mute"
                      and page.locator("#device-mute-status").inner_text().startswith("unmuted"))
                page.click("#device-mute-toggle")
                page.wait_for_function(
                    "uid => installation.devices[uid]?.device_muted === true && "
                    "installation.devices[uid]?.mute_status === 'current'", arg=uids[0])
                indicator = page.locator(
                    f'#device-roster .device-row[data-uid="{uids[0]}"] '
                    '[data-device-mute-indicator]')
                check("device receipt updates roster and selected detail",
                      "persistent device mute" in indicator.get_attribute("aria-label").lower()
                      and page.locator("#device-mute-toggle").inner_text() == "Unmute"
                      and page.locator("#device-mute-status").inner_text().startswith("muted"))

                page.click("#mute-all")
                page.wait_for_function("() => installation.muted === true")
                check("fleet overlay disables individual toggle and labels both layers",
                      page.locator("#device-mute-toggle").is_disabled()
                      and "fleet" in indicator.get_attribute("aria-label").lower()
                      and "persistent" in indicator.get_attribute("aria-label").lower())
                page.click("#mute-all")
                page.wait_for_function("() => installation.muted === false")
                check("fleet release restores persistent Device mute presentation",
                      not page.locator("#device-mute-toggle").is_disabled()
                      and "persistent device mute" in indicator.get_attribute(
                          "aria-label").lower())
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
