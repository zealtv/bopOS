#!/usr/bin/env python3
"""Real-dashboard browser journey: editing inside a drawer survives the
heartbeat (`52-preset-drawer-name-discarded`).

The Control surface rebuilds its whole card DOM on every heartbeat. Two drawers
let the operator type into that DOM — the preset save drawer's name field and
the generator drawer's argument fields — and both are supposed to be protected
by the host's render guard while focus is inside them.

Neither was. Both wired the guard as `drawer.onfocusin = fn`, and
`onfocusin`/`onfocusout` are **not** event-handler IDL attributes: the
assignment sets an inert expando that nothing ever calls
(`'onfocusin' in element` is `false` on a fresh element, where `onfocus` is
`true`). So the guard had never once run, and a preset name typed into the
drawer was wiped by the next heartbeat ~1 s later — after which `commit` read an
empty name and saved nothing at all.

Two independent protections, and this journey pins both, because they cover
different renders:

  1. a primary click reaches a numeric field without document pointerup
     clearing the focus guard and rebuilding the drawer;
  2. the guard holds while focus is inside the drawer, so the common case
     never re-renders at all; and
  3. the typed name is written through into the drawer's own state, so a render
     that happens ANYWAY — one provoked from outside the drawer, after focus has
     left — cannot silently empty a field the operator already filled.

Owned by code surface (control-surface.js drawer binding).
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
HOST = "#control-column-host"
# Several heartbeats at the fixture's 0.5 s interval: long enough that a
# rebuild is certain if nothing is holding it back.
HEARTBEATS_MS = 3000
UID = "b8:27:eb:00:00:01"


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
    patch = os.path.join(patches, "alpha")
    assets = os.path.join(root, "assets")
    os.makedirs(patch)
    os.makedirs(assets)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"interaction-guard")
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin",
            "params": [{"name": "density", "kind": "float", "min": 0,
                        "max": 1, "default": .2, "dashboard": True}],
            "events": [], "caps": [], "slots": [],
        }, target)
    state = {
        "schema": 1, "name": "Interaction guard rig",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha", "groups": {},
        # Bound, with params: a preset save captures a seat's values, so an
        # unbound seat with none would make the commit assertion vacuous.
        "seats": {"1": {"id": 1, "name": "Freda", "positions": [[1, 1]],
                        "groups": [], "bound": UID, "patch": "alpha",
                        "params": {"density": .2}}},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path, patches, assets


def bound(page, selector, handler):
    """Gotcha 16: an element existing is not its handler being bound."""
    page.wait_for_function(
        "argument => !!document.querySelector(argument.selector)"
        "?.[argument.handler]",
        arg={"selector": selector, "handler": handler})


def mark(page, selector):
    """Tag a node so a later read can tell replacement from a value change."""
    page.evaluate(
        "selector => { const node = document.querySelector(selector);"
        " if (node) node.dataset.guardMark = 'original'; }", selector)


def was_replaced(page, selector):
    return page.evaluate(
        "selector => document.querySelector(selector)?.dataset.guardMark"
        " !== 'original'", selector)


def open_preset_drawer(page):
    disclosure = page.locator(f"{HOST} .preset-menu").first
    bound(page, f"{HOST} .preset-menu", "ontoggle")
    disclosure.locator("summary").click()
    bound(page, f'{HOST} [data-preset-action="new"]', "onclick")
    page.locator(f'{HOST} [data-preset-action="new"]').first.click()
    field = page.locator(f"{HOST} [data-preset-drawer] [data-preset-name]")
    field.wait_for()
    return field


def main():
    temp = tempfile.TemporaryDirectory()
    state_path, patches, assets = make_fixture(temp.name)
    http_port = free_port(socket.SOCK_STREAM)
    listen_port = free_port(socket.SOCK_DGRAM)
    send_port = free_port(socket.SOCK_DGRAM)
    log_path = os.path.join(temp.name, "dashboard.log")
    dashboard = fleet = None
    try:
        with open(log_path, "w", encoding="utf-8") as log, \
                open(os.path.join(temp.name, "fleet.log"), "w",
                     encoding="utf-8") as fleet_log:
            dashboard = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--port", str(http_port), "--listen-port", str(listen_port),
                "--send-port", str(send_port), "--osc-target", "127.0.0.1",
                "--state-file", state_path, "--patches-dir", patches,
                "--assets-dir", assets,
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            base_url = f"http://127.0.0.1:{http_port}"
            wait_http(base_url + "/", dashboard)
            # A live fleet is the point: the heartbeat is what used to eat the
            # operator's typing.
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "1", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port",
                str(send_port), "--hb-interval", "0.5", "--boot-secs", "0.2",
                "--patches-dir", patches, "--assets-dir", assets,
                "--manifest", os.path.join(patches, "alpha",
                                           "bopos.patch.json"),
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser_name = os.environ.get("BOPOS_PLAYWRIGHT_BROWSER",
                                              "chromium")
                browser_type = getattr(playwright, browser_name, None)
                if browser_type is None:
                    raise RuntimeError("unknown Playwright browser: " +
                                       browser_name)
                browser = browser_type.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440,
                                                  "height": 1200})
                page.set_default_timeout(15000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))

                page.goto(base_url + "#control")
                page.wait_for_selector("#ws-status.online")

                # The platform fact the whole defect rests on, asserted rather
                # than assumed. `tests/test_dom_event_handlers.py` bans
                # assigning these; if a browser ever makes them real IDL
                # attributes, this is what says so and the ban can be revisited.
                idl = page.evaluate("""() => {
                  const fresh = document.createElement('div');
                  return {focusin: 'onfocusin' in fresh,
                          focusout: 'onfocusout' in fresh,
                          focus: 'onfocus' in fresh};
                }""")
                check("onfocusin/onfocusout are still not IDL attributes",
                      idl == {"focusin": False, "focusout": False,
                              "focus": True}, repr(idl))
                page.locator(
                    f'{HOST} .live-card[data-live-scope="all"]').wait_for()

                # --- 1. the guard holds while focus is in the drawer ---
                field = open_preset_drawer(page)
                field.fill("Dawn")
                name_selector = (f"{HOST} [data-preset-drawer] "
                                 "[data-preset-name]")
                mark(page, name_selector)
                check("focus reaches the drawer's name field",
                      page.evaluate(
                          "() => document.activeElement?.dataset"
                          "?.presetName !== undefined"))

                page.wait_for_timeout(HEARTBEATS_MS)
                check("a typed preset name survives the heartbeat",
                      page.locator(name_selector).input_value() == "Dawn",
                      repr(page.locator(name_selector).input_value()))
                check("the focused field is not even rebuilt",
                      not was_replaced(page, name_selector))

                # --- 2. write-through covers a render the guard does not ---
                # Focus leaves the drawer, which releases the guard, and then a
                # heartbeat rebuilds the cards. Before the write-through the
                # field was re-emitted from a stored name that was still "".
                page.locator("#ws-status").click()
                page.wait_for_function(
                    "() => document.activeElement?.dataset"
                    "?.presetName === undefined")
                mark(page, name_selector)
                page.wait_for_timeout(HEARTBEATS_MS)
                rebuilt = was_replaced(page, name_selector)
                check("leaving the drawer does release the guard",
                      rebuilt, "the card was never rebuilt, so this "
                               "assertion proved nothing")
                check("the name survives a rebuild that happens anyway",
                      page.locator(name_selector).input_value() == "Dawn",
                      repr(page.locator(name_selector).input_value()))

                # --- 3. and it still commits, which is the operator's point ---
                bound(page, f"{HOST} [data-preset-drawer] "
                            "[data-preset-commit]", "onclick")
                page.locator(
                    f"{HOST} [data-preset-drawer] [data-preset-commit]").click()
                saved = True
                try:
                    page.wait_for_function(
                        "() => (installation.preset_catalog?.alpha || [])"
                        ".length === 1")
                except Exception:
                    saved = False
                check("the preset actually saves", saved)

                # --- 4. the generator drawer carried the same broken guard ---
                page.locator(f"{HOST} [data-gen-toggle]").first.click()
                # NOT a range: `control-host.js`'s pointerdown/pointerup pair
                # arms the guard for a range and then deliberately releases it
                # a tick after the gesture, so a range can never show whether
                # FOCUS holds the guard. The numeric argument box can.
                gen_selector = f"{HOST} .live-param-gen input.live-gen-num"
                gen_field = page.locator(gen_selector).first
                gen_field.wait_for()
                # A programmatic focus was the old regression's blind spot:
                # primary pointerup saw the focus guard's shared boolean,
                # cleared it as though a range gesture had ended, and rebuilt
                # this node before a person could type.
                gen_field.click()
                check("a primary click focuses the generator number field",
                      gen_field.evaluate(
                          "node => document.activeElement === node"))
                gen_field.fill("0.35")
                mark(page, gen_selector)
                page.wait_for_timeout(HEARTBEATS_MS)
                check("the generator drawer's field is not rebuilt under focus",
                      not was_replaced(page, gen_selector))
                check("the clicked generator number remains editable",
                      page.locator(gen_selector).first.input_value() == "0.35",
                      repr(page.locator(gen_selector).first.input_value()))

                # Remote has its own document-level pointer guard around the
                # same ControlColumn. Pin the duplicate host seam explicitly.
                page.goto(base_url + "/facilitator")
                # Connected Remote deliberately renders an empty status span,
                # so it is attached and online but not Playwright-visible.
                page.wait_for_selector("#ws-status.online", state="attached")
                page.locator(f"{HOST} [data-gen-toggle]").first.click()
                remote_field = page.locator(gen_selector).first
                remote_field.wait_for()
                remote_field.click()
                check("Remote primary click focuses the generator number field",
                      remote_field.evaluate(
                          "node => document.activeElement === node"))
                remote_field.fill("0.45")
                mark(page, gen_selector)
                page.wait_for_timeout(HEARTBEATS_MS)
                check("Remote keeps the clicked number field through heartbeats",
                      not was_replaced(page, gen_selector)
                      and page.locator(gen_selector).first.input_value() ==
                      "0.45")

                check("no page errors", not errors, repr(errors))
                browser.close()
    finally:
        stop_process(fleet)
        stop_process(dashboard)
        if FAILURES and os.path.exists(log_path):
            with open(log_path, encoding="utf-8") as log:
                print("--- dashboard log ---")
                print(log.read()[-2000:])
        temp.cleanup()

    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed")
        return 1
    print("\nInteraction guard checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
