#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for patch presets on the Control tab
and the Device panel (`41-preset-primitive/07-control-device-ui`).

What this pins, each one a ruling:

  * a preset APPLIES from the row's dropdown, through the one server-side
    application core, and the card then states its provenance;
  * moving a parameter afterwards makes the provenance derived-dirty -- the
    `Dawn *` asterisk -- without anything being stored to say so;
  * a card whose targets carry different presets says `mixed`, the same idiom
    a mixed aggregate value uses;
  * SAVE captures everything by default, offers per-row include/exclude, and
    STATES the identities omitted because the target disagreed (review F8)
    before the write rather than after the next apply;
  * an overwrite is a compare-and-swap: a stale revision is refused, not
    silently clobbered;
  * the standalone facilitator/iPad surface carries NO preset affordance at
    all (Bob's Q4 ruling) -- removed, not inert;
  * saving never touches the patch fingerprint, because `presets/` is excluded
    from the distribution (contract v1.17 §9).

Owned by code surface (control-surface.js, facilitator.js, dashboard.js,
dashboard/server.py preset verbs).
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
        target.write(b"preset-surface-verifier")
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin",
            "params": [
                {"name": "density", "kind": "float", "min": 0, "max": 1,
                 "default": .2, "dashboard": True},
                {"name": "depth", "kind": "float", "min": 0, "max": 1,
                 "default": .4, "dashboard": True},
            ],
            "events": [], "caps": [], "slots": [],
        }, target)

    def seat(seat_id, name, uid):
        return {"id": seat_id, "name": name, "positions": [[seat_id, 1]],
                "groups": [], "bound": uid, "patch": "alpha",
                "params": {"density": .2, "depth": .4}}

    state = {
        "schema": 1, "name": "Preset rig",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "groups": {},
        "seats": {"1": seat(1, "Freda", UID_A), "2": seat(2, "Sparks", UID_B)},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path, patch


def surface(page):
    """The Control surface is mounted in this document since
    `3-iframe-retirement`. It is no longer a frame — but it is also no
    longer alone in its document, so every selector must be scoped to the
    Control host (CLAUDE.md gotcha 17) rather than reaching page-wide."""
    return page.locator("#control-column-host")


# The Control surface shares the dashboard document now, so the socket a
# test drives directly is the page's own.
def inner(page):
    return page


def wait_catalog(page, count):
    page.wait_for_function(
        "expected => (installation.preset_catalog?.alpha || []).length"
        " === expected", arg=count, timeout=15000)


def open_authoring(root):
    """Open the preset row's authoring disclosure.

    D8 (`08-control-tab-columns/4-n-columns/3-chrome-demotions`) demoted
    `new`/`save`/`del` behind one `<details>`; the `<select>` stayed in the row
    because applying is the live act. Assertions that only READ a button still
    work closed — a hidden element still reports its `disabled` — but a click
    has to open the menu, exactly as an operator does.
    """
    disclosure = root.locator(".live-preset-authoring").first
    if not disclosure.evaluate("element => element.open"):
        disclosure.locator("summary").click()


def save_from_row(page, frame, name, exclude=()):
    """Drive the row's save drawer the way an operator does."""
    open_authoring(frame)
    frame.locator('[data-preset-slot] [data-preset-action="new"]').click()
    drawer = frame.locator("[data-preset-drawer]")
    drawer.locator("[data-preset-name]").wait_for()
    drawer.locator("[data-preset-name]").fill(name)
    for identity in exclude:
        drawer.locator(f'[data-preset-include="{identity}"]').uncheck()
    drawer.locator("[data-preset-commit]").click()


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-presets-") as temp:
        state_path, patch_dir = make_fixture(temp)
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        presets_dir = os.path.join(patch_dir, "presets")
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
                page.on("dialog", lambda dialog: dialog.accept())

                page.goto(base_url + "#control")
                page.wait_for_selector("#ws-status.online")
                frame = surface(page)
                frame.locator('.live-card[data-live-scope="all"]').wait_for()

                # --- save: capture-everything with include/exclude (F8) ---
                save_from_row(page, frame, "Dawn")
                wait_catalog(page, 1)
                with open(os.path.join(presets_dir, "Dawn.json"),
                          encoding="utf-8") as source:
                    dawn = json.load(source)
                check("a save writes one sparse document under patches/…/presets",
                      sorted(dawn["params"]) == ["density", "depth"]
                      and dawn["name"] == "Dawn", repr(dawn))
                check("the stored values are the canonical dashboard state",
                      dawn["params"] == {"density": [.2], "depth": [.4]},
                      repr(dawn["params"]))

                # --- saving never restages the fleet patch (contract §9) ---
                fingerprint_before = page.evaluate(
                    "() => installation.fleet_patch?.fingerprint")
                save_from_row(page, frame, "Dusk", exclude=("depth",))
                wait_catalog(page, 2)
                with open(os.path.join(presets_dir, "Dusk.json"),
                          encoding="utf-8") as source:
                    dusk = json.load(source)
                check("unticking a row leaves that identity out of the file",
                      list(dusk["params"]) == ["density"], repr(dusk["params"]))
                time.sleep(1.5)
                check("a preset save does not change the patch fingerprint",
                      page.evaluate(
                          "() => installation.fleet_patch?.fingerprint")
                      == fingerprint_before)

                # --- move a value, then apply, then check provenance ---
                inner(page).evaluate(
                    "() => ws.send('set_live_param',"
                    " {scope:'all', name:'density', value:0.9})")
                page.wait_for_function(
                    "() => installation.seats['1'].params.density === 0.9")
                inner(page).evaluate(
                    "() => ws.send('apply_preset',"
                    " {scope:'all', patch:'alpha', name:'Dawn'})")
                page.wait_for_function(
                    "() => installation.seats['1'].applied_preset?.name"
                    " === 'Dawn'")
                check("apply restores the stored value on every target",
                      page.evaluate(
                          "() => [installation.seats['1'].params.density,"
                          " installation.seats['2'].params.density]")
                      == [.2, .2])
                check("apply is not dirty until something moves",
                      page.evaluate(
                          "() => !installation.seats['1'].preset_dirty"))

                # The apply report is ONE compact line with a disclosure,
                # never a modal.
                report = frame.locator(
                    '.live-card[data-live-scope="all"] .live-preset-report')
                report.wait_for()
                summary = report.locator("summary").inner_text()
                check("the apply report is one line with a disclosure",
                      "Dawn" in summary and "applied" in summary
                      and report.evaluate("node => node.tagName") == "DETAILS"
                      and not report.evaluate("node => node.open"),
                      repr(summary))

                selected = frame.locator(
                    '.live-card[data-live-scope="all"] [data-preset-select]')
                page.wait_for_function(
                    """() => {
                      const select = document
                        .querySelector('#control-column-host [data-preset-select]');
                      return select && select.value === 'Dawn';
                    }""")
                check("the row states the applied preset",
                      selected.input_value() == "Dawn")

                # --- the dropdown itself applies (gotcha 16: wait for the
                # handler, not the element -- bindPresets reassigns `onchange`
                # after every heartbeat re-render) ---
                page.wait_for_function(
                    """() => {
                      const doc = document.querySelector('#control-column-host');
                      return !!doc?.querySelector(
                        '.live-card[data-live-scope="all"] [data-preset-select]')
                        ?.onchange;
                    }""")
                selected.select_option("Dusk")
                page.wait_for_function(
                    "() => installation.seats['2'].applied_preset?.name"
                    " === 'Dusk'")
                check("choosing a preset in the dropdown applies it",
                      page.evaluate(
                          "() => installation.seats['1'].applied_preset?.name")
                      == "Dusk")
                inner(page).evaluate(
                    "() => ws.send('apply_preset',"
                    " {scope:'all', patch:'alpha', name:'Dawn'})")
                page.wait_for_function(
                    "() => installation.seats['1'].applied_preset?.name"
                    " === 'Dawn'")

                # --- derived dirtiness: nothing is stored to say so ---
                inner(page).evaluate(
                    "() => ws.send('set_live_param',"
                    " {scope:'all', name:'density', value:0.7})")
                page.wait_for_function(
                    "() => installation.seats['1'].preset_dirty === true")
                page.wait_for_function(
                    """() => {
                      const doc = document.querySelector('#control-column-host');
                      const option = doc?.querySelector(
                        '[data-preset-select] option[value="Dawn"]');
                      return !!option && option.textContent.includes('*');
                    }""")
                check("an edited target renders the derived-dirty asterisk",
                      True)

                # --- mixed: two targets carrying different presets ---
                inner(page).evaluate(
                    "() => ws.send('apply_preset',"
                    " {scope:'seat', id:1, patch:'alpha', name:'Dusk'})")
                page.wait_for_function(
                    "() => installation.seats['1'].applied_preset?.name"
                    " === 'Dusk'"
                    " && installation.seats['2'].applied_preset?.name"
                    " === 'Dawn'")
                mixed = page.wait_for_function(
                    """() => {
                      const doc = document.querySelector('#control-column-host');
                      const select = doc?.querySelector(
                        '.live-card[data-live-scope="all"] [data-preset-select]');
                      if (!select) return false;
                      const placeholder = select.querySelector('option');
                      return placeholder.disabled
                        && placeholder.textContent.trim() === 'Dusk +1'
                        && select.getAttribute('aria-label').includes('mixed');
                    }""")
                # SUPERSEDED: this pinned the dotted `·····` placeholder until
                # D6 (`08-control-tab-columns/1-columns-design`, Bob
                # 2026-07-31), which ruled that mixed must CARRY ITS CONTENT —
                # `Dusk +1` — because with N columns an All column reading
                # `·····` beside a group column reading `Dusk` looks like a
                # contradiction rather than an aggregate of one.
                check("a card whose targets disagree names the mixture",
                      bool(mixed))

                # --- omitted-as-mixed is stated BEFORE the save (F8) ---
                inner(page).evaluate(
                    "() => ws.send('set_live_param',"
                    " {scope:'seat', id:1, name:'depth', value:0.1})")
                page.wait_for_function(
                    "() => installation.seats['1'].params.depth === 0.1")
                open_authoring(frame)
                frame.locator(
                    '[data-preset-slot] [data-preset-action="new"]').click()
                omitted = frame.locator("[data-preset-drawer] .live-preset-omitted")
                omitted.wait_for()
                text = omitted.inner_text()
                check("the save drawer names the identities omitted as mixed",
                      "depth" in text and "omitted as mixed" in text.lower(),
                      repr(text))
                frame.locator("[data-preset-drawer] [data-preset-cancel]").click()

                # --- overwrite does not depend on provenance ---
                # This card is MIXED, so it states no applied preset at all;
                # updating an existing preset must still be reachable.
                check("save stays offered on a card with no agreed provenance",
                      not frame.locator(
                          '[data-preset-slot] [data-preset-action="save"]')
                      .is_disabled())
                inner(page).evaluate(
                    "() => ws.send('set_live_param',"
                    " {scope:'all', name:'density', value:0.42})")
                page.wait_for_function(
                    "() => installation.seats['1'].params.density === 0.42")
                open_authoring(frame)
                frame.locator(
                    '[data-preset-slot] [data-preset-action="save"]').click()
                picker = frame.locator("[data-preset-drawer] [data-preset-target]")
                picker.wait_for()
                check("the drawer names the preset it will overwrite",
                      picker.locator("option").all_text_contents() == ["Dawn", "Dusk"],
                      repr(picker.locator("option").all_text_contents()))
                picker.select_option("Dawn")
                before_revision = page.evaluate(
                    "() => installation.preset_catalog.alpha"
                    ".find(item => item.slug === 'Dawn').revision")
                frame.locator("[data-preset-drawer] [data-preset-commit]").click()
                page.wait_for_function(
                    "was => (installation.preset_catalog?.alpha || [])"
                    ".find(item => item.slug === 'Dawn')?.revision !== was",
                    arg=before_revision)
                with open(os.path.join(presets_dir, "Dawn.json"),
                          encoding="utf-8") as source:
                    updated = json.load(source)
                check("the overwrite stored the new value",
                      updated["params"]["density"] == [.42],
                      repr(updated["params"]))
                dawn = updated

                # --- a stale revision is refused, never silently clobbered ---
                conflict = inner(page).evaluate(
                    """() => new Promise(resolve => {
                      const handler = data => resolve(data?.message || "");
                      ws.on('error', handler);
                      ws.send('save_patch_preset', {
                        scope: 'seat', id: 2, patch: 'alpha', name: 'Dawn',
                        include: ['density'],
                        revision: 'sha256:' + '0'.repeat(64)});
                      setTimeout(() => resolve(""), 5000);
                    })""")
                check("an overwrite with a stale revision is refused",
                      "stale" in conflict.lower(), repr(conflict))
                with open(os.path.join(presets_dir, "Dawn.json"),
                          encoding="utf-8") as source:
                    check("the refused overwrite left the file untouched",
                          json.load(source) == dawn)

                # --- delete ---
                # Delete goes through the same compare-and-swap token the row
                # holds; the row's own button is gated on a selected preset,
                # which a mixed card deliberately does not have.
                inner(page).evaluate(
                    """() => {
                      const entry = installation.preset_catalog.alpha
                        .find(item => item.slug === 'Dusk');
                      ws.send('delete_patch_preset', {
                        patch: 'alpha', slug: 'Dusk',
                        revision: entry.revision});
                    }""")
                wait_catalog(page, 1)
                check("delete removes the file",
                      not os.path.exists(
                          os.path.join(presets_dir, "Dusk.json")))

                # --- the standalone facilitator has no preset affordance ---
                tablet = browser.new_page(viewport={"width": 1024,
                                                    "height": 768})
                tablet.set_default_timeout(15000)
                tablet_errors = []
                tablet.on("pageerror",
                          lambda error: tablet_errors.append(str(error)))
                tablet.goto(base_url + "/facilitator")
                # `#ws-status` is an EMPTY span when online (gotcha 5).
                tablet.wait_for_selector("#ws-status", state="attached")
                tablet.locator(".live-card").first.wait_for()
                check("the standalone facilitator renders parameter rows",
                      tablet.locator(".live-param").count() > 0)
                check("the standalone facilitator carries no preset row",
                      tablet.locator("[data-preset-slot]").count() == 0)
                check("no page errors on the facilitator", not tablet_errors,
                      repr(tablet_errors))
                tablet.close()

                # --- the Device panel: apply stays legal offline, save does
                # not (F8) ---
                page.click("#tab-button-devices")
                page.locator(
                    f'#device-roster .device-row[data-uid="{UID_A}"]').click()
                page.wait_for_selector("#device-control-toggle")
                if page.get_attribute(
                        "#device-control-toggle", "aria-expanded") != "true":
                    page.click("#device-control-toggle")
                page.wait_for_selector("#device-control [data-preset-slot]")
                check("the Device panel offers the same row while online",
                      page.evaluate(
                          "() => !document.querySelector("
                          "'#device-control [data-preset-action=\\\"new\\\"]')"
                          ".disabled"))
                stop_process(fleet)
                fleet = None
                # The offline sweep marks a device down 30 s after its last
                # heartbeat (CLAUDE.md gotcha 14).
                page.wait_for_function(
                    "uid => installation.devices[uid]?.online === false",
                    arg=UID_A, timeout=45000)
                page.wait_for_function(
                    """() => {
                      const button = document.querySelector(
                        '#device-control [data-preset-action="new"]');
                      return !!button && button.disabled;
                    }""")
                check("save is refused while the device is offline", True)
                check("applying stays offered offline",
                      not page.evaluate(
                          "() => document.querySelector("
                          "'#device-control [data-preset-select]').disabled"))

                check("no page errors", not errors, repr(errors))
                browser.close()
        finally:
            stop_process(fleet)
            stop_process(server)
            server_log.close()
            fleet_log.close()

    if FAILURES:
        print("\nFAILED: " + "; ".join(FAILURES))
        return 1
    print("\nPreset control-surface checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
