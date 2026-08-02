#!/usr/bin/env python3
"""Real-dashboard browser journey for preset save/recall in the patch editor
(`41-preset-primitive/08-editor-save-recall`).

This is the primary sculpt→save workflow, and it is deliberately the SAME
ControlSurface as the Control and Device tabs.

What this pins:

  * the editor's control panel carries the preset row for the patch being
    edited, with the ratified `new`/`save`/`del` anatomy;
  * parameters, events, hierarchy, and the generator drawer are emitted and
    bound by the shared ControlSurface; the audition engine is one solid
    member, never a synthetic mixed aggregate;
  * parameter rows stay atomic on a phone-sized viewport and the fixed-width
    drawer sets a reasonable, scrolling panel minimum instead of reflowing;
  * the editor panel is a neutral card, never a transparent bordered region
    or a patch of workspace ground;
  * SAVE captures the audition engine's state -- the same selector
    `set_editor_param` writes to -- and stores it under
    `patches/<patch>/presets/`;
  * a save while sculpting does NOT change the patch fingerprint and does not
    restage anything: `presets/` is excluded from the distribution
    (contract v1.17 §9), which is the whole reason the exclusion exists;
  * RECALL goes through the one server-side application core, so it restores
    the stored values after a nudge, emits `/0/p/*` on the audition relay, and
    records provenance;
  * DELETE removes the file.

Runs headless with `--sim-no-engine --sim-audio-backend none`: `set_edit`
reaches a real `edit` supervisor mode without launching Pure Data. Real PD/GUI
behaviour remains a hardware adoption check.

Owned by code surface (dashboard.js editor panel, control-surface.js preset
row, dashboard/server.py editor preset target).
"""

import json
import os
import random
import select
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright
from pythonosc.osc_message import OscMessage

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


def drain(sock):
    while select.select([sock], [], [], 0)[0]:
        sock.recvfrom(65535)


def collect(sock, seconds=1.0):
    frames = []
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        readable, _, _ = select.select(
            [sock], [], [], max(0, deadline - time.monotonic()))
        if not readable:
            continue
        message = OscMessage(sock.recvfrom(65535)[0])
        frames.append((message.address, list(message.params)))
    return frames


