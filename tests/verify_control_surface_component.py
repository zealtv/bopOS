#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for the shared control surface
(thread 37, stitch 07).

The surface used to live inside facilitator.js. It was extracted to
control-surface.js so the Device tab (stitch 09) and the Control tab (stitch 10)
render the identical rows -- Bob's ratified ruling was "same component,
different send". These checks pin that seam:

  (a) the component is loaded on BOTH pages (the facilitator and the dashboard
      index), because the Device tab needs it;
  (b) the facilitator still renders every scope through it -- all / group /
      seat -- with nested param branches intact;
  (c) a `device`-scoped render is markup-identical to a `seat`-scoped render of
      the same declarations once the scope/id attributes are normalized, which
      is what "one code path" means concretely;
  (d) binding a device-scoped row calls the HOST's send with the device scope
      and uid, proving the send is the host's business and not a second
      renderer inside the component;
  (e) the ratified row grammar and mixed/takeover presentation;
  (f) hierarchy accordions and the persistence of a collapsed branch across a
      heartbeat re-render and a reload.

Owned by code surface (dashboard/static/js/control-surface.js), not by a
stitch -- per the thread-27 durable-tests policy.
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


def stop(process):
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


UIDS = ["02:53:49:4d:00:01", "02:53:49:4d:00:02"]


