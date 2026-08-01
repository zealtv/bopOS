#!/usr/bin/env python3
"""Real Dashboard + simfleet verification for automation tracking/take-over."""

import json
import random
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright
from pythonosc.osc_message import OscMessage

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


def wait_for(predicate, timeout=6):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.1)
    return False


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


class DatagramProxy:
    """Record dashboard datagrams and forward them unchanged to simfleet."""

    def __init__(self, listen_port, target_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", listen_port))
        self.sock.settimeout(.1)
        self.target = ("127.0.0.1", target_port)
        self.messages = []
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def _run(self):
        while self.running:
            try:
                data, _source = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                message = OscMessage(data)
                self.messages.append((message.address, list(message.params), time.monotonic()))
            except Exception:
                pass
            self.sock.sendto(data, self.target)

    def close(self):
        self.running = False
        self.sock.close()
        self.thread.join(timeout=1)


def make_fixture(root):
    root = Path(root)
    patches = root / "patches"
    assets = root / "assets"
    state_dir = root / "fleet-state"
    shows = root / "shows"
    patch = patches / "automation"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"automation-takeover")
    manifest = {
        "engine": "test", "entrypoint": "main.bin", "caps": [], "slots": [],
        "params": [
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": .25, "dashboard": True},
            {"name": "voices", "type": "i", "min": 0, "max": 8,
             "default": 2, "dashboard": True},
            {"name": "label", "type": "s", "dashboard": True},
        ],
        "cues": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    uid0 = "02:53:49:4d:00:01"
    uid1 = "02:53:49:4d:00:02"
    devices_path = root / "devices.csv"
    devices_path.write_text(
        "mac,hostname,id\n"
        f"{uid0},sim0,0\n{uid1},sim1,1\n", encoding="utf-8")
    seats = {
        "0": {"id": 0, "name": "Zero", "positions": [[1, 1]], "groups": [],
              "bound": uid0, "patch": "automation",
              "params": {"gain": .25, "voices": 2, "label": "zero"}},
        "1": {"id": 1, "name": "One", "positions": [[2, 1]], "groups": [],
              "bound": uid1, "patch": "automation",
              "params": {"gain": .25, "voices": 2, "label": "one"}},
        "2": {"id": 2, "name": "Offline", "positions": [[3, 1]], "groups": [],
              "bound": "not-present-uid", "patch": "automation",
              "params": {"gain": .25, "voices": 2, "label": "offline"}},
    }
    state = {
        "schema": 1, "name": "Automation takeover verifier",
        "current_show": "automation", "params_patch": "automation",
        "fleet_patch": {"name": "automation", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "seats": seats, "groups": {}, "next_group_id": 0,
    }
    messages = [
        {"uid": "aaaa0001", "address": "/p/gain", "target": ["0"],
         "args": [{"type": "s", "value": "lfo"},
                  {"type": "s", "value": "sine"},
                  {"type": "f", "value": 0.1}, {"type": "f", "value": 0.9},
                  {"type": "s", "value": "2s"}]},
        {"uid": "aaaa0002", "address": "/p/gain", "target": ["1"],
         "args": [{"type": "f", "value": 0.9},
                  {"type": "s", "value": "2s"}]},
        {"uid": "aaaa0003", "address": "/p/gain", "target": ["2"],
         "args": [{"type": "s", "value": "lfo"},
                  {"type": "s", "value": "square"},
                  {"type": "f", "value": 0}, {"type": "f", "value": 1},
                  {"type": "s", "value": "4s"}]},
        # A hand-authored string generator is tracked server-side by the
        # declared-f classification rule but must never gain UI automation.
        {"uid": "aaaa0004", "address": "/p/label", "target": ["0"],
         "args": [{"type": "s", "value": "lfo"},
                  {"type": "s", "value": "sine"},
                  {"type": "f", "value": 0}, {"type": "f", "value": 1},
                  {"type": "s", "value": "2s"}]},
    ]
    show = {
        "schema": 1, "name": "automation", "items": [{
            "kind": "step", "uid": "11111111", "alias": "automation",
            "messages": messages, "duration_s": 10, "play_count": 1,
            "then_actions": [{"type": "stop"}],
        }],
    }
    state_path = root / "installation.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows / "automation.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path, devices_path


def param_messages(proxy, address):
    return [(args, stamp) for seen, args, stamp in proxy.messages if seen == address]


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-automation-takeover-") as root:
        (patches, assets, state_dir, manifest_path,
         state_path, devices_path) = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        proxy_port = free_port(socket.SOCK_DGRAM)
        fleet_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log_path = Path(root, "server.log")
        fleet_log_path = Path(root, "fleet.log")
        server_log = server_log_path.open("w", encoding="utf-8")
        fleet_log = fleet_log_path.open("w", encoding="utf-8")
        server = fleet = proxy = None
        try:
            proxy = DatagramProxy(proxy_port, fleet_port)
            proxy.start()
            server = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard" / "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(proxy_port),
                "--osc-target", "127.0.0.1", "--state-file", str(state_path),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base_url,
            ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, str(ROOT / "tools" / "simfleet.py"),
                "--devices", "2", "--devices-file", str(devices_path),
                "--target", "127.0.0.1", "--report-port", str(listen_port),
                "--cmd-port", str(fleet_port), "--hb-interval", "0.2",
                "--boot-secs", "0.2", "--state-dir", str(state_dir),
                "--manifest", str(manifest_path), "--patches-dir", str(patches),
                "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1180, "height": 1000})
                page = context.new_page()
                browser_errors = []
                page.on("pageerror", lambda error: browser_errors.append(str(error)))
                page.on("console", lambda message: browser_errors.append(message.text)
                        if message.type == "error" else None)
                page.goto(base_url + "/facilitator.html")
                page.wait_for_selector("#ws-status.online", state="attached")
                page.wait_for_function("() => Object.keys(installation.devices || {}).length >= 2")
                page.evaluate("() => ws.send('step_start', {uid: '11111111'})")

                all_gain = '.all-card label[data-param-path="gain"]'
                page.wait_for_selector(all_gain + " .live-param-glyph")
                check("All row exposes divergent generators as auto mixed",
                      "auto·mixed" in page.locator(all_gain).inner_text().lower()
                      and "automated, mixed" in
                      page.locator(all_gain + " [data-live-param]").get_attribute("aria-label"))

                saved = wait_for(
                    lambda: json.loads(state_path.read_text(encoding="utf-8"))
                    ["seats"]["1"]["params"].get("gain") == .9)
                check("fade destination lands in durable Seat params", saved)

                before_idle = len([item for item in proxy.messages if "/p/" in item[0]])
                time.sleep(.45)
                after_idle = len([item for item in proxy.messages if "/p/" in item[0]])
                check("automation indication adds zero OSC traffic",
                      after_idle == before_idle, f"{before_idle} -> {after_idle}")

                page.click('#live-scope-seats')
                seat0 = '.seat-card[data-live-id="0"] label[data-param-path="gain"]'
                seat1 = '.seat-card[data-live-id="1"] label[data-param-path="gain"]'
                seat2 = '.seat-card[data-live-id="2"] label[data-param-path="gain"]'
                page.wait_for_selector(seat0 + " .live-param-glyph")
                check("seat 0 shows smooth LFO glyph and accessible state",
                      page.locator(seat0 + " .live-param-glyph").inner_text() == "∿"
                      and "automated, sine LFO" in
                      page.locator(seat0 + " input").get_attribute("aria-label"))
                check("seat 1 shows fade glyph while in flight",
                      page.locator(seat1 + " .live-param-glyph").inner_text() == "╱")
                check("string params never gain an automation glyph",
                      page.locator('.seat-card[data-live-id="0"] label[data-param-path="label"] .live-param-glyph').count() == 0)
                offline_glyph = page.locator(seat2 + " .live-param-glyph")
                check("offline-bound automation is a dim static glyph",
                      offline_glyph.inner_text() == "⌁"
                      and float(offline_glyph.evaluate("el => getComputedStyle(el).opacity")) < 1
                      and offline_glyph.evaluate("el => getComputedStyle(el).animationName") == "none")

                reduced = browser.new_context(
                    viewport={"width": 900, "height": 900}, reduced_motion="reduce")
                reduced_page = reduced.new_page()
                reduced_errors = []
                reduced_page.on("pageerror", lambda error: reduced_errors.append(str(error)))
                reduced_page.on("console", lambda message: reduced_errors.append(message.text)
                                if message.type == "error" else None)
                reduced_page.goto(base_url + "/facilitator.html")
                reduced_page.wait_for_selector("#ws-status.online", state="attached")
                reduced_page.click('#live-scope-seats')
                reduced_page.wait_for_selector(seat0 + " .live-param-glyph")
                check("reduced motion retains the static glyph",
                      reduced_page.locator(seat0 + " .live-param-glyph").inner_text() == "∿")
                reduced.close()

                baseline = len(param_messages(proxy, "/0/p/gain"))
                slider = page.locator(seat0 + ' input[type="range"]')
                # scroll_into_view_if_needed waits for stability; the a5 marker
                # animation keeps the node perpetually "unstable" and heartbeat
                # re-renders can detach it mid-wait. One-shot JS scroll instead.
                page.evaluate(
                    "sel => document.querySelector(sel).scrollIntoView({block: 'center'})",
                    seat0 + ' input[type="range"]')
                box = slider.bounding_box()
                page.mouse.move(box["x"] + box["width"] * .25, box["y"] + box["height"] / 2)
                page.mouse.down()
                check("pointerdown starts the take-over drain",
                      page.locator(seat0).evaluate("el => el.classList.contains('taking-over')"))
                page.mouse.move(box["x"] + box["width"] * .68,
                                box["y"] + box["height"] / 2, steps=8)
                page.mouse.up()
                page.wait_for_function(
                    "() => !installation.automation?.['0']?.gain")
                page.wait_for_function(
                    "() => !document.querySelector('.seat-card[data-live-id=\"0\"] label[data-param-path=\"gain\"] .live-param-glyph')")
                takeover_packets = param_messages(proxy, "/0/p/gain")[baseline:]
                plain_packets = [args for args, _stamp in takeover_packets if len(args) == 1]
                check("take-over sends exactly one plain single-arg datagram",
                      len(takeover_packets) == 1 and len(plain_packets) == 1,
                      repr([args for args, _stamp in takeover_packets]))
                check("take-over announces the resulting constant once",
                      "gain automation stopped, set to" in
                      page.locator('.seat-card[data-live-id="0"] .live-param-status').text_content())
                check("take-over clears the glyph", page.locator(seat0 + " .live-param-glyph").count() == 0)

                check("browser emitted no console errors",
                      not browser_errors and not reduced_errors,
                      repr(browser_errors + reduced_errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            if proxy is not None:
                proxy.close()
            server_log.close()
            fleet_log.close()

        if FAILURES:
            print("\nserver log tail:\n", server_log_path.read_text(encoding="utf-8")[-4000:])
            print("\nfleet log tail:\n", fleet_log_path.read_text(encoding="utf-8")[-4000:])

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
        raise SystemExit(1)
    print("\nAll automation take-over checks passed.")


if __name__ == "__main__":
    main()
