#!/usr/bin/env python3
"""Real-dashboard + simfleet verification that a Control column SCROLLS its
body, and that Remote still grows with the page (55-control-column-targeting/
1-column-scroll).

The defect this guards: `.control-column`'s cards row was
`minmax(0, max-content)` with `align-content: start`, so the track took its
growth limit -- full content height -- however hard `max-height` clamped the
column. The cards element had `overflow-y: auto` throughout and it meant
nothing: its client height WAS its scroll height, so there was nothing to
scroll, and the overflow escaped the column and was clipped silently by
`#control-column-host`'s `overflow-y: hidden`. No scrollbar, no cue, ~698px of
a forty-row manifest permanently unreachable.

So the assertion here is deliberately NOT "the cards element has
`overflow-y: auto`" -- that was true all along and is exactly what made the bug
survive review. It is the measurable consequence: scrollHeight exceeds
clientHeight, scrollTop actually moves, and the last parameter row can be
brought inside the host's box.

Both hosts are pinned, because the fix is a grid-track change and the two hosts
resolve `max-height:100%` differently:

  * the Control tab gives the column a definite height, so it must scroll
    internally and must NOT overflow its host;
  * Remote (/facilitator) mounts one column in a parent with no definite
    height, where the column has always grown with the document and the PAGE
    scrolls. A fix that makes Remote clamp to the viewport is a worse
    regression than the bug, so it is asserted in the same file rather than
    reasoned about.

Owned by code surface (css/control-column.css, control-host.js).
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
  const column = document.querySelector('.control-column');
  const cards = document.querySelector('.control-column-cards');
  if (!host || !column || !cards) return null;
  const rows = cards.querySelectorAll('.live-param');
  return {
    hostHeight: Math.round(host.getBoundingClientRect().height),
    hostBottom: Math.round(host.getBoundingClientRect().bottom),
    columnHeight: Math.round(column.getBoundingClientRect().height),
    cardsClient: cards.clientHeight,
    cardsScroll: cards.scrollHeight,
    scrollTop: Math.round(cards.scrollTop),
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
                page.goto(base_url + "#control")
                page.wait_for_selector("#ws-status.online")
                page.wait_for_selector("#control-column-host .live-param")
                page.wait_for_function(
                    "() => document.querySelectorAll("
                    "'#control-column-host .live-param').length >= %d"
                    % PARAM_COUNT)
                before = page.evaluate(METRICS)
                check("the rig actually overflows the column",
                      before and before["cardsScroll"] > before["hostHeight"],
                      json.dumps(before))

                # The defect, stated as its consequence. Pre-fix this reports
                # equal values (1408 === 1408) and the guard fails.
                check("the cards body is a real scrollport "
                      "(scrollHeight > clientHeight)",
                      before["cardsScroll"] > before["cardsClient"],
                      "client {} === scroll {}".format(
                          before["cardsClient"], before["cardsScroll"]))

                check("the column does not overflow its host",
                      before["columnHeight"] <= before["hostHeight"] + 1,
                      "column {} > host {}".format(
                          before["columnHeight"], before["hostHeight"]))

                # Scrolling has to MOVE it, not merely be permitted.
                page.evaluate(
                    "() => { const cards = document.querySelector("
                    "'.control-column-cards');"
                    " cards.scrollTop = cards.scrollHeight; }")
                page.wait_for_timeout(120)
                after = page.evaluate(METRICS)
                check("scrolling the body moves it",
                      after["scrollTop"] > 0,
                      "scrollTop stayed at {}".format(after["scrollTop"]))
                check("the last parameter row is reachable inside the host",
                      after["lastRowBottom"] is not None
                      and after["lastRowBottom"] <= after["hostBottom"] + 2,
                      "last row bottom {} vs host bottom {}".format(
                          after["lastRowBottom"], after["hostBottom"]))

                # ---------------- Remote ----------------
                # MEASURED, not inherited from the comment. `control-column.css`
                # claims Remote "keeps growing with the page as it always did";
                # it does not, and never did. `facilitator.css:25` makes
                # `#control-column-host` itself a flex scrollport
                # (`flex:1; min-height:0; overflow-y:auto`) inside a
                # `height:100%` body, so the column clamps and its body already
                # scrolls correctly here. This half is therefore a REGRESSION
                # guard on behaviour that works today -- the risk of the grid
                # fix is that it breaks Remote, not that Remote is broken.
                page.goto(base_url + "/facilitator")
                page.wait_for_selector("#ws-status", state="attached")
                page.wait_for_selector(".live-param")
                page.wait_for_function(
                    "() => document.querySelectorAll('.live-param').length"
                    " >= %d" % PARAM_COUNT)
                remote = page.evaluate("""() => {
                  const cards =
                    document.querySelector('.control-column-cards');
                  const column = document.querySelector('.control-column');
                  return {
                    cardsClient: cards.clientHeight,
                    cardsScroll: cards.scrollHeight,
                    columnHeight:
                      Math.round(column.getBoundingClientRect().height),
                    docScroll: document.documentElement.scrollHeight,
                    viewport: window.innerHeight,
                  };
                }""")
                check("Remote's column body is a real scrollport",
                      remote["cardsScroll"] > remote["cardsClient"],
                      json.dumps(remote))
                check("Remote's column stays within the viewport",
                      remote["columnHeight"] <= remote["viewport"],
                      json.dumps(remote))
                page.evaluate(
                    "() => { const cards = document.querySelector("
                    "'.control-column-cards');"
                    " cards.scrollTop = cards.scrollHeight; }")
                page.wait_for_timeout(120)
                check("Remote scrolls its body, not the document",
                      page.evaluate(
                          "() => document.querySelector("
                          "'.control-column-cards').scrollTop > 0"))

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
