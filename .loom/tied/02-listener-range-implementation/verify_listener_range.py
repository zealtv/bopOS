#!/usr/bin/env python3
"""Playwright verification for 22-listener-range-ux/02-listener-range-implementation.

Proves the ratified design: range is scrubbed on a fixed collar that never
leaves the listener dot (so it is settable with the listener hard against the
top edge of the map -- the case that was impossible before), heading is a
separate gesture on a fixed-length handle, and neither perturbs the other.
Also covers the numeric field, the keyboard path, touch emulation, and a
set_listener round-trip through persistence.
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
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
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


def listener(page):
    return page.evaluate("JSON.parse(JSON.stringify(installation.listener))")


def puck_centre(page):
    """Body centre in page pixels, read in ONE scroll state (gotcha 9)."""
    return page.evaluate(
        "() => { const b = document.querySelector('#spatial .listener-body')"
        ".getBoundingClientRect();"
        " return [b.x + b.width / 2, b.y + b.height / 2]; }")


def mouse_drag(page, start, target, steps=16):
    page.mouse.move(*start)
    page.mouse.down()
    for step in range(1, steps + 1):
        page.mouse.move(start[0] + (target[0] - start[0]) * step / steps,
                        start[1] + (target[1] - start[1]) * step / steps)
    page.mouse.up()


def touch_drag(cdp, start, target, steps=12):
    cdp.send("Input.dispatchTouchEvent",
             {"type": "touchStart",
              "touchPoints": [{"x": start[0], "y": start[1], "id": 1}]})
    for step in range(1, steps + 1):
        cdp.send("Input.dispatchTouchEvent",
                 {"type": "touchMove", "touchPoints": [{
                     "x": start[0] + (target[0] - start[0]) * step / steps,
                     "y": start[1] + (target[1] - start[1]) * step / steps,
                     "id": 1}]})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


def main():
    with tempfile.TemporaryDirectory() as temp:
        # 3-4-5 room: the diagonal ceiling is exactly 5.0 m.
        room = {"width": 4.0, "depth": 3.0, "units": "m"}
        diagonal = math.hypot(room["width"], room["depth"])
        state_path = os.path.join(temp, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({
                "schema": 1, "name": "listener-range-fixture",
                "room": room,
                # HARD AGAINST THE TOP EDGE with a small range: under the old
                # tip-drag control every range above ~0.1 m in a northerly
                # heading needed a pointer position outside the map.
                "listener": {"x": 2.0, "y": 0.1, "heading": 0.0, "range": 1.0},
                "seats": {"0": {"id": 0, "name": "Seat 0", "positions": [[2.0, 1.5]],
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
                context = browser.new_context(viewport={"width": 1400, "height": 1200},
                                              has_touch=True)
                page = context.new_page()
                page.on("dialog", lambda dialog: dialog.accept("")
                        if dialog.type == "prompt" else dialog.accept())
                page.on("pageerror", lambda err: FAILURES.append(f"page error: {err}"))
                page.goto(base_url + "/#seats")
                page.wait_for_selector("#ws-status", state="attached", timeout=10000)
                page.evaluate("ws.send('set_simulation', {active: true, confirmed: true})")
                page.wait_for_function(
                    "() => installation.simulation && installation.simulation.active === true",
                    timeout=10000)
                page.wait_for_selector("#spatial .listener-collar", timeout=10000)
                page.evaluate("window.scrollTo(0, 0)")  # gotcha 2

                start = listener(page)
                check("fixture listener loads at the top edge with range 1.0",
                      close(start["range"], 1.0) and close(start["y"], 0.1), repr(start))

                # --- Rendering: field, outline, fixed-length handle -----------
                geometry = page.evaluate(
                    "() => { const q = s => document.querySelector('#spatial ' + s);"
                    " const tip = q('.listener-tip'), line = q('.listener-heading');"
                    " return {field: Number(q('.listener-field').getAttribute('r')),"
                    "  ring: Number(q('.listener-ring').getAttribute('r')),"
                    # SUPERSEDED by 26-listener-range-fixes/01: Bob ruled 2026-07-21
                    # that the range indication clips to the room, so the dashed
                    # out-of-room arc is retired. Assert its ABSENCE instead.
                    "  dashed: !!q('.listener-ring-outside'),"
                    "  collar: Number(q('.listener-collar').getAttribute('r')),"
                    "  handle: Math.hypot(Number(tip.getAttribute('cx')),"
                    "                     Number(tip.getAttribute('cy'))),"
                    # 26-listener-range-fixes/01 moved the clip UP one level, onto an
                    # untranslated wrapper: clipPathUnits is userSpaceOnUse, so a
                    # translate() on the referencing element slid the room window by
                    # the listener position. Look for the clip on any ancestor.
                    "  clipped: q('.listener-field').closest('[clip-path]')"
                    "             ?.getAttribute('clip-path') || null,"
                    "  tick: !!q('.listener-tick')}; }")
                check("range renders as a room-clipped field at r = range",
                      close(geometry["field"], 1.0)
                      and geometry["clipped"] == "url(#spatial-room-clip)", repr(geometry))
                check("range outline is drawn solid and clipped, with no out-of-room arc"
                      " (26-listener-range-fixes/01 supersedes the dashed arc)",
                      close(geometry["ring"], 1.0) and geometry["dashed"] is False,
                      repr(geometry))
                check("heading handle is a fixed 0.9 m, independent of range",
                      close(geometry["handle"], 0.9), repr(geometry))
                check("scrub collar is fixed at 0.45 m",
                      close(geometry["collar"], 0.45), repr(geometry))
                check("residual magnitude tick survives (Bob's ruling 5)",
                      geometry["tick"], repr(geometry))
                colours = page.evaluate(
                    "() => { const s = getComputedStyle(document.documentElement);"
                    " return {field: s.getPropertyValue('--listener-field').trim(),"
                    "  ring: s.getPropertyValue('--listener-ring').trim(),"
                    "  sim: s.getPropertyValue('--sim').trim(),"
                    "  green: s.getPropertyValue('--green').trim()}; }")
                check("range treatment resolves to --sim, never --green",
                      colours["field"] == colours["sim"]
                      and colours["ring"] == colours["sim"]
                      and colours["sim"] != colours["green"], repr(colours))

                # --- THE CASE THAT FAILED: large range at the top edge --------
                centre = puck_centre(page)
                scale = page.evaluate(
                    "() => { const r = document.querySelector('#spatial .room')"
                    ".getBoundingClientRect(); return r.width / 4.0; }")
                # Press ON the collar (south of the body so the body does not take
                # the pointerdown) and scrub outward INTO the room: the gesture
                # never has to leave the map even though the range does.
                collar_point = (centre[0], centre[1] + 0.45 * scale)
                mouse_drag(page, collar_point, (collar_point[0], collar_point[1] + 320))
                page.wait_for_timeout(150)
                big = listener(page)
                check("collar scrub at the top edge reaches the diagonal ceiling",
                      close(big["range"], diagonal), repr(big))
                check("collar scrub leaves heading untouched",
                      big["heading"] == start["heading"], repr(big))
                check("collar scrub leaves listener position untouched",
                      close(big["x"], start["x"]) and close(big["y"], start["y"]), repr(big))
                at_max = page.evaluate(
                    "() => document.querySelector('#spatial .listener-ring')"
                    ".classList.contains('at-max')")
                check("outline goes solid at the ceiling", at_max)
                check("readout reports the max",
                      "(max)" in page.locator("#listener-readout").inner_text(),
                      page.locator("#listener-readout").inner_text())
                page.screenshot(path=os.path.join(HERE, "shot-top-edge-max-range.png"))

                # Scrub back inward: press the collar and pull toward the dot and
                # past it -- signed travel along the grab axis keeps shrinking.
                page.evaluate("window.scrollTo(0, 0)")
                centre = puck_centre(page)
                collar_point = (centre[0], centre[1] + 0.45 * scale)
                mouse_drag(page, collar_point, (collar_point[0], collar_point[1] - 250))
                page.wait_for_timeout(150)
                small = listener(page)
                check("scrubbing back inward lowers range again",
                      small["range"] < big["range"], repr(small))
                check("inward scrub still leaves heading untouched",
                      small["heading"] == start["heading"], repr(small))

                # --- Heading without perturbing range ------------------------
                # Move the listener off the top edge for the aim tests: the
                # handle is a fixed 0.9 m, which sits above the canvas when the
                # listener is glued to the wall and pointing north.
                page.evaluate("ws.send('set_listener', "
                              "Object.assign({}, installation.listener, "
                              "{y: 1.5, range: 2.5}))")
                page.wait_for_timeout(200)
                page.reload()
                page.wait_for_selector("#spatial .listener-tip", timeout=10000)
                page.evaluate("window.scrollTo(0, 0)")
                before = listener(page)
                check("range 2.5 round-tripped through set_listener and a reload",
                      close(before["range"], 2.5), repr(before))
                centre = puck_centre(page)
                tip_box = page.evaluate(
                    "() => { const b = document.querySelector('#spatial .listener-tip')"
                    ".getBoundingClientRect();"
                    " return [b.x + b.width / 2, b.y + b.height / 2]; }")
                # Swing the tip east; it sits at a fixed 0.9 m so it is always
                # on-screen, and the drag distance no longer means anything.
                mouse_drag(page, tip_box, (centre[0] + 0.9 * scale, centre[1]))
                page.wait_for_timeout(150)
                aimed = listener(page)
                check("dragging the tip sets heading", close(aimed["heading"], 90, 6),
                      repr(aimed))
                check("dragging the tip does NOT change range (the reported defect)",
                      close(aimed["range"], before["range"]), repr(aimed))
                handle = page.evaluate(
                    "() => { const t = document.querySelector('#spatial .listener-tip');"
                    " return Math.hypot(Number(t.getAttribute('cx')),"
                    " Number(t.getAttribute('cy'))); }")
                check("heading handle stays 0.9 m after aiming", close(handle, 0.9),
                      repr(handle))
                page.screenshot(path=os.path.join(HERE, "shot-heading-vs-range.png"))

                # --- Numeric field -------------------------------------------
                page.locator("#listener-range").fill("3.75")
                page.locator("#listener-range").dispatch_event("change")
                page.wait_for_timeout(200)
                typed = listener(page)
                check("typed range commits", close(typed["range"], 3.75), repr(typed))
                check("typed range leaves heading alone",
                      close(typed["heading"], aimed["heading"]), repr(typed))
                page.locator("#listener-range").fill("999")
                page.locator("#listener-range").dispatch_event("change")
                page.wait_for_timeout(200)
                check("typed range clamps at the diagonal ceiling",
                      close(listener(page)["range"], diagonal), repr(listener(page)))
                page.locator("#listener-heading").fill("210")
                page.locator("#listener-heading").dispatch_event("change")
                page.wait_for_timeout(200)
                typed_heading = listener(page)
                check("typed heading commits without touching range",
                      close(typed_heading["heading"], 210)
                      and close(typed_heading["range"], diagonal), repr(typed_heading))

                # --- Keyboard ------------------------------------------------
                page.locator("#listener-range").fill("2.0")
                page.locator("#listener-range").dispatch_event("change")
                page.wait_for_timeout(400)  # let the broadcast re-render settle first
                # Focus and read in ONE evaluate: a heartbeat re-render between the
                # two calls otherwise lands before focus settles.
                focused = False
                for _ in range(6):
                    focused = page.evaluate(
                        "() => { document.querySelector('#spatial .listener-puck').focus();"
                        " return !!document.activeElement.closest('g[data-listener]'); }")
                    if focused:
                        break
                    page.wait_for_timeout(150)
                check("the listener puck takes keyboard focus", focused)
                page.keyboard.press("ArrowUp")
                page.keyboard.press("ArrowUp")
                page.wait_for_timeout(200)
                keyed = listener(page)
                check("arrow up nudges range by 0.1 m", close(keyed["range"], 2.2),
                      repr(keyed))
                check("arrow up leaves heading alone", close(keyed["heading"], 210),
                      repr(keyed))
                page.keyboard.press("Shift+ArrowRight")
                page.wait_for_timeout(200)
                keyed_heading = listener(page)
                check("shift+arrow right turns heading 15 degrees",
                      close(keyed_heading["heading"], 225), repr(keyed_heading))
                check("turning by keyboard leaves range alone",
                      close(keyed_heading["range"], 2.2), repr(keyed_heading))

                # --- Touch ---------------------------------------------------
                page.evaluate("window.scrollTo(0, 0)")
                centre = puck_centre(page)
                cdp = context.new_cdp_session(page)
                touch_start = (centre[0], centre[1] + 0.45 * scale)
                touch_drag(cdp, touch_start, (touch_start[0], touch_start[1] + 200))
                page.wait_for_timeout(200)
                touched = listener(page)
                check("touch scrub on the collar raises range",
                      touched["range"] > keyed_heading["range"], repr(touched))
                check("touch scrub leaves heading alone",
                      close(touched["heading"], keyed_heading["heading"]), repr(touched))

                # --- Persistence round-trip ----------------------------------
                final = listener(page)
                page.goto("about:blank")
                page.goto(base_url + "/#seats")
                page.wait_for_selector("#ws-status", state="attached", timeout=10000)
                reconnected = listener(page)
                check("reconnect restores the scrubbed range and heading",
                      close(reconnected["range"], final["range"])
                      and close(reconnected["heading"], final["heading"]),
                      repr(reconnected))
                check("listener still carries exactly the 4-value frame fields",
                      set(reconnected.keys()) == {"x", "y", "heading", "range"},
                      repr(reconnected))
                browser.close()
        finally:
            stop(server)
            log.close()

        reloaded = InstallationState(state_path)
        check("persisted installation.json carries the range",
              close(reloaded.data["listener"]["range"], final["range"]),
              repr(reloaded.data["listener"]))

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("22-listener-range-ux/02 checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
