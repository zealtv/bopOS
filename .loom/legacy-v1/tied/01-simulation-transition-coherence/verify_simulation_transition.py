#!/usr/bin/env python3
"""Rapid managed-audition -> Live coherence regression."""

import asyncio
import json
import os
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from types import SimpleNamespace

from playwright.sync_api import sync_playwright
from pythonosc.osc_message import OscMessage
from pythonosc.osc_message_builder import OscMessageBuilder

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "audition.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "dashboard"))
import server as dashboard_server  # noqa: E402


FAILURES = []
RESERVED = set()


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_port(kind, host="127.0.0.1"):
    for _attempt in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        if (host, port, kind) in RESERVED:
            continue
        probe = socket.socket(socket.AF_INET, kind)
        try:
            probe.bind((host, port))
        except OSError:
            probe.close()
            continue
        probe.close()
        RESERVED.add((host, port, kind))
        return port
    raise RuntimeError("cannot reserve loopback port")


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


def osc_packet(address, args):
    builder = OscMessageBuilder(address=address)
    for value in args:
        builder.add_arg(value)
    return builder.build().dgram


def drain(capture, duration=.5):
    frames = []
    deadline = time.monotonic() + duration
    capture.settimeout(.05)
    while time.monotonic() < deadline:
        try:
            packet, _source = capture.recvfrom(65535)
        except socket.timeout:
            continue
        message = OscMessage(packet)
        frames.append((message.address, list(message.params)))
    return frames


class FakeClient:
    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)


class FakeSender:
    def __init__(self):
        self.frames = []

    def sendto(self, packet, destination):
        message = OscMessage(packet)
        self.frames.append((message.address, list(message.params), destination))

    def close(self):
        pass


async def verify_queued_update_is_rejected(root):
    args = SimpleNamespace(
        state_file=os.path.join(root, "backend-state.json"), devices_file=None,
        listen_port=free_port(socket.SOCK_DGRAM),
        send_port=free_port(socket.SOCK_DGRAM), osc_target="192.0.2.1",
        assets_dir=os.path.join(root, "backend-assets"),
        patches_dir=os.path.join(root, "backend-patches"),
        sim_audio_backend="none", sim_no_engine=True,
    )
    dashboard = dashboard_server.Dashboard(args)
    client = FakeClient()
    dashboard.clients.add(client)
    stale = dashboard.state.ensure("audition-0001")
    stale.update(virtual=True, online=True, id=0)
    queued_payload = dict(stale)
    entered = asyncio.Event()
    release = asyncio.Event()
    enrich = dashboard.public_device

    async def delayed_enrichment(device, desired=None):
        entered.set()
        await release.wait()
        return await enrich(device, desired)

    dashboard.public_device = delayed_enrichment
    broadcast = asyncio.create_task(
        dashboard.broadcast("device_update", queued_payload))
    await entered.wait()
    dashboard.clear_audition_devices()
    release.set()
    await broadcast
    check("in-flight update for removed virtual uid is rejected by backend",
          client.messages == [], repr(client.messages))
    seat = {"id": 0, "name": "Seat Alpha", "positions": [[1.5, 2.5]],
            "params": {"gain": .25}, "bound": "live-0001"}
    dashboard.state.seats["0"] = seat
    dashboard.state.ensure("live-0001").update(id=0, online=True)
    dashboard.state.data.update(master=.37, muted=True)
    sender = FakeSender()
    dashboard.osc.sender = sender
    dashboard.osc.set_target("127.0.0.1")
    dashboard.restore_live_state()
    frames = [(address, args) for address, args, _destination in sender.frames]
    check("Live restoration retargets and replays assignment, master, and mute",
          dashboard.osc.destination[0] == "192.0.2.1"
          and has_restore(frames, .37, 1), repr(sender.frames))
    dashboard.osc.close()
    await dashboard.state.close()


def write_fixture(root):
    assets = os.path.join(root, "assets")
    patches = os.path.join(root, "patches")
    patch = os.path.join(patches, "alpha")
    os.makedirs(assets)
    os.makedirs(patch)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"transition fixture")
    with open(os.path.join(patch, "bopos.patch.json"), "w", encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin", "caps": [], "slots": [],
            "params": [{"name": "gain", "type": "f", "min": 0, "max": 1,
                        "default": .25, "facilitator": True}],
        }, target)
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump({
            "schema": 1, "name": "transition", "master": .37,
            "seats": {"0": {"id": 0, "name": "Seat Alpha",
                               "positions": [[1.5, 2.5]], "params": {"gain": .25},
                               "bound": "live-0001"}},
        }, target)
    return assets, patches, state_path


