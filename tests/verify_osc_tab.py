#!/usr/bin/env python3
"""The OSC reference tab on a real dashboard with private ports.

Generated from the fleet patch, regenerated from the edited patch in Patch
Edit, and live: real UDP to the input port shows a rejection and a clamp
without a reload.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright
from pythonosc.udp_client import SimpleUDPClient

sys.dont_write_bytecode = True
from project_fixture import data_root, project_path
from verify_manifest_param_visibility import FAILURES, ROOT, check, free_port, stop, wait_http


def write_patch(temp, name, params, events):
    folder = os.path.join(temp, "patches", name)
    os.makedirs(folder)
    with open(os.path.join(folder, "main.bin"), "wb") as target:
        target.write(b"osc-tab")
    with open(os.path.join(folder, "bopos.patch.json"), "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "caps": [], "slots": [],
                   "params": params, "events": events}, target)


def write_fixture(temp):
    os.makedirs(os.path.join(temp, "assets"))
    write_patch(
        temp, "choir",
        [{"name": "gain", "kind": "float", "min": 0, "max": 1, "default": .5},
         {"name": "colour", "kind": "enum", "options": ["warm", "cool", "bright"], "default": 0}],
        [{"name": "play", "path": ["trig"], "fields": [
            {"name": "clip", "kind": "int", "min": 0, "max": 15},
            {"name": "speed", "kind": "int", "min": 1, "max": 4, "default": 1, "optional": True}]},
         {"name": "gain", "fields": [{"name": "amount", "kind": "float", "min": 0, "max": 1}]}])
    write_patch(temp, "solo", [{"name": "tone", "kind": "float", "min": 0, "max": 1}],
                [{"name": "ping", "fields": []}])
    state = str(project_path(temp))
    with open(state, "w", encoding="utf-8") as target:
        json.dump({"schema": 1, "name": "OSC tab rig", "patches": ["solo"],
                   "fleet_patch": {"name": "choir", "fingerprint": "a" * 64, "staged_at": time.time()},
                   "groups": {"0": {"id": 0, "name": "spot1"}, "1": {"id": 1, "name": "choir-left"}},
                   "next_group_id": 2,
                   "seats": {"1": {"id": 1, "name": "Finn", "positions": [[1, 1]], "groups": [0], "params": {}}}},
                  target)
    return state


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-osc-tab-") as temp:
        state = write_fixture(temp)
        http_port = free_port(socket.SOCK_STREAM)
        input_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log = open(os.path.join(temp, "server.log"), "w", encoding="utf-8")
        server = subprocess.Popen([
            sys.executable, os.path.join(ROOT, "dashboard", "server.py"),
            "--host", "127.0.0.1", "--port", str(http_port),
            "--listen-port", str(free_port(socket.SOCK_DGRAM)),
            "--stream-port", str(free_port(socket.SOCK_DGRAM)),
            "--send-port", str(free_port(socket.SOCK_DGRAM)),
            "--input-port", str(input_port), "--osc-target", "127.0.0.1",
            "--data-dir", data_root(state), "--assets-dir", os.path.join(temp, "assets"),
            "--patches-dir", os.path.join(temp, "patches"),
            "--public-url", "http://192.168.4.20:8080", "--sim-no-engine",
        ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
        try:
            wait_http(base_url, server)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1400})
                page.set_default_timeout(10000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-osc")
                page.wait_for_selector("#osc-events .osc-row")

                def text(selector):
                    return page.locator(selector).inner_text()

                # ---- fleet patch ------------------------------------------
                check("the endpoint shows the configured host and the input port",
                      "192.168.4.20" in text("#osc-endpoint") and str(input_port) in text("#osc-endpoint"),
                      text("#osc-endpoint"))
                check("the line names the fleet patch", "fleet patch choir" in text("#osc-target"),
                      text("#osc-target"))
                check("the /bop commands are listed",
                      all(name in text("#osc-commands") for name in ("/bop/master", "/bop/mute", "/bop/lead")))
                events = text("#osc-events")
                check("events show short and explicit addresses with fields",
                      "/<target>/trig/play" in events and "/<target>/e/trig/play" in events
                      and "clip" in events and "(optional)" in events and "default 1" in events, events)
                gain_event = page.locator("#osc-events .osc-row", has_text="/e/gain")
                gain_param = page.locator("#osc-params .osc-row", has_text="/p/gain")
                check("an identity declared as event and param is flagged ambiguous in both",
                      "ambiguous" in gain_event.inner_text() and "ambiguous" in gain_param.inner_text())
                check("an unambiguous identity carries no flag",
                      "ambiguous" not in page.locator("#osc-events .osc-row", has_text="trig/play").inner_text())
                check("parameters show kind and options", "warm" in text("#osc-params"))
                groups = text("#osc-groups")
                check("groups appear by name and g<id>",
                      "spot1" in groups and "g0" in groups and "choir-left" in groups and "g1" in groups, groups)

                # ---- live rejections and clamps ----------------------------
                check("the list starts empty", page.locator("#osc-recent .osc-recent-row").count() == 0)
                client = SimpleUDPClient("127.0.0.1", input_port)
                client.send_message("/nobody/trig/play", [1])
                client.send_message("/all/trig/play", [99])
                page.wait_for_function(
                    "() => document.querySelectorAll('#osc-recent .osc-recent-row').length === 2")
                rows = page.locator("#osc-recent .osc-recent-row")
                check("the rejection appears live without a reload",
                      page.locator("#osc-recent .osc-recent-rejection", has_text="unknown target").count() == 1)
                check("the clamp appears live, tagged as a clamp",
                      page.locator("#osc-recent .osc-recent-clamp", has_text="clamped to 15").count() == 1)
                check("the newest entry is first", "/all/trig/play" in rows.nth(0).inner_text())
                check("rows carry the sender", "127.0.0.1" in rows.nth(0).inner_text())

                # ---- Patch Edit regenerates -------------------------------
                page.click("#tab-button-patches")
                page.wait_for_function(
                    "() => document.querySelectorAll('#patch-list .patch-item').length === 2")
                page.click('#patch-list [data-patch="solo"]')
                page.click("#patch-edit")
                page.wait_for_function(
                    "() => installation.supervisor?.mode === 'edit' && installation.editor?.patch === 'solo'")
                page.click("#tab-button-osc")
                page.wait_for_function(
                    "() => document.querySelector('#osc-target').textContent.includes('edited patch solo')")
                check("the edited patch replaces the fleet patch's reference",
                      "ping" in text("#osc-events") and "trig/play" not in text("#osc-events")
                      and "tone" in text("#osc-params") and "colour" not in text("#osc-params"))
                page.click("#tab-button-patches")
                page.click("#patch-edit")
                page.wait_for_function("() => installation.supervisor?.mode !== 'edit'")
                page.click("#tab-button-osc")
                page.wait_for_function(
                    "() => document.querySelector('#osc-target').textContent.includes('fleet patch choir')")
                check("leaving Patch Edit restores the fleet patch's reference", "trig/play" in text("#osc-events"))

                # ---- phone width -------------------------------------------
                page.set_viewport_size({"width": 390, "height": 900})
                time.sleep(.3)
                widths = page.evaluate(
                    "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
                check("no horizontal page scroll at phone width", widths[0] <= widths[1], str(widths))
                check("no page errors", not errors, "; ".join(errors))
                browser.close()
        finally:
            stop(server)
            server_log.close()
    if FAILURES:
        print("FAILED: " + "; ".join(FAILURES))
        return 1
    print("OSC tab checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
