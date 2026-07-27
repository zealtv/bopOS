#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for the generator drawer on the live
control surface (thread 37, stitch 08).

Bob ratified three things about this affordance, and each one is a check here:

  1. DRAWER, not popover, in every host -- so a numeric row has a value/gen
     switch that opens an inline drawer, and there is no popover variant.
  2. MIXED AGGREGATES USE THE EXISTING PATTERN -- the aggregate is never
     disabled because members disagree, and committing a generator sets all
     members. The failure mode this guards is a `mode === 'gen'` branch.
  3. STOP LIVES INSIDE THE DRAWER -- the switch stays strictly two-state, so
     stop is a control in the drawer and not a third segment.

It also pins the wire: the drawer compiles to the OSC contract section 3.2
grammar and reaches the node through set_live_automation, and stop clears the
recorded automation again.

Owned by code surface (control-surface.js + param-generator.js).
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


def wait_log(path, pattern, timeout=8):
    deadline = time.monotonic() + timeout
    rx = re.compile(pattern)
    while time.monotonic() < deadline:
        if rx.search(read_log(path)):
            return True
        time.sleep(.1)
    return False


# simfleet does not echo the generator command: it parses the section 3.2
# message, runs a real generator engine, and logs the scalar ticks the engine
# emits. So "the generator reached the wire and is running" is visible as a
# stream of *changing* p/<name>= values, which is a stronger claim than an echo
# would have been.
def density_ticks(path):
    return re.findall(r"p/density=([\d.eE+-]+)", read_log(path))


def param_ticks(path, name):
    return re.findall(r"p/%s=([\d.eE+-]+)" % name, read_log(path))


