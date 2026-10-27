#!/usr/bin/env python3
"""Typed event fields, authored in the Patch editor and fired from Control.

One journey on a real dashboard with private ports: author an event with mixed
fields (text, float, enum, int, toggle; the last four optional), reorder and
remove fields, save, reload, then fire the event from the Control tab and check
what the server and a simfleet node receive.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
from project_fixture import data_root, project_path
from verify_manifest_param_visibility import (
    FAILURES, ROOT, check, drag_before, free_port, stop, wait_http)

UID = "02:53:49:4d:00:01"
FOLDER = "m1s2/spot1/slice000"


def write_fixture(temp):
    patch = os.path.join(temp, "patches", "alpha")
    assets = os.path.join(temp, "assets")
    os.makedirs(patch)
    os.makedirs(assets)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"event-fields")
    manifest = os.path.join(patch, "bopos.patch.json")
    with open(manifest, "w", encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin",
                   "params": [{"name": "gain", "kind": "float", "min": 0,
                               "max": 1, "default": .5}],
                   "events": [{"name": "strike", "fields": [],
                               "dashboard": False}],
                   "caps": [], "slots": []}, target)
    state_path = str(project_path(temp))
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump({
            "schema": 1, "name": "Event fields rig",
            "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                            "staged_at": time.time()},
            "seats": {"1": {"id": 1, "name": "Finn", "positions": [[1, 1]],
                            "bound": UID, "params": {"gain": .5}}},
        }, target)
    # A Show with one event message, to check the Show inspector's builder.
    show_path = os.path.join(os.path.dirname(state_path), "shows", "Show.json")
    os.makedirs(os.path.dirname(show_path))
    with open(show_path, "w", encoding="utf-8") as target:
        json.dump({"schema": 1, "name": "fields", "items": [{
            "kind": "step", "uid": "11111111", "alias": "fields",
            "messages": [{"uid": "bbbb0001", "kind": "osc", "alias": None,
                          "address": "/e/play", "target": ["all"], "args": []}],
            "duration_s": 10, "play_count": 1,
            "then_actions": [{"type": "stop"}]}]}, target)
    return state_path, os.path.join(temp, "patches"), assets, manifest, show_path


def field_row(page, index):
    return page.locator(
        '#manifest-events .manifest-event[data-event-index="1"] .manifest-field'
    ).nth(index)


def author_field(page, index, name, kind, **values):
    """Fill one field row the way a person would: name, kind, then the rest."""
    page.locator('#manifest-events [data-add-field="1"]').click()
    row = field_row(page, index)
    row.locator('[data-manifest-field="name"]').fill(name)
    row.locator('[data-manifest-field="kind"]').select_option(kind)
    # A kind change re-renders the editor: take a fresh row for the rest.
    row = field_row(page, index)
    for key in ("min", "max", "options", "default"):
        if key in values:
            row.locator(f'[data-manifest-field="{key}"]').fill(str(values[key]))
    if values.get("optional"):
        row.locator('[data-manifest-field="optional"]').check()


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-event-fields-") as temp:
        state_path, patches, assets, manifest, show_path = write_fixture(temp)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        fleet_log_path = os.path.join(temp, "fleet.log")
        server_log = open(os.path.join(temp, "server.log"), "w", encoding="utf-8")
        fleet_log = open(fleet_log_path, "w", encoding="utf-8")
        server = fleet = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(ROOT, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port),
                "--stream-port", str(free_port(socket.SOCK_DGRAM)),
                "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--data-dir", data_root(state_path),
                "--assets-dir", assets, "--patches-dir", patches,
                "--public-url", base_url, "--sim-no-engine",
            ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1400})
                page.set_default_timeout(10000)
                errors, sent = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("websocket", lambda ws: ws.on(
                    "framesent", lambda payload: sent.append(json.loads(payload))))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")

                # ---- author -------------------------------------------------
                page.click("#tab-button-patches")
                page.click("#patch-edit")
                page.wait_for_function(
                    "() => installation.supervisor?.mode === 'edit'"
                    " && installation.editor?.patch === 'alpha'")
                page.wait_for_function(
                    "() => !document.querySelector('#manifest-add-event').disabled")
                check("the event row has no arity control",
                      page.locator('#manifest-events [data-manifest-field="arity"]').count() == 0
                      and page.locator("#manifest-events [data-event-default]").count() == 0)
                page.click("#manifest-add-event")
                page.locator('#manifest-events .manifest-event').nth(1).locator(
                    ':scope > label input[data-manifest-field="name"]').fill("play")
                author_field(page, 0, "folder", "text")
                author_field(page, 1, "density", "float", min=0, max=1, default=1,
                             optional=True)
                author_field(page, 2, "mode", "enum", options="soft\nmedium\nhard",
                             default=1, optional=True)
                author_field(page, 3, "play2end", "toggle", default=0, optional=True)
                author_field(page, 4, "count", "int", min=0, max=10, default=3,
                             optional=True)
                author_field(page, 5, "spare", "float")
                check("a field row offers name, kind, range, default and optional",
                      field_row(page, 1).locator(
                          '[data-manifest-field="name"], [data-manifest-field="kind"],'
                          ' [data-manifest-field="min"], [data-manifest-field="max"],'
                          ' [data-manifest-field="default"],'
                          ' [data-manifest-field="optional"]').count() == 6)
                check("a field row has no path or Remote control",
                      field_row(page, 1).locator(
                          '[data-manifest-field="path"], [data-manifest-field="dashboard"]'
                      ).count() == 0)
                field_row(page, 5).locator("[data-remove-field]").click()
                check("a field can be removed",
                      page.evaluate("() => manifestDraft.events[1].fields.length") == 5)
                drag_before(page,
                            field_row(page, 4).locator('[data-manifest-drag="fields"]'),
                            field_row(page, 3))
                order = page.evaluate(
                    "() => manifestDraft.events[1].fields.map(field => field.name)")
                check("a field can be reordered by its handle",
                      order == ["folder", "density", "mode", "count", "play2end"],
                      repr(order))

                # An event qualifies by path like a param (`point/0/start`).
                page.click("#manifest-add-event")
                start_row = page.locator('#manifest-events .manifest-event').nth(2)
                start_row.locator(
                    ':scope > label input[data-manifest-field="path"]').fill("point/0")
                start_row.locator(
                    ':scope > label input[data-manifest-field="name"]').fill("start")
                page.locator('#manifest-events [data-add-field="2"]').click()
                start_row.locator('.manifest-field [data-manifest-field="name"]').fill("file")
                start_row.locator('.manifest-field [data-manifest-field="kind"]'
                                  ).select_option("text")

                page.click("#manifest-save")
                page.wait_for_function(
                    "() => { const text=document.querySelector('#manifest-feedback')"
                    "?.textContent||''; return text && !text.includes('Saving manifest'); }")
                with open(manifest, encoding="utf-8") as source:
                    saved = json.load(source)
                check("an event saves its path",
                      saved["events"][2] == {
                          "name": "start", "path": ["point", "0"],
                          "fields": [{"name": "file", "kind": "text", "optional": False}],
                          "dashboard": False},
                      repr(saved["events"][2:]))
                play = next((event for event in saved["events"]
                             if event["name"] == "play"), {})
                expected = [
                    {"name": "folder", "kind": "text", "optional": False},
                    {"name": "density", "kind": "float", "min": 0, "max": 1,
                     "default": 1, "optional": True},
                    {"name": "mode", "kind": "enum", "min": 0, "max": 2,
                     "options": ["soft", "medium", "hard"], "default": 1,
                     "optional": True},
                    {"name": "count", "kind": "int", "min": 0, "max": 10,
                     "default": 3, "optional": True},
                    {"name": "play2end", "kind": "toggle", "min": 0, "max": 1,
                     "default": 0, "optional": True},
                ]
                feedback = page.locator("#manifest-feedback").inner_text()
                check("the saved manifest carries the authored fields",
                      # The server stores the normalized form: derived enum and
                      # toggle ranges, optional spelled out.
                      play.get("fields") == expected and "arity" not in play
                      and "defaults" not in play,
                      f"feedback={feedback!r} saved={play!r}")
                check("an event without fields saves as an empty list",
                      saved["events"][0] == {"name": "strike", "fields": [],
                                             "dashboard": False},
                      repr(saved["events"][0]))

                # ---- reload -------------------------------------------------
                page.reload()
                page.wait_for_selector("#ws-status.online")
                page.wait_for_selector(
                    '#manifest-events .manifest-event[data-event-index="1"] .manifest-field')
                loaded = page.evaluate("""() => [...document.querySelectorAll(
                  '#manifest-events .manifest-event[data-event-index="1"] .manifest-field')]
                  .map(row => ({
                    name: row.querySelector('[data-manifest-field=name]').value,
                    kind: row.querySelector('[data-manifest-field=kind]').value,
                    optional: row.querySelector('[data-manifest-field=optional]').checked,
                    default: row.querySelector('[data-manifest-field=default]').value}))""")
                check("a reloaded editor shows the saved fields",
                      [(f["name"], f["kind"], f["optional"], f["default"])
                       for f in loaded]
                      == [("folder", "text", False, ""), ("density", "float", True, "1"),
                          ("mode", "enum", True, "1"), ("count", "int", True, "3"),
                          ("play2end", "toggle", True, "0")], repr(loaded))
                check("a reloaded editor shows the event path",
                      page.locator('#manifest-events .manifest-event[data-event-index="2"]'
                                   ' > label input[data-manifest-field="path"]'
                                   ).input_value() == "point/0")

                # A required field after an optional one is the validator's
                # call; the editor shows its words rather than saving.
                field_row(page, 0).locator('[data-manifest-field="optional"]').check()
                field_row(page, 0).locator('[data-manifest-field="default"]').fill("x")
                page.locator('#manifest-events .manifest-event[data-event-index="1"]'
                             ).locator('[data-add-field]').click()
                field_row(page, 5).locator('[data-manifest-field="name"]').fill("late")
                page.click("#manifest-save")
                page.wait_for_function(
                    "() => document.querySelector('#manifest-feedback').textContent"
                    ".startsWith('Not saved:')")
                with open(manifest, encoding="utf-8") as source:
                    check("an invalid field list leaves the saved manifest intact",
                          json.load(source) == saved)
                page.reload()
                page.wait_for_selector("#ws-status.online")

                # ---- fire ---------------------------------------------------
                page.click("#tab-button-patches")
                page.click("#patch-edit")  # confirm: back to Live
                page.wait_for_function(
                    "() => installation.supervisor?.mode !== 'edit'")
                fleet = subprocess.Popen([
                    sys.executable, os.path.join(ROOT, "tools", "simfleet.py"),
                    "--devices", "1", "--target", "127.0.0.1",
                    "--report-port", str(listen_port),
                    "--cmd-port", str(send_port), "--hb-interval", "0.3",
                    "--boot-secs", "0.2", "--manifest", manifest,
                    "--patches-dir", patches, "--assets-dir", assets,
                ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)
                page.wait_for_function(
                    "uid => installation.devices[uid]?.online === true", arg=UID)
                page.click("#tab-button-control")
                row = page.locator(
                    '#control-column-host .live-param-event[data-live-scope="all"]'
                    '[data-param-path="play"]')
                row.wait_for()
                controls = row.locator("[data-event-field]")
                check("the fire row has one control per field, in field order",
                      controls.count() == 5 and row.evaluate(
                          "node => [...node.querySelectorAll('.live-event-field-name')]"
                          ".map(label => label.textContent).join(',')")
                      == "folder,density,mode,count,play2end")
                check("a path event fires from its branch in the Control tab",
                      page.locator(
                          '#control-column-host [data-param-branch="point/0"]'
                          ' .live-param-event[data-live-scope="all"]'
                          '[data-param-path="point/0/start"]').count() == 1)
                kinds = row.evaluate(
                    "node => [...node.querySelectorAll('[data-event-field]')]"
                    ".map(control => control.tagName + ':' + control.dataset.fieldKind"
                    " + ':' + (control.type || ''))")
                check("each field uses its kind's control",
                      kinds == ["INPUT:text:text", "INPUT:float:number",
                                "SELECT:enum:select-one", "INPUT:int:number",
                                "BUTTON:toggle:button"], repr(kinds))
                shown = row.evaluate(
                    "node => [...node.querySelectorAll('[data-event-field]')]"
                    ".map(control => control.tagName === 'BUTTON'"
                    " ? control.getAttribute('aria-pressed') : control.value)")
                check("the controls start at the declared defaults",
                      shown == ["", "1", "1", "3", "false"], repr(shown))
                check("a name sits under no control of the zero-field event",
                      page.locator('#control-column-host .live-param-event'
                                   '[data-live-scope="all"][data-param-path="strike"]'
                                   ' [data-event-field]').count() == 0)

                fires = lambda: [m for m in sent if m.get("type") == "fire_event"]
                row.locator(".live-event-send").click()
                page.wait_for_function(
                    "() => document.querySelector('.live-param-event"
                    "[data-param-path=\"play\"] [data-event-field][aria-invalid=true]')")
                check("an empty required text field holds the fire",
                      not fires())
                row.locator('[data-field-kind="text"]').fill("has space")
                row.locator(".live-event-send").click()
                check("text with whitespace holds the fire", not fires())

                row.locator('[data-field-kind="text"]').fill(FOLDER)
                row.locator('[data-field-kind="float"]').fill("0.25")
                row.locator('[data-field-kind="enum"]').select_option("2")
                row.locator('[data-field-kind="int"]').fill("7")
                row.locator('[data-field-kind="toggle"]').click()
                row.locator(".live-event-send").click()
                deadline = time.monotonic() + 5
                while not fires() and time.monotonic() < deadline:
                    time.sleep(.05)
                check("the fire carries every field's value, typed by kind",
                      fires() and fires()[0]["data"]["identity"] == "play"
                      and fires()[0]["data"]["elements"] == [FOLDER, .25, 2, 7, 1],
                      repr(fires()))

                line = None
                deadline = time.monotonic() + 8
                while line is None and time.monotonic() < deadline:
                    with open(fleet_log_path, encoding="utf-8") as log:
                        line = next((entry for entry in log
                                     if "event play fired" in entry), None)
                    time.sleep(.1)
                check("a simfleet node receives the mixed fields",
                      line is not None
                      and f"elements={FOLDER} 0.25 2 7 1" in line, repr(line))

                # The shared number box clamps to the declared range on commit,
                # as it does for parameters.
                page.wait_for_function(
                    "() => !document.querySelector('.live-event-send[data-firing]')")
                count = row.locator('[data-field-kind="int"]')
                count.fill("11")
                count.press("Tab")
                check("a number box clamps to the field's declared range",
                      count.input_value() == "10", repr(count.input_value()))

                # ---- Show ---------------------------------------------------
                page.click("#tab-button-show")
                page.locator('[data-show-message-focus="bbbb0001"]').click()
                builder = page.locator('[data-payload-builder="event"]')
                builder.wait_for()
                # Switching the event (re)fills the message from its defaults.
                builder.locator("#show-event-picker").select_option("play")
                page.wait_for_function(
                    "() => document.querySelectorAll("
                    "'[data-payload-builder=event] [data-event-element]').length === 5")
                names = page.evaluate(
                    "() => [...document.querySelectorAll("
                    "'[data-payload-builder=event] label')].map(label => label.firstChild"
                    ".textContent.trim()).filter(Boolean)")
                check("the Show builder has one labelled control per field",
                      names[-5:] == ["folder", "density", "mode", "count", "play2end"],
                      repr(names))

                def saved_args():
                    with open(show_path, encoding="utf-8") as source:
                        message = json.load(source)["items"][0]["messages"][0]
                    return [(arg["type"], arg["value"]) for arg in message["args"]]

                def wait_args(expected):
                    deadline = time.monotonic() + 5
                    while saved_args() != expected and time.monotonic() < deadline:
                        time.sleep(.1)
                    return saved_args()

                # A required text field has no default; the message starts
                # with the empty text a person must replace.
                builder = page.locator('[data-payload-builder="event"]')
                builder.locator('[data-field-kind="text"]').fill(FOLDER)
                builder.locator('[data-field-kind="text"]').press("Tab")
                builder.locator('[data-field-kind="float"]').fill("0.5")
                builder.locator('[data-field-kind="float"]').press("Tab")
                builder.locator('[data-field-kind="enum"]').select_option("0")
                builder.locator('[data-field-kind="toggle"]').click()
                got = wait_args([("s", FOLDER), ("f", .5), ("i", 0), ("i", 3), ("i", 1)])
                check("Show saves each field with its kind's OSC tag", got ==
                      [("s", FOLDER), ("f", .5), ("i", 0), ("i", 3), ("i", 1)],
                      repr(got))

                check("browser surfaces emitted no page errors", not errors,
                      repr(errors))
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
    print("Event fields editor checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
