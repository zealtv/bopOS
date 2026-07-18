#!/usr/bin/env python3
"""Playwright verification for Show structural editing (stitch 6).

Covers: message copy/cut/paste/delete with fresh uids on paste, keyboard
copy/paste on focused pills, step/divider add/move/delete (confirm on
non-empty steps), persistence across reload, and a goto whose target step
was deleted falling back to stop with the stale reference surfaced.
"""

import json
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "tools" / "simfleet.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
HERE = Path(__file__).resolve().parent
FAILURES = []
RESERVED = set()


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
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
    raise RuntimeError("cannot reserve loopback port")


def wait_http(url, process):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before serving HTTP")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not serve HTTP")


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def make_fixture(root):
    patches = Path(root, "patches")
    assets = Path(root, "assets")
    state_dir = Path(root, "sim-state")
    patch = patches / "alpha"
    shows_dir = Path(root, "shows")
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows_dir.mkdir()
    (patch / "main.bin").write_bytes(b"show-editing-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": .4, "facilitator": True},
        ],
        "cues": [{"id": "snap", "label": "Snap"}], "caps": [], "slots": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Show editing verifier",
        "current_show": "opening-set",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "seats": {
            "0": {"id": 0, "name": "Front", "positions": [[1, 1]],
                  "groups": [], "bound": None, "patch": "alpha", "params": {}},
        },
        "groups": {},
        "next_group_id": 0,
    }
    show = {
        "schema": 1, "name": "opening-set",
        "items": [
            {"kind": "step", "uid": "11111111", "alias": "alpha",
             "messages": [
                 {"uid": "aaaa0001", "alias": "gain up", "address": "/p/gain",
                  "args": [{"type": "f", "value": 0.6}], "target": ["all"]},
                 {"uid": "aaaa0002", "alias": None, "address": "/cue",
                  "args": [{"type": "s", "value": "snap"}], "target": ["all"]},
             ],
             "duration_s": 0.3, "play_count": 1,
             "then_actions": [{"type": "goto", "target_uid": "22222222"}],
             "forward_sync": False},
            {"kind": "step", "uid": "22222222", "alias": "bravo",
             "messages": [
                 {"uid": "bbbb0001", "alias": "sparkle", "address": "/p/gain",
                  "args": [{"type": "f", "value": 1.0}], "target": ["0"]},
             ],
             "duration_s": 5.0, "play_count": 1,
             "then_actions": [], "forward_sync": False},
            {"kind": "divider", "uid": "dddd0001"},
            {"kind": "step", "uid": "33333333", "alias": "charlie",
             "messages": [],
             "duration_s": 5.0, "play_count": 1,
             "then_actions": [], "forward_sync": False},
        ],
    }
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows_dir / "opening-set.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-editing-") as root:
        patches, assets, state_dir, manifest_path, state_path = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log_path = Path(root, "server.log")
        fleet_log_path = Path(root, "fleet.log")
        server_log = server_log_path.open("w", encoding="utf-8")
        fleet_log = fleet_log_path.open("w", encoding="utf-8")
        server = fleet = None
        try:
            server = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard" / "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", str(state_path),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base_url,
            ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, str(ROOT / "tools" / "simfleet.py"),
                "--devices", "1", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.2", "--boot-secs", "0.2",
                "--state-dir", str(state_dir), "--manifest", str(manifest_path),
                "--patches-dir", str(patches), "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 768, "height": 1024}, has_touch=True,
                    is_mobile=True, device_scale_factor=1,
                )
                page = context.new_page()
                page_errors = []
                dialogs = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def on_dialog(dialog):
                    dialogs.append(dialog.message)
                    if dialog.type == "prompt":
                        dialog.accept("")
                    else:
                        dialog.accept()

                page.on("dialog", on_dialog)
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                page.wait_for_selector('.show-step-row[data-show-step-row="11111111"]')

                def pill_uids(step_uid):
                    return page.evaluate(
                        """(uid) => [...document.querySelectorAll(
                             `.show-step-row[data-show-step-row="${uid}"] [data-show-message-focus]`
                           )].map(pill => pill.dataset.showMessageFocus)""", step_uid)

                def row_order():
                    return page.evaluate(
                        """() => [...document.querySelectorAll(
                             '[data-show-step-row], [data-show-divider-row]'
                           )].map(row => row.dataset.showStepRow || `div:${row.dataset.showDividerRow}`)""")

                # -- copy / paste with fresh uid ------------------------------
                page.locator('[data-show-message-focus="aaaa0001"]').click()
                page.wait_for_selector('[data-message-copy="aaaa0001"]')
                check("paste starts disabled with an empty clipboard",
                      page.locator('.show-step-row[data-show-step-row="11111111"]').click() is None
                      and page.wait_for_selector("[data-paste-message]") is not None
                      and page.locator("[data-paste-message]").is_disabled())
                page.locator('[data-show-message-focus="aaaa0001"]').click()
                page.locator('[data-message-copy="aaaa0001"]').click()
                page.locator('.show-step-row[data-show-step-row="33333333"]').click()
                page.wait_for_selector("[data-paste-message]:not([disabled])")
                page.locator("[data-paste-message]").click()
                page.wait_for_function(
                    """() => document.querySelectorAll(
                         '.show-step-row[data-show-step-row="33333333"] [data-show-message-focus]'
                       ).length === 1""")
                pasted = pill_uids("33333333")
                check("paste clones the copied message into the target step with a fresh uid",
                      len(pasted) == 1 and pasted[0] != "aaaa0001"
                      and "gain up" in page.locator(
                          '.show-step-row[data-show-step-row="33333333"]').inner_text()
                      and pill_uids("11111111") == ["aaaa0001", "aaaa0002"],
                      repr(pasted))
                check("paste focuses the new pill and opens its inspector",
                      page.locator(f'[data-show-message-focus="{pasted[0]}"].focused').count() == 1)

                # -- cut / paste moves content, fresh uid ---------------------
                page.locator('[data-show-message-focus="bbbb0001"]').click()
                page.wait_for_selector('[data-message-cut="bbbb0001"]')
                page.locator('[data-message-cut="bbbb0001"]').click()
                page.wait_for_function(
                    """() => document.querySelectorAll(
                         '.show-step-row[data-show-step-row="22222222"] [data-show-message-focus]'
                       ).length === 0""")
                page.locator('.show-step-row[data-show-step-row="11111111"]').click()
                page.wait_for_selector("[data-paste-message]:not([disabled])")
                page.locator("[data-paste-message]").click()
                page.wait_for_function(
                    """() => document.querySelectorAll(
                         '.show-step-row[data-show-step-row="11111111"] [data-show-message-focus]'
                       ).length === 3""")
                moved = [uid for uid in pill_uids("11111111")
                         if uid not in ("aaaa0001", "aaaa0002")]
                check("cut removes the pill and paste re-creates it elsewhere with a fresh uid",
                      len(moved) == 1 and moved[0] != "bbbb0001"
                      and "sparkle" in page.locator(
                          '.show-step-row[data-show-step-row="11111111"]').inner_text(),
                      repr(pill_uids("11111111")))

                # -- keyboard copy / paste ------------------------------------
                page.locator('[data-show-message-focus="aaaa0002"]').click()
                page.keyboard.press("Control+c")
                page.locator('.show-step-row[data-show-step-row="22222222"]').click()
                page.keyboard.press("Control+v")
                page.wait_for_function(
                    """() => document.querySelectorAll(
                         '.show-step-row[data-show-step-row="22222222"] [data-show-message-focus]'
                       ).length === 1""")
                check("keyboard copy on a pill and paste on a row clone the message",
                      pill_uids("22222222")[0] != "aaaa0002")

                # -- delete a message -----------------------------------------
                keyboard_clone = pill_uids("22222222")[0]
                page.locator(f'[data-show-message-focus="{keyboard_clone}"]').click()
                page.wait_for_selector(f'[data-message-delete="{keyboard_clone}"]')
                page.locator(f'[data-message-delete="{keyboard_clone}"]').click()
                page.wait_for_function(
                    """() => document.querySelectorAll(
                         '.show-step-row[data-show-step-row="22222222"] [data-show-message-focus]'
                       ).length === 0""")
                check("delete removes the message", True)

                # -- move a message between steps via the picker --------------
                sparkle_uid = moved[0]
                page.locator(f'[data-show-message-focus="{sparkle_uid}"]').click()
                page.wait_for_selector(f'[data-message-move-step="{sparkle_uid}"]')
                page.select_option(f'[data-message-move-step="{sparkle_uid}"]', "22222222")
                page.wait_for_function(
                    """() => document.querySelectorAll(
                         '.show-step-row[data-show-step-row="22222222"] [data-show-message-focus]'
                       ).length === 1""")
                check("move-to-step relocates the message keeping its uid",
                      pill_uids("22222222") == [sparkle_uid],
                      repr(pill_uids("22222222")))

                # -- reorder a message within a step --------------------------
                first_pair = pill_uids("11111111")
                page.locator('[data-show-message-focus="aaaa0002"]').click()
                page.wait_for_selector('[data-message-move][data-message-uid="aaaa0002"]')
                page.locator('[data-message-move="-1"][data-message-uid="aaaa0002"]').click()
                page.wait_for_function(
                    """(before) => {
                        const now = [...document.querySelectorAll(
                          '.show-step-row[data-show-step-row=\\"11111111\\"] [data-show-message-focus]'
                        )].map(pill => pill.dataset.showMessageFocus);
                        return JSON.stringify(now) !== JSON.stringify(before);
                    }""", arg=first_pair)
                check("move-left reorders the pill within its step",
                      pill_uids("11111111")[0] == "aaaa0002", repr(pill_uids("11111111")))

                # -- structural: add step / divider, move, delete -------------
                base_order = row_order()
                page.locator('[data-item-add-end="step"]').click()
                page.wait_for_function(
                    f"() => document.querySelectorAll('[data-show-step-row]').length === 4")
                appended = row_order()[-1]
                check("add-bar appends a step at the end",
                      appended not in base_order and not appended.startswith("div:"),
                      repr(row_order()))

                page.locator(f'.show-step-row[data-show-step-row="{appended}"]').click()
                page.wait_for_selector(f'[data-item-add="divider"][data-item-uid="{appended}"]')
                page.locator(f'[data-item-add="divider"][data-item-uid="{appended}"]').click()
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-show-divider-row]').length === 2")
                check("inspector adds a divider below the focused step",
                      row_order()[-1].startswith("div:"), repr(row_order()))

                page.locator(f'[data-item-move="-1"][data-item-uid="{appended}"]').click()
                page.wait_for_function(
                    """(uid) => {
                        const order = [...document.querySelectorAll(
                          '[data-show-step-row], [data-show-divider-row]'
                        )].map(row => row.dataset.showStepRow || row.dataset.showDividerRow);
                        return order.indexOf(uid) === order.length - 3;
                    }""", arg=appended)
                check("move-up walks the step above its neighbour", True)
                page.locator(f'[data-item-move="1"][data-item-uid="{appended}"]').click()
                page.wait_for_function(
                    """(uid) => {
                        const order = [...document.querySelectorAll(
                          '[data-show-step-row], [data-show-divider-row]'
                        )].map(row => row.dataset.showStepRow || row.dataset.showDividerRow);
                        return order.indexOf(uid) === order.length - 2;
                    }""", arg=appended)

                new_divider = row_order()[-1].split(":", 1)[1]
                page.locator(f'[data-show-divider-row="{new_divider}"]').click()
                page.wait_for_selector(f'[data-item-delete="{new_divider}"]')
                page.locator(f'[data-item-delete="{new_divider}"]').click()
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-show-divider-row]').length === 1")
                dialog_count = len(dialogs)
                page.locator(f'.show-step-row[data-show-step-row="{appended}"]').click()
                page.wait_for_selector(f'[data-item-delete="{appended}"]')
                page.locator(f'[data-item-delete="{appended}"]').click()
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-show-step-row]').length === 3")
                check("deleting a divider and an empty step needs no confirm",
                      len(dialogs) == dialog_count, repr(dialogs[dialog_count:]))
                check("structure returned to the seeded shape",
                      row_order() == base_order, f"{row_order()} vs {base_order}")

                # -- goto at a deleted step -----------------------------------
                page.locator('.show-step-row[data-show-step-row="22222222"]').click()
                page.wait_for_selector('[data-item-delete="22222222"]')
                dialog_count = len(dialogs)
                page.locator('[data-item-delete="22222222"]').click()
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-show-step-row]').length === 2")
                check("deleting a step holding messages raises the confirm dialog",
                      len(dialogs) == dialog_count + 1
                      and "bravo" in dialogs[-1], repr(dialogs[dialog_count:]))

                page.locator('.show-step-row[data-show-step-row="11111111"]').click()
                page.wait_for_selector('[data-then-goto="0"]')
                check("stale goto renders as a missing-step option",
                      "missing step" in page.locator('[data-then-goto="0"]')
                          .locator("option[selected]").inner_text())

                page.locator(
                    '.show-step-row[data-show-step-row="11111111"] '
                    '[data-show-action="step_start"]').click()
                page.wait_for_selector(
                    '.show-step-row[data-show-step-row="11111111"].show-step-stopped',
                    timeout=8000)
                page.wait_for_selector(".show-goto-missing")
                check("goto to a deleted step falls back to stop and flags the row", True)

                # -- persistence across reload --------------------------------
                before_reload = row_order()
                pills_before = pill_uids("11111111")
                page.reload()
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                page.wait_for_selector('.show-step-row[data-show-step-row="11111111"]')
                check("edited structure persists across reload",
                      row_order() == before_reload
                      and pill_uids("11111111") == pills_before,
                      f"{row_order()} vs {before_reload}")

                check("browser emitted no page errors", not page_errors, repr(page_errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

        if FAILURES:
            print("\nserver log tail:\n", server_log_path.read_text(encoding="utf-8")[-4000:])
            print("\nfleet log tail:\n", fleet_log_path.read_text(encoding="utf-8")[-4000:])

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
