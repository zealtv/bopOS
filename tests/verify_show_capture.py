#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for venue-wide capture-as-Show-step
(`08-control-tab-columns/4-n-columns/2-venue-wide-capture`, D1-D3).

What this pins, each one a ruling:

  * capture is ONE unparameterised action reachable from TWO surfaces -- the
    Control tab's strip and the Show tab's edit bar -- and never from inside a
    column, because a column's scope is not what capture takes;
  * NO DIALOGS: the two alert()s and the confirm() are gone, replaced by
    ambient count -> arm -> non-modal preview -> commit -> inline undo. This
    file fails if any dialog opens at all;
  * the preview lists the messages the server would mint, marks a DIRTY row
    ("captures the preset, not the edits") and says whether each target is
    portable or site-bound -- all derived locally, with no round trip;
  * the two disabled states name their causes IN PLACE, and tell "nothing
    applied since the dashboard started" (provenance is never persisted, so a
    restart clears it) apart from "nothing applied";
  * a captured step is named after what it holds (`Dawn`), not "Captured
    presets", and lands in the Show tab's click-to-edit rename;
  * undo removes it, and the offer withdraws once it is no longer the top of
    the undo stack.

Owned by code surface (show-capture.js, control-host.js, show.js,
dashboard/server.py capture verb).
"""

import json
import os
import random
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
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before serving HTTP")
        try:
            urllib.request.urlopen(url, timeout=1).read()
            return
        except OSError:
            time.sleep(.2)
    raise RuntimeError("dashboard did not serve HTTP")


def make_fixture(root):
    patches = os.path.join(root, "patches")
    assets = os.path.join(root, "assets")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(assets)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"show-capture-verifier")
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin",
            "params": [
                {"name": "density", "kind": "float", "min": 0, "max": 1,
                 "default": .2, "dashboard": True},
            ],
            "events": [], "caps": [], "slots": [],
        }, target)

    def seat(seat_id, name, uid, groups):
        return {"id": seat_id, "name": name, "positions": [[seat_id, 1]],
                "groups": groups, "bound": uid, "patch": "alpha",
                "params": {"density": .2}}

    state = {
        "schema": 1, "name": "Capture rig",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        # Both seats in one named group, so `capture_target` can prefer the
        # PORTABLE `group:Pair` shape -- and so the site-bound shape is a real
        # contrast rather than the only option.
        "groups": {"1": {"id": 1, "name": "Pair"}},
        "next_group_id": 2,
        "seats": {"1": seat(1, "Freda", UID_A, [1]),
                  "2": seat(2, "Sparks", UID_B, [1])},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path


def send(page, kind, payload):
    page.evaluate(f"() => ws.send({kind!r}, {json.dumps(payload)})")


def capture_button(page, host):
    return page.locator(f"{host} .show-capture-button")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-capture-") as temp:
        state_path = make_fixture(temp)
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log = open(os.path.join(temp, "server.log"), "w",
                          encoding="utf-8")
        fleet_log = open(os.path.join(temp, "fleet.log"), "w",
                         encoding="utf-8")
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
                "--manifest", os.path.join(patches, "alpha",
                                           "bopos.patch.json"),
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440,
                                                  "height": 1200})
                page.set_default_timeout(15000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                # D2: not "the dialogs are nicer" -- there are NO dialogs. A
                # handler that records rather than accepts is the assertion:
                # anything that opens one leaves evidence, and an un-accepted
                # dialog would also hang the run it appeared in.
                dialogs = []
                page.on("dialog", lambda dialog: (
                    dialogs.append(dialog.message), dialog.dismiss()))

                page.goto(base_url + "#control")
                page.wait_for_selector("#ws-status.online")
                # Read the step back from the server's own broadcast rather
                # than from the DOM: what lands in the show is the assertion,
                # and the Show tab may not even be rendered yet.
                page.evaluate(
                    "() => ws.on('show', data => { window.__lastShow = data; })")
                control = "#control-column-host"
                page.locator(f'{control} .live-card[data-live-scope="all"]'
                             ).wait_for()

                strip = capture_button(page, "#control-capture-slot")
                strip.wait_for()

                # --- disabled state 1: no show ---
                check("with no Show loaded the control is disabled and says so",
                      strip.is_disabled()
                      and "no Show loaded" in strip.inner_text(),
                      repr(strip.inner_text()))

                # --- disabled state 2: a show, but no provenance ---
                send(page, "create_show", {"name": "opening"})
                page.wait_for_function(
                    "() => !document.querySelector('#control-capture-slot"
                    " .show-capture-button').title.includes('Load or create')")
                page.wait_for_function(
                    "() => document.querySelector("
                    "'#control-capture-slot .show-capture-button')"
                    "?.disabled === true")
                check("an empty capture names the restart-amnesia cause",
                      "nothing applied this session" in strip.inner_text(),
                      repr(strip.inner_text()))

                # --- ambient count, with no click and no request ---
                send(page, "save_patch_preset",
                     {"scope": "all", "patch": "alpha", "name": "Dawn",
                      "include": ["density"]})
                page.wait_for_function(
                    "() => (installation.preset_catalog?.alpha || []).length"
                    " === 1")
                send(page, "apply_preset",
                     {"scope": "all", "patch": "alpha", "name": "Dawn"})
                page.wait_for_function(
                    "() => installation.seats['1'].applied_preset?.name"
                    " === 'Dawn'")
                page.wait_for_function(
                    "() => document.querySelector("
                    "'#control-capture-slot .show-capture-button')"
                    "?.disabled === false")
                check("the count is ambient and derived from provenance",
                      "2/2" in strip.inner_text(), repr(strip.inner_text()))

                # --- arm: a non-modal preview, not a confirm ---
                strip.click()
                preview = page.locator(
                    "#control-capture-panel .show-capture-preview")
                preview.wait_for()
                rows = preview.locator("tbody tr")
                check("arming previews the messages the server would mint",
                      rows.count() == 1
                      and "Dawn" in rows.first.inner_text()
                      and "all Seats" in rows.first.inner_text(),
                      repr(rows.first.inner_text()))
                check("a portable target says so",
                      preview.locator(".show-capture-note").first.inner_text()
                      == "portable")

                # --- a dirty row is marked, and omissions are counted ---
                page.locator(
                    "#control-capture-panel [data-show-capture='cancel']"
                    ).click()
                send(page, "apply_preset",
                     {"scope": "seat", "id": 2, "patch": "alpha",
                      "name": None})
                page.wait_for_function(
                    "() => !installation.seats['2'].applied_preset")
                send(page, "set_live_param",
                     {"scope": "seat", "id": 1, "name": "density",
                      "value": .9})
                page.wait_for_function(
                    "() => installation.seats['1'].preset_dirty === true")
                strip.click()
                preview.wait_for()
                heading = preview.locator("h2").inner_text()
                check("the preview counts what it will NOT capture",
                      "1 message" in heading and "1 Seat omitted" in heading,
                      repr(heading))
                check("a dirty row warns that it captures the preset, "
                      "not the edits",
                      preview.locator(".show-capture-warn").count() == 1)
                check("a seat-id target is marked site-bound",
                      "site-bound" in preview.locator(
                          ".show-capture-note").first.inner_text()
                      and "Seat 1" in rows.first.inner_text(),
                      repr(rows.first.inner_text()))
                check("the omitted seats are shown, not silently dropped",
                      preview.locator(".show-capture-omitted").count() == 1)

                # --- commit: a derived name, and an inline undo ---
                page.locator(
                    "#control-capture-panel [data-show-capture='commit']"
                    ).click()
                page.wait_for_function(
                    "() => document.querySelector('#control-capture-slot"
                    " .show-capture-done')")
                check("the preview closes on commit",
                      preview.count() == 0)

                page.wait_for_function(
                    "() => window.__lastShow?.items?.length === 1")
                step = page.evaluate("() => window.__lastShow.items[0]")
                check("the captured step is named after what it holds (D3)",
                      step["alias"] == "Dawn", repr(step["alias"]))
                check("the captured step carries the site-bound target",
                      [message["target"] for message in step["messages"]]
                      == [["1"]], repr(step["messages"]))

                # --- undo, from the same slot ---
                page.locator(
                    "#control-capture-slot .show-capture-undo").click()
                page.wait_for_function(
                    "() => window.__lastShow?.items?.length === 0")
                check("undo removes the captured step",
                      page.evaluate("() => window.__lastShow.items.length")
                      == 0)

                # --- the same action, from the Show tab's edit bar ---
                page.click("#tab-button-show")
                show_button = capture_button(page, "#show-root .show-edit-bar")
                show_button.wait_for()
                check("the Show tab's edit bar offers the same action",
                      "2/2" not in show_button.inner_text()
                      and "1/2" in show_button.inner_text(),
                      repr(show_button.inner_text()))
                show_button.click()
                page.locator(
                    "#show-root .show-capture-preview").wait_for()
                page.locator(
                    "#show-root [data-show-capture='commit']").click()
                page.wait_for_function(
                    "() => window.__lastShow?.items?.length === 1")
                rename = page.locator("#show-root [data-show-name-input]")
                rename.wait_for()
                check("the captured step lands in click-to-edit rename (D3)",
                      rename.input_value() == "Dawn",
                      repr(rename.input_value()))

                # --- the offer withdraws once it stops being undoable ---
                # `undo_show` pops the LAST show mutation, whatever it was. An
                # undo offer that outlives an intervening edit does not undo
                # the capture -- it silently discards that edit instead.
                check("the undo offer is on screen before anything else edits",
                      page.locator("#show-root .show-capture-done").count() == 1)
                page.locator(
                    '#show-root [data-edit-bar-action="add-step"]').click()
                page.wait_for_function(
                    "() => window.__lastShow?.items?.length === 2")
                check("an intervening show edit withdraws the undo offer",
                      page.locator("#show-root .show-capture-done").count() == 0
                      and page.locator(
                          "#show-root .show-capture-button").count() == 1)

                # --- the whole point: none of this was a dialog ---
                check("no alert or confirm was ever opened (D2)",
                      dialogs == [], repr(dialogs))
                check("no page errors", not errors, repr(errors))
        finally:
            stop_process(fleet)
            stop_process(server)
            server_log.close()
            fleet_log.close()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed:")
        for label in FAILURES:
            print(f"  - {label}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
