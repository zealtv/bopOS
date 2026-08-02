#!/usr/bin/env python3
"""Real-dashboard verification of the downward, page-scrolling cards grid.

This deliberately supersedes `1-column-scroll`: neither host may clamp a card
or make `.control-column-cards` a nested scrollport. Four cards share flexible
tracks on desktop; both Control and Remote grow the document downward, and the
last manifest row is reached by scrolling the page.
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

# Forced from the MANIFEST rather than from the number of targets, so this
# stays an honest reproduction if `2-multi-target-model` collapses a
# multi-target selection into a single aggregate panel.
PARAM_COUNT = 40


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
            continue
        finally:
            probe.close()
        RESERVED.add((kind, port))
        return port
    raise RuntimeError("no free port")


def wait_http(base_url, process):
    for _attempt in range(200):
        if process.poll() is not None:
            raise RuntimeError("dashboard exited early")
        try:
            urllib.request.urlopen(base_url, timeout=.5).read()
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
        target.write(b"control-column-scroll-verifier")
    params = [{"name": f"p{index:02d}", "kind": "float", "min": 0, "max": 1,
               "default": .2, "dashboard": True}
              for index in range(PARAM_COUNT)]
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin",
            "params": params, "events": [], "caps": [], "slots": [],
        }, target)

    values = {declaration["name"]: .2 for declaration in params}

    def seat(seat_id, name, uid, groups):
        return {"id": seat_id, "name": name, "positions": [[seat_id, 1]],
                "groups": groups, "bound": uid, "patch": "alpha",
                "params": dict(values)}

    state = {
        "schema": 1, "name": "Column scroll rig",
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


METRICS = """() => {
  const host = document.querySelector('#control-column-host');
  const columns = [...document.querySelectorAll('.control-column')];
  const cards = document.querySelector('.control-column-cards');
  if (!host || !columns.length || !cards) return null;
  const widths = columns.map(column =>
    Math.round(column.getBoundingClientRect().width));
  const rows = document.querySelectorAll('.live-param');
  return {
    display: getComputedStyle(host).display,
    hostOverflowY: getComputedStyle(host).overflowY,
    cardsOverflowY: getComputedStyle(cards).overflowY,
    widths,
    docScroll: document.documentElement.scrollHeight,
    viewport: window.innerHeight,
    pageY: Math.round(window.scrollY),
    rows: rows.length,
    lastRowBottom: rows.length
      ? Math.round(rows[rows.length - 1].getBoundingClientRect().bottom)
      : null,
  };
}"""


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-column-scroll-") as temp:
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
                                                  "height": 900})
                page.set_default_timeout(12000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())

                # ---------------- the Control tab ----------------
                page.add_init_script("""() => localStorage.setItem(
                  'bopos.control.cards', JSON.stringify({
                    version:1, targets:['2','g0','all','1']
                  }))""")
                page.goto(base_url + "#control")
                page.wait_for_selector("#ws-status.online")
                page.wait_for_selector("#control-column-host .live-param")
                page.wait_for_function(
                    "() => document.querySelectorAll("
                    "'#control-column-host .live-param').length >= %d"
                    % (PARAM_COUNT * 4))
                before = page.evaluate(METRICS)
                check("Control lays four cards into a wrapping flex row",
                      before and before["display"] == "flex"
                      and len(before["widths"]) == 4,
                      json.dumps(before))
                check("Control cards flex within the requested bounds",
                      max(before["widths"]) - min(before["widths"]) <= 1
                      and min(before["widths"]) >= 340
                      and max(before["widths"]) <= 560,
                      json.dumps(before["widths"]))
                page.set_viewport_size({"width": 1200, "height": 900})
                sparse = page.evaluate("""() => {
                  const cards=[...document.querySelectorAll(
                    '#control-column-host>.control-column')];
                  return cards.map(card => ({
                    left:Math.round(card.getBoundingClientRect().left),
                    top:Math.round(card.getBoundingClientRect().top),
                    width:Math.round(card.getBoundingClientRect().width),
                  }));
                }""")
                check("a sparse final Control row stays left packed",
                      len(sparse) == 4
                      and sparse[3]["top"] > sparse[0]["top"]
                      and abs(sparse[3]["left"] - sparse[0]["left"]) <= 1
                      and 340 <= sparse[3]["width"] <= 560,
                      json.dumps(sparse))
                page.set_viewport_size({"width": 1440, "height": 900})
                check("Control cards and host expose no nested scrollport",
                      before["cardsOverflowY"] == "visible"
                      and before["hostOverflowY"] == "visible",
                      json.dumps(before))
                check("the long cards grow the document below the viewport",
                      before["docScroll"] > before["viewport"],
                      json.dumps(before))
                page.evaluate(
                    "() => window.scrollTo(0, document.documentElement.scrollHeight)")
                page.wait_for_timeout(120)
                after = page.evaluate(METRICS)
                check("Control scrolls the page",
                      after["pageY"] > 0,
                      "pageY stayed at {}".format(after["pageY"]))
                check("the final Control row is reachable in the viewport",
                      after["lastRowBottom"] is not None
                      and after["lastRowBottom"] <= after["viewport"] + 2,
                      json.dumps(after))

                # ---------------- Remote ----------------
                page.goto(base_url + "/facilitator")
                page.wait_for_selector("#ws-status", state="attached")
                page.wait_for_selector(".live-param")
                page.wait_for_function(
                    "() => document.querySelectorAll('.live-param').length"
                    " >= %d" % (PARAM_COUNT * 4))
                remote = page.evaluate("""() => {
                  const host=document.querySelector('#control-column-host');
                  const cards=document.querySelector('.control-column-cards');
                  const targets=[...document.querySelectorAll('.live-card')];
                  const rows=document.querySelectorAll('.live-param');
                  return {
                    display:getComputedStyle(host).display,
                    cardsDisplay:getComputedStyle(cards).display,
                    hostOverflowY:getComputedStyle(host).overflowY,
                    cardsOverflowY:getComputedStyle(cards).overflowY,
                    widths:targets.map(card=>Math.round(
                      card.getBoundingClientRect().width)),
                    docScroll: document.documentElement.scrollHeight,
                    viewport: window.innerHeight,
                    lastRowBottom:Math.round(
                      rows[rows.length-1].getBoundingClientRect().bottom),
                  };
                }""")
                check("Remote derives four flexible cards",
                      remote["display"] == "flex"
                      and remote["cardsDisplay"] == "flex"
                      and len(remote["widths"]) == 4
                      and max(remote["widths"]) - min(remote["widths"]) <= 1
                      and max(remote["widths"]) <= 560,
                      json.dumps(remote))
                check("Remote also has no nested vertical scrollport",
                      remote["hostOverflowY"] == "visible"
                      and remote["cardsOverflowY"] == "visible",
                      json.dumps(remote))
                check("Remote grows the document below the viewport",
                      remote["docScroll"] > remote["viewport"],
                      json.dumps(remote))
                page.evaluate(
                    "() => window.scrollTo(0, document.documentElement.scrollHeight)")
                page.wait_for_timeout(120)
                check("Remote reaches its final row through page scroll",
                      page.evaluate(
                          "() => window.scrollY > 0 && [...document.querySelectorAll("
                          "'.live-param')].at(-1).getBoundingClientRect().bottom"
                          " <= window.innerHeight + 2"))

                check("no page errors", not errors, "; ".join(errors[:3]))
                browser.close()
        finally:
            for process in (fleet, server):
                if process and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
            server_log.close()
            fleet_log.close()

    print()
    if FAILURES:
        print("FAILED: " + ", ".join(FAILURES))
        return 1
    print("all control-column scroll checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
