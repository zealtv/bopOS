#!/usr/bin/env python3
"""Playwright verification for 26-listener-range-fixes/02-retire-listener-toolbar.

Bob, 2026-07-21: "remove the listener tool bar -- not required, all control can be
graphical."

So the point of this guard is not that the bar is gone (one selector) but that
nothing the bar did was lost with it: heading, range and position must all still
be settable by pointer AND keyboard, the values must still round-trip through
set_listener and survive a reload, and the puck's aria-label -- now the only
textual statement of those values anywhere in the UI -- must track a gesture
live rather than only updating at render.
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


def aria(page):
    return page.evaluate(
        "() => document.querySelector('#spatial .listener-puck')"
        "?.getAttribute('aria-label') || ''")


def puck_centre(page):
    return page.evaluate(
        "() => { const b = document.querySelector('#spatial .listener-body')"
        ".getBoundingClientRect();"
        " return [b.x + b.width / 2, b.y + b.height / 2]; }")


def main():
    with tempfile.TemporaryDirectory() as temp:
        room = {"width": 10.0, "depth": 8.0, "units": "m"}
        diagonal = math.hypot(room["width"], room["depth"])
        state_path = os.path.join(temp, "installation.json")
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump({
                "schema": 1, "name": "toolbar-retirement-fixture",
                "room": room,
                "listener": {"x": 5.0, "y": 4.0, "heading": 0.0, "range": 3.0},
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

                # --- the bar and every id it owned are gone ------------------
                gone = page.evaluate(
                    """() => ({bar: !!document.getElementById('listener-bar'),
                               range: !!document.getElementById('listener-range'),
                               heading: !!document.getElementById('listener-heading'),
                               readout: !!document.getElementById('listener-readout')})""")
                check("the Listener toolbar and all three of its controls are gone",
                      not any(gone.values()), repr(gone))

                # The map itself must still be there -- a guard that passes because
                # the whole panel failed to render would be worthless.
                check("the listener puck still renders (the bar went, not the map)",
                      page.evaluate(
                          "() => !!document.querySelector('#spatial .listener-puck')"))

                # --- range: still settable by pointer (collar scrub) ---------
                centre = puck_centre(page)
                scale = page.evaluate(
                    "() => { const r = document.querySelector('#spatial .room')"
                    ".getBoundingClientRect(); return r.width / 10.0; }")
                collar_point = (centre[0], centre[1] + 0.45 * scale)
                page.mouse.move(*collar_point)
                page.mouse.down()
                page.mouse.move(collar_point[0], collar_point[1] + 60)
                page.mouse.move(collar_point[0], collar_point[1] + 120)
                mid_aria = aria(page)
                mid_label = page.evaluate(
                    """() => { const p = document.querySelector('#spatial .listener-puck');
                         return {text: p.querySelector('.listener-value')?.textContent,
                                 shown: p.classList.contains('gesturing')}; }""")
                page.mouse.up()
                page.wait_for_timeout(200)
                scrubbed = listener(page)
                check("range is still settable by collar scrub",
                      scrubbed["range"] > 3.0, repr(scrubbed))
                check("the on-canvas value label shows during the range gesture",
                      mid_label["shown"] and mid_label["text"].endswith("m"),
                      repr(mid_label))
                check("aria-label reports the new range MID-gesture, not just at render",
                      f"range {scrubbed['range']}" in mid_aria
                      or any(str(round(scrubbed["range"], 2)) in mid_aria for _ in [0]),
                      f"mid={mid_aria!r} final={scrubbed}")

                # --- heading: still settable by dragging the tip -------------
                page.evaluate("window.scrollTo(0, 0)")
                centre = puck_centre(page)
                tip = page.evaluate(
                    "() => { const b = document.querySelector('#spatial .listener-tip')"
                    ".getBoundingClientRect();"
                    " return [b.x + b.width / 2, b.y + b.height / 2]; }")
                page.mouse.move(*tip)
                page.mouse.down()
                page.mouse.move(centre[0] + 1.2 * scale, centre[1])
                page.mouse.move(centre[0] + 1.6 * scale, centre[1])
                heading_aria = aria(page)
                heading_label = page.evaluate(
                    "() => document.querySelector('#spatial .listener-value')?.textContent")
                page.mouse.up()
                page.wait_for_timeout(200)
                aimed = listener(page)
                check("heading is still settable by dragging the tip",
                      close(aimed["heading"], 90, 6), repr(aimed))
                check("the tip drag left range untouched",
                      close(aimed["range"], scrubbed["range"], 0.05), repr(aimed))
                check("the value label reports degrees during a heading gesture",
                      (heading_label or "").endswith("°"), repr(heading_label))
                check("aria-label tracks heading mid-gesture",
                      "heading" in heading_aria and "degrees" in heading_aria,
                      repr(heading_aria))

                # --- position: still settable by dragging the puck -----------
                page.evaluate("window.scrollTo(0, 0)")
                centre = puck_centre(page)
                page.mouse.move(*centre)
                page.mouse.down()
                page.mouse.move(centre[0] - 1.5 * scale, centre[1] + 1.0 * scale)
                page.mouse.move(centre[0] - 2.0 * scale, centre[1] + 1.5 * scale)
                move_label = page.evaluate(
                    "() => document.querySelector('#spatial .listener-value')?.textContent")
                page.mouse.up()
                page.wait_for_timeout(200)
                moved = listener(page)
                check("position is still settable by dragging the puck",
                      not close(moved["x"], 5.0) and not close(moved["y"], 4.0), repr(moved))
                check("the value label reports coordinates during a move gesture",
                      (move_label or "").endswith("m") and "," in (move_label or ""),
                      repr(move_label))

                # --- keyboard paths still work with no input in the row ------
                page.evaluate(
                    "() => document.querySelector('#spatial .listener-puck').focus()")
                focused = page.evaluate(
                    "() => document.activeElement.classList.contains('listener-puck')")
                check("the puck still takes keyboard focus with the bar gone", focused)

                before_keys = listener(page)
                page.keyboard.press("ArrowUp")
                page.wait_for_timeout(120)
                after_up = listener(page)
                check("arrow up still nudges range by 0.1 m",
                      close(after_up["range"], before_keys["range"] + 0.1),
                      f"{before_keys['range']} -> {after_up['range']}")
                key_label = page.evaluate(
                    """() => { const p = document.querySelector('#spatial .listener-puck');
                         return {text: p.querySelector('.listener-value')?.textContent,
                                 shown: p.classList.contains('gesturing')}; }""")
                check("the value label shows for the keyboard range path too",
                      key_label["shown"], repr(key_label))

                page.keyboard.press("Shift+ArrowRight")
                page.wait_for_timeout(120)
                after_turn = listener(page)
                check("shift+arrow right still turns heading 15 degrees",
                      close(after_turn["heading"],
                            (after_up["heading"] + 15) % 360, 0.6),
                      f"{after_up['heading']} -> {after_turn['heading']}")
                check("turning by keyboard still leaves range alone",
                      close(after_turn["range"], after_up["range"]), repr(after_turn))

                # the label must not stick around forever on the keyboard path
                page.wait_for_timeout(1100)
                check("the value label fades after a keyboard nudge (no end event)",
                      not page.evaluate(
                          "() => document.querySelector('#spatial .listener-puck')"
                          ".classList.contains('gesturing')"))

                # --- values round-trip and survive a reload ------------------
                expected = listener(page)
                page.reload()
                page.wait_for_selector("#ws-status", state="attached", timeout=10000)
                page.wait_for_selector("#spatial .listener-collar", timeout=10000)
                reloaded = listener(page)
                check("range, heading and position all survive a reload",
                      close(reloaded["range"], expected["range"])
                      and close(reloaded["heading"], expected["heading"], 0.6)
                      and close(reloaded["x"], expected["x"])
                      and close(reloaded["y"], expected["y"]),
                      f"{expected} -> {reloaded}")

                with open(state_path, encoding="utf-8") as handle:
                    persisted = json.load(handle)["listener"]
                check("the persisted installation.json carries the gestured values",
                      close(persisted["range"], expected["range"])
                      and close(persisted["heading"], expected["heading"], 0.6),
                      repr(persisted))

                # --- screenshots of the tidied header row --------------------
                page.evaluate("window.scrollTo(0, 0)")
                for theme in ("dark", "light"):
                    page.evaluate("t => document.documentElement.setAttribute('data-theme', t)",
                                  arg=theme)
                    for width, tag in ((1400, "wide"), (760, "narrow")):
                        page.set_viewport_size({"width": width, "height": 1000})
                        page.wait_for_timeout(250)
                        page.screenshot(path=os.path.join(HERE, f"after-{theme}-{tag}.png"))
                page.set_viewport_size({"width": 1400, "height": 1200})

                context.close()
                browser.close()
        finally:
            stop(server)
            log.close()
            if FAILURES:
                with open(log_path, encoding="utf-8") as handle:
                    print("\n--- dashboard log tail ---\n" + handle.read()[-2000:])

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): " + "; ".join(FAILURES))
        return 1
    print("all listener-toolbar-retirement checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
