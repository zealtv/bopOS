#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for the Control tab (thread 37,
stitch 10).

Bob's rulings, each one a check:

  * the Dashboard tab is renamed CONTROL -- and an existing #dashboard bookmark
    still resolves, because renaming a route silently breaks links;
  * the target filter is All / Groups / Seat, built as a REUSABLE component
    (window.SeatFilter) rather than a widget belonging to this tab, and it
    scopes the surface below it;
  * the Seat choice is shared -- picking a Seat on the Seats tab is the Seat
    the filter lands on;
  * CUES sit above the surface;
  * PRESETS follow the target filter: the shelf names the current target, and a
    save under one Seat captures that Seat rather than the whole venue.

Also pins the correction that came with the ratification: the Control tab hosts
NO patch deployment -- the picker stays on the Patches tab.

Owned by code surface (seat-filter.js, facilitator.js, dashboard.js tabs).
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


def make_fixture(root):
    patches = os.path.join(root, "patches")
    assets = os.path.join(root, "assets")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(assets)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"control-tab-verifier")
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin",
            "params": [{"name": "density", "kind": "float", "min": 0, "max": 1,
                        "default": .2, "dashboard": True}],
            "events": [{"name": "go", "arity": 0, "dashboard": True}],
            "caps": [], "slots": [],
        }, target)

    def seat(seat_id, name, uid, groups):
        return {"id": seat_id, "name": name, "positions": [[seat_id, 1]],
                "groups": groups, "bound": uid, "patch": "alpha",
                "params": {"density": .2}}

    state = {
        "schema": 1, "name": "Control tab rig",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "groups": {"0": {"id": 0, "name": "Front"}},
        "seats": {"1": seat(1, "Freda", UID_A, [0]),
                  "2": seat(2, "Sparks", UID_B, [])},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path


def surface(page):
    """The Control surface is an iframe; its filter and cards live inside."""
    return page.frame_locator("#dashboard-live-view")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-control-tab-") as temp:
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
                page.set_default_timeout(12000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())

                # --- the rename, and the old bookmark ---
                page.goto(base_url + "#dashboard")
                page.wait_for_selector("#ws-status.online")
                check("the tab is labelled Control",
                      page.locator("#tab-button-control").inner_text().strip()
                      == "Control")
                check("an existing #dashboard bookmark still opens the tab",
                      page.locator("#tab-control").get_attribute("hidden")
                      is None)
                check("no tab is still called Dashboard",
                      page.locator('[data-tab="dashboard"]').count() == 0)

                # --- 02-component-unification/03-chrome-reclamation ---
                # The standalone view moved into the tab bar and is named
                # Remote. It is an <a> to another document, so it must sit
                # BESIDE role="tablist"; inside it, assistive tech announces a
                # seventh tab that isn't one.
                check("the standalone view is a tab-bar link named Remote",
                      page.locator(".primary-tabs #facilitator-link")
                      .inner_text().strip() == "Remote")
                check("the Remote link points at the standalone view",
                      page.locator("#facilitator-link").get_attribute("href")
                      == "/facilitator")
                check("the Remote link is outside the tablist",
                      page.locator('[role="tablist"] #facilitator-link')
                      .count() == 0)
                # Scoped to the primary list on purpose: the Seats sidebar and
                # the Monitor dock are tablists too.
                check("the primary tablist still holds exactly the six tabs",
                      page.locator('#primary-tabs[role="tablist"] [role="tab"]')
                      .count() == 6)
                check("the dead Control heading is gone",
                      page.locator("#tab-control h2").count() == 0
                      and page.locator("#tab-control .eyebrow").count() == 0)

                # --- the Control tab hosts no patch deployment ---
                check("the Control tab hosts no patch picker",
                      page.locator("#tab-control #patch-target").count() == 0
                      and page.locator("#tab-control #patch-select").count()
                      == 0)
                check("the patch picker is still on the Patches tab",
                      page.locator("#tab-patches #patch-target").count() == 1)

                # --- the filter is the reusable component ---
                frame = surface(page)
                frame.locator(".target-filter").wait_for()
                check("the filter is a reusable component, not a local widget",
                      page.frames[-1].evaluate(
                          "() => typeof window.SeatFilter?.create"
                          " === 'function'"))
                modes = frame.locator(
                    ".target-filter [data-target-mode]").all_text_contents()
                check("the filter offers All / Groups / Seat",
                      [item.strip() for item in modes]
                      == ["All", "Groups", "Seat"], repr(modes))

                # --- events sit above the parameters, inside the panel ---
                # `/cue` is retired (thread 44 child 4) and the top event panel
                # went with it (`04-event-fire-affordance`): firing lives on the
                # panel's own rows, and the Events section leads the card.
                check("the retired top event panel is gone",
                      page.frames[-1].evaluate(
                          "() => !document.querySelector('#event-panel')"
                          " && !document.querySelector('#event-lead')"))
                check("events sit above parameters in the panel",
                      page.frames[-1].evaluate(
                          "() => { const card ="
                          " document.querySelector('.live-card');"
                          " const sections = [...card.querySelectorAll("
                          "'.live-control-section')].map(node =>"
                          " node.className.includes('-events')"
                          " ? 'events' : 'parameters');"
                          " return sections[0] === 'events'; }"))

                # --- the filter scopes the surface ---
                frame.locator('.live-card[data-live-scope="all"]').wait_for()
                check("All shows the aggregate card only",
                      frame.locator(".live-card").count() == 1)

                # --- the preset row (01-control-panel/7, made live by
                # 41-preset-primitive/07) ---
                # The slot shipped inert; the preset system landed into it
                # without redesigning it, so the ratified anatomy and placement
                # are still what this checks. Behaviour lives in
                # verify_preset_surfaces.py.
                slot = frame.locator(
                    '.live-card[data-live-scope="all"] [data-preset-slot]')
                check("the panel carries the preset row",
                      slot.count() == 1)
                check("the preset row names the live patch",
                      slot.locator(".live-preset-patch").inner_text().strip()
                      == "alpha")
                check("it offers the ratified preset controls",
                      slot.locator(".live-preset-select").count() == 1
                      and [button.strip() for button in slot.locator(
                          ".live-preset-action").all_text_contents()]
                      == ["new", "save", "del"])
                placement = page.frames[-1].evaluate(
                    """() => {
                      const card = document.querySelector(
                        '.live-card[data-live-scope="all"]');
                      const row = card.querySelector("[data-preset-slot]");
                      const head = card.querySelector(".live-card-head");
                      const rows = card.querySelector(".promoted-controls");
                      const after = Node.DOCUMENT_POSITION_FOLLOWING;
                      return {
                        belowHead: !!(head.compareDocumentPosition(row) & after),
                        aboveRows: !!(row.compareDocumentPosition(rows) & after),
                        live: [...row.querySelectorAll("select,button")]
                          .filter(control => !control.disabled).length,
                      };
                    }""")
                check("the preset row sits between the header and the rows",
                      placement["belowHead"] and placement["aboveRows"],
                      repr(placement))
                # Supersedes this file's two `7-preset-slot` inertness checks:
                # Bob ratified the preset design in `41-preset-primitive/1`, so
                # the row is live and the visually-hidden "not built yet" note
                # is gone with it.
                check("the preset row is live, not a placeholder",
                      placement["live"] > 0, repr(placement))

                frame.locator('[data-target-mode="groups"]').click()
                frame.locator('.live-card[data-live-scope="group"]').wait_for()
                check("Groups shows the group cards",
                      frame.locator(
                          '.live-card[data-live-scope="group"]').count() == 1)
                frame.locator('[data-target-mode="seat"]').click()
                frame.locator('.live-card[data-live-scope="seat"]').wait_for()
                check("Seat shows exactly one Seat card",
                      frame.locator(".live-card").count() == 1)

                # --- the Seat choice is shared with the Seats tab ---
                page.click("#tab-button-seats")
                page.wait_for_selector("#tab-seats:not([hidden])")
                # The row's centre is its name <input>, and the row's click
                # handler deliberately ignores clicks inside inputs — aim at
                # the ID label instead.
                page.click('#assigned .device-row[data-seat-id="2"] small')
                page.click("#tab-button-control")
                frame = surface(page)
                # The filter re-reads the shared key on its next render, which
                # a heartbeat drives, so wait for the card rather than sampling.
                frame.locator(
                    '.live-card[data-live-scope="seat"][data-live-id="2"]'
                ).wait_for(timeout=15000)
                check("the filter follows the Seat chosen on the Seats tab",
                      frame.locator('.live-card[data-live-scope="seat"]')
                      .get_attribute("data-live-id") == "2")

                # The old venue-level shelf is retired. Patch presets remain
                # on each embedded Control card (asserted above).
                check("the venue-preset shelf is absent",
                      page.locator("#preset-bar").count() == 0)

                check("no page errors", not errors, repr(errors))

                standalone = browser.new_page(viewport={"width": 1024,
                                                        "height": 768})
                standalone_errors = []
                standalone.on(
                    "pageerror",
                    lambda error: standalone_errors.append(str(error)))
                standalone.goto(base_url + "/facilitator")
                standalone.wait_for_function(
                    "() => document.querySelector('#ws-status')"
                    "?.classList.contains('online')")
                standalone.locator(".live-card").first.wait_for()
                check("the standalone facilitator has no preset affordance",
                      standalone.locator("#preset-section").count() == 0
                      and standalone.locator("[data-preset-slot]").count() == 0)
                check("no standalone page errors", not standalone_errors,
                      repr(standalone_errors))
                standalone.close()
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
    print("Control tab checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
