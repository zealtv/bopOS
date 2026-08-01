#!/usr/bin/env python3
"""Real-dashboard browser journey: a late consumer still gets the connect burst
(`51-control-column-first-render-flake`).

The defect: the server sends its snapshot burst the moment the socket opens,
and the page's consumers are spread across separate classic `<script>` tags.
`dashboard.js` opens the socket and registers for `state` first;
`control-host.js`, `monitor.js` and `show.js` are five to seven more network
fetches away, and the event loop is free to deliver socket messages during
those fetches. `ws.js` used to buffer a message only while a type had NO
handlers, so once `dashboard.js` had registered, the burst was delivered to it
alone and the later handlers received nothing — ever.

For the Control tab that meant `venueKnown` never became true and the column
never painted a single card. Nothing recovered it: heartbeats are
`device_update`, and no periodic full-`state` broadcast exists anywhere.

Reproduced deterministically by stalling ONE script's fetch, which is what a
slow connection does on its own. Under full-suite load it showed up as
`verify_show_capture.py` timing out on
`#control-column-host .live-card[data-live-scope="all"]`; standalone it passed,
which is why it read as a flake for as long as it did.

Owned by code surface (dashboard/static/js/ws.js).
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

# Long enough that the burst is certainly delivered before the script runs;
# short enough not to slow the suite.
STALL_SECONDS = 1.5


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
        target.write(b"ws-snapshot-replay")
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin",
            "params": [{"name": "density", "kind": "float", "min": 0,
                        "max": 1, "default": .2, "dashboard": True}],
            "events": [], "caps": [], "slots": [],
        }, target)
    state = {
        "schema": 1, "name": "Snapshot replay rig",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha", "groups": {},
        "seats": {"1": {"id": 1, "name": "Seat 1", "pos": [1, 1]}},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path, patches, assets


def stop_process(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main():
    temp = tempfile.TemporaryDirectory()
    state_path, patches, assets = make_fixture(temp.name)
    http_port = free_port(socket.SOCK_STREAM)
    listen_port = free_port(socket.SOCK_DGRAM)
    send_port = free_port(socket.SOCK_DGRAM)
    log_path = os.path.join(temp.name, "dashboard.log")
    dashboard = None
    try:
        with open(log_path, "w", encoding="utf-8") as log:
            dashboard = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--port", str(http_port), "--listen-port", str(listen_port),
                "--send-port", str(send_port), "--osc-target", "127.0.0.1",
                "--state-file", state_path, "--patches-dir", patches,
                "--assets-dir", assets,
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            base_url = f"http://127.0.0.1:{http_port}"
            wait_http(base_url + "/", dashboard)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440,
                                                  "height": 1200})
                page.set_default_timeout(15000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))

                # Stall ONLY the last consumer's script, so the burst is
                # certainly delivered while `dashboard.js` is the sole
                # registered handler. The route makes the timing deterministic;
                # it does not create the window, network latency does.
                def stall(route):
                    time.sleep(STALL_SECONDS)
                    route.continue_()
                page.route("**/js/control-host.js", stall)

                page.goto(base_url + "#control")
                page.wait_for_selector("#ws-status.online")

                # THE regression. Before the fix this timed out: the handler
                # was registered and simply never called.
                painted = True
                try:
                    page.locator(
                        '#control-column-host .live-card[data-live-scope="all"]'
                    ).wait_for()
                except Exception as error:
                    painted = False
                    detail = str(error).splitlines()[0]
                check("the Control column paints although its script "
                      "loaded after the connect burst",
                      painted, "" if painted else detail)

                # Not merely present — carrying the venue it would have had.
                if painted:
                    check("the late-mounted column renders real parameters",
                          page.locator(
                              "#control-column-host .live-param").count() > 0)

                # The mechanism itself, asked of the socket rather than
                # inferred from the DOM: the burst is retained and nothing was
                # left queued as if it were an unconsumed event.
                observed = page.evaluate("""() => ({
                  retained: Object.keys(ws.latest || {}).sort(),
                  stateHandlers: (ws.handlers?.state || []).length,
                  queuedState: !!ws.pending?.state,
                })""")
                check("every connect-burst type is retained for replay",
                      set(observed["retained"]) >= {
                          "state", "distribution", "venues", "shows",
                          "show", "show_warnings", "show_playback"},
                      repr(observed["retained"]))
                check("more than one consumer registered for state",
                      observed["stateHandlers"] > 1,
                      repr(observed["stateHandlers"]))
                check("a snapshot is not also left on the event queue",
                      not observed["queuedState"])

                # A handler registered long after connect is brought up to
                # date, not replayed a stale first snapshot.
                #
                # The timeout is load-bearing: on the unfixed tree this
                # promise NEVER resolves, and an unbounded wait here hangs the
                # whole run instead of failing it. A regression guard that
                # hangs on the regression is not a guard.
                current = page.evaluate("""() => new Promise(resolve => {
                  const timer = setTimeout(() => resolve("__never__"), 5000);
                  ws.on('state', data => {
                    clearTimeout(timer);
                    resolve(data?.name);
                  });
                })""")
                check("a handler registered later still receives the state",
                      current == "Snapshot replay rig", repr(current))

                check("no page errors", not errors, repr(errors))
                browser.close()
    finally:
        stop_process(dashboard)
        if FAILURES and os.path.exists(log_path):
            with open(log_path, encoding="utf-8") as log:
                print("--- dashboard log ---")
                print(log.read()[-2000:])
        temp.cleanup()

    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed")
        return 1
    print("\nWebSocket snapshot replay checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
