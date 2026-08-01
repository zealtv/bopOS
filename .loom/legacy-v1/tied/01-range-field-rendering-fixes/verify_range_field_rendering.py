#!/usr/bin/env python3
"""Playwright verification for 26-listener-range-fixes/01-range-field-rendering-fixes.

Covers the three rendering defects Bob found on the Seats tab (2026-07-21):

  1. the range indication drew outside the room rectangle;
  2. the gradient wash filled only the quadrant down-and-right of the puck;
  3. the range field lagged behind the puck during a listener drag.

Defects 1 and 2 turned out to be one root cause: clipPathUnits is
userSpaceOnUse, so `#spatial-room-clip` resolved in the coordinate system of the
element referencing it -- and that element sat inside a translate(listener) group,
sliding the room-shaped clip window by the listener position. The window's top-left
corner landed ON the listener, which is exactly why the wash squared off at the
listener's x/y and why a solid arc survived outside the room to the bottom-right.

Two of the checks here are pixel checks against a real screenshot rather than DOM
assertions, because an SVG element's getBoundingClientRect() reports its *geometry*
box and ignores clipping entirely -- the DOM cannot tell you what actually painted.
Needs Pillow in ~/.venvs/bopos (see the stitch notes).
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

from PIL import Image
from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent

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


def shoot(page, path):
    page.screenshot(path=path)
    return Image.open(path).convert("RGB")


def sample(image, ratio, x, y):
    """Read a device-pixel from a CSS-pixel coordinate."""
    return image.getpixel((int(x * ratio), int(y * ratio)))


def differs(a, b, threshold=6):
    return max(abs(int(p) - int(q)) for p, q in zip(a, b)) >= threshold


def main():
    with tempfile.TemporaryDirectory() as temp:
        # Bob's room: 10 x 8, diagonal 12.806 m.
        room = {"width": 10.0, "depth": 8.0, "units": "m"}
        diagonal = math.hypot(room["width"], room["depth"])
        state_path = os.path.join(temp, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({
                "schema": 1, "name": "range-field-fixture",
                "room": room,
                "listener": {"x": 5.0, "y": 4.0, "heading": 0.0, "range": 5.73},
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
                context = browser.new_context(viewport={"width": 1400, "height": 1200})
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
                ratio = page.evaluate("() => window.devicePixelRatio")

                # --- 1. the dashed out-of-room arc is retired -----------------
                check("the out-of-room dashed arc is gone (Bob 2026-07-21)",
                      page.evaluate(
                          "() => !document.querySelector('#spatial .listener-ring-outside')"))

                # --- the root cause: the clip window must BE the room ---------
                # Map the clip rect (0,0,W,D) through the CTM of the element that
                # references the clip path, and compare with the room rect on screen.
                # Before the fix these differed by exactly the listener offset.
                clip = page.evaluate(
                    """() => {
                      const svg = document.querySelector('#spatial svg') ||
                                  document.querySelector('#spatial');
                      const ref = document.querySelector('#spatial .listener-range-field');
                      const room = document.querySelector('#spatial .room');
                      const rect = document.querySelector('#spatial-room-clip rect') ||
                                   document.querySelector('clipPath#spatial-room-clip rect');
                      const m = ref.getScreenCTM();
                      const owner = ref.ownerSVGElement;
                      const corner = (x, y) => {
                        const p = owner.createSVGPoint(); p.x = x; p.y = y;
                        return p.matrixTransform(m);
                      };
                      const w = Number(rect.getAttribute('width'));
                      const h = Number(rect.getAttribute('height'));
                      const a = corner(0, 0), b = corner(w, h);
                      const rr = room.getBoundingClientRect();
                      return {clip: [a.x, a.y, b.x, b.y],
                              room: [rr.x, rr.y, rr.x + rr.width, rr.y + rr.height]};
                    }""")
                deltas = [abs(c - r) for c, r in zip(clip["clip"], clip["room"])]
                check("the room clip window coincides with the room rect on screen",
                      max(deltas) < 1.5,
                      f"clip={clip['clip']} room={clip['room']} deltas={deltas}")

                # --- range at the diagonal max, then look at real pixels ------
                page.evaluate(
                    "d => { installation.listener.range = d;"
                    " ws.send('set_listener', JSON.parse(JSON.stringify(installation.listener)));"
                    " Spatial.frame(); }", arg=diagonal)
                page.wait_for_timeout(300)
                maxed = listener(page)
                check("range sits at the diagonal ceiling for the paint check",
                      close(maxed["range"], diagonal, 0.05), repr(maxed))

                geometry = page.evaluate(
                    """() => {
                      const room = document.querySelector('#spatial .room')
                        .getBoundingClientRect();
                      const body = document.querySelector('#spatial .listener-body')
                        .getBoundingClientRect();
                      return {room: [room.x, room.y, room.width, room.height],
                              puck: [body.x + body.width / 2, body.y + body.height / 2]};
                    }""")
                rx, ry, rw, rh = geometry["room"]
                px, py = geometry["puck"]
                scale = rw / room["width"]

                shot_dir = HERE
                after = shoot(page, os.path.join(shot_dir, "after-dark.png"))

                # Background reference: a point well outside the room, clear of the
                # tray and the panel furniture, sampled from the same screenshot.
                outside_probes = [
                    ("left of the room", rx - 14, ry + rh * 0.5),
                    ("right of the room", rx + rw + 14, ry + rh * 0.5),
                    ("above the room", rx + rw * 0.5, ry - 14),
                ]
                base = sample(after, ratio, rx - 30, ry + rh * 0.5)
                for label, x, y in outside_probes:
                    check(f"nothing of the range field paints {label}",
                          not differs(sample(after, ratio, x, y), base),
                          f"pixel={sample(after, ratio, x, y)} base={base}")

                # --- 2. the wash covers all four quadrants -------------------
                # Drop back to a small range so there is plenty of BARE ROOM to use
                # as the reference: the reference must be a room pixel, not a pixel
                # outside the room, or it only measures the room's own fill and
                # passes even when three quadrants are unpainted.
                page.evaluate(
                    "() => { installation.listener.range = 2.0;"
                    " ws.send('set_listener', JSON.parse(JSON.stringify(installation.listener)));"
                    " Spatial.frame(); }")
                page.wait_for_timeout(300)
                small = shoot(page, os.path.join(shot_dir, "after-dark-gradient.png"))
                scale_px = rw / room["width"]
                bare = sample(small, ratio, rx + rw - 8, ry + rh - 8)  # far room corner

                reach = 0.8 * scale_px  # well inside the 2.0 m range
                quadrants = {
                    "up-left": (px - reach, py - reach),
                    "up-right": (px + reach, py - reach),
                    "down-left": (px - reach, py + reach),
                    "down-right": (px + reach, py + reach),
                }
                tint = {k: sample(small, ratio, *v) for k, v in quadrants.items()}
                check("the gradient wash covers all four quadrants around the puck",
                      all(differs(v, bare) for v in tint.values()),
                      f"probes={tint} bare-room={bare}")
                # A correct radial gradient is symmetric: equal radius, equal colour.
                spread = [max(abs(int(a) - int(b)) for a, b in zip(v, w))
                          for v in tint.values() for w in tint.values()]
                check("the wash is radially symmetric about the listener",
                      max(spread) <= 4, f"probes={tint} max-spread={max(spread)}")

                # The wash must still be denser at the listener than at the edge --
                # the ratified visual intent survives the fix.
                near = sample(small, ratio, px + 0.3 * scale_px, py)
                far = sample(small, ratio, px + 1.8 * scale_px, py)
                check("the wash stays denser at the listener than toward the edge",
                      differs(near, far, 3), f"near={near} far={far} bare={bare}")

                # --- the tick clips with the ring ----------------------------
                check("the magnitude tick clips with the ring (one clipped group)",
                      page.evaluate(
                          "() => { const t = document.querySelector('#spatial .listener-tick');"
                          " const r = document.querySelector('#spatial .listener-ring');"
                          " return !!t && t.parentNode === r.parentNode; }"))

                # --- 3. the field tracks the puck MID-drag -------------------
                page.evaluate("window.scrollTo(0, 0)")
                before_drag = listener(page)
                fresh = page.evaluate(
                    """() => { const b = document.querySelector('#spatial .listener-body')
                         .getBoundingClientRect();
                       return [b.x + b.width / 2, b.y + b.height / 2]; }""")
                target = (fresh[0] - min(rw, rh) * 0.2, fresh[1] + min(rh, rw) * 0.2)
                page.mouse.move(*fresh)
                page.mouse.down()
                mid_states = []
                for step in range(1, 7):
                    page.mouse.move(fresh[0] + (target[0] - fresh[0]) * step / 6,
                                    fresh[1] + (target[1] - fresh[1]) * step / 6)
                    # Fall back to the pre-fix wrapper so a regression run reports a
                    # failure instead of crashing on a null.
                    mid_states.append(page.evaluate(
                        "() => { const q = s => document.querySelector('#spatial ' + s);"
                        " const field = q('.listener-range-at') || q('.listener-range-field');"
                        " return {puck: q('.listener-puck')?.getAttribute('transform'),"
                        "  field: field?.getAttribute('transform')}; }"))
                moved_mid = mid_states[-1]["puck"] != mid_states[0]["puck"]
                tracked = all(s["puck"] == s["field"] for s in mid_states)
                page.mouse.up()
                page.wait_for_timeout(200)
                check("the puck actually moved during the drag (guard is live)",
                      moved_mid, repr(mid_states[:2]))
                check("the range field tracks the puck mid-drag, not only at mouseup",
                      tracked, repr(mid_states))

                dropped = listener(page)
                check("the drag committed a new listener position",
                      not close(dropped["x"], before_drag["x"])
                      or not close(dropped["y"], before_drag["y"]), repr(dropped))
                check("the drag left the range untouched",
                      close(dropped["range"], before_drag["range"], 0.05), repr(dropped))

                # --- light theme: same geometry, tokens still resolve --------
                page.evaluate("document.documentElement.setAttribute('data-theme', 'light')")
                page.wait_for_timeout(200)
                light = shoot(page, os.path.join(shot_dir, "after-light.png"))
                light_base = sample(light, ratio, rx - 30, ry + rh * 0.5)
                light_outside = sample(light, ratio, rx + rw + 14, ry + rh * 0.5)
                check("nothing paints outside the room in the light theme",
                      not differs(light_outside, light_base),
                      f"pixel={light_outside} base={light_base}")
                page.evaluate("document.documentElement.setAttribute('data-theme', 'dark')")

                context.close()
                browser.close()
        finally:
            stop(server)
            log.close()
            if FAILURES:
                with open(log_path, encoding="utf-8") as handle:
                    tail = handle.read()[-2000:]
                print("\n--- dashboard log tail ---\n" + tail)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): " + "; ".join(FAILURES))
        return 1
    print("all range-field rendering checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
