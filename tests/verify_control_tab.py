#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for the Control tab (thread 37,
stitch 10).

Bob's rulings, each one a check:

  * the Dashboard tab is renamed CONTROL -- and an existing #dashboard bookmark
    still resolves, because renaming a route silently breaks links;
  * the target picker is a REUSABLE component (window.TargetPicker) rather than
    a widget belonging to this tab, and it scopes the surface below it;
  * the Seat choice is shared -- picking a Seat on the Seats tab is the Seat
    the picker lands on;
  * CUES sit above the surface;
  * PRESETS follow the target filter: the shelf names the current target, and a
    save under one Seat captures that Seat rather than the whole venue.

Also pins the correction that came with the ratification: the Control tab hosts
NO patch deployment -- the picker stays on the Patches tab.

The All/Groups/Seat radio model this file originally pinned was retired by
`02-component-unification/07`: Bob's unified picker is a chip disclosure where
All, groups and Seats mix freely, so the mode tabs became chips. What survives
unchanged is every ruling above -- a reusable component, scoping the surface,
following the shared Seat.

Owned by code surface (target-picker.js, facilitator.js, dashboard.js tabs).
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

from playwright.sync_api import TimeoutError as PlaywrightTimeout
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
        # Remote keeps the per-device commands D8 took off Control, so the
        # fixture has to declare some for that half to be testable at all.
        "facilitator_commands": ["restart-engine", "reboot"],
        "groups": {"0": {"id": 0, "name": "Front"}},
        "seats": {"1": seat(1, "Freda", UID_A, [0]),
                  "2": seat(2, "Sparks", UID_B, [])},
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


def reload_control(page, base_url):
    """A REAL reload of the Control tab.

    `page.goto(base_url + "#control")` from a page already on `base_url` is a
    same-document navigation — the fragment changes, nothing reloads, and a
    persistence check written that way passes on the live objects it was
    supposed to have thrown away. This one throws them away.
    """
    page.goto(base_url + "#control")
    page.reload()
    page.wait_for_selector("#ws-status.online")


