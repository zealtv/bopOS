#!/usr/bin/env python3
"""Real-dashboard + simfleet verification for the Device-tab live-control panel
(thread 37, stitch 09).

Bob's rulings, each one a check:

  * device-tab order is patch diagnostics -> device ACTIONS -> device CONTROL
    (the actions move up; the control panel sits below them);
  * the panel is COLLAPSED by default and remembers the operator's choice;
  * an OFFLINE device shows its last known values, DISABLED -- never hidden;
  * one code path: a device write goes through the shared component and reaches
    only that device.

Plus the thing the placement design left for implementation: a PINNED device
runs a patch other than the fleet's, so its panel must render that patch's
promoted params, not the fleet's.

Owned by code surface (dashboard.js device detail + server live_* helpers).
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
UID_A = "02:53:49:4d:00:01"
UID_B = "02:53:49:4d:00:02"
UID_C = "02:53:49:4d:00:03"


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


def wait_log(path, pattern, timeout=8):
    deadline = time.monotonic() + timeout
    rx = re.compile(pattern)
    while time.monotonic() < deadline:
        try:
            with open(path, encoding="utf-8") as source:
                if rx.search(source.read()):
                    return True
        except OSError:
            pass
        time.sleep(.1)
    return False


def write_patch(patches, name, params):
    path = os.path.join(patches, name)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "main.bin"), "wb") as target:
        target.write(name.encode())
    with open(os.path.join(path, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin",
                   "params": params, "caps": [], "slots": []},
                  target)


# `alpha` is the fleet patch; `beta` is what one device gets pinned to, and it
# deliberately promotes a differently-named param so "whose schema is this?" has
# an unambiguous answer.
ALPHA_PARAMS = [
    {"name": "density", "kind": "float", "min": 0, "max": 1, "default": .2,
     "dashboard": True},
]
BETA_PARAMS = [
    {"name": "shimmer", "kind": "float", "min": 0, "max": 1, "default": .4,
     "dashboard": True},
]

PANEL = "#device-control"
BODY = "#device-control-body"
TOGGLE = "#device-control-toggle"


def select_device(page, uid):
    page.click(f'#device-roster .device-row[data-uid="{uid}"]')
    page.wait_for_selector(PANEL)


def section_order(page):
    return page.evaluate(
        "() => [...document.querySelectorAll('#detail > section')]"
        ".map(s => s.id || s.querySelector('h2')?.textContent || '')")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-device-control-") as temp:
        state_path = os.path.join(temp, "installation.json")
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        os.makedirs(assets)
        os.makedirs(patches)
        write_patch(patches, "alpha", ALPHA_PARAMS)
        write_patch(patches, "beta", BETA_PARAMS)
        state = {
            "schema": 1, "name": "Device control rig",
            "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                            "staged_at": time.time(), "previous": None},
            "params_patch": "alpha",
            "seats": {
                "1": {"id": 1, "name": "Finn", "positions": [[1, 1]],
                      "params": {"density": .2}, "bound": UID_A},
                "2": {"id": 2, "name": "Ciro", "positions": [[2, 1]],
                      "params": {"density": .2}, "bound": UID_B},
            },
            "device_registry": {
                UID_C: {"alias": "Imani Silver", "source": "custom",
                        "generator": 2, "device_enabled": True},
            },
        }
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump(state, target)

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
                "--devices", "3", "--unassigned", "1",
                "--target", "127.0.0.1",
                "--report-port", str(listen_port),
                "--cmd-port", str(send_port),
                "--hb-interval", "0.3", "--boot-secs", "0.2",
                "--fetch-seconds", "0.3", "--patches-dir", patches,
                "--manifest", os.path.join(patches, "alpha",
                                           "bopos.patch.json"),
                "--assets-dir", assets,
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440,
                                                  "height": 1200})
                page.set_default_timeout(12000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "() => Object.keys(installation.devices||{}).length === 3")

                page.click("#tab-button-devices")
                page.wait_for_selector("#tab-devices:not([hidden])")
                # Seat rows carry data-uid too, so scope to the roster
                # (CLAUDE.md testing gotcha 12).
                select_device(page, UID_A)

                # --- panel order: diagnostics -> actions -> control ---
                order = section_order(page)
                ids = [item.strip().lower() for item in order]
                try:
                    diagnostics = ids.index("patch-diagnostics")
                    actions = ids.index("actions")
                    control = ids.index("device-control")
                except ValueError:
                    diagnostics = actions = control = -1
                check("device tab orders diagnostics, then actions, "
                      "then device control",
                      -1 not in (diagnostics, actions, control)
                      and diagnostics < actions < control, repr(order))

                # --- collapsed by default, and remembered ---
                check("device control is collapsed by default",
                      page.locator(BODY).get_attribute("hidden") is not None)
                page.click(TOGGLE)
                page.wait_for_selector(BODY + ":not([hidden])")
                check("the toggle opens the panel",
                      page.locator(BODY + " .live-param").count() >= 1)
                page.reload()
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-devices")
                select_device(page, UID_A)
                check("the open choice is remembered across a reload",
                      page.locator(BODY).get_attribute("hidden") is None)

                # --- fresh unbound device: full detail, safe default values ---
                # Recreate Imani's first-session record at the moment of the
                # click. The snapshot is taken synchronously with rendering so
                # the simulator's report replies cannot race the null-state
                # assertions.
                unbound = page.evaluate(
                    """uid => {
                      const device = installation.devices[uid];
                      Object.assign(device, {
                        id: -1, report: null, patches: null, assets: null,
                        declared: null,
                      });
                      document.querySelector(
                        `#device-roster .device-row[data-uid="${uid}"]`
                      ).click();
                      const detail = document.querySelector("#detail");
                      const controls = [...detail.querySelectorAll(
                        "#device-control [data-live-param]")];
                      const density = detail.querySelector(
                        '#device-control input[type="range"]'
                        + '[data-param-path="density"]');
                      return {
                        selected: document.querySelector(
                          `#device-roster .device-row[data-uid="${uid}"]`
                        ).classList.contains("selected"),
                        text: detail.innerText,
                        controls: controls.length,
                        allDisabled: controls.every(node => node.disabled),
                        densityValue: density?.value,
                        densityReadout: density?.closest(".live-param")
                          ?.querySelector("output")?.textContent,
                        assignment: !!detail.querySelector("#device-binding"),
                        diagnostics: !!detail.querySelector(
                          "#patch-diagnostics"),
                        actions: detail.querySelectorAll(
                          "[data-action], [data-identify]").length,
                        enabled: !!detail.querySelector(
                          "#device-enabled-toggle"),
                        audio: !!detail.querySelector("#device-audio"),
                        logging: !!detail.querySelector("#device-log"),
                        assets: !!detail.querySelector(
                          ".device-assets-summary"),
                        report: !!detail.querySelector("#refresh-report"),
                      };
                    }""", UID_C)
                check("fresh unbound roster selection opens Imani detail",
                      unbound["selected"]
                      and "Imani Silver" in unbound["text"]
                      and UID_C in unbound["text"]
                      and "unbound" in unbound["text"].lower(),
                      repr(unbound))
                check("fresh unbound detail exposes administration surfaces",
                      unbound["assignment"] and unbound["diagnostics"]
                      and unbound["actions"] == 5 and unbound["enabled"]
                      and unbound["audio"] and unbound["logging"]
                      and unbound["assets"] and unbound["report"],
                      repr(unbound))
                check("unbound controls show patch defaults and provenance",
                      unbound["controls"] >= 1 and unbound["allDisabled"]
                      and unbound["densityValue"] == "0.2"
                      and unbound["densityReadout"] == "0.2"
                      and "showing patch defaults" in unbound["text"].lower(),
                      repr(unbound))

                page.evaluate(
                    """() => {
                      window.__unboundControlMessages = [];
                      const original = ws.send.bind(ws);
                      ws.send = (kind, data) => {
                        if (kind === "set_live_param"
                            || kind === "set_live_automation") {
                          window.__unboundControlMessages.push({kind, data});
                        }
                        return original(kind, data);
                      };
                      document.querySelector(
                        '#device-control input[data-live-param]'
                      )?.click();
                      document.querySelector(
                        '#device-control [data-gen-toggle]'
                      )?.click();
                    }""")
                check("unbound disabled controls emit no content messages",
                      page.evaluate(
                          "() => window.__unboundControlMessages.length") == 0)

                # --- one code path: a device write reaches only that device ---
                select_device(page, UID_A)
                slider = (BODY + ' input[type="range"][data-live-param]'
                          '[data-param-path="density"]')
                check("the panel renders the shared component's rows",
                      page.locator(slider).count() == 1
                      and page.get_attribute(slider, "data-live-scope")
                      == "device")
                # The provisional preset slot (01-control-panel/7) is part of
                # the shared panel, so the Device tab gets the same designed
                # home for `41-preset-primitive` that the Control tab has.
                preset = page.evaluate(
                    """sel => {
                      const body = document.querySelector(sel);
                      const row = body.querySelector("[data-preset-slot]");
                      if (!row) return {present: false};
                      const rows = body.querySelector(".promoted-controls");
                      return {
                        present: true,
                        patch: row.querySelector(".live-preset-patch")
                          .textContent.trim(),
                        aboveRows: !!(row.compareDocumentPosition(rows)
                          & Node.DOCUMENT_POSITION_FOLLOWING),
                        live: [...row.querySelectorAll("select,button")]
                          .filter(control => !control.disabled).length,
                      };
                    }""", BODY)
                check("the device panel carries the same preset slot",
                      preset["present"] and preset.get("patch") == "alpha"
                      and preset.get("aboveRows")
                      and preset.get("live") == 0, repr(preset))

                page.eval_on_selector(
                    slider,
                    "node => { node.value = '0.63';"
                    " node.dispatchEvent(new Event('change', "
                    "{bubbles: true})); }")
                check("a device-scoped write reaches the wire",
                      wait_log(fleet_log_path, r"p/density=0\.63"),
                      "fleet log missing the device write")
                only_one = page.wait_for_function(
                    "() => installation.seats['1'].params.density === 0.63"
                    " && installation.seats['2'].params.density !== 0.63",
                    timeout=8000)
                check("the write lands on that device's seat only",
                      only_one is not None)

                # --- a pinned device renders ITS patch's params ---
                page.click("#tab-button-patches")
                page.wait_for_selector(
                    "#tab-patches:not([hidden]) #fleet-patch-panel")
                page.wait_for_function(
                    "() => [...document.querySelectorAll"
                    "('#patch-select option')]"
                    ".some(option => option.value === 'beta')")
                page.select_option("#patch-target", UID_B)
                page.select_option("#patch-select", "beta")
                page.click("#patch-switch")
                page.wait_for_function(
                    "uid => installation.devices[uid]?.pinned_patch === 'beta'",
                    arg=UID_B, timeout=20000)
                page.wait_for_function(
                    "uid => installation.devices[uid]?.live_controls?.patch"
                    " === 'beta'", arg=UID_B, timeout=10000)

                page.click("#tab-button-devices")
                select_device(page, UID_B)
                check("a pinned device renders its own patch's params",
                      page.locator(
                          BODY + ' [data-live-param]'
                          '[data-param-path="shimmer"]').count() >= 1
                      and page.locator(
                          BODY + ' [data-live-param]'
                          '[data-param-path="density"]').count() == 0)
                check("the panel names the patch it is showing",
                      "beta" in page.locator(PANEL).inner_text().lower()
                      and "pinned" in page.locator(PANEL).inner_text().lower())

                # --- offline: last values, disabled, never hidden ---
                stop_process(fleet)
                fleet = None
                # The offline sweep marks a device down 30 s after its last
                # heartbeat, so this wait has to outlast that.
                page.wait_for_function(
                    "uid => installation.devices[uid]?.online === false",
                    arg=UID_B, timeout=45000)
                select_device(page, UID_B)
                check("an offline device still shows its control panel",
                      page.locator(PANEL).count() == 1
                      and page.locator(BODY).get_attribute("hidden") is None)
                check("offline controls are disabled, not hidden",
                      page.locator(BODY + " [data-live-param]").count() >= 1
                      and page.eval_on_selector_all(
                          BODY + " [data-live-param]",
                          "nodes => nodes.every(n => n.disabled)"))

                check("no page errors", not errors, repr(errors))
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
    print("Device control panel checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
