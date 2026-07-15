#!/usr/bin/env python3
"""Focused Playwright verification for managed patch edit mode."""

import json
import asyncio
import os
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from types import SimpleNamespace
from unittest import mock

from playwright.sync_api import sync_playwright
from pythonosc import osc_message

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "audition.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repo")
    REPO = parent
sys.path.insert(0, REPO)
from tools import audition  # noqa: E402
sys.path.insert(0, os.path.join(REPO, "dashboard"))
import server as dashboard_server  # noqa: E402

FAILURES = []
RESERVED_PORTS = set()


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_port(kind):
    # Choose a dynamic high port without relying on bind(port=0), which some
    # CI sandboxes deny even while permitting ordinary loopback sockets.
    for _attempt in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        if port in RESERVED_PORTS:
            continue
        sock = socket.socket(socket.AF_INET, kind)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            sock.close()
            continue
        sock.close()
        RESERVED_PORTS.add(port)
        return port
    raise RuntimeError("cannot reserve a dynamic non-default loopback port")


def write_patch(root, name, params, valid=True):
    path = os.path.join(root, name)
    os.makedirs(path)
    with open(os.path.join(path, "main.bin"), "wb") as target:
        target.write(name.encode())
    with open(os.path.join(path, "bopos.patch.json"), "w", encoding="utf-8") as target:
        if valid:
            json.dump({"engine": "test", "entrypoint": "main.bin", "params": params,
                       "caps": [], "slots": []}, target)
        else:
            target.write('{"engine":"test","entrypoint":"missing.bin"}')


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


def receive(capture, address, timeout=3):
    deadline = time.monotonic() + timeout
    capture.settimeout(.2)
    while time.monotonic() < deadline:
        try:
            data, _source = capture.recvfrom(65535)
        except socket.timeout:
            continue
        message = osc_message.OscMessage(data)
        if message.address == address:
            return list(message.params)
    return None


def receive_value(capture, address, expected, timeout=3):
    deadline = time.monotonic() + timeout
    seen = []
    while time.monotonic() < deadline:
        value = receive(capture, address, min(.5, deadline - time.monotonic()))
        if value is None:
            continue
        seen.append(value)
        if value and abs(float(value[0]) - expected) < 1e-5:
            return value, seen
    return None, seen