def wait_ticking(path, distinct=3, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if len(set(density_ticks(path))) >= distinct:
            return True
        time.sleep(.2)
    return False


UIDS = ["02:53:49:4d:00:01", "02:53:49:4d:00:02"]


def make_fixture(root, mixed):
    """`mixed` gives the two seats different values for `density`, which is how
    the aggregate lands in its mixed state without any UI interaction."""
    patches = os.path.join(root, "patches")
    assets = os.path.join(root, "assets")
    state_dir = os.path.join(root, "sim-state")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(assets)
    os.makedirs(state_dir)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"generator-drawer-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"name": "density", "kind": "float", "min": 0, "max": 1,
             "default": .2, "dashboard": True},
            {"name": "label", "kind": "text", "dashboard": True},
            # Enums automate like ints (Q2, 2026-07-27): the generator drives
            # the option INDEX, quantized on the same integer path.
            {"name": "mode", "kind": "enum", "options": ["dry", "hall", "plate"],
             "default": 0, "dashboard": True},
        ], "cues": [], "caps": [], "slots": [],
    }
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump(manifest, target, indent=2)

    def seat(seat_id, name, uid, density):
        return {"id": seat_id, "name": name, "positions": [[seat_id, 1]],
                "groups": [], "bound": uid, "patch": "alpha",
                "params": {"density": density, "label": "hi", "mode": 0}}

    state = {
        "schema": 1, "name": "Generator drawer verifier",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "seats": {"1": seat(1, "Freda", UIDS[0], .2),
                  "2": seat(2, "Sparks", UIDS[1], .8 if mixed else .2)},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path


ALL_DENSITY = ('.live-card[data-live-scope="all"] '
               'input[data-live-param][data-param-path="density"]')
ALL_ROW = ('.live-card[data-live-scope="all"] '
           '.live-param[data-param-path="density"]')
# The ratified row grammar (01-control-panel/4-row-regrind) replaced the
# `value ▸ gen` two-button switch with the ∿ icon: one disclosure that both
# opens the drawer and indicates modulation.
MOD_ICON = (ALL_ROW + " [data-gen-toggle]")
DRAWER = '.live-card[data-live-scope="all"] .live-param-gen'


def run(page, base_url, fleet_log_path, state_path, mixed):
    page.goto(base_url + "/facilitator")
    page.wait_for_selector('.live-card[data-live-scope="all"]')
    page.wait_for_function(
        "() => Object.keys(installation.devices||{}).length === 2")

    label = "mixed" if mixed else "agreeing"

    # --- 1. the ∿ icon exists on numeric rows only ---
    check(f"[{label}] numeric row carries a ∿ generator icon",
          page.locator(MOD_ICON).count() == 1)
    check(f"[{label}] string row carries no generator icon",
          page.locator('.live-card[data-live-scope="all"] '
                       '.live-param[data-param-path="label"] '
                       '[data-gen-toggle]').count() == 0)
    check(f"[{label}] the icon is a disclosure, closed to start",
          page.locator(MOD_ICON).get_attribute("aria-expanded") == "false")

    # --- 2. mixed aggregates are NOT disabled ---
    if mixed:
        check("[mixed] the aggregate row reports its mixed state",
              "mixed" in (page.locator(ALL_ROW).get_attribute("class") or ""))
        check("[mixed] the ∿ icon is NOT disabled by disagreement",
              not page.locator(MOD_ICON).is_disabled())
        # The ratified encoding: one 45° slash pattern across the whole
        # slider, the same pattern in the value box, dots for the value the
        # box cannot state, and no marker line — nothing is at "the" value.
        presentation = page.evaluate(
            """sel => {
              const row = document.querySelector(sel);
              const box = row.querySelector("output.live-param-value");
              const fill = row.querySelector(".live-param-fill");
              const wrap = row.querySelector(".live-param-range-wrap");
              return {
                boxText: box.textContent,
                boxHatch: getComputedStyle(box).backgroundImage,
                fillHatch: getComputedStyle(fill).backgroundImage,
                // clientWidth is the trough inside its 1px border, which is
                // the box the absolutely-positioned fill spans.
                fillWidth: Math.round(fill.getBoundingClientRect().width),
                wrapWidth: wrap.clientWidth,
                marker: getComputedStyle(wrap, "::after").display,
                modInk: row.classList.contains("mixed-mod"),
              };
            }""", ALL_ROW)
        check("[mixed] the value box hatches and shows dots",
              presentation["boxText"] == "·····"
              and "repeating-linear-gradient" in presentation["boxHatch"],
              repr(presentation))
        check("[mixed] the slider hatches across its whole width",
              "repeating-linear-gradient" in presentation["fillHatch"]
              and presentation["fillWidth"] == presentation["wrapWidth"],
              repr(presentation))
        check("[mixed] a mixed row carries no marker line",
              presentation["marker"] == "none", repr(presentation))
        check("[mixed] no generator is involved, so the hatch stays gray",
              not presentation["modInk"], repr(presentation))

    # --- the drawer opens inline ---
    page.click(MOD_ICON)
    page.wait_for_selector(DRAWER)
    check(f"[{label}] gen opens an inline drawer",
          page.locator(DRAWER).count() == 1)
    check(f"[{label}] the drawer is a sibling of its row, not a popover",
          page.evaluate(
              "sel => { const d = document.querySelector(sel);"
              " return d.previousElementSibling?.classList"
              ".contains('live-param'); }", DRAWER))

    # --- 3. stop is inside the drawer, not an icon state ---
    check(f"[{label}] stop is a control inside the drawer",
          page.locator(DRAWER + " [data-gen-stop]").count() == 1)
    check(f"[{label}] the row still carries exactly one ∿ icon",
          page.locator(ALL_ROW + " [data-gen-toggle]").count() == 1)
    check(f"[{label}] opening the drawer lights the icon",
          page.locator(MOD_ICON).get_attribute("aria-expanded") == "true")

    # --- the builder is the ratified one: kind tabs, fields, preview ---
    kinds = page.eval_on_selector_all(
        DRAWER + " [data-gen-kind-tab]",
        "nodes => nodes.map(n => n.dataset.genKindTab)")
    check(f"[{label}] the drawer offers the generator kinds as tabs",
          kinds == ["lfo", "loop", "fade"], repr(kinds))
    pressed = page.eval_on_selector_all(
        DRAWER + " [data-gen-kind-tab]",
        "nodes => nodes.filter(n => n.getAttribute('aria-pressed') === 'true')"
        ".map(n => n.dataset.genKindTab)")
    check(f"[{label}] exactly one kind tab is latched on",
          pressed == ["lfo"], repr(pressed))
    # --- the drawer body is the ratified panel language (01-control-panel/9) ---
    # The drawer used to render the Show inspector's stacked labelled inputs
    # with a captioned preview figure beneath them. The panel's drawer is built
    # AROUND its display: the shape select lives inside it, the shaping args are
    # mini-sliders beside it, and the numbers sit in one args row underneath.
    body = page.evaluate(
        """sel => {
          const drawer = document.querySelector(sel);
          const wave = drawer.querySelector(".live-gen-wave");
          return {
            wave: !!wave,
            trace: !!drawer.querySelector(".live-gen-wave-line"),
            // the shape picker is INSIDE the display, not a labelled row
            shapeInside: !!wave?.querySelector('[data-param-lfo="shape"]'),
            // phase is a mini-slider, not a number field
            phaseRange: drawer.querySelector('[data-param-lfo="phase"]')?.type,
            args: [...drawer.querySelectorAll(".live-gen-args .live-gen-field")]
              .map(field => field.textContent.trim()),
            // the Show inspector's markup is gone from this host
            inspectorFigure: drawer.querySelectorAll(".show-param-preview").length,
            inspectorGrid: drawer.querySelectorAll(".show-param-lfo").length,
          };
        }""", DRAWER)
    check(f"[{label}] the drawer is built around a waveform display",
          body["wave"] and body["trace"] and body["shapeInside"], repr(body))
    check(f"[{label}] shaping args are mini-sliders",
          body["phaseRange"] == "range", repr(body))
    check(f"[{label}] min, max and period sit in one args row",
          body["args"] == ["min", "max", "period"], repr(body))
    check(f"[{label}] the Show inspector's drawer markup is gone",
          body["inspectorFigure"] == 0 and body["inspectorGrid"] == 0,
          repr(body))

    # Curve bends tri, saw and drift and does nothing to the rest, so the
    # panel only offers it where it bites (Bob, 2026-07-27). The engine
    # (`python/paramgen.py` `_lfo_value`) is the authority for that list.
    def curve_shown():
        return page.evaluate(
            """sel => {
              const slot = document.querySelector(sel + " .live-gen-curve-slot");
              return !!slot && !slot.hidden;
            }""", DRAWER)

    check(f"[{label}] a sine offers no curve control", not curve_shown())
    page.select_option(DRAWER + ' [data-param-lfo="shape"]', "tri")
    check(f"[{label}] a tri does offer curve", curve_shown())
    page.select_option(DRAWER + ' [data-param-lfo="shape"]', "square")
    check(f"[{label}] switching back to square takes curve away again",
          not curve_shown())
    page.select_option(DRAWER + ' [data-param-lfo="shape"]', "sine")

    # --- the wire: a committed generator reaches the node as sec 3.2 args ---
    page.select_option(DRAWER + ' [data-param-lfo="shape"]', "tri")
    page.fill(DRAWER + ' [data-param-lfo="period"]', "2")
    page.click(DRAWER + " [data-gen-apply]")
    check(f"[{label}] applying runs the generator on the node",
          wait_ticking(fleet_log_path),
          "fleet log shows no ticking density: "
          + repr(density_ticks(fleet_log_path)[-6:]))
    check(f"[{label}] the node accepted the grammar",
          "grammar error" not in read_log(fleet_log_path))

    # --- committing sets ALL members, so the aggregate is no longer mixed ---
    became = page.wait_for_function(
        "() => Object.values(installation.automation || {})"
        ".filter(entry => entry.density).length === 2", timeout=8000)
    check(f"[{label}] the generator is recorded for every member seat",
          became is not None)

    # --- stop clears it again ---
    page.click(DRAWER + " [data-gen-stop]")
    before = len(density_ticks(fleet_log_path))
    time.sleep(1.5)
    settled = len(density_ticks(fleet_log_path))
    time.sleep(1.0)
    check(f"[{label}] stop halts the generator on the node",
          len(density_ticks(fleet_log_path)) == settled and settled >= before,
          f"ticks kept arriving after stop: {before} -> {settled} -> "
          f"{len(density_ticks(fleet_log_path))}")
    cleared = page.wait_for_function(
        "() => Object.values(installation.automation || {})"
        ".every(entry => !entry.density)", timeout=8000)
    check(f"[{label}] stop clears the recorded automation", cleared is not None)

    # --- the fade's optional `from` is stated, not implied (Bob, 2026-07-27) ---
    # "No from value" is a real state — start from wherever the parameter is —
    # and an empty box could not say it out loud. An unlabelled latching box
    # says it, and this pins that the box, not the field's emptiness, is what
    # reaches the wire.
    page.click(DRAWER + ' [data-gen-kind-tab="fade"]')
    page.wait_for_selector(DRAWER + " [data-param-from-enabled]")
    # A long segment, so the fade is still running when its args are read.
    page.fill(DRAWER + " [data-param-segment-duration]", "30")
    gate = DRAWER + " [data-param-from-enabled]"
    check(f"[{label}] the from box starts off, and its field with it",
          not page.is_checked(gate)
          and page.is_disabled(DRAWER + " [data-param-from]"))
    page.click(DRAWER + " [data-gen-apply]")
    without = page.wait_for_function(
        """() => {
          const entry = Object.values(installation.automation || {})
            .map(item => item.density).find(Boolean);
          if (!entry) return null;
          const parsed = window.ParamSpec.parse(entry.args, "f");
          return parsed.mode === "fade" ? {from: parsed.from} : null;
        }""", timeout=8000).json_value()
    check(f"[{label}] with the box off the fade carries no from value",
          without["from"] is None, repr(without))
    page.check(gate)
    check(f"[{label}] checking the box wakes its field",
          not page.is_disabled(DRAWER + " [data-param-from]"))
    page.fill(DRAWER + " [data-param-from]", "0.15")
    page.click(DRAWER + " [data-gen-apply]")
    with_from = page.wait_for_function(
        """() => {
          const entry = Object.values(installation.automation || {})
            .map(item => item.density).find(Boolean);
          if (!entry) return null;
          const parsed = window.ParamSpec.parse(entry.args, "f");
          return parsed.mode === "fade" && parsed.from === 0.15
            ? {from: parsed.from} : null;
        }""", timeout=8000).json_value()
    check(f"[{label}] checking it puts that start value on the wire",
          with_from is not None and with_from["from"] == .15, repr(with_from))
    page.click(DRAWER + " [data-gen-stop]")
    page.click(DRAWER + ' [data-gen-kind-tab="lfo"]')

    # --- a second click on the ∿ icon closes the drawer and stops nothing ---
    page.click(MOD_ICON)
    check(f"[{label}] the ∿ icon closes the drawer again",
          page.locator(DRAWER).count() == 0)
    check(f"[{label}] the underlying control is still usable",
          page.locator(ALL_DENSITY).count() == 1
          and not page.locator(ALL_DENSITY).is_disabled())

    # --- an enum takes the same drawer, and drives the option index ---
    # Q2 (2026-07-27): enums automate like ints. The row is a select, but the
    # generator path underneath it is the integer one, so the ticks the node
    # emits have to be whole option indices inside the declared range.
    enum_row = ('.live-card[data-live-scope="all"] '
                '.live-param[data-param-path="mode"]')
    check(f"[{label}] an enum row carries the ∿ icon",
          page.locator(enum_row + " [data-gen-toggle]").count() == 1)
    page.click(enum_row + " [data-gen-toggle]")
    enum_drawer = '.live-card[data-live-scope="all"] [data-gen-drawer$=":mode"]'
    page.wait_for_selector(enum_drawer)
    page.fill(enum_drawer + ' [data-param-lfo="period"]', "1")
    page.click(enum_drawer + " [data-gen-apply]")
    ticking = False
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not ticking:
        ticking = len(set(param_ticks(fleet_log_path, "mode"))) >= 2
        time.sleep(.2)
    ticks = param_ticks(fleet_log_path, "mode")
    check(f"[{label}] a generator on an enum runs on the node", ticking,
          repr(ticks[-6:]))
    check(f"[{label}] enum generator ticks are whole indices in range",
          ticks and all(float(tick) == int(float(tick))
                        and 0 <= float(tick) <= 2 for tick in ticks),
          repr(sorted(set(ticks))))
    page.click(enum_drawer + " [data-gen-stop]")
    page.click(enum_row + " [data-gen-toggle]")


def main():
    for mixed in (False, True):
        prefix = "bopos-gen-drawer-"
        with tempfile.TemporaryDirectory(prefix=prefix) as temp:
            state_path = make_fixture(temp, mixed)
            assets = os.path.join(temp, "assets")
            patches = os.path.join(temp, "patches")
            state_dir = os.path.join(temp, "sim-state")
            http_port = free_port(socket.SOCK_STREAM)
            listen_port = free_port(socket.SOCK_DGRAM)
            send_port = free_port(socket.SOCK_DGRAM)
            base_url = f"http://127.0.0.1:{http_port}"
            fleet_log_path = os.path.join(temp, "fleet.log")
            server_log = open(os.path.join(temp, "server.log"), "w",
                              encoding="utf-8")
            fleet_log = open(fleet_log_path, "w", encoding="utf-8")
            server = fleet = None
            try:
                server = subprocess.Popen([
                    sys.executable,
                    os.path.join(REPO, "dashboard", "server.py"),
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
                    "--state-dir", state_dir, "--manifest",
                    os.path.join(patches, "alpha", "bopos.patch.json"),
                    "--patches-dir", patches, "--assets-dir", assets,
                ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width": 900,
                                                      "height": 1400})
                    page.set_default_timeout(10000)
                    errors, alerts = [], []
                    page.on("pageerror",
                            lambda error: errors.append(str(error)))
                    page.on("dialog",
                            lambda dialog: (alerts.append(dialog.message),
                                            dialog.dismiss()))
                    run(page, base_url, fleet_log_path, state_path, mixed)
                    label = "mixed" if mixed else "agreeing"
                    check(f"[{label}] no server rejection alert fired",
                          not alerts, repr(alerts))
                    check(f"[{label}] no page errors", not errors,
                          repr(errors))
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
    print("Generator drawer checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
