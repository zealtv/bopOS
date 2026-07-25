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
      renderer inside the component.

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
            {"name": "gate", "type": "i", "min": 0, "max": 1,
             "default": 0, "dashboard": True},
            {"name": "density", "type": "f", "min": 0, "max": 1,
             "default": .2, "dashboard": True},
            # A nested path exercises the branch renderer.
            {"name": "cutoff", "type": "f", "min": 0, "max": 1,
             "default": .5, "path": ["filter"], "dashboard": True},
            # A string declaration must omit `default` -- the validator only
            # allows numeric min/max/default (CLAUDE.md testing gotcha 7).
            {"name": "label", "type": "s", "dashboard": True},
        ], "cues": [], "caps": [], "slots": [],
    }
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump(manifest, target, indent=2)

    def seat(seat_id, name, uid):
        # Identical values keep the All aggregate non-mixed, so the aggregate
        # and seat renders are comparable.
        return {"id": seat_id, "name": name, "positions": [[seat_id, 1]],
                "groups": [0], "bound": uid, "patch": "alpha",
                "params": {"gate": 0, "density": .2, "filter/cutoff": .5,
                           "label": "hello"}}

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
  const declarations = installation.live_controls.declarations
    .map(d => ({...d, path: d.path || []}));
  const device = {online: true, engine_alive: 1, device_enabled: true,
                  output_enabled: true, uid: seat.bound};
  const probe = window.ControlSurface.create({
    getState: () => installation,
    deviceForSeat: () => device,
    deviceForScope: () => device,
    send: payload => (window.__probeSent = window.__probeSent || []).push(payload),
  });
  const normalize = html => html
    .replace(/data-live-scope="[^"]*"/g, 'data-live-scope="X"')
    .replace(/data-live-id="[^"]*"/g, 'data-live-id="X"');
  const seatHtml = probe.tree("seat", seat.id, [seat], declarations, false);
  const deviceHtml = probe.tree("device", seat.bound, [seat], declarations, false);
  const host = document.createElement("div");
  host.id = "surface-probe";
  host.innerHTML = deviceHtml;
  document.body.appendChild(host);
  probe.bind(host);
  return {
    identical: normalize(seatHtml) === normalize(deviceHtml),
    seatHtml: normalize(seatHtml).slice(0, 400),
    deviceHtml: normalize(deviceHtml).slice(0, 400),
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
                for scope in ("all", "group"):
                    check(
                        f"{scope} card renders rows through the component",
                        page.locator(
                            f'.live-card[data-live-scope="{scope}"] '
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
                check("string and boolean declarations render their own kinds",
                      page.locator(
                          '.live-card[data-live-scope="all"] '
                          'input[type="text"][data-param-path="label"]'
                      ).count() == 1
                      and page.locator(
                          '.live-card[data-live-scope="all"] '
                          'input[type="checkbox"][data-param-path="gate"]'
                      ).count() == 1)

                page.click('[data-live-scope-view="seats"]')
                page.wait_for_selector('.live-card[data-live-scope="seat"]')
                check("seat cards render rows through the component",
                      page.locator(
                          '.live-card[data-live-scope="seat"] '
                          '[data-live-param][data-param-path="density"]'
                      ).count() == 2)

                # --- (c) device scope is the same render as seat scope ---
                parity = page.evaluate(PARITY_JS)
                check("device-scoped render is markup-identical to seat scope",
                      parity["identical"],
                      f"seat={parity['seatHtml']!r} "
                      f"device={parity['deviceHtml']!r}")

                # --- (d) the send is the host's, carrying scope + uid ---
                page.click(
                    '#surface-probe input[type="checkbox"]'
                    '[data-param-path="gate"]')
                sent = page.evaluate("() => window.__probeSent || []")
                check("device-scoped row calls the host send with scope+uid",
                      len(sent) == 1
                      and sent[0].get("scope") == "device"
                      and sent[0].get("id") == UIDS[0]
                      and sent[0].get("name") == "gate"
                      and sent[0].get("value") == 1,
                      repr(sent))

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
