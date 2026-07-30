#!/usr/bin/env python3
"""The shared target picker: one component, two domains
(`desktop-ui-overhaul/02-component-unification/07`).

Bob, 2026-07-30: "all or a selection of groups or a selection of seats or a
mixture of all of them using that consistent target UI device", and separately
"here we're targeting devices rather than seats. So perhaps a device picker and a
seat picker are two different things." Both rulings are checks below: one
disclosure/chip/summary chrome, two rosters and two wire vocabularies.

Two passes:

  (a) the component in isolation, on a fixture page — the selection algebra, the
      chip states, per-host persistence, the shared focus seat, and the
      re-render survival that a heartbeat-driven host depends on;
  (b) the DEVICE domain against the real dashboard, on the Assets tab, which had
      no living journey at all before this file.

Seat-domain integration is covered where it already lives: verify_control_tab.py
(the Control surface) and verify_show_reference_foundation.py (the Show
inspector's portable `group:<name>` selectors).
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

STATIC = os.path.join(REPO, "dashboard", "static")
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


# ---------------------------------------------------------------------------
# (a) the component in isolation
# ---------------------------------------------------------------------------

FIXTURE = """
  <div id="seat-host"></div>
  <div id="device-host"></div>
"""

SETUP = """
  window.venue = {
    groups: [{id: 0, name: "Front"}, {id: 7, name: "Back"}],
    seats: [{id: 0, name: "Zero"}, {id: 1, name: "One"}, {id: 2, name: "Two"}],
  };
  window.changes = [];
  window.seatPicker = TargetPicker.create({
    host: document.querySelector("#seat-host"),
    id: "control", storageKey: "test.seat", followFocusSeat: true,
    spec: () => ({
      label: "Control target",
      sections: TargetPicker.seatSections({...window.venue, groupSelector: "id"}),
    }),
    onChange: selection => window.changes.push(selection),
  });
  window.deviceRoster = [
    {uid: "uid-a", label: "Finn Jet"},
    {uid: "uid-b", label: "Ciro Toast"},
    {uid: "uid-c", label: "Offline One", sub: "offline", disabled: true},
  ];
  window.devicePicker = TargetPicker.create({
    host: document.querySelector("#device-host"),
    id: "assets", storageKey: "test.device",
    spec: () => ({
      label: "device", allowAll: false, multiple: false,
      sections: TargetPicker.deviceSections(window.deviceRoster),
    }),
  });
  window.seatPicker.render();
  window.devicePicker.render();
  void 0;
