#!/usr/bin/env python3
"""Playwright verification for the audition-falloff range widget.

Covers audition-falloff/2-range-widget: dragging the listener heading
widget's tip sets both heading and range (audible distance), clamped to
[0.5m, room diagonal], and the range flows through state/broadcast/
persistence exactly like heading already did.
"""

import json
import math
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "audition.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent

sys.path.insert(0, os.path.join(REPO, "dashboard"))
from state import InstallationState  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def close(actual, expected, tolerance=0.03):
    return abs(float(actual) - float(expected)) <= tolerance


def free_port(kind):
    sock = socket.socket(socket.AF_INET, kind)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def wait_http(url, process, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before serving HTTP")
        try:
            urllib.request.urlopen(url, timeout=0.4).close()
            return
        except OSError:
            time.sleep(0.1)
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


def drag(page, locator, target_x, target_y):
    box = locator.bounding_box()
    if box is None:
        raise AssertionError("drag source has no bounding box")
    start_x = box["x"] + box["width"] / 2
    start_y = box["y"] + box["height"] / 2
    page.mouse.move(start_x, start_y)
    page.mouse.down()
    for step in range(1, 13):
        page.mouse.move(start_x + (target_x - start_x) * step / 12,
                        start_y + (target_y - start_y) * step / 12)
    page.mouse.up()


def pure_state_contract_tests():
    """Browser-free contract checks for the clean_listener/default_listener
    range clamp and fallback logic, ahead of the interactive drag checks."""
    with tempfile.TemporaryDirectory() as temp:
        state = InstallationState(os.path.join(temp, "installation.json"))

        diagonal = math.hypot(state.DEFAULT_ROOM["width"], state.DEFAULT_ROOM["depth"])
        default = state.default_listener()
        check("default_listener range is the room diagonal (today's behaviour)",
              close(default["range"], diagonal), repr(default))

        # Missing range on an older persisted listener falls back to the
        # diagonal -- existing installations sound unchanged until dragged.
        legacy = state.clean_listener({"x": 1, "y": 1, "heading": 0})
        check("clean_listener fills in missing range with the room diagonal",
              legacy is not None and close(legacy["range"], diagonal), repr(legacy))

        # Range below the floor clamps to 0.5.
        too_close = state.clean_listener({"x": 1, "y": 1, "heading": 0, "range": 0.01})
        check("clean_listener clamps range to the 0.5m floor",
              too_close is not None and too_close["range"] == 0.5, repr(too_close))

        # Range above the diagonal clamps to the diagonal.
        too_far = state.clean_listener({"x": 1, "y": 1, "heading": 0, "range": 999})
        check("clean_listener clamps range to the room diagonal ceiling",
              too_far is not None and close(too_far["range"], diagonal), repr(too_far))

        # A valid mid-range value passes through unchanged.
        mid = state.clean_listener({"x": 1, "y": 1, "heading": 0, "range": 3.5})
        check("clean_listener passes a valid range through unchanged",
              mid is not None and mid["range"] == 3.5, repr(mid))

        # Invalid range (non-numeric / bool) falls back to the diagonal too.
        bad = state.clean_listener({"x": 1, "y": 1, "heading": 0, "range": "nope"})
        check("clean_listener falls back to diagonal for non-numeric range",
              bad is not None and close(bad["range"], diagonal), repr(bad))
        bad_bool = state.clean_listener({"x": 1, "y": 1, "heading": 0, "range": True})
        check("clean_listener falls back to diagonal for a boolean range",
              bad_bool is not None and close(bad_bool["range"], diagonal), repr(bad_bool))


def main():
    pure_state_contract_tests()

    with tempfile.TemporaryDirectory() as temp:
        # A small room with an exact 3-4-5 diagonal (5.0m) keeps the pixel
        # offsets needed to exceed/undercut the clamp bounds small, so the
        # drag targets stay comfortably inside the browser viewport.
        room = {"width": 4.0, "depth": 3.0, "units": "m"}
        diagonal = math.hypot(room["width"], room["depth"])
        check("fixture room has the expected 5.0m diagonal", diagonal == 5.0, repr(diagonal))

        state_path = os.path.join(temp, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({
                "schema": 1, "name": "range-widget-fixture",
                "room": room,
                # Range 1.5 keeps the tip on-screen and inside the room at
                # load, unlike the diagonal default which typically renders
                # the tip well outside the room -- see notes.md.
                "listener": {"x": 2.0, "y": 1.5, "heading": 0.0, "range": 1.5},
                "seats": {"0": {"id": 0, "name": "Seat 0", "positions": [[2.0, 0.5]],
                                "params": {}, "groups": [], "bound": None}},
            }, target)

        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        engine_base = free_port(socket.SOCK_DGRAM)
        log_path = os.path.join(temp, "dashboard.log")
        log = open(log_path, "w", encoding="utf-8")
        server = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--sim-no-engine", "--sim-audio-backend", "none",
                "--sim-engine-port-base", str(engine_base),
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            base_url = f"http://127.0.0.1:{http_port}"
            wait_http(base_url + "/", server)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1400, "height": 1400})

                def handle_dialog(dialog):
                    if dialog.type == "prompt":
                        dialog.accept("")
                    else:
                        dialog.accept()

                page.on("dialog", handle_dialog)
                page.goto(base_url + "/#seats")
                page.wait_for_selector("#ws-status.online", timeout=10000)

                # Enable simulation directly over the websocket (bypassing
                # the confirm-dialog UI button) so the gated listener puck
                # renders (spatial.js: "listener && installation.simulation
                # ?.active").
                page.evaluate(
                    "ws.send('set_simulation', {active: true, confirmed: true})")
                page.wait_for_function(
                    "() => installation.simulation && installation.simulation.active === true",
                    timeout=10000)
                page.wait_for_selector("#spatial .listener-tip", timeout=10000)
                page.evaluate("window.scrollTo(0, 0)")

                initial_listener = page.evaluate(
                    "JSON.parse(JSON.stringify(installation.listener))")
                check("fixture listener range loaded as-is",
                      close(initial_listener["range"], 1.5), repr(initial_listener))

                room_box = page.locator("#spatial .room").bounding_box()
                scale_x = room_box["width"] / room["width"]
                scale_y = room_box["height"] / room["depth"]

                # Drag the tip outward, past the room diagonal (5.0m), along
                # a diagonal southeast heading so the pixel offset needed in
                # either axis alone stays modest.
                tip = page.locator("#spatial .listener-tip")
                listener_body = page.locator("#spatial .listener-body").bounding_box()
                center_x = listener_body["x"] + listener_body["width"] / 2
                center_y = listener_body["y"] + listener_body["height"] / 2
                far_offset_m = diagonal * 0.78  # per-axis; combined magnitude > diagonal
                target_x = center_x + far_offset_m * scale_x
                target_y = center_y + far_offset_m * scale_y
                drag(page, tip, target_x, target_y)
                page.wait_for_timeout(150)

                outward = page.evaluate(
                    "JSON.parse(JSON.stringify(installation.listener))")
                check("dragging the tip outward clamps range to the room diagonal",
                      close(outward["range"], diagonal), repr(outward))
                check("dragging the tip outward also updates heading",
                      outward["heading"] != initial_listener["heading"], repr(outward))

                # Drag the tip back in, well below the 0.5m floor.
                tip = page.locator("#spatial .listener-tip")
                near_offset_m = 0.2
                target_x = center_x + near_offset_m * scale_x
                target_y = center_y + near_offset_m * scale_y
                drag(page, tip, target_x, target_y)
                page.wait_for_timeout(150)

                inward = page.evaluate(
                    "JSON.parse(JSON.stringify(installation.listener))")
                check("dragging the tip inward clamps range to the 0.5m floor",
                      inward["range"] == 0.5, repr(inward))

                # The /audition/listener frame shape is unchanged (still 4
                # values): confirm the client still only tracks x/y/heading/
                # range on the listener object, nothing extra leaked in.
                check("listener object still carries exactly the 4-value frame fields",
                      set(inward.keys()) == {"x", "y", "heading", "range"}, repr(inward))

                # Reconnect: durable persistence carries the dragged range.
                page.evaluate("ws.send('set_simulation', {active: false, confirmed: true})")
                page.wait_for_timeout(200)
                page.goto("about:blank")
                page.goto(base_url + "/#seats")
                page.wait_for_selector("#ws-status.online", timeout=10000)
                reconnected = page.evaluate(
                    "JSON.parse(JSON.stringify(installation.listener))")
                check("browser reconnect restores the persisted (clamped) range",
                      reconnected["range"] == 0.5, repr(reconnected))

                browser.close()
        finally:
            stop(server)
            log.close()

        # Confirm the on-disk durable state also carries the clamped range,
        # independent of what the browser happened to report.
        reloaded = InstallationState(state_path)
        check("persisted installation.json carries the clamped range",
              reloaded.data["listener"]["range"] == 0.5, repr(reloaded.data["listener"]))

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("audition-falloff/2-range-widget checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