def make_fixture(root):
    patches = os.path.join(root, "patches")
    assets = os.path.join(root, "assets")
    state_dir = os.path.join(root, "sim-state")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(assets)
    os.makedirs(state_dir)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"control-surface-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"name": "gate", "kind": "toggle",
             "default": 0, "dashboard": True},
            {"name": "density", "kind": "float", "min": 0, "max": 1,
             "default": .2, "dashboard": True},
            # A non-boolean integer: its value box right-aligns, which is how
            # the ratified row grammar says "this parameter is an integer".
            {"name": "steps", "kind": "int", "min": 0, "max": 8,
             "default": 2, "dashboard": True},
            # An enum names its integer indices; the range is derived from the
            # options, and it automates like any other integer (Q2 ruling).
            {"name": "mode", "kind": "enum", "options": ["dry", "hall", "plate"],
             "default": 1, "dashboard": True},
            # A nested path exercises the branch renderer.
            {"name": "cutoff", "kind": "float", "min": 0, "max": 1,
             "default": .5, "path": ["filter"], "dashboard": True},
            # Text defaults are strings; omitting one still yields an empty control.
            {"name": "label", "kind": "text", "dashboard": True},
        ],
        # Declared, rendered, and inert: the `<target>/e/*` wire is
        # `44-event-plane`'s question, so this row must render without
        # sending anything.
        "events": [{"name": "strike", "arity": 2,
                    "labels": ["note", "velocity"], "defaults": [64, 127],
                    "dashboard": True}],
        "caps": [], "slots": [],
    }
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump(manifest, target, indent=2)

    def seat(seat_id, name, uid):
        # Identical values keep the All aggregate non-mixed, so the aggregate
        # and seat renders are comparable.
        return {"id": seat_id, "name": name, "positions": [[seat_id, 1]],
                "groups": [0], "bound": uid, "patch": "alpha",
                "params": {"gate": 0, "density": .2, "steps": 2,
                           "filter/cutoff": .5, "label": "hello",
                           "mode": 1}}

    state = {
        "schema": 1, "name": "Control surface verifier",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "groups": {"0": {"id": 0, "name": "Front"}},
        "seats": {"1": seat(1, "Freda", UIDS[0]),
                  "2": seat(2, "Sparks", UIDS[1])},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path


# Renders the same declarations at seat scope and at device scope through a
# freshly created component instance, normalizes the scope/id attributes, and
# reports whether the markup is otherwise identical.
PARITY_JS = """
() => {
  const seat = Object.values(installation.seats)[0];
  installation.automation = {
    [String(seat.id)]: {
      density: {
        args: ["lfo", "sine", 0.1, 0.9, "2s"],
        kind: "lfo",
        shape: "sine",
        free: false,
        phase_at_send_ms: 250,
        sent_at: Date.now() / 1000,
      },
    },
  };
  const declarations = [...installation.live_controls.declarations,
                        ...(installation.live_controls.events || [])]
    .map(d => ({...d, path: d.path || []}));
  const device = {online: true, engine_alive: 1, device_enabled: true,
                  output_enabled: true, uid: seat.bound};
  const probe = window.ControlSurface.create({
    getState: () => installation,
    deviceForSeat: () => device,
    deviceForScope: () => device,
    send: payload => (window.__probeSent = window.__probeSent || []).push(payload),
  });
  probe.refreshAnchors(installation);
  const normalize = html => html
    .replace(/data-live-scope="[^"]*"/g, 'data-live-scope="X"')
    .replace(/data-live-id="[^"]*"/g, 'data-live-id="X"')
    // The generator drawer key is scope:id:identity, so it varies for the
    // same reason the scope attributes do.
    .replace(/data-gen-key="[^"]*"/g, 'data-gen-key="X"')
    // Likewise the accordion's collapse key, which is scope:branch-path.
    .replace(/data-branch-key="[^"]*"/g, 'data-branch-key="X"')
    // Sequential renders can cross a millisecond boundary; elapsed phase is
    // presentation bookkeeping, not a seat/device scope difference.
    .replace(/--auto-elapsed:[^;"]+/g, '--auto-elapsed:X');
  const seatHtml = probe.tree("seat", seat.id, [seat], declarations, false);
  const deviceHtml = probe.tree("device", seat.bound, [seat], declarations, false);
  // Keep the probe under the same panel-scoped stylesheet as shipping rows,
  // but outside `#cards`: facilitator heartbeats replace that container's
  // innerHTML and used to intermittently delete the probe between checks.
  const fixture = document.createElement("article");
  fixture.id = "surface-probe-card";
  fixture.className = "live-card";
  const host = document.createElement("div");
  host.id = "surface-probe";
  host.innerHTML = deviceHtml;
  fixture.appendChild(host);
  document.getElementById("cards").after(fixture);
  probe.bind(host);
  return {
    identical: normalize(seatHtml) === normalize(deviceHtml),
    seatAutomated: seatHtml.includes('data-automated="true"')
      && seatHtml.includes("live-param-marker"),
    deviceAutomated: deviceHtml.includes('data-automated="true"')
      && deviceHtml.includes("live-param-marker"),
    seatHtml: normalize(seatHtml).slice(0, 400),
    deviceHtml: normalize(deviceHtml).slice(0, 400),
  };
}
"""


# Measures the ratified parameter-row grammar
# (`[value box][name-in-slider][∿]`) on the probe host. PARITY_JS keeps it in
# a dedicated `.live-card` outside the heartbeat-rendered `#cards`, so the
# panel stylesheet applies without making the fixture disposable. `density`
# there is generator-driven, `steps`/`filter/cutoff` are manual.
ROW_GRAMMAR_JS = """
() => {
  const host = document.getElementById("surface-probe");
  const row = path => host.querySelector(`.live-param[data-param-path="${path}"]`);
  const density = row("density");
  const steps = row("steps");
  const cutoff = row("filter/cutoff");
  const wrap = cutoff.querySelector(".live-param-range-wrap");
  const range = wrap.querySelector('input[type="range"]');
  const fillOf = element => element.querySelector(".live-param-range-wrap")
    .style.getPropertyValue("--v");
  // Drive the range the way a drag does, so the binding under test is the
  // shipping `oninput` handler rather than a re-render.
  range.value = "0.8";
  range.dispatchEvent(new Event("input", {bubbles: true}));
  const marker = density.querySelector(".live-param-marker");
  return {
    // `precise-output` is added by the precision-field binding, so name the
    // row's own class rather than the whole class list.
    shape: [...cutoff.children].map(
      node => `${node.tagName}.${node.classList[0]}`),
    nameInsideSlider: !!density.querySelector(
      ".live-param-range-wrap > .live-param-name"),
    nameText: density.querySelector(".live-param-name").textContent,
    fillPosition: fillOf(density),
    integerFillPosition: fillOf(steps),
    fillAfterDrag: fillOf(cutoff),
    floatAlign: getComputedStyle(
      cutoff.querySelector("output.live-param-value")).textAlign,
    integerAlign: getComputedStyle(
      steps.querySelector("output.live-param-value")).textAlign,
    rangeBackground: getComputedStyle(range).backgroundColor,
    automatedStaticFill: getComputedStyle(
      density.querySelector(".live-param-fill")).display,
    automatedMarkerFill: marker
      ? getComputedStyle(marker, "::before").backgroundColor : "",
    manualStaticFill: getComputedStyle(
      steps.querySelector(".live-param-fill")).display,
    manualMarkerLine: getComputedStyle(
      steps.querySelector(".live-param-range-wrap"), "::after").display,
  };
}
"""


# "Editing unifies" (design-language §6) rendered on a probe aggregate, so the
# takeover is measurable without sending anything to the fleet: the probe's
# send callback collects payloads instead of reaching a host websocket.
MIXED_TAKEOVER_JS = """
() => {
  const [first, second] = Object.values(installation.seats);
  const disagreeing = {...second, params: {...second.params, density: .9}};
  const declarations = installation.live_controls.declarations
    .map(d => ({...d, path: d.path || []}));
  const probe = window.ControlSurface.create({
    getState: () => installation,
    deviceForSeat: () => ({online: true, engine_alive: 1,
                           device_enabled: true, output_enabled: true}),
    send: payload => (window.__mixedSent = window.__mixedSent || []).push(payload),
  });
  const host = document.createElement("div");
  host.id = "mixed-probe";
  host.innerHTML = probe.tree("all", null, [first, disagreeing],
                              declarations, false);
  document.querySelector(".live-card").appendChild(host);
  probe.bind(host);
  const row = host.querySelector('.live-param[data-param-path="density"]');
  const fill = row.querySelector(".live-param-fill");
  const range = row.querySelector('input[type="range"]');
  const before = {
    mixed: row.classList.contains("mixed"),
    hatch: getComputedStyle(fill).backgroundImage,
    width: getComputedStyle(fill).width,
  };
  range.value = "0.6";
  range.dispatchEvent(new Event("input", {bubbles: true}));
  return {
    before,
    after: {
      mixed: row.classList.contains("mixed"),
      hatch: getComputedStyle(fill).backgroundImage,
      position: row.querySelector(".live-param-range-wrap")
        .style.getPropertyValue("--v"),
    },
    sent: window.__mixedSent || [],
  };
}
"""

# The non-float kinds (control-panel-design §2), measured on the probe host
# inside a real `.live-card` so the panel stylesheet applies. `gate` was
# clicked on before this runs, so it reads as pressed; `mode` is an enum over
# three option labels; `strike` is a declared event, which must render its
# ratified row and stay inert.
KIND_SHAPE_JS = """
() => {
  const host = document.getElementById("surface-probe");
  const row = path => host.querySelector(`.live-param[data-param-path="${path}"]`);
  const gate = row("gate");
  const toggle = gate.querySelector("button.live-toggle");
  const mode = row("mode");
  const select = mode.querySelector("select.live-enum");
  const event = row("strike");
  const string = row("label");
  const boxes = [...event.querySelectorAll(".live-event-box")];
  return {
    toggleIsButton: toggle.tagName === "BUTTON",
    togglePressed: toggle.getAttribute("aria-pressed"),
    // The box carries the state; the name is a sibling label, not its text.
    toggleMark: toggle.textContent.trim(),
    toggleName: gate.querySelector(":scope > .live-param-name").textContent,
    toggleSquare: (() => { const r = toggle.getBoundingClientRect();
                           return Math.round(r.width) === Math.round(r.height); })(),
    // A latching control is sharp, a momentary one is rounded (§8).
    toggleRadius: getComputedStyle(toggle).borderTopLeftRadius,
    toggleNoCheckbox: !gate.querySelector('input[type="checkbox"]'),
    toggleHasMod: !!gate.querySelector("button.live-param-mod"),
    enumOptions: [...select.options].map(option => option.textContent),
    enumValue: select.value,
    enumName: mode.querySelector(":scope > .live-param-name").textContent,
    enumHasMod: !!mode.querySelector("button.live-param-mod"),
    // The string row is one row tall like every other kind.
    stringHeight: Math.round(string.getBoundingClientRect().height),
    stringFieldHeight: Math.round(
      string.querySelector('input[type="text"]').getBoundingClientRect().height),
    rowHeight: Math.round(row("steps").getBoundingClientRect().height),
    eventArity: event.dataset.eventArity,
    eventBoxes: boxes.map(box => box.value),
    // The name hugs the last box; only the gap separates them.
    eventNameGap: Math.round(
      event.querySelector(":scope > .live-param-name").getBoundingClientRect().left
      - boxes[boxes.length - 1].getBoundingClientRect().right),
    eventButtons: [...event.querySelectorAll("button")].map(
      button => [button.textContent.trim(), button.disabled]),
    // Left to right: fire, the element boxes, then the name. The `sync`
    // toggle this once pinned is gone -- superseded by `4-cue-retirement`
    // (Bob, 2026-07-27: every event forward-syncs, so a per-row choice
    // cannot exist; global lead 0 is the only sync-off).
    eventLayout: (() => {
      const x = node => node.getBoundingClientRect().left;
      const send = event.querySelector(".live-event-send");
      const name = event.querySelector(":scope > .live-param-name");
      return {
        ordered: x(send) < x(boxes[0]) && x(boxes[0]) < x(name),
        noSyncToggle: !event.querySelector(".live-event-sync"),
      };
    })(),
  };
}
"""


# What a control does when its generator's value is NOT knowable (Bob,
# 2026-07-27). An LFO's and a loop's position are painted by a CSS animation,
# so no JavaScript holds the value between heartbeats: a marker-bearing slider
# still shows it exactly, but the number box, a toggle and an enum cannot. Those
# show the mixed dots and pulse the modulation ink rather than animate something
# that reads as a value. A fade is the control case — the rAF animator samples
# it every frame, so it keeps its number and does not pulse.
PULSE_JS = """
() => {
  const seat = Object.values(installation.seats)[0];
  const now = Date.now() / 1000;
  const entry = (args, kind, shape) => ({args, kind, shape, free: false,
                                         phase_at_send_ms: 0, sent_at: now});
  installation.automation = {
    [String(seat.id)]: {
      density: entry(["lfo", "sine", 0.1, 0.9, "4s"], "lfo", "sine"),
      // A fade is bare positional args — from, to, duration (§3.2); a
      // leading "fade" keyword is not the grammar.
      steps: entry([0, 8, "600s"], "fade"),
      gate: entry(["lfo", "square", 0, 1, "2s"], "lfo", "square"),
      mode: entry(["lfo", "tri", 0, 2, "4s"], "lfo", "tri"),
    },
  };
  const declarations = [...installation.live_controls.declarations,
                        ...(installation.live_controls.events || [])]
    .map(d => ({...d, path: d.path || []}));
  const probe = window.ControlSurface.create({
    getState: () => installation,
    deviceForSeat: () => ({online: true, engine_alive: 1,
                           device_enabled: true, output_enabled: true}),
    send: () => {},
  });
  probe.refreshAnchors(installation);
  const host = document.createElement("div");
  host.id = "pulse-probe";
  host.innerHTML = probe.tree("seat", seat.id, [seat], declarations, false);
  document.querySelector(".live-card").appendChild(host);
  probe.bind(host);
  const read = path => {
    const row = host.querySelector(`.live-param[data-param-path="${path}"]`);
    const box = row.querySelector("output.live-param-value");
    const control = row.querySelector(
      ".live-toggle, .live-enum, .live-param-range-wrap");
    return {
      automated: row.classList.contains("automated"),
      pulsing: row.classList.contains("auto-pulse"),
      animation: getComputedStyle(control).animationName,
      dots: box ? box.dataset.dots === "true" : null,
      text: box ? box.textContent : null,
      ink: box ? getComputedStyle(box).color : null,
    };
  };
  return {lfo: read("density"), fade: read("steps"),
          toggle: read("gate"), enumeration: read("mode"),
          manual: read("filter/cutoff")};
}
"""


# Changing an enum puts the option INDEX on the wire, not its label: the enum
# is a labelled view of the same integer a generator drives (Q2).
# Reading `__probeSent.at(-1)` straight after the dispatch is a race: a
# heartbeat re-render landing between the value write and the dispatch swaps
# the <select> for a freshly bound one, and the last entry is then still
# whatever the previous interaction sent. Re-query after the write and look
# for THIS param's send rather than trusting position. (Pre-existing flake,
# reproduced on the commit before `4-cue-retirement`; fixed here because it
# reddens the browser tier at roughly one run in three.)
ENUM_SEND_JS = """
() => {
  const find = () => document.querySelector(
    '#surface-probe select.live-enum[data-param-path="mode"]');
  const before = (window.__probeSent || []).length;
  const select = find();
  select.value = "2";
  find().dispatchEvent(new Event("change", {bubbles: true}));
  const sent = window.__probeSent || [];
  return sent.slice(before).find(entry => entry && entry.name === "mode")
    ?? sent.at(-1);
}
"""


# The hierarchy accordion (design-language §9): a `<details>` whose `<summary>`
# is the `▸ name` / `▾ name` disclosure row, children indented 12px. The
# disclosure glyph is a `::before`, so it is invisible to textContent and has
# to be read off the computed style.
ACCORDION_SHAPE_JS = """
selector => {
  const branch = document.querySelector(selector);
  const summary = branch.querySelector(":scope > summary");
  const kids = branch.querySelector(":scope > .live-param-branch-kids");
  return {
    tag: branch.tagName,
    open: branch.open === true,
    summary: summary ? summary.textContent.trim() : null,
    marker: summary
      ? getComputedStyle(summary, "::before").content.replace(/"/g, "") : null,
    kids: !!(kids
      && kids.querySelector('[data-param-path="filter/cutoff"]')),
    indent: kids ? getComputedStyle(kids).marginLeft : null,
  };
}
"""


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-control-surface-") as temp:
        state_path = make_fixture(temp)
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        state_dir = os.path.join(temp, "sim-state")
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
                "--state-dir", state_dir, "--manifest",
                os.path.join(patches, "alpha", "bopos.patch.json"),
                "--patches-dir", patches, "--assets-dir", assets,
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 900,
                                                  "height": 1200})
                page.set_default_timeout(10000)
                page_errors = []
                page.on("pageerror",
                        lambda error: page_errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.dismiss())

                page.goto(base_url + "/facilitator")
                page.wait_for_selector('.live-card[data-live-scope="all"]')
                page.wait_for_function(
                    "() => Object.keys(installation.devices||{}).length === 2")

                check("component is loaded on the facilitator page",
                      page.evaluate(
                          "() => typeof window.ControlSurface?.create"
                          " === 'function'"))

                # --- (b) every scope still renders through the component ---
                # The target filter (37/10) shows one scope at a time, so walk
                # it rather than expecting all the cards at once.
                check("all card renders rows through the component",
                      page.locator(
                          '.live-card[data-live-scope="all"] '
                          '[data-live-param][data-param-path="density"]'
                      ).count() >= 1)
                # Both the wrapping label and the input carry data-param-path,
                # so pin the input to get an unambiguous count.
                check("nested path renders a param branch",
                      page.locator(
                          '.live-card[data-live-scope="all"] '
                          '.live-param-branch[data-param-branch="filter"] '
                          'input[data-live-param]'
                          '[data-param-path="filter/cutoff"]').count() == 1)
                check("string and toggle declarations render their own kinds",
                      page.locator(
                          '.live-card[data-live-scope="all"] '
                          'input[type="text"][data-param-path="label"]'
                      ).count() == 1
                      and page.locator(
                          '.live-card[data-live-scope="all"] '
                          'button.live-toggle[data-param-path="gate"]'
                      ).count() == 1)

                page.click('[data-target-mode="groups"]')
                page.wait_for_selector('.live-card[data-live-scope="group"]')
                check("group card renders rows through the component",
                      page.locator(
                          '.live-card[data-live-scope="group"] '
                          '[data-live-param][data-param-path="density"]'
                      ).count() >= 1)

                page.click('[data-target-mode="seat"]')
                page.wait_for_selector('.live-card[data-live-scope="seat"]')
                check("seat cards render rows through the component",
                      page.locator(
                          '.live-card[data-live-scope="seat"] '
                          '[data-live-param][data-param-path="density"]'
                      ).count() == 1)

                # --- (c) device scope is the same render as seat scope ---
                parity = page.evaluate(PARITY_JS)
                check("device-scoped value and automation presentation is "
                      "markup-identical to seat scope",
                      parity["identical"] and parity["seatAutomated"]
                      and parity["deviceAutomated"],
                      f"seat={parity['seatHtml']!r} "
                      f"device={parity['deviceHtml']!r}")

                # --- (d) the send is the host's, carrying scope + uid ---
                page.click(
                    '#surface-probe button.live-toggle'
                    '[data-param-path="gate"]')
                sent = page.evaluate("() => window.__probeSent || []")
                check("device-scoped row calls the host send with scope+uid",
                      len(sent) == 1
                      and sent[0].get("scope") == "device"
                      and sent[0].get("id") == UIDS[0]
                      and sent[0].get("name") == "gate"
                      and sent[0].get("value") == 1,
                      repr(sent))

                # --- (e) the ratified row grammar (01-control-panel/4) ---
                # The probe host lives in a dedicated `.live-card` outside
                # `#cards`, so the panel-scoped stylesheet applies without a
                # heartbeat replacing the fixture. PARITY_JS put an LFO on
                # `density`, alongside the manual rows measured here.
                grammar = page.evaluate(ROW_GRAMMAR_JS)
                check("the row is [value box][name-in-slider][∿]",
                      grammar["shape"] == ["OUTPUT.live-param-value",
                                           "SPAN.live-param-range-wrap",
                                           "BUTTON.live-param-mod"],
                      repr(grammar["shape"]))
                check("the parameter name lives inside the slider",
                      grammar["nameInsideSlider"]
                      and grammar["nameText"].startswith("density"),
                      repr(grammar))
                check("the fill position follows the value",
                      grammar["fillPosition"] == "0.2"
                      and grammar["integerFillPosition"] == "0.25",
                      repr([grammar["fillPosition"],
                            grammar["integerFillPosition"]]))
                check("dragging the slider moves the fill with it",
                      grammar["fillAfterDrag"] == "0.8",
                      repr(grammar["fillAfterDrag"]))
                check("floats left-align in the value box, integers right",
                      grammar["floatAlign"] == "left"
                      and grammar["integerAlign"] == "right",
                      repr([grammar["floatAlign"], grammar["integerAlign"]]))
                check("the native range is a transparent overlay",
                      grammar["rangeBackground"] in ("rgba(0, 0, 0, 0)",
                                                     "transparent"),
                      repr(grammar["rangeBackground"]))
                check("a generator-driven row hands the fill to its marker",
                      grammar["automatedStaticFill"] == "none"
                      and grammar["automatedMarkerFill"]
                      not in ("", "rgba(0, 0, 0, 0)", "none"),
                      repr([grammar["automatedStaticFill"],
                            grammar["automatedMarkerFill"]]))
                check("a manual row keeps its own fill and marker line",
                      grammar["manualStaticFill"] == "block"
                      and grammar["manualMarkerLine"] != "none",
                      repr([grammar["manualStaticFill"],
                            grammar["manualMarkerLine"]]))

                # --- the non-float kinds (01-control-panel/6) ---
                kinds = page.evaluate(KIND_SHAPE_JS)
                check("a 0/1 int is a square latching box, not a checkbox",
                      kinds["toggleIsButton"] and kinds["toggleNoCheckbox"]
                      and kinds["togglePressed"] == "true"
                      and kinds["toggleMark"] == "✕"
                      and kinds["toggleSquare"]
                      and kinds["toggleRadius"] == "1px",
                      repr(kinds))
                check("the toggle and enum label their box from beside it",
                      kinds["toggleName"] == "gate"
                      and kinds["enumName"] == "mode",
                      repr([kinds["toggleName"], kinds["enumName"]]))
                check("the string row is one row tall, like every other kind",
                      kinds["stringHeight"] == kinds["rowHeight"]
                      and kinds["stringFieldHeight"] == kinds["rowHeight"],
                      repr([kinds["stringHeight"], kinds["stringFieldHeight"],
                            kinds["rowHeight"]]))
                check("a toggle carries the ∿ icon like any numeric row",
                      kinds["toggleHasMod"] and kinds["enumHasMod"],
                      repr([kinds["toggleHasMod"], kinds["enumHasMod"]]))
                check("an enum renders its manifest option labels",
                      kinds["enumOptions"] == ["dry", "hall", "plate"]
                      and kinds["enumValue"] == "1", repr(kinds))
                # `bindParams` assigns `onchange` after each re-render, so a
                # dispatch aimed at a freshly rendered <select> lands on an
                # unbound element and sends nothing. Wait for the binding
                # rather than the element.
                page.wait_for_function(
                    "() => !!document.querySelector("
                    "'#surface-probe select.live-enum"
                    "[data-param-path=\"mode\"]')?.onchange")
                enum_sent = page.evaluate(ENUM_SEND_JS)
                check("choosing an enum option sends its integer index",
                      enum_sent
                      and enum_sent.get("name") == "mode"
                      and enum_sent.get("value") == 2, repr(enum_sent))
                check("an event declaration renders exactly arity boxes",
                      kinds["eventArity"] == "2"
                      # Exactly arity boxes: no slot is held open for the
                      # elements a lower-arity event does not have.
                      and kinds["eventBoxes"] == ["64", "127"],
                      repr(kinds))
                # Superseded by `4-cue-retirement`: this asserted the row was
                # inert ("sends nothing until 44-event-plane lands") and
                # carried a disabled `sync` toggle. The plane landed, so the
                # row is live and has exactly one fire button.
                check("the event row is live with a single fire button",
                      kinds["eventButtons"] == [["fire", False]],
                      repr(kinds["eventButtons"]))
                check("the event row reads fire · elements · name",
                      kinds["eventLayout"]["ordered"]
                      and kinds["eventLayout"]["noSyncToggle"]
                      # Hugging its last box, not floating in a fixed column.
                      and kinds["eventNameGap"] <= 8,
                      repr([kinds["eventLayout"], kinds["eventNameGap"]]))

                # --- no misleading automation cue (8-kind-feedback-pass) ---
                pulse = page.evaluate(PULSE_JS)
                check("a periodic generator shows dots, not a stale number",
                      pulse["lfo"]["dots"]
                      and pulse["lfo"]["text"] == "·····"
                      # the modulation ink, kept: cyan says who owns the value
                      and pulse["lfo"]["ink"] != pulse["manual"]["ink"],
                      repr([pulse["lfo"], pulse["manual"]]))
                check("a marker-bearing slider does not pulse — it shows the "
                      "value exactly",
                      pulse["lfo"]["automated"]
                      and not pulse["lfo"]["pulsing"]
                      and pulse["lfo"]["animation"] == "none",
                      repr(pulse["lfo"]))
                check("a fade keeps its number: the rAF animator samples it",
                      pulse["fade"]["automated"]
                      and not pulse["fade"]["dots"]
                      and not pulse["fade"]["pulsing"],
                      repr(pulse["fade"]))
                check("a generator-driven toggle pulses instead of flashing "
                      "a value",
                      pulse["toggle"]["automated"]
                      and pulse["toggle"]["pulsing"]
                      and pulse["toggle"]["animation"] == "live-param-pulse",
                      repr(pulse["toggle"]))
                check("a generator-driven enum pulses too",
                      pulse["enumeration"]["automated"]
                      and pulse["enumeration"]["pulsing"]
                      and pulse["enumeration"]["animation"]
                      == "live-param-pulse",
                      repr(pulse["enumeration"]))

                takeover = page.evaluate(MIXED_TAKEOVER_JS)
                check("a disagreeing aggregate hatches its slider",
                      takeover["before"]["mixed"]
                      and "repeating-linear-gradient"
                      in takeover["before"]["hatch"],
                      repr(takeover["before"]))
                check("editing a mixed row renders it solid at the new value",
                      not takeover["after"]["mixed"]
                      and "repeating-linear-gradient"
                      not in takeover["after"]["hatch"]
                      and takeover["after"]["position"] == "0.6",
                      repr(takeover["after"]))
                check("editing a mixed row sends the value to every member",
                      len(takeover["sent"]) >= 1
                      and takeover["sent"][-1].get("scope") == "all"
                      and takeover["sent"][-1].get("value") == .6,
                      repr(takeover["sent"]))

                # --- (f) hierarchy accordions (01-control-panel/5) ---
                # The seat card is the one on screen at this point; its manifest
                # carries the nested `filter/cutoff`, so `filter` is a branch.
                # Scoped through `.promoted-controls` because the probe hosts
                # appended above render their own `filter` branch inside the
                # same card.
                branch = ('.live-card[data-live-scope="seat"] '
                          '.promoted-controls '
                          '.live-param-branch[data-param-branch="filter"]')
                child = branch + ' input[data-param-path="filter/cutoff"]'
                shape = page.evaluate(ACCORDION_SHAPE_JS, branch)
                check("a nested branch is a disclosure accordion, open by "
                      "default",
                      shape["tag"] == "DETAILS" and shape["open"]
                      and shape["summary"] == "filter"
                      and shape["kids"], repr(shape))
                check("the accordion's children indent 12px",
                      shape["indent"] == "12px", repr(shape["indent"]))
                check("an open branch shows the ▾ disclosure glyph",
                      shape["marker"] == "▾", repr(shape["marker"]))

                # Collapse it, then prove the pruning survives both a heartbeat
                # re-render (which replaces the node) and a reload.
                page.eval_on_selector(branch,
                                      "node => node.dataset.renderProbe = '1'")
                page.click(branch + " > summary")
                collapsed = page.evaluate(ACCORDION_SHAPE_JS, branch)
                check("clicking the summary collapses the branch",
                      not collapsed["open"]
                      and not page.locator(child).is_visible(),
                      repr(collapsed))
                check("a collapsed branch shows the ▸ disclosure glyph",
                      collapsed["marker"] == "▸", repr(collapsed["marker"]))
                page.wait_for_function(
                    "selector => document.querySelector(selector)"
                    " && !document.querySelector(selector).dataset.renderProbe",
                    arg=branch)
                check("the collapse survives the heartbeat re-render",
                      page.locator(branch).get_attribute("open") is None
                      and not page.locator(child).is_visible())

                page.reload()
                # The target filter persists its own mode, so the reload comes
                # back on Seats; click it anyway rather than assume either way.
                page.wait_for_selector('.live-card')
                page.click('[data-target-mode="seat"]')
                page.wait_for_selector('.live-card[data-live-scope="seat"]')
                check("the collapse survives a reload",
                      page.locator(branch).get_attribute("open") is None
                      and not page.locator(child).is_visible())
                check("the collapse is keyed by scope and branch path",
                      page.evaluate(
                          "() => JSON.parse(localStorage.getItem("
                          "'bopos.control.collapsed-branches') || '[]')")
                      == ["seat:filter"])

                # Re-opening clears the pruning again, so the store never
                # accumulates state for branches the operator has restored.
                page.click(branch + " > summary")
                # `toggle` is dispatched asynchronously, so wait for the store
                # to settle rather than reading it in the same tick.
                cleared = True
                try:
                    page.wait_for_function(
                        "() => JSON.parse(localStorage.getItem("
                        "'bopos.control.collapsed-branches') || '[]')"
                        ".length === 0")
                except Exception:
                    cleared = False
                check("re-opening the branch restores its children and clears "
                      "the stored collapse",
                      page.locator(branch).get_attribute("open") is not None
                      and page.locator(child).is_visible()
                      and cleared)

                check("facilitator emitted no page errors",
                      not page_errors, repr(page_errors))

                # --- (a) the dashboard index loads it too, for stitch 09 ---
                dash_errors = []
                dash = browser.new_page(viewport={"width": 1400,
                                                  "height": 1000})
                dash.on("pageerror",
                        lambda error: dash_errors.append(str(error)))
                dash.goto(base_url + "/")
                dash.wait_for_function(
                    "() => typeof window.ControlSurface?.create"
                    " === 'function'")
                check("component is loaded on the dashboard page", True)
                check("dashboard emitted no page errors",
                      not dash_errors, repr(dash_errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

    print()
    if FAILURES:
        print("FAILED: " + "; ".join(FAILURES))
        return 1
    print("Control surface component checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
