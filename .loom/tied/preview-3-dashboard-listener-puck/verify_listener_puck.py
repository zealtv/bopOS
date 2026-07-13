#!/usr/bin/env python3
"""Focused browser/UDP verification for the dashboard listener puck."""

import json
import importlib.util
import math
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import types
from urllib.request import urlopen

from playwright.sync_api import sync_playwright
from pythonosc import osc_message, osc_message_builder


sys.dont_write_bytecode = True


def repo_root():
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "tools" / "audition.py").is_file():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "dashboard"))
import audition_geometry  # noqa: E402
import audition_matrix  # noqa: E402
from state import InstallationState  # noqa: E402


checks = 0


def check(condition, label, detail=""):
    global checks
    if not condition:
        raise AssertionError(f"{label}: {detail}" if detail else label)
    checks += 1
    print(f"[PASS] {label}")


def free_tcp_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def free_udp_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def contiguous_udp_sockets(count):
    base = free_udp_port()
    while base + count - 1 <= 65535:
        sockets = []
        try:
            for offset in range(count):
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(("127.0.0.1", base + offset))
                sock.settimeout(0.8)
                sockets.append(sock)
            return base, sockets
        except OSError:
            for sock in sockets:
                sock.close()
            base += count
    raise RuntimeError("could not reserve contiguous UDP engine ports")


def wait_http(url, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=0.4) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.08)
    raise AssertionError(f"dashboard did not start at {url}")


def receive(sock):
    message = osc_message.OscMessage(sock.recvfrom(65535)[0])
    return message.address, list(message.params)


def drain(sock):
    sock.settimeout(0.01)
    while True:
        try:
            receive(sock)
        except socket.timeout:
            sock.settimeout(0.8)
            return


def close_values(actual, expected, tolerance=3e-6):
    if len(actual) != len(expected):
        return False
    return all(abs(float(got) - float(want)) <= tolerance
               for got, want in zip(actual, expected))


def wait_message(sock, address, expected=None, timeout=2.5):
    deadline = time.monotonic() + timeout
    observed = []
    while time.monotonic() < deadline:
        sock.settimeout(max(0.01, deadline - time.monotonic()))
        try:
            got_address, args = receive(sock)
        except socket.timeout:
            break
        if got_address != address:
            continue
        observed.append(args)
        if expected is None or close_values(args, expected):
            return args
    raise AssertionError(f"did not receive {address} {expected!r}; observed {observed!r}")