def open_picker(scope):
    """Reveal a column's chips.

    The Control column's picker is CLOSED by default since
    `4-n-columns/1-columns-layout` (D4): its terse readout is the column's
    title, and an open picker costs ~180px of a 342px column, times N. Chips
    inside a closed `<details>` resolve but are never visible, so every chip
    click in this file goes through here.
    """
    if scope.locator(".target-picker[open]").count() == 0:
        scope.locator(".target-picker > summary").click()
    scope.locator(".target-picker[open]").wait_for()


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

                # --- the picker is the reusable component ---
                frame = surface(page)
                frame.locator(".target-picker").wait_for()
                check("the picker is a reusable component, not a local widget",
                      page.evaluate(
                          "() => typeof window.TargetPicker?.create"
                          " === 'function'"))
                chips = frame.locator(
                    ".target-picker [data-target-toggle]").all_text_contents()
                check("the picker offers All, the group and both Seats as chips",
                      [item.strip() for item in chips]
                      == ["All", "Frontg0", "1", "2"], repr(chips))

                # --- events sit above the parameters, inside the panel ---
                # `/cue` is retired (thread 44 child 4) and the top event panel
                # went with it (`04-event-fire-affordance`): firing lives on the
                # panel's own rows, and the Events section leads the card.
                check("the retired top event panel is gone",
                      page.evaluate(
                          "() => !document.querySelector('#event-panel')"
                          " && !document.querySelector('#event-lead')"))
                check("events sit above parameters in the panel",
                      page.evaluate(
                          "() => { const card ="
                          " document.querySelector('#control-column-host .live-card');"
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
                check("it offers one shared recall and authoring menu",
                      slot.locator(".preset-menu").count() == 1
                      and [button.strip() for button in slot.locator(
                          ".live-preset-action").all_text_contents()]
                      == ["+new", "↥save", "⌫delete"])
                check("the preset menu is closed at rest",
                      slot.locator(".preset-menu[open]").count()
                      == 0
                      and slot.locator(
                          '.preset-menu [data-preset-action]')
                      .count() == 3
                      and not slot.locator(
                          '[data-preset-action="new"]').is_visible())
                placement = page.evaluate(
                    """() => {
                      const card = document.querySelector(
                        '#control-column-host'
                        + ' .live-card[data-live-scope="all"]');
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

                # One card has one target. A second chip replaces the first;
                # mixtures now require a second card.
                open_picker(frame)
                frame.locator('[data-target-toggle="g0"]').click()
                frame.locator('.live-card[data-live-scope="group"]').wait_for()
                check("a group chip shows that group's card only",
                      frame.locator(".live-card").count() == 1
                      and frame.locator(
                          '.live-card[data-live-scope="group"]').count() == 1)
                frame.locator('[data-target-toggle="2"]').click()
                frame.locator('.live-card[data-live-scope="seat"]').wait_for()
                check("a second target replaces rather than mixes",
                      frame.locator(".live-card").count() == 1
                      and frame.locator(
                          '.live-card[data-live-scope="seat"]'
                          '[data-live-id="2"]').count() == 1
                      and frame.locator(
                          '.live-card[data-live-scope="group"]').count() == 0)
                frame.locator('[data-target-toggle="all"]').click()
                frame.locator('.live-card[data-live-scope="all"]').wait_for()
                check("All is exclusive with everything else",
                      frame.locator(".live-card").count() == 1)

                # --- Control does NOT follow the Seats tab's focus Seat ---
                # SUPERSEDED: this checked the opposite until
                # `08-control-tab-columns/1-columns-design` D7 (Bob,
                # 2026-07-31), which retired `followFocusSeat` on Control
                # outright, at every N. A column that silently re-aims itself
                # because someone selected a Seat in another tab is wrong as
                # soon as there is more than one column, and it was ambient
                # rather than asked for even at N=1. The Seats → Control
                # workflow returns as an explicit action, owned by `4-n-columns`.
                page.click("#tab-button-seats")
                page.wait_for_selector("#tab-seats:not([hidden])")
                # The row's centre is its name <input>, and the row's click
                # handler deliberately ignores clicks inside inputs — aim at
                # the ID label instead.
                page.click('#assigned .device-row[data-seat-id="2"] small')
                page.click("#tab-button-control")
                frame = surface(page)
                frame.locator('.live-card[data-live-scope="all"]').wait_for()
                check("choosing a Seat elsewhere does not re-aim Control",
                      frame.locator(".live-card").count() == 1
                      and frame.locator('.live-card[data-live-scope="seat"]')
                      .count() == 0)
                # The target moves only when the operator moves it.
                open_picker(frame)
                frame.locator('[data-target-toggle="2"]').click()
                frame.locator(
                    '.live-card[data-live-scope="seat"][data-live-id="2"]'
                ).wait_for(timeout=15000)
                check("choosing a Seat chip in the column does aim it",
                      frame.locator('.live-card[data-live-scope="seat"]')
                      .get_attribute("data-live-id") == "2")

                # --- D8: chrome demoted off the Control card -----------------
                # Six chrome controls per card, times three cards in a mixture,
                # times N columns, was fifty-four before a single parameter.
                # `Send all` is a rescue action for a returning node and moved
                # to an overflow; device lifecycle belongs to the Devices tab
                # and left the column entirely, replaced by a hand-off.
                card = frame.locator('.live-card[data-live-scope="seat"]')
                check("the Control card carries no device-command disclosure",
                      card.locator(".device-commands").count() == 0)
                check("Send all is behind the overflow, not in the head",
                      card.locator(".live-card-overflow .send-all").count() == 1
                      and not card.locator(".send-all").is_visible())
                card.locator(".live-card-overflow > summary").click()
                card.locator(".live-card-overflow[open]").wait_for()
                # The hand-off is offered only once this Seat HAS a device to
                # hand off to, so it waits for the binding rather than racing
                # the heartbeat that carries it.
                card.locator("[data-open-device]").wait_for()
                check("the overflow holds Send all and the device hand-off",
                      card.locator(".send-all").is_visible()
                      and card.locator("[data-open-device]").is_visible())
                # The hand-off follows `07`'s "Set patch…" pattern: it selects
                # the device and switches tabs, rather than carrying the
                # commands themselves back into a live parameter panel.
                uid = card.locator("[data-open-device]").get_attribute(
                    "data-open-device")
                card.locator("[data-open-device]").click()
                page.wait_for_selector("#tab-devices:not([hidden])")
                check("the hand-off opens that device on the Devices tab",
                      page.evaluate("() => selected") == uid,
                      repr(page.evaluate("() => selected")))
                page.click("#tab-button-control")
                frame = surface(page)

                # A target removed from the venue removes its card; it must
                # never widen into All behind the operator's back.
                page.click("#tab-button-seats")
                page.wait_for_selector("#tab-seats:not([hidden])")
                page.fill("#seat-id", "5")
                page.click("#seat-reindex")
                page.click("#tab-button-control")
                frame = surface(page)
                page.wait_for_function(
                    "() => document.querySelectorAll("
                    "'#control-column-host .control-column').length === 0")
                stored_cards = json.loads(page.evaluate(
                    "() => localStorage.getItem('bopos.control.cards')"))
                check("a lost target is never widened to every Seat",
                      stored_cards == {"version": 1, "targets": []},
                      repr(stored_cards))
                check("the removed target removes its card and controls",
                      frame.locator(".live-card").count() == 0)

                # --- authored card set, derived order ----------------------
                columns = page.locator("#control-column-host .control-column")
                page.evaluate(
                    """() => {
                      localStorage.removeItem('bopos.control.cards');
                      localStorage.setItem('bopos.control.columns', JSON.stringify([
                        {id:'old-seat', target:['5'], open:true},
                        {id:'old-all', target:['all'], open:false},
                        {id:'duplicate', target:['5'], open:false}
                      ]));
                    }""")
                reload_control(page, base_url)
                columns.first.locator(".live-card").wait_for()
                stored_cards = json.loads(page.evaluate(
                    "() => localStorage.getItem('bopos.control.cards')"))
                check("legacy columns migrate to a unique target set",
                      stored_cards == {"version": 1,
                                       "targets": ["all", "5"]},
                      repr(stored_cards))
                check("migration discards authored order and sorts All first",
                      columns.count() == 2
                      and columns.nth(0).locator(
                          '.live-card[data-live-scope="all"]').count() == 1
                      and columns.nth(1).locator(
                          '.live-card[data-live-scope="seat"]'
                          '[data-live-id="5"]').count() == 1)
                check("every committed card can be closed, including the last",
                      columns.first.locator(".control-column-close")
                      .is_visible())

                page.click("#control-add-column")
                page.wait_for_function(
                    "() => document.querySelectorAll("
                    "'#control-column-host .control-column').length === 3")
                draft = columns.nth(2)
                check("+ card creates one transient open picker",
                      draft.locator(".target-picker[open]").count() == 1)
                page.click("#control-add-column")
                check("a second + focuses rather than duplicates the draft",
                      columns.count() == 3)
                check("targets already represented by cards are disabled",
                      draft.locator('[data-target-toggle="all"]').is_disabled()
                      and draft.locator('[data-target-toggle="5"]')
                      .is_disabled())
                draft.locator('[data-target-toggle="g0"]').click()
                columns.nth(1).locator(
                    '.live-card[data-live-scope="group"]').wait_for()
                check("committing a draft re-sorts it between All and Seats",
                      columns.nth(0).locator(
                          '.live-card[data-live-scope="all"]').count() == 1
                      and columns.nth(1).locator(
                          '.live-card[data-live-scope="group"]'
                          '[data-live-id="0"]').count() == 1
                      and columns.nth(2).locator(
                          '.live-card[data-live-scope="seat"]'
                          '[data-live-id="5"]').count() == 1)
                stored_cards = json.loads(page.evaluate(
                    "() => localStorage.getItem('bopos.control.cards')"))
                check("only target membership is persisted",
                      stored_cards == {"version": 1,
                                       "targets": ["all", "g0", "5"]},
                      repr(stored_cards))

                before = columns.first.locator(".live-card").inner_html()
                slider = columns.nth(2).locator('input[type="range"]').first
                slider.wait_for()
                page.wait_for_function("() => [...document.querySelectorAll("
                                       "'#control-column-host input[type=\"range\"]')"
                                       "].at(-1)?.onchange != null")
                slider.fill("0.8")
                slider.dispatch_event("change")
                page.wait_for_timeout(500)
                check("a send in one card leaves the others alone",
                      columns.first.locator(".live-card").count() == 1
                      and columns.first.locator(
                          '.live-card[data-live-scope="all"]').count() == 1
                      and columns.first.locator(".live-card").inner_html()
                      == before)
                check("one live region per card",
                      page.locator("#control-column-host .live-param-status")
                      .count() == 0
                      and page.locator(
                          "#control-column-host .control-column-status")
                      .count() == 3)

                reload_control(page, base_url)
                columns.nth(2).locator(".live-card").wait_for()
                check("the target set and derived order survive reload",
                      columns.count() == 3
                      and [card.get_attribute("data-live-scope")
                           for card in columns.locator(".live-card").all()]
                      == ["all", "group", "seat"])

                # --- the explicit replacement for the retired ambient follow ---
                page.click("#tab-button-seats")
                page.wait_for_selector("#tab-seats:not([hidden])")
                page.click('#assigned .device-row[data-seat-id="1"] small')
                page.click("#seat-open-control")
                page.wait_for_selector("#tab-control:not([hidden])")
                page.wait_for_function(
                    "() => document.querySelectorAll("
                    "'#control-column-host .control-column').length === 4")
                check("Open in Control adds a card for that Seat",
                      columns.nth(3).locator(
                          '.live-card[data-live-scope="seat"]'
                          '[data-live-id="1"]').count() == 1)
                # Asked for twice, it FOCUSES rather than duplicating.
                page.click("#tab-button-seats")
                page.click('#assigned .device-row[data-seat-id="1"] small')
                page.click("#seat-open-control")
                page.wait_for_selector("#tab-control:not([hidden])")
                page.wait_for_timeout(400)
                check("asked twice, it focuses the card it already opened",
                      columns.count() == 4)

                columns.nth(1).locator(".control-column-close").click()
                page.wait_for_function(
                    "() => document.querySelectorAll("
                    "'#control-column-host .control-column').length === 3")
                check("closing a card removes its target",
                      columns.count() == 3
                      and columns.locator(
                          '.live-card[data-live-scope="group"]').count() == 0)
                reload_control(page, base_url)
                columns.nth(2).locator(".live-card").wait_for()
                check("closing persists and no drag affordance remains",
                      columns.count() == 3
                      and page.locator(".control-column-grip").count() == 0)

                # The old venue-level shelf is retired. Patch presets remain
                # on each Control card (asserted above).
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
                check("Remote has labels rather than target pickers",
                      standalone.locator(".target-picker").count() == 0)
                remote_cards = standalone.locator(".live-card")
                check("Remote derives All, every group and every Seat",
                      [(card.get_attribute("data-live-scope"),
                        card.get_attribute("data-live-id"))
                       for card in remote_cards.all()]
                      == [("all", None), ("group", "0"),
                          ("seat", "1"), ("seat", "5")])
                # D8's other half: the commands LEFT Control, they were not
                # deleted. An iPad away from the rack is where a per-device
                # reboot earns its place, so Remote still draws them — in the
                # card, not behind a hand-off it has no tab to hand off to.
                remote_card = standalone.locator(
                    '.live-card[data-live-scope="seat"]').first
                check("Remote still carries the device-command disclosure",
                      remote_card.locator(
                          "details.device-commands").count() == 1
                      and remote_card.locator(
                          "[data-device-command]").count() == 2)
                check("Remote offers no Devices-tab hand-off",
                      remote_card.locator("[data-open-device]").count() == 0)
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
