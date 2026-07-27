#!/usr/bin/env python3
"""Real Dashboard browser journey for the Device-tab log-destination block.

Drives the real dashboard/server.py against a fake physical peer speaking the
wire (the same harness shape as verify_device_control_modes.py). Exercises the
Logging block, the exact-uid `log-config` envelope round trip, and the visible
`usb` -> `internal` fallback when no stick is mounted.
"""

import json
import os
import random
import select
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
from pythonosc.osc_message_builder import OscMessageBuilder

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
UID = "02:53:49:4d:00:01"
FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_port(kind, host="127.0.0.1"):
    for _attempt in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        probe = socket.socket(socket.AF_INET, kind)
        try:
            probe.bind((host, port))
        except OSError:
            probe.close()
            continue
        probe.close()
        return port
    raise RuntimeError("cannot reserve localhost port")


def physical_host():
    override = os.environ.get("BOPOS_TEST_PHYSICAL_HOST")
    if override:
        return override
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))
        host = probe.getsockname()[0]
    finally:
        probe.close()
    if not host or host.startswith("127."):
        raise RuntimeError(
            "set BOPOS_TEST_PHYSICAL_HOST to a local non-loopback address")
    return host


def packet(address, *args):
    builder = OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def wait_http(url, process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before serving HTTP")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not serve HTTP")


