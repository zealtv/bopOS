#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for Control-panel events.

The Control tab mounts the column in the dashboard document (the iframe was
retired in `3-iframe-retirement`).  This journey fires one declared event at
All, group, and Seat scope, then uses simfleet's stdout as the wire observer.  simfleet logs an event only after parsing the leading shared-time
string and validating every remaining argument as a float.
"""

import json
import os
import random
import re
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
        raise SystemExit("cannot locate bopOS repository")
    REPO = parent

FAILURES = []
RESERVED = set()
UID_A = "02:53:49:4d:00:01"
UID_B = "02:53:49:4d:00:02"


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""), flush=True)
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
    raise RuntimeError("could not reserve a local port")


def stop_process(process):
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


def read_log(path):
    try:
        with open(path, encoding="utf-8") as source:
            return source.read()
    except OSError:
        return ""


def event_ids(path, elements):
    """Return device IDs from simfleet's parsed event log for one float pair."""
    pattern = re.compile(
        r"id=(-?\d+) event strike fired dev_deadline=\d+ fire_mono=\d+ "
        r"elements=" + re.escape(elements) + r"(?: LATE)?$",
        re.MULTILINE)
    return [int(value) for value in pattern.findall(read_log(path))]


def wait_event_ids(path, elements, expected, timeout=8):
    deadline = time.monotonic() + timeout
    expected = set(expected)
    found = []
    while time.monotonic() < deadline:
        found = event_ids(path, elements)
        if expected.issubset(found):
            # Give a wrongly broad selector time to expose extra recipients.
            time.sleep(.75)
            return event_ids(path, elements)
        time.sleep(.1)
    return found