def assert_no_message(sock, address, timeout=0.3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        sock.settimeout(max(0.01, deadline - time.monotonic()))
        try:
            got_address, args = receive(sock)
        except socket.timeout:
            return
        if got_address == address:
            raise AssertionError(f"unexpected {address}: {args!r}")


def send_heartbeat(report_port, uid, device_id):
    builder = osc_message_builder.OscMessageBuilder(address="/hb")
    for value in (uid, device_id, "audition-2", 0):
        builder.add_arg(value)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(builder.build().dgram, ("127.0.0.1", report_port))
    finally:
        sock.close()


def load_audition_module():
    path = ROOT / "tools" / "audition.py"
    spec = importlib.util.spec_from_file_location("preview3_audition_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def pure_contract_tests(temp_path):
    audition = load_audition_module()

    class CaptureSocket:
        def __init__(self):
            self.sent = []

        def sendto(self, packet, destination):
            self.sent.append((packet, destination))

    rig = object.__new__(audition.AuditionRig)
    rig.sock = CaptureSocket()
    rig.args = types.SimpleNamespace(report_port=54321)
    rig.report_target = ("255.255.255.255", 54321)
    rig.send_ready()
    packet_data, destination = rig.sock.sent[0]
    ready = osc_message.OscMessage(packet_data)
    check(destination == ("127.0.0.1", 54321)
          and ready.address == "/audition/ready",
          "audition ready ignores broadcast target and uses loopback",
          repr((destination, ready.address)))

    malformed = temp_path / "malformed-room.json"
    malformed.write_text(json.dumps({
        "room": {"width": "not-finite", "depth": 8},
        "listener": {"x": 999, "y": 999, "heading": 0},
        "devices": {},
    }))
    state = InstallationState(str(malformed))
    check(state.data["room"] == state.DEFAULT_ROOM,
          "malformed persisted room falls back to default", repr(state.data["room"]))
    check(state.data["listener"] == {"x": 10.0, "y": 8.0, "heading": 0.0},
          "persisted listener clamps against fallback room", repr(state.data["listener"]))


def expected_matrix(listener, positions, room):
    if not positions:
        return audition_matrix.IDENTITY
    model_listener = audition_geometry.Listener(
        listener["x"], listener["y"], listener["heading"],
        math.hypot(room["width"], room["depth"]),
    )
    terms = audition_geometry.terms_for_positions(model_listener, positions)
    return audition_matrix.pd_safe_matrix(
        audition_matrix.matrix_for_positions(terms)
    )


def browser_state(page, expression):
    return page.evaluate(f"JSON.parse(JSON.stringify({expression}))")


def drag_to(page, locator, x, y):
    box = locator.bounding_box()
    if box is None:
        raise AssertionError("drag source has no bounding box")
    start_x = box["x"] + box["width"] / 2
    start_y = box["y"] + box["height"] / 2
    page.mouse.move(start_x, start_y)
    page.mouse.down()
    for step in range(1, 13):
        page.mouse.move(start_x + (x - start_x) * step / 12,
                        start_y + (y - start_y) * step / 12)
    page.mouse.up()


def start_audition(command_port, report_port, engine_base, log):
    return subprocess.Popen([
        sys.executable, str(ROOT / "tools" / "audition.py"),
        "--devices", "2", "--no-engine", "--bind", "127.0.0.1",
        "--target", "127.0.0.1", "--cmd-port", str(command_port),
        "--report-port", str(report_port), "--engine-port-base", str(engine_base),
        "--hb-interval", "30", "--catchup-secs", "0.1",
    ], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)


def stop_process(process):
    if process is None or process.poll() is not None:
        return
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def main():
    http_port = free_tcp_port()
    report_port = free_udp_port()
    command_port = free_udp_port()
    engine_base, engines = contiguous_udp_sockets(2)
    server = audition = None

    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        pure_contract_tests(temp_path)
        state_file = temp_path / "installation.json"
        server_log = (temp_path / "dashboard.log").open("w+")
        audition_log = (temp_path / "audition.log").open("w+")
        state_file.write_text(json.dumps({
            "name": "listener-puck-fixture",
            "room": {"width": 10.0, "depth": 8.0, "units": "m"},
            "listener": {"x": 5.0, "y": 4.0, "heading": 0.0},
            "devices": {
                "audition-0001": {
                    "id": 1, "name": "one-position", "pos1": [5.0, 2.0],
                },
                "audition-0002": {"id": 2, "name": "zero-position"},
            },
        }, indent=2))

        server = subprocess.Popen([
            sys.executable, str(ROOT / "dashboard" / "server.py"),
            "--host", "127.0.0.1", "--port", str(http_port),
            "--listen-port", str(report_port), "--send-port", str(command_port),
            "--osc-target", "127.0.0.1", "--state-file", str(state_file),
        ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
        try:
            wait_http(f"http://127.0.0.1:{http_port}/")
            audition = start_audition(command_port, report_port, engine_base, audition_log)

            # Dashboard heartbeat catch-up supplies positions and the loopback-only
            # listener frame. The engine receives complete matrices, never geometry.
            room = {"width": 10.0, "depth": 8.0}
            listener = {"x": 5.0, "y": 4.0, "heading": 0.0}
            wait_message(engines[0], "/audition/matrix",
                         expected_matrix(listener, [[5.0, 2.0]], room), timeout=4)
            wait_message(engines[1], "/audition/matrix", audition_matrix.IDENTITY, timeout=4)
            check(True, "loopback listener and initial 1/0-position matrices")

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1400, "height": 1000})
                page.goto(f"http://127.0.0.1:{http_port}/")
                page.wait_for_selector("#spatial .listener-puck", timeout=10000)
                check(page.locator("#spatial .listener-puck").count() == 1,
                      "listener puck rendered once")
                check(page.locator("#listener-heading").input_value() == "0",
                      "durable heading rendered")

                # Regression: the tray can sit below the viewport after later
                # spatial controls grow the page. Bring the unplaced source into
                # view before reading either box, then keep the room target on
                # screen. Dropping over the listener is safe because the SVG
                # retains pointer capture from the element's pointer-down.
                zero_uid = "audition-0002"
                zero_source = page.locator(
                    f'#spatial [data-uid="{zero_uid}"] .p1')
                zero_source.scroll_into_view_if_needed()
                zero_source = page.locator(
                    f'#spatial [data-uid="{zero_uid}"] .p1')
                source_box = zero_source.bounding_box()
                room_box = page.locator("#spatial .room").bounding_box()
                viewport_height = page.viewport_size["height"]
                target_x = room_box["x"] + room_box["width"] * 0.25
                desired_y = room_box["y"] + room_box["height"] * 0.35
                target_y = min(max(desired_y, room_box["y"] + 30, 40),
                               room_box["y"] + room_box["height"] - 30,
                               viewport_height - 40)
                check(source_box is not None and source_box["y"] < viewport_height,
                      "zero-position tray source scrolled into view", repr(source_box))
                drain(engines[1])
                drag_to(page, zero_source, target_x, target_y)
                page.wait_for_function(
                    "() => Array.isArray(installation.devices['audition-0002'].pos1)")
                zero_positions = browser_state(page,
                    "[installation.devices['audition-0002'].pos1]")
                zero_to_one = expected_matrix(listener, zero_positions, room)
                wait_message(engines[1], "/audition/matrix", zero_to_one)
                check(not close_values(zero_to_one, audition_matrix.IDENTITY),
                      "zero-to-one room drag emits complete non-identity matrix",
                      repr(zero_to_one))

                # Return the element to the now-visible tray so the rest of the
                # fixture continues to exercise the original zero-position node.
                tray_box = page.locator("#spatial .tray").bounding_box()
                tray_y = min(tray_box["y"] + tray_box["height"] * 0.6,
                             viewport_height - 20)
                drain(engines[1])
                drag_to(page,
                        page.locator(f'#spatial [data-uid="{zero_uid}"] .p1'),
                        tray_box["x"] + tray_box["width"] * 0.75, tray_y)
                page.wait_for_function(
                    "() => installation.devices['audition-0002'].pos1 === null")
                wait_message(engines[1], "/audition/matrix", audition_matrix.IDENTITY)
                check(True, "one-to-zero tray return restores identity")

                # Heading is a full-state listener update and changes the exact matrix.
                drain(engines[0])
                page.fill("#listener-heading", "90")
                page.dispatch_event("#listener-heading", "change")
                listener["heading"] = 90.0
                wait_message(engines[0], "/audition/matrix",
                             expected_matrix(listener, [[5.0, 2.0]], room))
                tip = page.locator("#spatial .listener-heading")
                check(float(tip.get_attribute("x2")) > 0.7
                      and abs(float(tip.get_attribute("y2"))) < 0.02,
                      "heading ray follows clockwise degree convention")

                # Drag streams and finalises x/y while retaining heading.
                page.evaluate("window.scrollTo(0, 0)")
                room_box = page.locator("#spatial .room").bounding_box()
                target_x = room_box["x"] + room_box["width"] * 0.3
                target_y = room_box["y"] + room_box["height"] * 0.65
                drain(engines[0])
                drag_to(page, page.locator("#spatial .listener-body"), target_x, target_y)
                page.wait_for_timeout(250)
                listener = browser_state(page, "installation.listener")
                positions = browser_state(page,
                    "[installation.devices['audition-0001'].pos1]")
                wait_message(engines[0], "/audition/matrix",
                             expected_matrix(listener, positions, room))
                check(abs(listener["x"] - 3.0) < 0.08
                      and abs(listener["y"] - 5.2) < 0.08
                      and listener["heading"] == 90,
                      "puck drag updates bounded x/y and retains heading", repr(listener))

                # A malformed WS edit is atomic: state and current matrix hold.
                held = dict(listener)
                drain(engines[0])
                page.evaluate("ws.send('set_listener', {x: 1, y: 2})")
                page.wait_for_timeout(250)
                check(browser_state(page, "installation.listener") == held,
                      "malformed listener retains browser/server state")
                assert_no_message(engines[0], "/audition/matrix", timeout=0.25)
                check(True, "malformed listener emits no matrix")

                # Resizing the room clamps listener coordinates and changes the
                # derived listener range carried by the private full-state frame.
                before_resize = expected_matrix(listener, positions, room)
                drain(engines[0])
                page.fill("#room-w", "6")
                page.fill("#room-d", "5")
                page.dispatch_event("#room-d", "change")
                page.wait_for_function(
                    "() => installation.room.width === 6 && installation.room.depth === 5"
                    " && installation.listener.y === 5")
                room = browser_state(page, "installation.room")
                listener = browser_state(page, "installation.listener")
                resized_matrix = expected_matrix(listener, positions, room)
                wait_message(engines[0], "/audition/matrix", resized_matrix)
                check(listener["x"] == 3.0 and listener["y"] == 5.0,
                      "room resize clamps listener", repr(listener))
                check(not close_values(before_resize, resized_matrix),
                      "room resize changes derived range and matrix")
                held = dict(listener)

                # Double-clicking an element adds/removes pos2; each edit rides a
                # complete assignment and recomputes the fixed-stereo matrix.
                uid = "audition-0001"
                element = page.locator(f'#spatial [data-uid="{uid}"] .p1')
                drain(engines[0])
                element.dblclick()
                page.wait_for_function(
                    "() => Array.isArray(installation.devices['audition-0001'].pos2)")
                positions = browser_state(page,
                    "[installation.devices['audition-0001'].pos1, installation.devices['audition-0001'].pos2]")
                wait_message(engines[0], "/audition/matrix",
                             expected_matrix(listener, positions, room))
                check(len(positions) == 2, "one-to-two position convergence")

                # Re-arm the UI's explicit two-click detector. Reacquire after
                # the first click because selection may re-render the SVG.
                page.wait_for_timeout(450)
                page.locator(f'#spatial [data-uid="{uid}"] .p1').click()
                page.locator(f'#spatial [data-uid="{uid}"] .p1').click()
                page.wait_for_function(
                    "() => installation.devices['audition-0001'].pos2 === null")
                positions = browser_state(page,
                    "[installation.devices['audition-0001'].pos1]")
                wait_message(engines[0], "/audition/matrix",
                             expected_matrix(listener, positions, room))
                check(len(positions) == 1, "two-to-one position convergence")

                # Moving the only element to the tray clears both positions and
                # must produce exact identity rather than silence.
                page.evaluate("window.scrollTo(0, 0)")
                tray = page.locator("#spatial .tray").bounding_box()
                drain(engines[0])
                drag_to(page, page.locator(f'#spatial [data-uid="{uid}"] .p1'),
                        tray["x"] + tray["width"] * 0.5,
                        tray["y"] + tray["height"] * 0.65)
                page.wait_for_function(
                    "() => installation.devices['audition-0001'].pos1 === null")
                wait_message(engines[0], "/audition/matrix", audition_matrix.IDENTITY)
                check(True, "one-to-zero position converges to identity")

                # Restore one position so relay restart catch-up cannot pass with
                # an empty/default assignment by accident.
                drain(engines[0])
                page.evaluate(
                    "ws.send('set_position', {uid: 'audition-0001', pos1: [7, 2]})")
                page.wait_for_function(
                    "() => Array.isArray(installation.devices['audition-0001'].pos1)")
                positions = browser_state(page,
                    "[installation.devices['audition-0001'].pos1]")
                wait_message(engines[0], "/audition/matrix",
                             expected_matrix(listener, positions, room))

                # Browser reconnect restores durable puck state from the server.
                drain(engines[0])
                page.goto("about:blank")
                page.goto(f"http://127.0.0.1:{http_port}/")
                page.wait_for_selector("#spatial .listener-puck", timeout=10000)
                check(browser_state(page, "installation.listener") == held,
                      "browser reconnect restores listener full state")
                wait_message(engines[0], "/audition/matrix",
                             expected_matrix(held, positions, room))
                check(True, "browser reconnect replays current listener matrix")

                # A fresh relay with the same default IDs has lost all positions.
                # Heartbeat catch-up must replay assignments and listener state,
                # yielding the current non-identity matrix without another edit.
                # Refresh last_seen immediately before replacement so this proves
                # the fast-restart path, not the >30 s offline fallback.
                send_heartbeat(report_port, "audition-0001", 1)
                send_heartbeat(report_port, "audition-0002", 2)
                page.wait_for_timeout(100)
                stop_process(audition)
                audition = None
                for sock in engines:
                    drain(sock)
                audition = start_audition(command_port, report_port, engine_base, audition_log)
                wait_message(engines[0], "/audition/matrix",
                             expected_matrix(held, positions, room), timeout=5)
                check(True, "relay restart catches up assignment and listener")

                browser.close()
        finally:
            stop_process(audition)
            stop_process(server)
            for sock in engines:
                sock.close()
            server_log.close()
            audition_log.close()

    print(f"listener puck verify: {checks} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