def verify_real_gui_pd_launch():
    pd_bin = audition.parse_args([]).pd_bin
    if not (os.path.isfile(pd_bin) and os.access(pd_bin, os.X_OK)):
        print(f"[SKIP] real GUI-PD launch -- PD executable unavailable: {pd_bin}")
        return None
    report_port = free_port(socket.SOCK_DGRAM)
    command_port = free_port(socket.SOCK_DGRAM)
    engine_port = free_port(socket.SOCK_DGRAM)
    capture = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    capture.bind(("127.0.0.1", report_port))
    process = None
    pattern = "Pd-0.55-2.app/Contents/Resources/bin/pd|pd-watchdog"

    def pd_pids():
        result = subprocess.run(["pgrep", "-f", pattern], check=False,
                                text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
        return {int(value) for value in result.stdout.split() if value.isdigit()}

    before = pd_pids()
    ok = False
    try:
        process = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools", "audition.py"),
            "--edit", "--devices", "7", "--id-base", "0",
            "--bind", "127.0.0.1", "--target", "127.0.0.1",
            "--cmd-port", str(command_port), "--report-port", str(report_port),
            "--engine-port-base", str(engine_port), "--audio-backend", "none",
            "--hb-interval", ".2", "--manifest",
            os.path.join(REPO, "patches", "demo-pd", "bopos.patch.json"),
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        heartbeat = receive(capture, "/hb", timeout=8)
        ok = (process.poll() is None and heartbeat is not None
              and heartbeat[0] == "audition-0001" and int(heartbeat[3]) == 1)
        check("real edit launch starts one live GUI-PD engine", ok, repr(heartbeat))
    finally:
        stop(process)
        capture.close()
    deadline = time.monotonic() + 2
    remaining = pd_pids() - before
    while remaining and time.monotonic() < deadline:
        time.sleep(.05)
        remaining = pd_pids() - before
    check("real GUI-PD launch leaves no managed child or watchdog", not remaining,
          repr(sorted(remaining)))
    return ok and not remaining


async def verify_launch_failure_rolls_back(temp, patches, assets, state_path):
    args = SimpleNamespace(
        state_file=state_path, devices_file=None,
        listen_port=free_port(socket.SOCK_DGRAM),
        send_port=free_port(socket.SOCK_DGRAM), osc_target="192.0.2.1",
        assets_dir=assets, patches_dir=patches, sim_audio_backend="none",
        sim_engine_port_base=free_port(socket.SOCK_DGRAM), sim_no_engine=True,
    )
    dashboard = dashboard_server.Dashboard(args)
    try:
        with mock.patch.object(dashboard_server.subprocess, "Popen",
                               side_effect=OSError("synthetic launch failure")):
            await dashboard.start_edit("alpha")
        ok = (dashboard.supervisor_mode == "off"
              and not dashboard.state.data["editor"]["active"]
              and dashboard.state.data["editor"]["status"] == "launch failed"
              and dashboard.osc.destination[0] == "192.0.2.1")
        check("failed editor spawn rolls back mode, state, and OSC target", ok)
        class FakeWS:
            def __init__(self):
                self.messages = []

            async def send_json(self, message):
                self.messages.append(message)

        ws = FakeWS()
        before = dashboard.state.data.get("fleet_patch")
        dashboard.set_supervisor_mode("edit")
        await dashboard.handle_ws({"type": "set_fleet_patch", "data": {
            "patch": "alpha", "confirmed": True}}, ws)
        check("backend rejects fleet mutation during edit without changing durable intent",
              dashboard.state.data.get("fleet_patch") == before
              and ws.messages and ws.messages[-1]["type"] == "error")
        dashboard.set_supervisor_mode("off")
    finally:
        dashboard.osc.close()
        await dashboard.state.close()


def main():
    edit_args = audition.parse_args(["--edit", "--devices", "9", "--no-engine"])
    sim_args = audition.parse_args(["--devices", "1", "--no-engine"])
    node = audition.VirtualNode(0, 0, "verify", 16661)
    loaded = {"engine": "pd", "entrypoint": "main.pd"}
    rig = audition.AuditionRig.__new__(audition.AuditionRig)
    rig.args = edit_args
    edit_command = rig.engine_command(
        node, os.path.join(REPO, "patches", "demo-pd"), loaded,
        {"seed": 1, "run_id": "verify"})
    rig.args = sim_args
    sim_command = rig.engine_command(
        node, os.path.join(REPO, "patches", "demo-pd"), loaded,
        {"seed": 1, "run_id": "verify"})
    check("--edit forces exactly one managed audition device", edit_args.devices == 1)
    check("only PD edit launch removes -nogui",
          "-nogui" not in edit_command and "-nogui" in sim_command,
          repr(edit_command) + "\n" + repr(sim_command))

    class CaptureSocket:
        packet = None

        def sendto(self, packet, _target):
            self.packet = packet

    rig.args = edit_args
    rig.sock = CaptureSocket()
    rig.send_ready()
    ready = osc_message.OscMessage(rig.sock.packet)
    check("audition ready frame reports edit mode",
          ready.address == "/audition/ready" and list(ready.params)[-1] == "edit",
          ready.address + " " + repr(list(ready.params)))

    with tempfile.TemporaryDirectory() as temp:
        patches = os.path.join(temp, "patches")
        assets = os.path.join(temp, "assets")
        os.makedirs(patches)
        os.makedirs(assets)
        write_patch(patches, "alpha", [
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": .25, "group": "mix", "facilitator": True},
            {"name": "tone", "type": "f", "min": 100, "max": 1000,
             "default": 440, "group": "sound"},
            {"name": "label", "type": "s", "group": "sound"},
        ])
        write_patch(patches, "beta", [
            {"name": "gate", "type": "i", "min": 0, "max": 1,
             "default": 0, "group": "switches"},
        ])
        write_patch(patches, "invalid", [], valid=False)
        state_path = os.path.join(temp, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({"schema": 1, "name": "pe2", "seats": {
                "0": {"id": 0, "name": "edit seat", "positions": [[0, 0]],
                      "params": {}, "bound": None}
            }}, target)

        asyncio.run(verify_launch_failure_rolls_back(
            temp, patches, assets, state_path))

        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        command_port = free_port(socket.SOCK_DGRAM)
        engine_port = free_port(socket.SOCK_DGRAM)
        capture = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        capture.bind(("127.0.0.1", engine_port))
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = os.path.join(temp, "dashboard.log")
        log = open(log_path, "w", encoding="utf-8")
        server = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(command_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", assets, "--patches-dir", patches,
                "--sim-no-engine", "--sim-audio-backend", "none",
                "--sim-engine-port-base", str(engine_port),
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1400, "height": 1100})
                dialog_mode = {"accept": True}
                dialogs = []

                def handle_dialog(dialog):
                    dialogs.append((dialog.type, dialog.message))
                    if dialog_mode["accept"]:
                        dialog.accept()
                    else:
                        dialog.dismiss()

                page.on("dialog", handle_dialog)
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "() => [...document.querySelectorAll('#editor-patch option')]"
                    ".some(option => option.value === 'beta')")
                options = page.locator("#editor-patch option").all_text_contents()
                check("editor lists only valid host patches",
                      options == ["alpha", "beta"], repr(options))

                page.select_option("#editor-patch", "alpha")
                page.click("#editor-launch")
                page.wait_for_function(
                    "() => installation.supervisor?.mode === 'edit'"
                    " && installation.editor?.patch === 'alpha'"
                    " && installation.editor?.engine_alive === 0", timeout=10000)
                check("patch launch enters exclusive edit mode",
                      page.evaluate("installation.editor.active"
                                    " && !installation.simulation.active"
                                    " && installation.supervisor.mode === 'edit'"))
                caught_master, seen = receive_value(capture, "/os/master", 1.0)
                check("editor declaration catch-up restores dashboard master",
                      caught_master is not None, repr(seen))
                check("fleet patch mutations are disabled while edit owns the relay",
                      page.locator("#patch-switch").is_disabled()
                      and page.locator("#fleet-patch-revert").is_disabled())

                panel = page.locator("#editor-panel")
                panel_text = panel.inner_text().lower()
                check("all manifest groups and facilitator badge render",
                      "mix" in panel_text and "sound" in panel_text
                      and "gain" in panel_text and "tone" in panel_text
                      and panel.locator(".facilitator-badge").count() == 1,
                      panel_text)
                check("editor includes master and excludes framework mute",
                      panel.locator("#editor-master").count() == 1
                      and "mute" not in panel_text, panel_text)

                page.locator('[data-editor-param="gain"]').evaluate(
                    "el => { el.value='0.42'; el.dispatchEvent(new Event('input', {bubbles:true})); }")
                delivered, seen = receive_value(capture, "/p/gain", .42)
                check("editor parameter uses the managed relay engine surface",
                      delivered is not None and abs(delivered[0] - .42) < 1e-5,
                      repr(seen))
                text_control = page.locator('[data-editor-param="label"]')
                text_control.click()
                text_control.type("hello editor")
                page.wait_for_timeout(300)
                focused_text = (text_control.evaluate("el => document.activeElement === el")
                                and text_control.input_value() == "hello editor")
                text_control.press("Tab")
                delivered_text = receive(capture, "/p/label")
                check("text entry keeps focus through state renders and sends the full value",
                      focused_text and delivered_text == ["hello editor"],
                      repr(delivered_text))
                page.locator("#editor-master").evaluate(
                    "el => { el.value='0.61'; el.dispatchEvent(new Event('input', {bubbles:true})); }")
                delivered_master, seen = receive_value(capture, "/os/master", .61)
                check("editor master reaches the same managed engine surface",
                      delivered_master is not None and abs(delivered_master[0] - .61) < 1e-5,
                      repr(seen))

                status = page.locator("#editor-status").inner_text().lower()
                generation = page.evaluate("installation.editor.generation")
                check("no-engine heartbeat deterministically reports closed engine",
                      "engine closed" in status and page.locator("#editor-relaunch").count() == 1,
                      status)
                page.click("#editor-relaunch")
                page.wait_for_function(
                    "old => installation.editor?.generation > old"
                    " && installation.editor?.engine_alive === 0", arg=generation,
                    timeout=10000)
                check("Relaunch is explicit and remains honest under --no-engine", True)
                generation = page.evaluate("installation.editor.generation")
                check("explicit Restart is present", page.locator("#editor-restart").count() == 1)
                page.click("#editor-restart")
                page.wait_for_function(
                    "old => installation.editor?.generation > old", arg=generation,
                    timeout=10000)
                check("Restart performs a fresh managed launch", True)

                check("editor exposes Hear it in the sim cross-mode control",
                      page.locator("#editor-hear-sim").count() == 1)
                page.click("#editor-hear-sim")
                page.wait_for_function(
                    "() => installation.supervisor?.mode === 'simulate'"
                    " && installation.simulation?.active"
                    " && !installation.editor?.active", timeout=10000)
                check("Hear it in the sim stops edit and starts one simulation mode", True)
                check("simulation exposes Edit this patch cross-mode control",
                      page.locator("#edit-sim-patch").is_visible())

                dialog_mode["accept"] = False
                page.click("#edit-sim-patch")
                page.wait_for_timeout(250)
                check("cancelled simulation exit leaves simulation running",
                      page.evaluate("installation.supervisor.mode === 'simulate'"
                                    " && installation.simulation.active"))
                dialog_mode["accept"] = True
                page.click("#edit-sim-patch")
                page.wait_for_function(
                    "() => installation.supervisor?.mode === 'edit'"
                    " && installation.editor?.active"
                    " && !installation.simulation?.active", timeout=10000)
                check("confirmed Edit this patch makes modes mutually exclusive",
                      any(kind == "confirm" and "running simulation" in message
                          for kind, message in dialogs), repr(dialogs))

                page.select_option("#editor-patch", "beta")
                page.click("#editor-launch")
                page.wait_for_function("() => installation.editor?.patch === 'beta'",
                                       timeout=10000)
                check("select and launch retargets the editor patch", True)
                page.locator('[data-editor-param="gate"]').check()
                delivered_gate, seen = receive_value(capture, "/p/gate", 1.0)
                later_gate = receive(capture, "/p/gate", timeout=.5)
                check("checkbox sends its new value without a stale pointer-up write",
                      delivered_gate is not None
                      and (later_gate is None or int(later_gate[0]) != 0),
                      repr(seen) + " later=" + repr(later_gate))
                browser.close()
        finally:
            stop(server)
            capture.close()
            log.close()
            if server is not None and server.returncode not in (0, -15):
                with open(log_path, encoding="utf-8") as source:
                    print("\n--- dashboard log ---\n" + source.read())

    gui_result = verify_real_gui_pd_launch()
    total = 25 + 2 * int(gui_result is not None)
    print(f"\n{total - len(FAILURES)}/{total} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