def make_fixture(root):
    patches = os.path.join(root, "patches")
    assets = os.path.join(root, "assets")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(assets)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"preset-editor-verifier")
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin",
            "params": [
                {"name": "density", "kind": "float", "min": 0, "max": 1,
                 "default": .2, "dashboard": True},
                {"name": "depth", "kind": "float", "min": 0, "max": 1,
                 "default": .4, "dashboard": False},
            ],
            "events": [
                {"name": "strike", "arity": 1, "defaults": [0.75],
                 "dashboard": True},
            ],
            "caps": [], "slots": [],
        }, target)
    state = {
        "schema": 1, "name": "Editor preset rig",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha", "groups": {}, "seats": {},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path, patch


def bound(page, selector, handler):
    """Wait for `selector`'s first match to carry a live `handler`.

    Gotcha 16: waiting for the ELEMENT is not waiting for its handler.
    `bindPresets` reassigns `ontoggle` and every `[data-preset-action]`
    `onclick` after each heartbeat re-render, so a click resolved against a
    freshly replaced node can land before that pass and silently do nothing.
    The selector stays scoped to `#editor-params` (gotcha 17): the component
    classes it names occur several times over in this document.
    """
    page.wait_for_function(
        "argument => !!document.querySelector(argument.selector)"
        "?.[argument.handler]",
        arg={"selector": selector, "handler": handler})


def open_menu(page):
    """Open the editor row's shared recall/authoring menu."""
    disclosure = page.locator("#editor-params .preset-menu").first
    if disclosure.evaluate("element => element.open"):
        return
    # A click landing on an unbound disclosure opens it without the component
    # recording that it is open, so the next re-render closes it again and the
    # action click that follows times out — see `bound`.
    disclosure.locator("summary").wait_for()
    bound(page, "#editor-params .preset-menu", "ontoggle")
    disclosure.locator("summary").click()
    disclosure.locator("[data-preset-action]").first.wait_for()


def click_action(page, action):
    """Click one demoted preset action, once it is bound.

    `open_menu` waits for the disclosure's binding, which says nothing
    about the render AFTER it — the click re-resolves the selector and may
    reach a node from a later, not-yet-bound `bindPresets` pass. Waiting on the
    button actually about to be clicked is what closes that window.
    """
    open_menu(page)
    selector = f'#editor-params [data-preset-action="{action}"]'
    bound(page, selector, "onclick")
    page.click(selector)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-editor-presets-") as temp:
        state_path, patch_dir = make_fixture(temp)
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        presets_dir = os.path.join(patch_dir, "presets")
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        engine_port = free_port(socket.SOCK_DGRAM)
        engine = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        engine.bind(("127.0.0.1", engine_port))
        base_url = f"http://127.0.0.1:{http_port}"
        server_log = open(os.path.join(temp, "server.log"), "w",
                          encoding="utf-8")
        server = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port),
                "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", assets, "--patches-dir", patches,
                "--public-url", base_url,
                "--sim-audio-backend", "none", "--sim-no-engine",
                "--sim-engine-port-base", str(engine_port),
            ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440,
                                                  "height": 1200})
                page.set_default_timeout(15000)
                errors = []
                dialogs = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("dialog", lambda dialog: (
                    dialogs.append(dialog.message), dialog.accept()))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.evaluate(
                    "() => ws.send('set_edit',"
                    " {active:true, patch:'alpha', confirmed:true})")
                page.wait_for_function(
                    "() => installation.supervisor?.mode === 'edit'")
                page.click("#tab-button-patches")
                page.wait_for_selector("#editor-params [data-preset-slot]")

                row = page.locator("#editor-params [data-preset-slot]")
                check("the editor panel carries the preset row for its patch",
                      row.locator(".live-preset-patch").inner_text().strip()
                      == "alpha")
                check("it is the ratified row anatomy",
                      [button.strip() for button in row.locator(
                          ".live-preset-action").all_text_contents()]
                      == ["+new", "↥save", "⌫delete"])

                # --- the whole editor panel is now the shared component ----
                density = page.locator(
                    '#editor-params .live-param[data-param-path="density"]')
                strike = page.locator(
                    '#editor-params .live-param-event'
                    '[data-param-path="strike"]')
                check("the editor renders shared parameter rows",
                      density.count() == 1
                      and density.locator(".live-param-range-wrap").count() == 1)
                check("the editor renders declared events in the same panel",
                      strike.count() == 1
                      and strike.locator(".live-event-send").count() == 1)
                check("one audition engine renders as a solid member",
                      "mixed" not in (density.get_attribute("class") or "")
                      and density.locator(".live-param-value").inner_text()
                      == "0.2")
                check("Remote presentation metadata stays in manifest authoring",
                      page.locator("#editor-params .dashboard-badge").count() == 0)

                card = page.eval_on_selector("#editor-params", """node => {
                  const style=getComputedStyle(node);
                  return {
                    background:style.backgroundColor,
                    panel:style.getPropertyValue('--panel').trim(),
                    minimum:parseFloat(style.minWidth),
                  };
                }""")
                check("the editor ControlSurface sits on a neutral card",
                      card["background"] not in (
                          "rgba(0, 0, 0, 0)", "transparent")
                      and card["background"]
                      == page.evaluate(
                          "() => {"
                          " const probe=document.createElement('i');"
                          " probe.style.color='var(--panel)';"
                          " document.body.append(probe);"
                          " const value=getComputedStyle(probe).color;"
                          " probe.remove(); return value;"
                          " }"),
                      repr(card))

                page.set_viewport_size({"width": 360, "height": 900})
                phone = page.eval_on_selector(
                    '#editor-params .live-param[data-param-path="density"]',
                    """row => {
                      const parts=[
                        row.querySelector('.live-param-value'),
                        row.querySelector('.live-param-range-wrap'),
                        row.querySelector('.live-param-mod'),
                      ].map(node => node.getBoundingClientRect());
                      const panel=row.closest('#editor-params');
                      return {
                        centers:parts.map(rect => rect.top + rect.height / 2),
                        panelMin:parseFloat(getComputedStyle(panel).minWidth),
                        viewport:innerWidth,
                      };
                    }""")
                check("the parameter row stays atomic on a phone",
                      max(phone["centers"]) - min(phone["centers"]) <= 1,
                      repr(phone))
                check("the drawer-defined minimum is reasonable on a phone",
                      phone["panelMin"] <= phone["viewport"],
                      repr(phone))
                page.set_viewport_size({"width": 1440, "height": 1200})

                page.click(
                    '#editor-params .live-param[data-param-path="density"]'
                    ' [data-gen-toggle]')
                page.wait_for_selector("#editor-params .live-param-gen")
                drawer = page.eval_on_selector(
                    "#editor-params .live-param-gen",
                    """node => ({
                      width:node.getBoundingClientRect().width,
                      argsWrap:getComputedStyle(
                        node.querySelector('.live-gen-args')).flexWrap,
                    })""")
                check("the shared generator drawer keeps its fixed face",
                      abs(drawer["width"] - 320) <= 1
                      and drawer["argsWrap"] == "nowrap", repr(drawer))

                drain(engine)
                page.wait_for_function(
                    "() => !!document.querySelector("
                    "'#editor-params [data-gen-apply]')?.onclick")
                page.click("#editor-params [data-gen-apply]")
                page.wait_for_timeout(1000)
                running = page.evaluate(
                    "() => installation.automation?.editor?.density || null")
                check("the editor records its generator separately from Seat 0",
                      running is not None, repr(dialogs))
                frames = collect(engine, .5)
                ticks = [float(args[0]) for address, args in frames
                         if address.endswith("/p/density") and len(args) == 1]
                check("the editor drawer drives its audition engine",
                      len({round(value, 3) for value in ticks}) >= 3,
                      repr(frames))
                if running is not None:
                    page.click("#editor-params [data-gen-stop]")
                    page.wait_for_function(
                        "() => !installation.automation?.editor?.density")

                drain(engine)
                page.click(
                    '#editor-params .live-param-event'
                    '[data-param-path="strike"] .live-event-send')
                frames = collect(engine, .5)
                check("the shared event row fires on the audition engine",
                      any(address.endswith("/e/strike")
                          and args
                          and abs(float(args[0]) - .75) < 1e-5
                          for address, args in frames), repr(frames))

                # --- sculpt, then save what the audition engine is holding ---
                page.evaluate(
                    "() => ws.send('set_editor_param',"
                    " {name:'density', value:0.83})")
                page.wait_for_function(
                    "() => installation.editor?.params?.density === 0.83")
                fingerprint_before = page.evaluate(
                    "() => installation.fleet_patch?.fingerprint")

                click_action(page, "new")
                page.wait_for_selector("#editor-params [data-preset-name]")
                page.fill("#editor-params [data-preset-name]", "Sculpt")
                page.click("#editor-params [data-preset-commit]")
                page.wait_for_function(
                    "() => (installation.preset_catalog?.alpha || []).length"
                    " === 1")
                with open(os.path.join(presets_dir, "Sculpt.json"),
                          encoding="utf-8") as source:
                    stored = json.load(source)
                check("the editor save captures the audition engine's state",
                      stored["params"] == {"density": [.83], "depth": [.4]},
                      repr(stored["params"]))

                # --- and never restages the patch it was saved into ---
                time.sleep(1.5)
                check("a save while sculpting leaves the fingerprint alone",
                      page.evaluate(
                          "() => installation.fleet_patch?.fingerprint")
                      == fingerprint_before)
                check("the fleet patch is not marked stale by a save",
                      page.evaluate(
                          "() => !installation.fleet_patch?.previous"))

                # --- nudge away, then recall through the application core ---
                page.evaluate(
                    "() => ws.send('set_editor_param',"
                    " {name:'density', value:0.11})")
                page.wait_for_function(
                    "() => installation.editor?.params?.density === 0.11")
                drain(engine)
                open_menu(page)
                bound(page, '#editor-params [data-preset-choice="Sculpt"]',
                      "onclick")
                page.click('#editor-params [data-preset-choice="Sculpt"]')
                page.wait_for_function(
                    "() => installation.editor?.params?.density === 0.83")
                frames = collect(engine, 1.0)
                check("recall restores the stored value after a nudge",
                      page.evaluate(
                          "() => installation.editor.params.density") == .83)
                # The dashboard addresses `/0/p/<identity>`; the audition
                # relay strips the seat selector before the engine sees it, so
                # what arrives here is the engine-side `/p/<identity>`.
                check("recall reaches the audition engine on selector 0",
                      any(address.endswith("/p/density")
                          and args and abs(float(args[0]) - .83) < 1e-4
                          for address, args in frames), repr(frames))
                page.wait_for_function(
                    "() => installation.editor?.applied_preset?.name"
                    " === 'Sculpt'")
                check("the editor records applied-preset provenance", True)

                # --- derived dirtiness carries over to this surface too ---
                page.evaluate(
                    "() => ws.send('set_editor_param',"
                    " {name:'depth', value:0.05})")
                page.wait_for_function(
                    "() => installation.editor?.preset_dirty === 'deviated'")
                check("moving a value after a recall reads as dirty", True)

                # --- delete ---
                page.wait_for_function(
                    """() => !!document.querySelector(
                      '#editor-params [data-preset-action="del"]')
                      && !document.querySelector(
                      '#editor-params [data-preset-action="del"]').disabled""")
                click_action(page, "del")
                page.wait_for_function(
                    "() => (installation.preset_catalog?.alpha || []).length"
                    " === 0")
                check("delete removes the preset file",
                      not os.path.exists(
                          os.path.join(presets_dir, "Sculpt.json")))

                page.evaluate(
                    "() => ws.send('set_edit', {active:false, confirmed:true})")
                page.wait_for_function(
                    "() => installation.supervisor?.mode === 'off'")
                check("no page errors", not errors, repr(errors))
                browser.close()
        finally:
            stop_process(server)
            engine.close()
            server_log.close()

    if FAILURES:
        print("\nFAILED: " + "; ".join(FAILURES))
        return 1
    print("\nEditor preset checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