class PhysicalPeer:
    """A fake physical node: heartbeats, reports a `log` object, and honours
    the exact-uid `log-config` envelope with a fallback-aware receipt."""

    def __init__(self, host, command_port, report_port, manifest_text):
        self.host = host
        self.command_port = command_port
        self.report_port = report_port
        self.manifest_text = manifest_text
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, command_port))
        self.running = True
        self.log_destination = "internal"
        self.usb_present = False  # no stick mounted -> usb falls back
        self.frames = []
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        self.thread.start()

    def send(self, address, *args):
        self.sock.sendto(packet(address, *args), ("127.0.0.1", self.report_port))

    def heartbeat(self):
        self.send("/hb", UID, 0, "physical-test", 1)

    def log_state(self):
        effective = ("usb" if self.log_destination == "usb" and self.usb_present
                     else "internal")
        return {"destination": self.log_destination, "effective": effective,
                "usb_present": self.usb_present}

    def report(self):
        self.send("/os/report", json.dumps({
            "uid": UID, "hostname": "finn-jet", "engine": "test",
            "patch": "alpha", "git_rev": "physical-test",
            "update_model": "persistent", "contract_version": "1.14",
            "groups": [], "device_enabled": True, "mute_all": False,
            "output_enabled": True,
            "log": self.log_state(),
        }))

    def handle(self, data):
        message = OscMessage(data)
        frame = (message.address, list(message.params))
        with self.lock:
            self.frames.append(frame)
        if message.address == "/all/os/to" and len(message.params) >= 2:
            uid, verb = str(message.params[0]), str(message.params[1])
            if uid != UID:
                return
            if verb == "report":
                self.report()
            elif verb == "log-config" and len(message.params) == 3:
                request = json.loads(str(message.params[2]))
                destination = request.get("destination")
                if destination in ("internal", "usb"):
                    self.log_destination = destination
                    status = "ok"
                else:
                    status = "err"
                self.send("/os/log-config", UID, status,
                          json.dumps(self.log_state()))
        elif message.address.endswith("/os/params"):
            self.send("/os/params", self.manifest_text)
        elif message.address.endswith("/os/patches"):
            self.send("/os/patches", json.dumps(
                [{"name": "alpha", "active": True, "git": False, "manifest": True}]))
        elif message.address.endswith("/os/assets"):
            self.send("/os/assets", "[]")

    def run(self):
        next_hb = 0.0
        while self.running:
            now = time.monotonic()
            if now >= next_hb:
                self.heartbeat()
                next_hb = now + .2
            readable, _, _ = select.select([self.sock], [], [], .05)
            if readable:
                self.handle(self.sock.recvfrom(65535)[0])

    def clear(self):
        with self.lock:
            self.frames.clear()

    def snapshot(self):
        with self.lock:
            return list(self.frames)

    def wait_frame(self, predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            frames = self.snapshot()
            if any(predicate(frame) for frame in frames):
                return frames
            time.sleep(.05)
        return self.snapshot()

    def close(self):
        self.running = False
        self.thread.join(timeout=2)
        self.sock.close()


def write_fixture(root):
    patches = Path(root, "patches")
    assets = Path(root, "assets")
    patch = patches / "alpha"
    patch.mkdir(parents=True)
    assets.mkdir()
    manifest = {"engine": "test", "entrypoint": "main.bin", "caps": [],
                "slots": [], "params": []}
    manifest_text = json.dumps(manifest)
    (patch / "bopos.patch.json").write_text(manifest_text, encoding="utf-8")
    (patch / "main.bin").write_bytes(b"log destination")
    state = Path(root, "installation.json")
    state.write_text(json.dumps({
        "schema": 1, "name": "log dest", "master": .6,
        "seats": {"0": {"id": 0, "name": "Seat 0", "bound": UID,
                        "positions": [[1.0, 2.0]], "params": {}}},
        "device_registry": {UID: {"alias": "Finn Jet", "source": "custom",
                                  "generator": 2, "device_enabled": True}},
        "fleet_patch": {"name": "alpha", "fingerprint": "0" * 64},
    }), encoding="utf-8")
    return patches, assets, state, manifest_text


def has_log_config(frames, destination=None):
    for address, args in frames:
        if (address == "/all/os/to" and len(args) == 3
                and args[0] == UID and args[1] == "log-config"):
            if destination is None:
                return True
            try:
                return json.loads(args[2]).get("destination") == destination
            except (ValueError, TypeError):
                return False
    return False


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-log-dest-") as root:
        patches, assets, state, manifest_text = write_fixture(root)
        physical_target = physical_host()
        http_port = free_port(socket.SOCK_STREAM)
        report_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM, physical_target)
        engine_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        dashboard = subprocess.Popen([
            sys.executable, str(ROOT / "dashboard" / "server.py"),
            "--host", "127.0.0.1", "--port", str(http_port),
            "--listen-port", str(report_port),
            "--send-port", str(command_port),
            "--osc-target", physical_target,
            "--state-file", str(state),
            "--assets-dir", str(assets),
            "--patches-dir", str(patches),
            "--public-url", base_url,
            "--sim-audio-backend", "none",
            "--sim-no-engine",
            "--sim-engine-port-base", str(engine_port),
        ], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        peer = PhysicalPeer(
            physical_target, command_port, report_port, manifest_text)
        try:
            peer.start()
            wait_http(base_url, dashboard)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base_url)
                page.wait_for_function(
                    "uid => installation.devices?.[uid]?.online === true", arg=UID)
                page.click("#tab-button-devices")
                page.locator(
                    f'#device-roster .device-row[data-uid="{UID}"]').click()
                page.wait_for_selector("#refresh-report")
                page.locator("#refresh-report").click()
                page.wait_for_function(
                    "uid => installation.devices[uid]?.report?.log?.destination"
                    " === 'internal'", arg=UID)
                page.wait_for_selector("#log-destination")

                check(
                    "Logging block shows destination selector and effective state",
                    page.locator("#log-destination").input_value() == "internal"
                    and page.locator("#device-log .log-state").inner_text().lower()
                    == "internal")

                peer.clear()
                # Select and apply back-to-back: heartbeat-driven re-renders
                # reset an unsaved selection (the render guard only preserves a
                # focused control), so don't await between the two.
                page.locator("#log-destination").select_option("usb")
                page.locator("#log-apply").click()

                frames = peer.wait_frame(
                    lambda frame: has_log_config([frame], "usb"))
                check(
                    "USB choice sends the exact-uid log-config envelope",
                    has_log_config(frames, "usb"), repr(frames))

                page.wait_for_function(
                    "uid => installation.devices[uid]?.report?.log?.destination"
                    " === 'usb'", arg=UID)
                check(
                    "receipt records destination usb with visible internal fallback",
                    page.evaluate(
                        "uid => installation.devices[uid].report.log.effective",
                        UID) == "internal"
                    and page.evaluate(
                        "uid => installation.devices[uid].report.log.usb_present",
                        UID) is False)
                check(
                    "fallback is surfaced to the operator",
                    "internal" in page.locator("#log-feedback").inner_text().lower()
                    or "not mounted" in page.locator(
                        "#log-feedback").inner_text().lower(),
                    page.locator("#log-feedback").inner_text())

                check("browser emitted no page errors", not page_errors,
                      repr(page_errors))
                screenshot = os.environ.get("BOPOS_LOG_SCREENSHOT")
                if screenshot:
                    page.locator("#device-log").screenshot(path=screenshot)
                browser.close()
        finally:
            peer.close()
            stop(dashboard)

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
