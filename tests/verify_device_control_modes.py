#!/usr/bin/env python3
"""Real Dashboard browser journey for physical/execution route separation."""

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
        # UDP connect selects an interface without sending a packet.
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


def drain_socket(sock):
    while select.select([sock], [], [], 0)[0]:
        sock.recvfrom(65535)


def wait_engine_master(sock, value, timeout=5):
    deadline = time.monotonic() + timeout
    seen = []
    while time.monotonic() < deadline:
        readable, _, _ = select.select(
            [sock], [], [], max(0, deadline - time.monotonic()))
        if not readable:
            break
        message = OscMessage(sock.recvfrom(65535)[0])
        frame = (message.address, list(message.params))
        seen.append(frame)
        if (message.address == "/os/master" and message.params
                and abs(float(message.params[0]) - value) < 1e-5):
            return True, seen
    return False, seen


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
    def __init__(self, host, command_port, report_port, manifest_text):
        self.host = host
        self.command_port = command_port
        self.report_port = report_port
        self.manifest_text = manifest_text
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, command_port))
        self.running = True
        self.device_id = 0
        self.device_enabled = True
        self.audio_config = {
            "card": "DigiAMP", "mixer_control": "Digital",
            "sample_rate": 44100, "period_size": 512, "nperiods": 2,
        }
        self.frames = []
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        self.thread.start()

    def send(self, address, *args):
        self.sock.sendto(
            packet(address, *args), ("127.0.0.1", self.report_port))

    def heartbeat(self):
        self.send("/hb", UID, self.device_id, "physical-test", 1)

    def report(self):
        self.send("/os/report", json.dumps({
            "uid": UID,
            "hostname": "finn-jet",
            "engine": "test",
            "patch": "alpha",
            "git_rev": "physical-test",
            "update_model": "persistent",
            "contract_version": "1.15",
            "groups": [],
            "device_enabled": self.device_enabled,
            "mute_all": False,
            "output_enabled": self.device_enabled,
            "audio": {
                "configured": dict(self.audio_config),
                "active": dict(self.audio_config),
                "cards": [{
                    "id": "DigiAMP", "index": 1,
                    "label": "IQaudIO DigiAMP",
                    "mixer_controls": ["Digital"],
                }],
                "status": "active",
                "error": None,
            },
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
            if verb == "enabled" and len(message.params) == 3:
                self.device_enabled = bool(int(message.params[2]))
                self.send(
                    "/os/enabled", UID, int(self.device_enabled),
                    int(self.device_enabled))
            elif verb == "report":
                self.report()
            elif verb == "unassign":
                self.device_id = -1
                self.heartbeat()
            elif verb == "hostname" and len(message.params) == 3:
                self.send("/os/hostname", UID, str(message.params[2]), "ok")
            elif verb == "audio-config" and len(message.params) == 3:
                self.audio_config = json.loads(str(message.params[2]))
                payload = {
                    "configured": dict(self.audio_config),
                    "active": dict(self.audio_config),
                    "cards": [{
                        "id": "DigiAMP", "index": 1,
                        "label": "IQaudIO DigiAMP",
                        "mixer_controls": ["Digital"],
                    }],
                    "status": "active",
                    "error": None,
                }
                self.send(
                    "/os/audio-config", UID, "ok", "applied",
                    json.dumps(payload))
        elif message.address.endswith("/os/params"):
            self.send("/os/params", self.manifest_text)
        elif message.address.endswith("/os/patches"):
            self.send("/os/patches", json.dumps([
                {"name": "alpha", "active": True, "git": False,
                 "manifest": True},
            ]))
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
    manifest = {
        "engine": "test", "entrypoint": "main.bin", "caps": [], "slots": [],
        "params": [{
            "name": "gain", "kind": "float", "min": 0, "max": 1,
            "default": .5, "dashboard": True,
        }],
    }
    manifest_text = json.dumps(manifest)
    (patch / "bopos.patch.json").write_text(manifest_text, encoding="utf-8")
    (patch / "main.bin").write_bytes(b"mode matrix")
    state = Path(root, "installation.json")
    state.write_text(json.dumps({
        "schema": 1,
        "name": "mode matrix",
        "master": .6,
        "seats": {
            "0": {
                "id": 0, "name": "Seat 0", "bound": UID,
                "positions": [[1.0, 2.0]], "params": {"gain": .5},
            },
        },
        "device_registry": {
            UID: {
                "alias": "Finn Jet", "source": "custom", "generator": 2,
                "device_enabled": True,
            },
        },
        "fleet_patch": {"name": "alpha", "fingerprint": "0" * 64},
    }), encoding="utf-8")
    return patches, assets, state, manifest_text


def has_enabled(frames):
    return any(
        address == "/all/os/to" and len(args) >= 2
        and args[0] == UID and args[1] == "enabled"
        for address, args in frames)


def has_audio_config(frames):
    return any(
        address == "/all/os/to" and len(args) == 3
        and args[0] == UID and args[1] == "audio-config"
        for address, args in frames)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-device-modes-") as root:
        patches, assets, state, manifest_text = write_fixture(root)
        physical_target = physical_host()
        http_port = free_port(socket.SOCK_STREAM)
        report_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM, physical_target)
        engine_port = free_port(socket.SOCK_DGRAM)
        engine = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        engine.bind(("127.0.0.1", engine_port))
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
                    "uid => installation.devices?.[uid]?.online === true",
                    arg=UID)
                page.click("#tab-button-devices")
                page.locator(
                    f'#device-roster .device-row[data-uid="{UID}"]').click()
                page.wait_for_selector("#device-enabled-toggle")
                page.wait_for_function(
                    "uid => installation.devices[uid]?.enabled_status === 'current'",
                    arg=UID)
                check(
                    "Devices UI presents positive enabled terminology",
                    page.locator("#device-enabled-status").inner_text()
                    == "enabled"
                    and page.locator("#device-enabled-toggle").inner_text()
                    == "Disable")
                check(
                    "physical appearance converges desired Device enabled once",
                    has_enabled(peer.snapshot()), repr(peer.snapshot()))

                peer.clear()
                peer.device_enabled = False
                peer.report()
                repaired = peer.wait_frame(
                    lambda frame: frame == (
                        "/all/os/to", [UID, "enabled", 1]))
                page.wait_for_function(
                    "uid => installation.devices[uid]?.enabled_status"
                    " === 'current'", arg=UID)
                check(
                    "mismatched physical report triggers one enabled repair",
                    has_enabled(repaired) and peer.device_enabled,
                    repr(repaired))

                peer.clear()
                page.locator('[data-execution-target="simulate"]').click()
                page.wait_for_function(
                    "() => installation.supervisor?.mode === 'simulate'")
                time.sleep(.5)
                check(
                    "entering Simulation emits no physical enabled command",
                    not has_enabled(peer.snapshot()), repr(peer.snapshot()))
                drain_socket(engine)

                peer.clear()
                page.locator("#audio-rate").select_option("48000")
                page.locator("#audio-period").select_option("256")
                page.locator("#audio-nperiods").select_option("3")
                check(
                    "Audio form hides mixer control and exposes operator settings",
                    page.locator("#audio-card").input_value() == "DigiAMP"
                    and page.locator("#audio-mixer").count() == 0
                    and not page.locator("#audio-apply").is_disabled())
                page.locator("#audio-apply").click()
                audio_frames = peer.wait_frame(
                    lambda frame: has_audio_config([frame]))
                page.wait_for_function(
                    "uid => installation.devices[uid]?.audio_apply?.phase"
                    " === 'applied'", arg=UID)
                check(
                    "Simulation Audio apply reaches exact physical Device",
                    has_audio_config(audio_frames)
                    and peer.audio_config["mixer_control"] == "Digital"
                    and peer.audio_config["sample_rate"] == 48000
                    and peer.audio_config["period_size"] == 256
                    and peer.audio_config["nperiods"] == 3,
                    repr(audio_frames))
                check(
                    "Audio receipt renders active applied feedback",
                    "Applied" in page.locator("#audio-feedback").inner_text()
                    and "48000 Hz" in page.locator(
                        "#device-audio .section-head p").inner_text())
                screenshot = os.environ.get("BOPOS_AUDIO_SCREENSHOT")
                if screenshot:
                    page.locator("#device-audio").screenshot(path=screenshot)

                peer.clear()
                page.locator("#device-enabled-toggle").click()
                frames = peer.wait_frame(
                    lambda frame: frame == (
                        "/all/os/to", [UID, "enabled", 0]))
                page.wait_for_function(
                    "uid => installation.devices[uid]?.device_enabled === false"
                    " && installation.devices[uid]?.enabled_status === 'current'",
                    arg=UID)
                check(
                    "Simulation Device disable reaches the physical receiver",
                    has_enabled(frames)
                    and page.locator("#device-enabled-toggle").inner_text()
                    == "Enable",
                    repr(frames))

                peer.clear()
                page.locator("#mute-all").click()
                page.wait_for_function("() => installation.muted === true")
                muted_engine, muted_frames = wait_engine_master(engine, 0.0)
                check(
                    "Simulation MUTE ALL gates audition and not the physical receiver",
                    muted_engine
                    and not any(address == "/all/os/mute"
                                for address, _args in peer.snapshot()),
                    f"physical={peer.snapshot()!r} engine={muted_frames!r}")

                drain_socket(engine)
                page.locator("#master").evaluate(
                    "(element) => { element.value = '0.25';"
                    " element.dispatchEvent(new Event('input', {bubbles:true})); }")
                held_engine, held_frames = wait_engine_master(engine, 0.0)
                check(
                    "master changes remain gated while Simulation is muted",
                    held_engine
                    and not any(address == "/all/os/mute"
                                for address, _args in peer.snapshot()),
                    f"physical={peer.snapshot()!r} engine={held_frames!r}")

                peer.clear()
                page.evaluate(
                    "() => ws.send('set_edit', "
                    "{active:true,patch:'alpha',confirmed:true})")
                page.wait_for_function(
                    "() => installation.supervisor?.mode === 'edit'")
                time.sleep(.5)
                drain_socket(engine)
                check(
                    "entering Patch Edit emits no physical enabled command",
                    not has_enabled(peer.snapshot()), repr(peer.snapshot()))

                page.click("#tab-button-devices")
                page.locator(
                    f'#device-roster .device-row[data-uid="{UID}"]').click()
                peer.clear()
                page.locator("#device-enabled-toggle").click()
                frames = peer.wait_frame(
                    lambda frame: frame == (
                        "/all/os/to", [UID, "enabled", 1]))
                page.wait_for_function(
                    "uid => installation.devices[uid]?.device_enabled === true"
                    " && installation.devices[uid]?.enabled_status === 'current'",
                    arg=UID)
                check(
                    "Patch Edit Device enable reaches the physical receiver",
                    has_enabled(frames), repr(frames))

                peer.clear()
                page.locator("#mute-all").click()
                page.wait_for_function("() => installation.muted === false")
                resumed_engine, resumed_frames = wait_engine_master(engine, .25)
                check(
                    "Patch Edit MUTE ALL resumes latest master on execution only",
                    resumed_engine
                    and not any(address == "/all/os/mute"
                                for address, _args in peer.snapshot()),
                    f"physical={peer.snapshot()!r} engine={resumed_frames!r}")

                peer.clear()
                page.evaluate(
                    "() => ws.send('set_edit', {active:false,confirmed:true})")
                page.wait_for_function(
                    "() => installation.supervisor?.mode === 'off'")
                time.sleep(.5)
                live_restore = peer.snapshot()
                check(
                    "Live restore sends runtime state but no Device enabled",
                    any(address == "/all/os/master"
                        for address, _args in live_restore)
                    and any(address == "/all/os/mute"
                            for address, _args in live_restore)
                    and not has_enabled(live_restore),
                    repr(live_restore))

                peer.clear()
                alias = page.locator("#device-alias")
                alias.fill("Niko Cloud")
                page.locator("#device-alias-save").click()
                page.wait_for_function(
                    "uid => installation.device_registry[uid]?.alias"
                    " === 'Niko Cloud'", arg=UID)
                time.sleep(.3)
                check(
                    "host-only alias change emits no physical command",
                    not [frame for frame in peer.snapshot()
                         if frame[0] != "/sync/ping"],
                    repr(peer.snapshot()))
                check(
                    "browser emitted no page errors",
                    not page_errors, repr(page_errors))
                browser.close()
        finally:
            peer.close()
            engine.close()
            stop(dashboard)

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