def make_fixture(root):
    patches = os.path.join(root, "patches")
    assets = os.path.join(root, "assets")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(assets)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"event-control-panel-verifier")
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({
            "engine": "test",
            "entrypoint": "main.bin",
            "params": [{
                "name": "density", "kind": "float", "min": 0, "max": 1,
                "default": .2, "dashboard": True,
            }],
            "events": [{
                "name": "strike", "arity": 2,
                "defaults": [64, 127],
                "dashboard": True,
            }],
            "caps": [],
            "slots": [],
        }, target)

    def seat(seat_id, name, uid, groups):
        return {
            "id": seat_id,
            "name": name,
            "positions": [[seat_id, 1]],
            "groups": groups,
            "bound": uid,
            "patch": "alpha",
            "params": {"density": .2},
        }

    state = {
        "schema": 1,
        "name": "Event control panel rig",
        "fleet_patch": {
            "name": "alpha", "fingerprint": "a" * 64,
            "staged_at": time.time(), "previous": None,
        },
        "params_patch": "alpha",
        "groups": {"7": {"id": 7, "name": "Front"}},
        "seats": {
            "1": seat(1, "Freda", UID_A, [7]),
            "2": seat(2, "Sparks", UID_B, []),
        },
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path


def surface(page):
    """The Control surface is mounted in this document since
    `3-iframe-retirement`. It is no longer a frame — but it is also no
    longer alone in its document, so every selector must be scoped to the
    Control host (CLAUDE.md gotcha 17) rather than reaching page-wide."""
    return page.locator("#control-column-host")


def click_once(page, locator):
    """Click a freshly measured point without Playwright stability waiting."""
    locator.wait_for(state="attached")
    locator.evaluate(
        "(element) => element.scrollIntoView({block: 'center', inline: 'center'})")
    box = locator.bounding_box()
    if box is None:
        raise RuntimeError("attached control has no bounding box")
    page.mouse.click(box["x"] + box["width"] / 2,
                     box["y"] + box["height"] / 2)


def set_event_values(row, values):
    """Set both boxes in one DOM turn and hold rendering until the fire click."""
    return row.evaluate(
        """(eventRow, values) => {
          const boxes = [...eventRow.querySelectorAll(".live-event-box")];
          const setter = Object.getOwnPropertyDescriptor(
            HTMLInputElement.prototype, "value").set;
          boxes.forEach((box, index) => {
            setter.call(box, String(values[index]));
            box.dispatchEvent(new Event("input", {bubbles: true}));
            box.dispatchEvent(new Event("change", {bubbles: true}));
          });
          boxes.at(-1)?.focus();
          return boxes.map(box => box.value);
        }""", values)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-event-control-") as temp:
        state_path = make_fixture(temp)
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log = open(os.path.join(temp, "server.log"), "w",
                          encoding="utf-8")
        fleet_log_path = os.path.join(temp, "fleet.log")
        fleet_log = open(fleet_log_path, "w", encoding="utf-8")
        server = fleet = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port),
                "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", assets, "--patches-dir", patches,
                "--public-url", base_url,
            ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "2", "--target", "127.0.0.1",
                "--report-port", str(listen_port),
                "--cmd-port", str(send_port),
                "--hb-interval", "0.5", "--boot-secs", "0.2",
                "--patches-dir", patches, "--assets-dir", assets,
                "--manifest", os.path.join(
                    patches, "alpha", "bopos.patch.json"),
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440,
                                                  "height": 1200})
                page.set_default_timeout(12000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))

                page.goto(base_url + "#control")
                page.wait_for_selector("#ws-status.online", state="attached")
                frame = surface(page)
                frame.locator(
                    '.live-card[data-live-scope="all"]'
                ).wait_for(state="attached")
                # One document now: the surface's frame IS the page's.
                live_frame = page.main_frame
                live_frame.wait_for_function(
                    "() => Object.keys(installation.devices || {}).length === 2")

                # --- declared event row anatomy ---
                section = frame.locator(
                    '.live-card[data-live-scope="all"] '
                    ".live-control-section-events")
                section.wait_for(state="attached")
                row = section.locator(
                    '.live-param-event[data-param-path="strike"]')
                row.wait_for(state="attached")
                shape = row.evaluate(
                    """eventRow => {
                      const boxes = [...eventRow.querySelectorAll(
                        ".live-event-box")];
                      return {
                        name: eventRow.querySelector(
                          ":scope > .live-param-name")?.textContent.trim(),
                        boxes: boxes.length,
                        editable: boxes.every(box =>
                          box.type === "number" && !box.disabled &&
                          !box.readOnly),
                        sendButtons: eventRow.querySelectorAll(
                          ".live-event-send").length,
                        allButtons: eventRow.querySelectorAll("button").length,
                        syncToggles: eventRow.querySelectorAll(
                          ".live-event-sync").length,
                      };
                    }""")
                # `inner_text` applies CSS `text-transform`, so the heading
                # comes back in whatever case the stylesheet renders it
                # (CLAUDE.md Playwright gotcha 1) -- compare case-insensitively.
                check("the Control surface shows an Events section",
                      section.locator(":scope > h3").inner_text().strip().lower()
                      == "events")
                check("the Events section contains the strike row",
                      shape["name"] == "strike", repr(shape))
                check("strike has two editable event element boxes",
                      shape["boxes"] == 2 and shape["editable"], repr(shape))
                check("strike has one fire button and no sync toggle",
                      shape["sendButtons"] == 1
                      and shape["allButtons"] == 1
                      and shape["syncToggles"] == 0, repr(shape))

                # --- All -> /all/e/strike ---
                click_once(page, frame.locator('[data-target-toggle="all"]'))
                row = frame.locator(
                    '.live-card[data-live-scope="all"] '
                    '.live-param-event[data-param-path="strike"]')
                row.wait_for(state="attached")
                all_values = [11.25, 22.5]
                typed = set_event_values(row, all_values)
                click_once(page, row.locator(".live-event-send"))
                all_ids = wait_event_ids(
                    fleet_log_path, "11.25 22.5", {1, 2})
                check("All fires /all/e/strike to both devices",
                      sorted(all_ids) == [1, 2], repr(all_ids))
                check("All carries the typed floats after shared time",
                      typed == ["11.25", "22.5"]
                      and sorted(all_ids) == [1, 2], repr(typed))

                # --- Group 7 -> /g7/e/strike ---
                # Chips, not modes (02-component-unification/07): selecting the
                # group chip replaces All with that one group.
                click_once(
                    page, frame.locator('[data-target-toggle="g7"]'))
                group_row = frame.locator(
                    '.live-card[data-live-scope="group"][data-live-id="7"] '
                    '.live-param-event[data-param-path="strike"]')
                group_row.wait_for(state="attached")
                group_values = [33.75, 44.125]
                typed = set_event_values(group_row, group_values)
                click_once(page, group_row.locator(".live-event-send"))
                group_ids = wait_event_ids(
                    fleet_log_path, "33.75 44.125", {1})
                check("Group 7 fires /g7/e/strike only to its member",
                      group_ids == [1], repr(group_ids))
                check("Group carries the typed floats after shared time",
                      typed == ["33.75", "44.125"]
                      and group_ids == [1], repr(typed))

                # --- Seat 2 -> /2/e/strike ---
                # Deselect the group and select Seat 2, leaving one Seat card.
                click_once(page, frame.locator('[data-target-toggle="g7"]'))
                click_once(page, frame.locator('[data-target-toggle="2"]'))
                seat_row = frame.locator(
                    '.live-card[data-live-scope="seat"][data-live-id="2"] '
                    '.live-param-event[data-param-path="strike"]')
                seat_row.wait_for(state="attached")
                seat_values = [55.5, 66.625]
                typed = set_event_values(seat_row, seat_values)
                click_once(page, seat_row.locator(".live-event-send"))
                seat_ids = wait_event_ids(
                    fleet_log_path, "55.5 66.625", {2})
                check("Seat 2 fires /2/e/strike only to device 2",
                      seat_ids == [2], repr(seat_ids))
                check("Seat carries the typed floats after shared time",
                      typed == ["55.5", "66.625"]
                      and seat_ids == [2], repr(typed))

                # --- the fire button's lead sweep and fire flash ---
                # `04-event-fire-affordance`: the feedback the retired `/cue`
                # buttons carried now lives on the row's fire button. The
                # button sweeps for exactly the lead the host sent, flashes on
                # arrival, then returns to rest.
                fire = seat_row.locator(".live-event-send")
                geometry = fire.evaluate(
                    """button => {
                      const rect = button.getBoundingClientRect();
                      const style = getComputedStyle(button);
                      return {width: Math.round(rect.width),
                              height: Math.round(rect.height),
                              radius: style.borderTopLeftRadius,
                              sweeps: button.querySelectorAll(
                                ".live-event-sweep").length};
                    }""")
                box_width = seat_row.locator(".live-event-box").first.evaluate(
                    "box => Math.round(box.getBoundingClientRect().width)")
                check("fire takes the value box's column width",
                      geometry["width"] == box_width, repr([geometry, box_width]))
                check("fire is a momentary-shaped panel object",
                      geometry["radius"] == "7px"
                      and geometry["sweeps"] == 1, repr(geometry))
                click_once(page, fire)
                # The class is applied in the click handler, so it is already
                # set by the time this evaluates; waiting keeps it robust
                # against a slow first paint.
                live_frame.wait_for_function(
                    """() => {
                      const button = document.querySelector(
                        '#control-column-host' +
                        ' .live-card[data-live-scope="seat"]' +
                        ' .live-param-event[data-param-path="strike"]' +
                        ' .live-event-send');
                      return button && button.classList.contains("firing");
                    }""")
                lead = fire.evaluate(
                    "button => button.style.getPropertyValue("
                    "'--event-lead-duration')")
                check("the sweep runs for the scheduled lead",
                      lead == "500ms", repr(lead))
                live_frame.wait_for_function(
                    """() => {
                      const button = document.querySelector(
                        '#control-column-host' +
                        ' .live-card[data-live-scope="seat"]' +
                        ' .live-param-event[data-param-path="strike"]' +
                        ' .live-event-send');
                      return button && button.classList.contains("fired");
                    }""")
                live_frame.wait_for_function(
                    """() => {
                      const button = document.querySelector(
                        '#control-column-host' +
                        ' .live-card[data-live-scope="seat"]' +
                        ' .live-param-event[data-param-path="strike"]' +
                        ' .live-event-send');
                      return button && !button.classList.contains("fired")
                        && !button.classList.contains("firing")
                        && !button.hasAttribute("aria-busy");
                    }""")
                check("the button returns to rest after the flash", True)

                check("no page errors", not errors, repr(errors))
                browser.close()
        finally:
            stop_process(fleet)
            stop_process(server)
            server_log.close()
            fleet_log.close()

    print()
    if FAILURES:
        print("FAILED: " + "; ".join(FAILURES))
        return 1
    print("Event control panel checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
