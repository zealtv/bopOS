#!/usr/bin/env python3
"""Verify the global controls live in the Monitor dock.

Master fader, event lead time, and MUTE ALL share one Globals panel in the
Monitor dock. They are gone from the app header, the Control tab, and the
Show transport. A muted fleet stays visible while the dock is collapsed.
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
ROOT = os.path.realpath(os.path.dirname(__file__))
while not os.path.isfile(os.path.join(ROOT, "tools", "simfleet.py")):
    parent = os.path.dirname(ROOT)
    if parent == ROOT:
        raise SystemExit("cannot locate bopOS repository")
    ROOT = parent

FAILURES = []
RESERVED = set()
UID = "02:53:49:4d:00:01"


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


PARAMS = [{"name": "gain", "kind": "float", "min": 0, "max": 1,
           "default": .5, "dashboard": True}]


def write_fixture(temp):
    patches = os.path.join(temp, "patches")
    assets = os.path.join(temp, "assets")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(assets)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"global-controls")
    manifest = os.path.join(patch, "bopos.patch.json")
    with open(manifest, "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin",
                   "params": PARAMS, "caps": [], "slots": []}, target)
    shows = os.path.join(temp, "shows")
    os.makedirs(shows)
    with open(os.path.join(shows, "Journey.json"), "w", encoding="utf-8") as target:
        json.dump({"name": "Journey", "items": [
            {"kind": "step", "uid": "aaaa1111", "alias": "One",
             "duration_s": 5, "messages": [], "then_actions": []}]}, target)
    state_path = os.path.join(temp, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump({
            "schema": 1, "name": "Global controls rig",
            "master": 1.0, "event_lead_ms": 500, "current_show": "Journey",
            "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                            "staged_at": time.time(), "previous": None},
            "params_patch": "alpha",
            "seats": {"1": {"id": 1, "name": "Finn", "positions": [[1, 1]],
                            "bound": UID, "params": {"gain": .5}}},
        }, target)
    return state_path, patches, assets, manifest


def open_globals(page):
    """The Globals tab is reachable from the collapsed dock header."""
    page.click('[data-monitor-tab="globals"]')
    page.wait_for_selector("#monitor-panel-globals #mute-all", state="visible")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-global-controls-") as temp:
        state_path, patches, assets, manifest = write_fixture(temp)
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
                sys.executable, os.path.join(ROOT, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port),
                "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", assets, "--patches-dir", patches,
                "--public-url", base_url,
            ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(ROOT, "tools", "simfleet.py"),
                "--devices", "1", "--target", "127.0.0.1",
                "--report-port", str(listen_port),
                "--cmd-port", str(send_port), "--hb-interval", "0.3",
                "--boot-secs", "0.2", "--manifest", manifest,
                "--patches-dir", patches, "--assets-dir", assets,
                "--sim-no-engine", "--sim-audio-backend", "none",
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440,
                                                  "height": 1100})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_selector("#monitor-dock")

                # --- the three controls are gone from their old homes
                check("MUTE ALL has left the app header",
                      page.locator("header #mute-all").count() == 0)
                check("the master fader has left the app header",
                      page.locator("header #master-control").count() == 0)
                check("the master fader has left the Control tab",
                      page.locator("#tab-control #master-control").count() == 0)
                page.click("#tab-button-show")
                page.wait_for_selector(".show-transport-strip")
                check("the Show transport no longer carries event lead",
                      page.locator(".show-transport-strip "
                                   "input[type=number]").count() == 0)
                check("no stray event-lead control survives the relocation",
                      page.locator("#show-event-lead").count() == 0)

                # --- they are all in one Monitor panel
                located = page.evaluate("""() => {
                  const panel = document.getElementById('monitor-panel-globals');
                  const owns = id => !!panel?.querySelector('#' + id);
                  return {master: owns('master'), lead: owns('event-lead-ms'),
                          mute: owns('mute-all')};
                }""")
                check("master, event lead, and MUTE ALL share the Globals panel",
                      located == {"master": True, "lead": True, "mute": True},
                      repr(located))
                check("event lead sits with the master fader",
                      page.locator("#monitor-panel-globals "
                                   ".monitor-globals-audio #master").count() == 1
                      and page.locator("#monitor-panel-globals "
                                       ".monitor-globals-audio "
                                       "#event-lead-ms").count() == 1)
                check("MUTE ALL keeps its danger affordance",
                      "danger" in (page.locator("#mute-all")
                                   .get_attribute("class") or ""))

                open_globals(page)
                check("the Globals panel is reachable from the collapsed dock",
                      page.locator("#monitor-panel-globals").is_visible())

                # --- and they still work
                page.locator("#master").evaluate(
                    "(element) => { element.value = '0.4';"
                    " element.dispatchEvent(new Event('change', {bubbles:true})); }")
                page.wait_for_function("() => Math.abs(master - .4) < 1e-6")
                readout = page.locator("#master-out").evaluate(
                    "element => element.value")
                check("the relocated master fader still sets master",
                      readout == "40%", repr(readout))

                page.locator("#event-lead-ms").fill("250")
                page.locator("#event-lead-ms").dispatch_event("change")
                page.wait_for_function(
                    "() => installation.event_lead_ms === 250")
                check("the relocated event lead still sets the lead time", True)

                page.locator("#mute-all").click()
                page.wait_for_function("() => installation.muted === true")
                check("the relocated MUTE ALL still mutes",
                      page.locator("#mute-all").inner_text() == "MUTED — UNMUTE",
                      page.locator("#mute-all").inner_text())

                # --- a muted fleet is never invisible
                page.click("[data-monitor-collapse]")
                page.wait_for_selector("#monitor-dock.is-collapsed")
                check("the collapsed dock hides the Globals panel",
                      not page.locator("#monitor-panel-globals").is_visible())
                check("a muted fleet stays visible on the collapsed dock",
                      page.locator("[data-monitor-mute-flag]").is_visible())
                page.click("[data-monitor-mute-flag]")
                page.wait_for_function("() => installation.muted === false")
                check("the collapsed mute flag unmutes and then disappears",
                      not page.locator("[data-monitor-mute-flag]").is_visible())

                # --- Monitor persistence covers the new panel
                open_globals(page)
                page.reload()
                page.wait_for_selector("#ws-status.online")
                page.wait_for_selector("#monitor-panel-globals #mute-all")
                check("the Globals selection survives a reload",
                      page.locator('[data-monitor-tab="globals"]')
                      .get_attribute("aria-selected") == "true")

                check("no page errors during the journey", not errors,
                      repr(errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed:")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("all global-control checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