"""


def component_pass(browser):
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    # A real origin, fabricated rather than served: `about:blank` denies
    # localStorage, and per-host persistence is one of the things under test.
    page.route("https://target-picker.test/**", lambda route: route.fulfill(
        status=200, content_type="text/html", body=FIXTURE))
    page.goto("https://target-picker.test/")
    # The real host base layer, in load order: the component has to win against
    # `style.css`'s generic `button` face, which is why it doubles its classes.
    page.emulate_media(color_scheme="dark")
    page.add_style_tag(path=os.path.join(STATIC, "css", "style.css"))
    page.add_style_tag(path=os.path.join(STATIC, "css", "control-panel.css"))
    page.add_style_tag(path=os.path.join(STATIC, "css", "target-picker.css"))
    page.add_script_tag(path=os.path.join(STATIC, "js", "target-picker.js"))
    page.evaluate(SETUP)

    seat = page.locator("#seat-host")
    device = page.locator("#device-host")

    # --- one chrome, two rosters ---
    check("both domains render the same disclosure chrome",
          seat.locator("details.target-picker > summary "
                       ".target-picker-terse").count() == 1
          and device.locator("details.target-picker > summary "
                             ".target-picker-terse").count() == 1)
    check("the seat domain offers All, groups and Seats",
          [text.strip() for text in seat.locator(
              "[data-target-toggle]").all_text_contents()]
          == ["All", "Frontg0", "Backg7", "0", "1", "2"])
    check("the device domain offers devices and no All",
          [text.strip() for text in device.locator(
              "[data-target-toggle]").all_text_contents()]
          == ["Finn Jet", "Ciro Toast", "Offline Oneoffline"]
          and device.locator('[data-target-toggle="all"]').count() == 0)
    check("a group chip carries its portable alias alongside the wire id",
          seat.locator('[data-target-toggle="g7"]')
          .get_attribute("data-target-legacy") == "group:Back")
    check("an ineligible device is present but disabled",
          device.locator('[data-target-toggle="uid-c"]').is_disabled())

    # --- selection: mixable, All exclusive ---
    check("a seat picker starts on All",
          page.evaluate("() => seatPicker.selection()") == ["all"]
          and seat.locator('[data-target-toggle="all"]')
          .get_attribute("aria-pressed") == "true")
    seat.locator('[data-target-toggle="g7"]').click()
    seat.locator('[data-target-toggle="1"]').click()
    check("groups and Seats mix in one selection",
          page.evaluate("() => seatPicker.selection()") == ["g7", "1"])
    check("the closed state names the mixture tersely",
          seat.locator(".target-picker-terse").inner_text().strip() == "Back+1")
    check("All is no longer pressed while a mixture is chosen",
          seat.locator('[data-target-toggle="all"]')
          .get_attribute("aria-pressed") == "false")
    check("the summary row offers one removal per selected entry",
          [text.strip() for text in seat.locator(
              "[data-target-remove]").all_text_contents()] == ["Back ×", "1 ×"])
    seat.locator('[data-target-remove="g7"]').click()
    check("removing an entry leaves the rest",
          page.evaluate("() => seatPicker.selection()") == ["1"])
    seat.locator('[data-target-toggle="all"]').click()
    check("All replaces everything else",
          page.evaluate("() => seatPicker.selection()") == ["all"])
    seat.locator('[data-target-toggle="1"]').click()
    check("choosing a chip from All drops All",
          page.evaluate("() => seatPicker.selection()") == ["1"])
    seat.locator('[data-target-toggle="1"]').click()
    check("deselecting the last entry falls back to All",
          page.evaluate("() => seatPicker.selection()") == ["all"])
    check("every change reached the host",
          page.evaluate("() => changes.length") == 6,
          str(page.evaluate("() => changes")))

    # --- single-select is a different model, not a different component ---
    check("a single-select picker starts on its first eligible chip",
          page.evaluate("() => devicePicker.selection()") == ["uid-a"])
    device.locator('[data-target-toggle="uid-b"]').click()
    check("a single-select choice REPLACES rather than accumulates",
          page.evaluate("() => devicePicker.selection()") == ["uid-b"])
    check("single-select has no summary row: the terse state names the choice",
          device.locator(".target-picker-terse").inner_text().strip()
          == "Ciro Toast"
          and device.locator(".target-picker-summary").count() == 0
          and device.locator("[data-target-remove]").count() == 0)

    # A chosen device that goes offline mid-session must not stay the target —
    # the Assets tab advanced to the next eligible device before the picker, and
    # a disabled chip is not a selectable one.
    page.evaluate("""() => {
      window.deviceRoster[1].disabled = true;
      window.deviceRoster[1].sub = "offline";
      devicePicker.render();
    }""")
    check("a chosen target that becomes ineligible advances to an eligible one",
          page.evaluate("() => devicePicker.selection()") == ["uid-a"])

    # --- per-host persistence, one shared focus seat ---
    check("each host persists its own selection",
          json.loads(page.evaluate(
              "() => localStorage.getItem('test.seat')")) == ["all"]
          and json.loads(page.evaluate(
              "() => localStorage.getItem('test.device')")) == ["uid-a"])
    page.evaluate("() => TargetPicker.focusSeat(2)")
    page.evaluate("() => seatPicker.render()")
    check("the shared focus seat moves a following picker to that Seat",
          page.evaluate("() => seatPicker.selection()") == ["2"])
    check("the focus seat is the one documented shared key",
          page.evaluate("() => TargetPicker.FOCUS_SEAT_KEY")
          == "bopos.selected-seat"
          and page.evaluate("() => TargetPicker.focusedSeat()") == 2)
    page.evaluate("() => devicePicker.render()")
    check("a picker that does not follow focus is unmoved by it",
          page.evaluate("() => devicePicker.selection()") == ["uid-a"])

    # --- surviving the host's re-render ---
    seat.locator('[data-target-toggle="2"]').focus()
    page.evaluate("() => seatPicker.render()")
    check("a re-render keeps keyboard focus on the same chip",
          page.evaluate(
              "() => document.activeElement?.dataset?.targetToggle") == "2")
    page.evaluate("""() => {
      const roster = document.querySelector('#seat-host .target-picker-roster');
      roster.style.maxHeight = '10px';
      roster.scrollTop = 6;
    }""")
    page.evaluate("() => seatPicker.render()")
    check("a re-render keeps a scrolled roster where it was",
          page.evaluate(
              "() => document.querySelector("
              "'#seat-host .target-picker-roster').scrollTop") > 0)

    # --- a selector this venue lost is pruned, not targeted ---
    page.evaluate("""() => {
      window.venue.groups = [{id: 0, name: "Front"}];
      seatPicker.set(["g7", "1"]);
      seatPicker.render();
    }""")
    check("a departed group is pruned from the selection",
          page.evaluate("() => seatPicker.selection()") == ["1"])
    page.evaluate("""() => {
      window.venue.seats = [];
      seatPicker.render();
    }""")
    check("a selection with nothing left falls back to All",
          page.evaluate("() => seatPicker.selection()") == ["all"])

    # --- the appearance rulings that are the component's own ---
    face = page.evaluate("""() => {
      const chip = document.querySelector('#device-host [data-target-toggle]');
      const style = getComputedStyle(chip);
      return {radius: style.borderTopLeftRadius,
              height: Math.round(chip.getBoundingClientRect().height)};
    }""")
    check("a chip is a latching button: near-square, one row high",
          face["radius"] == "1px" and face["height"] == 24, repr(face))
    selected = page.evaluate("""() => {
      const chip = document.querySelector('#seat-host [data-target-toggle="all"]');
      return getComputedStyle(chip).borderTopColor;
    }""")
    accent = page.evaluate(
        "() => getComputedStyle(document.documentElement)"
        ".getPropertyValue('--accent').trim()")
    check("selection chrome is the purple accent, not modulation cyan",
          selected == "rgb(138, 130, 216)" and accent == "#8A82D8",
          repr((selected, accent)))

    check("no page errors", not errors, repr(errors))
    page.close()


# ---------------------------------------------------------------------------
# (b) the device domain on the real Assets tab
# ---------------------------------------------------------------------------

def make_fixture(root):
    patches = os.path.join(root, "patches")
    assets = os.path.join(root, "assets")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(os.path.join(assets, "kit"))
    with open(os.path.join(assets, "kit", "one.wav"), "wb") as target:
        target.write(b"target-picker-verifier")
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"target-picker-verifier")
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin",
            "params": [{"name": "density", "kind": "float", "min": 0, "max": 1,
                        "default": .2, "dashboard": True}],
            "caps": [], "slots": [],
        }, target)

    def seat(seat_id, name, uid):
        return {"id": seat_id, "name": name, "positions": [[seat_id, 1]],
                "groups": [], "bound": uid, "patch": "alpha", "params": {}}

    state = {
        "schema": 1, "name": "Target picker rig",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "groups": {},
        # Seat 1 is bound and Seat 2 is not, so the roster carries one eligible
        # device and one that is only ineligible because it is unassigned.
        "seats": {"1": seat(1, "Freda", UID_A), "2": seat(2, "Sparks", None)},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path


def assets_pass(browser, base_url):
    page = browser.new_page(viewport={"width": 1440, "height": 1200})
    page.set_default_timeout(12000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("dialog", lambda dialog: dialog.accept())
    page.goto(base_url)
    page.wait_for_selector("#ws-status.online")
    page.click("#tab-button-assets")
    page.wait_for_selector("#tab-assets:not([hidden])")

    host = page.locator("#asset-target-host")
    host.locator(".target-picker").wait_for()
    check("the Assets tab's device picker is the shared component",
          host.locator("details.target-picker .target-picker-terse").count() == 1)
    check("the retired device <select> is gone",
          page.locator("#asset-target").count() == 0)
    page.wait_for_function(
        "() => document.querySelectorAll("
        "'#asset-target-host [data-target-toggle]').length === 2")
    chips = page.evaluate("""() => [...document.querySelectorAll(
      '#asset-target-host [data-target-toggle]')].map(chip => ({
        uid: chip.dataset.targetToggle,
        on: chip.getAttribute('aria-pressed') === 'true',
        disabled: chip.disabled,
        text: chip.innerText.trim(),
      }))""")
    eligible = [chip for chip in chips if not chip["disabled"]]
    ineligible = [chip for chip in chips if chip["disabled"]]
    check("every discovered device is a chip", len(chips) == 2, repr(chips))
    check("the assigned device is choosable and chosen",
          len(eligible) == 1 and eligible[0]["uid"] == UID_A
          and eligible[0]["on"], repr(chips))
    check("the unassigned device is a disabled chip wearing its reason",
          len(ineligible) == 1 and "unassigned" in ineligible[0]["text"],
          repr(chips))
    check("the catalog compares against the chosen device",
          "compared with" in page.locator("#asset-catalog-summary").inner_text())
    check("no page errors", not errors, repr(errors))
    page.close()


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-target-picker-") as temp:
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
                component_pass(browser)
                assets_pass(browser, base_url)
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
    print("Target picker checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