def has_restore(frames, master, muted):
    assignment = any(
        address == "/all/os/assign" and args[:3] == ["live-0001", 0, "Seat Alpha"]
        and len(args) >= 5 and abs(float(args[3]) - 1.5) < 1e-5
        and abs(float(args[4]) - 2.5) < 1e-5
        for address, args in frames)
    master_frame = any(
        address == "/all/os/master" and args and abs(float(args[0]) - master) < 1e-5
        for address, args in frames)
    mute_frame = any(
        address == "/all/os/mute" and args == [muted]
        for address, args in frames)
    return assignment and master_frame and mute_frame


def verify_browser(root):
    assets, patches, state_path = write_fixture(root)
    http_port = free_port(socket.SOCK_STREAM)
    listen_port = free_port(socket.SOCK_DGRAM)
    command_port = free_port(socket.SOCK_DGRAM)
    engine_port = free_port(socket.SOCK_DGRAM)
    heartbeat = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    heartbeat.bind(("127.0.0.1", 0))
    base_url = f"http://127.0.0.1:{http_port}"
    log_path = os.path.join(root, "dashboard.log")
    log = open(log_path, "w", encoding="utf-8")
    process = None
    try:
        process = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard", "server.py"),
            "--host", "127.0.0.1", "--port", str(http_port),
            "--listen-port", str(listen_port), "--send-port", str(command_port),
            "--osc-target", "127.0.0.1", "--state-file", state_path,
            "--assets-dir", assets, "--patches-dir", patches,
            "--sim-no-engine", "--sim-audio-backend", "none",
            "--sim-engine-port-base", str(engine_port),
        ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
        wait_http(base_url, process)
        heartbeat.sendto(osc_packet(
            "/hb", ["live-0001", 0, "verify-live", 1, -45]),
            ("127.0.0.1", listen_port))

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 1000})
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(base_url)
            page.wait_for_selector("#ws-status.online")
            page.wait_for_function("() => installation.devices?.['live-0001']?.online")
            live_frame = page.frame_locator("#dashboard-live-view")
            live_frame.locator("#cards .card").wait_for()

            page.fill("#master", "0.37")
            page.dispatch_event("#master", "input")
            page.click("#mute-all")
            page.wait_for_function(
                "() => Math.abs(master - .37) < .001 && muted === true")

            page.click("#tab-button-seats")
            page.click("#simulate-toggle")
            page.wait_for_function(
                "() => installation.supervisor?.mode === 'simulate'"
                " && Object.values(installation.devices || {}).some(d => d.virtual)")
            check("managed Simulation adds a virtual dashboard card",
                  live_frame.locator("#cards .card").count() == 2)
            page.click("#simulate-toggle")
            page.wait_for_function(
                "() => installation.supervisor?.mode === 'off'"
                " && !Object.values(installation.devices || {}).some(d => d.virtual)")
            check("Simulation -> Live clears only virtual cards without refresh",
                  live_frame.locator("#cards .card").count() == 1
                  and page.evaluate("installation.seats['0'].bound") == "live-0001"
                  and page.evaluate("Math.abs(master - .37) < .001 && muted === true"))

            page.click("#tab-button-patches")
            page.select_option("#editor-patch", "alpha")
            page.click("#editor-launch")
            page.wait_for_function(
                "() => installation.supervisor?.mode === 'edit'"
                " && Object.values(installation.devices || {}).some(d => d.virtual)")
            page.click("#editor-stop")
            page.wait_for_function(
                "() => installation.supervisor?.mode === 'off'"
                " && !Object.values(installation.devices || {}).some(d => d.virtual)")
            check("Patch edit -> Live clears virtual cards without refresh",
                  live_frame.locator("#cards .card").count() == 1
                  and page.evaluate("installation.seats['0'].bound") == "live-0001"
                  and page.evaluate("Math.abs(master - .37) < .001 && muted === true"))
            check("rapid transitions finish on the correct live UI state",
                  page.locator("#mode-status").inner_text().lower() == "live fleet"
                  and "active" in (page.locator("#mute-all").get_attribute("class") or "")
                  and page.locator("#master-out").evaluate("element => element.value") == "37%"
                  and live_frame.locator("#cards .card").count() == 1)
            browser.close()
    finally:
        stop(process)
        heartbeat.close()
        log.close()
    server_log = open(log_path, encoding="utf-8").read()
    check("dashboard process exits cleanly",
          process is not None and process.returncode in (0, -15)
          and "Application shutdown complete" in server_log,
          f"returncode={getattr(process, 'returncode', None)}\n{server_log}")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-transition-") as root:
        asyncio.run(verify_queued_update_is_rejected(root))
        verify_browser(root)
    total = 7
    print(f"\n{total - len(FAILURES)}/{total} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
