#!/usr/bin/env python3
"""Focused Playwright verification for the Show edit bar + inline step name.

Covers 02-edit-bar-and-inline-step-name: the persistent edit bar above
`.show-rows-box` (desktop icon+text / narrow icon-only, stable positions,
message-focus disables Duplicate/Delete, insertion-after-selected vs.
append), the `duplicate_item` model/server operation (fresh uids for the
item and every nested message, undo, persistence, second-client broadcast),
no delete confirmation, and inline step-name rename (click/tap, Enter,
blur, Escape, blank -> untitled, F2). No simulated fleet is needed --
this stitch never touches Seat/device state.
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


def message(uid, alias, value):
    return {"uid": uid, "alias": alias, "address": "/p/gain",
            "args": [{"type": "f", "value": value}], "target": ["all"]}


def make_fixture(root):
    root = Path(root)
    patches, assets, shows = root / "patches", root / "assets", root / "shows"
    patch = patches / "alpha"
    patch.mkdir(parents=True)
    assets.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"edit-bar-verify")
    (patch / "bopos.patch.json").write_text(json.dumps({
        "engine": "test", "entrypoint": "main.bin",
        "params": [{"name": "gain", "type": "f", "min": 0, "max": 1,
                    "default": .4, "facilitator": True}],
        "cues": [], "caps": [], "slots": [],
    }), encoding="utf-8")
    state = {
        "schema": 1, "name": "Edit bar verifier",
        "current_show": "opening-set", "params_patch": "alpha",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "seats": {}, "groups": {}, "next_group_id": 0,
    }
    populated = {"schema": 1, "name": "opening-set", "items": [
        {"kind": "step", "uid": "11111111", "alias": "alpha",
         "messages": [message("aaaa0001", "one", .1), message("aaaa0002", "two", .2)],
         "duration_s": 5, "play_count": 1, "then_actions": [{"type": "stop"}]},
        {"kind": "divider", "uid": "dddd0001"},
        {"kind": "step", "uid": "22222222", "alias": "bravo",
         "messages": [], "duration_s": 5, "play_count": 1,
         "then_actions": [{"type": "stop"}]},
    ]}
    empty = {"schema": 1, "name": "empty-set", "items": []}
    state_path = root / "installation.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows / "opening-set.json").write_text(json.dumps(populated, indent=2) + "\n", encoding="utf-8")
    (shows / "empty-set.json").write_text(json.dumps(empty, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_path, shows / "opening-set.json"


def item_order(page):
    return page.locator("[data-show-step-row],[data-show-divider-row]").evaluate_all(
        "nodes => nodes.map(node => node.dataset.showStepRow || `div:${node.dataset.showDividerRow}`)")


def message_uids(page, step_uid):
    return page.locator(f'[data-show-step-row="{step_uid}"] [data-drag-message]').evaluate_all(
        "nodes => nodes.map(node => node.dataset.dragMessage)")


def no_horizontal_overflow(page):
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-edit-bar-verify-") as root:
        patches, assets, state_path, show_path = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = Path(root, "server.log")
        log = log_path.open("w", encoding="utf-8")
        server = None
        try:
            server = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard" / "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", str(state_path),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base_url,
            ], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)

                dialogs = []

                def on_dialog(dialog):
                    dialogs.append(dialog.message)
                    dialog.accept("") if dialog.type == "prompt" else dialog.accept()

                # ------------------------------------------------------------
                # Desktop (1280px)
                # ------------------------------------------------------------
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = context.new_page()
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.on("dialog", on_dialog)
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="11111111"]')

                bar = page.locator(".show-edit-bar")
                check("edit bar sits immediately above the rows box",
                      page.evaluate("""() => {
                        const bar = document.querySelector('.show-edit-bar');
                        const box = document.querySelector('.show-rows-box');
                        return bar && box && bar.compareDocumentPosition(box) === Node.DOCUMENT_POSITION_FOLLOWING;
                      }"""))
                check("edit bar is inside .show-list-shell",
                      page.evaluate("""() =>
                        !!document.querySelector('.show-list-shell > .show-edit-bar')"""))
                check("wide layout shows icon + text labels",
                      bar.locator('[data-edit-bar-action="add-step"] .show-edit-bar-label').is_visible())

                add_step = bar.locator('[data-edit-bar-action="add-step"]')
                add_divider = bar.locator('[data-edit-bar-action="add-divider"]')
                duplicate_btn = bar.locator('[data-edit-bar-action="duplicate"]')
                delete_btn = bar.locator('[data-edit-bar-action="delete"]')

                check("Duplicate/Delete disabled with nothing selected",
                      duplicate_btn.is_disabled() and delete_btn.is_disabled())
                check("+ Step / + Divider stay enabled with nothing selected",
                      add_step.is_enabled() and add_divider.is_enabled())
                for locator, label in ((add_step, "add-step"), (add_divider, "add-divider"),
                                       (duplicate_btn, "duplicate"), (delete_btn, "delete")):
                    aria = locator.get_attribute("aria-label")
                    title = locator.get_attribute("title")
                    check(f"{label} has aria-label and title", bool(aria) and bool(title), repr((aria, title)))
                box = add_step.bounding_box()
                check("edit bar buttons are touch-sized (>=40px tall)", box["height"] >= 40, repr(box))

                # Append with nothing selected -> goes to the very end.
                before = item_order(page)
                add_step.click()
                page.wait_for_function(
                    "count => document.querySelectorAll('[data-show-step-row],[data-show-divider-row]').length === count",
                    arg=len(before) + 1)
                after_append = item_order(page)
                check("+ Step with no selection appends to the end",
                      after_append[:-1] == before and after_append[-1] not in before,
                      repr((before, after_append)))
                appended_uid = after_append[-1]

                # Select the first step; insertion now happens right after it.
                page.locator('[data-show-step-row="11111111"]').click()
                check("selecting a step enables Duplicate/Delete",
                      duplicate_btn.is_enabled() and delete_btn.is_enabled())
                before = item_order(page)
                add_divider.click()
                page.wait_for_function(
                    "count => document.querySelectorAll('[data-show-step-row],[data-show-divider-row]').length === count",
                    arg=len(before) + 1)
                after_insert = item_order(page)
                check("+ Divider inserts right after the selected structural row",
                      after_insert[0] == "11111111" and after_insert[1].startswith("div:")
                      and after_insert[1] not in before and after_insert[2:] == before[1:],
                      repr((before, after_insert)))
                inserted_divider = after_insert[1].split(":", 1)[1]

                # Message focus disables Duplicate/Delete (structural-only bar).
                page.locator('[data-drag-message="aaaa0001"]').click()
                check("message focus disables Duplicate/Delete",
                      duplicate_btn.is_disabled() and delete_btn.is_disabled())
                check("+ Step / + Divider still enabled on message focus",
                      add_step.is_enabled() and add_divider.is_enabled())

                # -------------------------------------------------------
                # Duplicate: step with nested messages -> fresh uids.
                # -------------------------------------------------------
                page.locator('[data-show-step-row="11111111"]').click()
                before = item_order(page)
                original_messages = message_uids(page, "11111111")
                duplicate_btn.click()
                page.wait_for_function(
                    "count => document.querySelectorAll('[data-show-step-row],[data-show-divider-row]').length === count",
                    arg=len(before) + 1)
                after_dup = item_order(page)
                check("Duplicate inserts the clone right after the original step",
                      after_dup[0] == "11111111" and after_dup[2:] == before[1:],
                      repr((before, after_dup)))
                duplicated_step_uid = after_dup[1]
                check("duplicated step has a fresh uid",
                      duplicated_step_uid != "11111111" and duplicated_step_uid not in before)
                duplicated_messages = message_uids(page, duplicated_step_uid)
                check("duplicated step carries the same message count",
                      len(duplicated_messages) == len(original_messages),
                      repr((original_messages, duplicated_messages)))
                check("duplicated messages all received fresh uids",
                      set(duplicated_messages).isdisjoint(original_messages)
                      and len(set(duplicated_messages)) == len(duplicated_messages),
                      repr((original_messages, duplicated_messages)))
                duplicated_texts = page.locator(
                    f'[data-show-step-row="{duplicated_step_uid}"] [data-drag-message]').all_inner_texts()
                stripped_texts = [text.replace("⋮", "").strip() for text in duplicated_texts]
                check("duplicated message content (aliases) carried over",
                      sorted(stripped_texts) == sorted(["one", "two"]), repr(duplicated_texts))

                # -------------------------------------------------------
                # Delete: no confirmation dialog, even for a non-empty step.
                # -------------------------------------------------------
                dialog_count = len(dialogs)
                page.locator(f'[data-show-step-row="{duplicated_step_uid}"]').click()
                check("duplicated (non-empty) step selected for delete",
                      delete_btn.is_enabled())
                before = item_order(page)
                delete_btn.click()
                page.wait_for_function(
                    "count => document.querySelectorAll('[data-show-step-row],[data-show-divider-row]').length === count",
                    arg=len(before) - 1)
                check("Delete removes a non-empty step without any confirm dialog",
                      len(dialogs) == dialog_count, repr(dialogs[dialog_count:]))
                check("deleted step no longer in the list", duplicated_step_uid not in item_order(page))

                # -------------------------------------------------------
                # Undo covers duplicate + delete (no other structural ops
                # interleaved, so two undos round-trips: undo1 reverts the
                # delete, undo2 reverts the duplicate itself).
                # -------------------------------------------------------
                before_undo = item_order(page)
                page.keyboard.press("Control+z")
                page.wait_for_function(
                    "count => document.querySelectorAll('[data-show-step-row],[data-show-divider-row]').length === count",
                    arg=len(before_undo) + 1)
                check("undo restores the deleted step", duplicated_step_uid in item_order(page))
                page.keyboard.press("Control+z")
                page.wait_for_function(
                    "uid => !document.querySelector(`[data-show-step-row=\"${uid}\"]`)", arg=duplicated_step_uid)
                check("a second undo removes the duplicated step again",
                      duplicated_step_uid not in item_order(page))

                # -------------------------------------------------------
                # Duplicate: divider allowed, fresh uid.
                # -------------------------------------------------------
                page.locator(f'[data-show-divider-row="{inserted_divider}"]').click()
                before = item_order(page)
                duplicate_btn.click()
                page.wait_for_function(
                    "count => document.querySelectorAll('[data-show-step-row],[data-show-divider-row]').length === count",
                    arg=len(before) + 1)
                after_div_dup = item_order(page)
                new_divider_token = [token for token in after_div_dup if token.startswith("div:")
                                     and token.split(":", 1)[1] not in (inserted_divider, "dddd0001")]
                check("divider Duplicate clones it with a fresh uid",
                      len(new_divider_token) == 1, repr(after_div_dup))

                # -------------------------------------------------------
                # Cleanup extra rows added above and settle on a known set,
                # then persistence / second-client broadcast checks.
                # -------------------------------------------------------
                current = item_order(page)
                check("appended step and inserted/duplicated divider remain",
                      appended_uid in current and f"div:{inserted_divider}" in current, repr(current))

                peer_context = browser.new_context(viewport={"width": 1024, "height": 800})
                peer = peer_context.new_page()
                peer.on("pageerror", lambda error: page_errors.append(f"peer: {error}"))
                peer.goto(base_url)
                peer.wait_for_selector("#ws-status.online", state="attached")
                peer.click("#tab-button-show")
                peer.wait_for_selector(f'[data-show-step-row="{appended_uid}"]')
                check("second client sees the same structural edits",
                      item_order(peer) == item_order(page), repr((item_order(peer), item_order(page))))

                before_reload = item_order(page)
                page.reload()
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.wait_for_selector(f'[data-show-step-row="{appended_uid}"]')
                check("structural edits persist across reload",
                      item_order(page) == before_reload, repr((before_reload, item_order(page))))
                saved = json.loads(show_path.read_text(encoding="utf-8"))
                saved_uids = [item["uid"] for item in saved["items"]]
                client_uids = [token.split(":", 1)[-1] for token in before_reload]
                check("persisted show file matches the client's structural order",
                      saved_uids == client_uids, repr((saved_uids, client_uids)))

                # -------------------------------------------------------
                # Message pill copy/paste keyboard flow untouched (hard
                # retention constraint from 01-layout-review decisions.md).
                # -------------------------------------------------------
                remaining_pills = page.locator('[data-show-step-row="11111111"] [data-drag-message]')
                first_pill_uid = remaining_pills.first.get_attribute("data-drag-message")
                page.locator(f'[data-drag-message="{first_pill_uid}"]').click()
                page.keyboard.press("Control+c")
                page.locator('[data-show-step-row="22222222"]').focus()
                page.keyboard.press("Control+v")
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-show-step-row=\"22222222\"] [data-drag-message]').length === 1")
                check("message pill Ctrl+C/Ctrl+V keyboard flow still works",
                      len(message_uids(page, "22222222")) == 1)

                # -------------------------------------------------------
                # Drag reorder regression (structural rows still drag).
                # -------------------------------------------------------
                def drag(source, x, y):
                    src_box = source.bounding_box()
                    page.mouse.move(src_box["x"] + src_box["width"] / 2, src_box["y"] + src_box["height"] / 2)
                    page.mouse.down()
                    page.mouse.move(x, y, steps=10)
                    page.mouse.up()

                page.evaluate("window.scrollTo(0, 0)")
                rows_before = item_order(page)
                last_uid = rows_before[-1].split(":", 1)[-1]
                first_row = page.locator("[data-show-step-row],[data-show-divider-row]").first
                first_box = first_row.bounding_box()
                drag(page.locator(f'[data-drag-item="{last_uid}"]'), first_box["x"] + 10, first_box["y"] + 1)
                page.wait_for_function(
                    "uid => { const rows=[...document.querySelectorAll('[data-show-step-row],[data-show-divider-row]')]; return (rows[0].dataset.showStepRow||rows[0].dataset.showDividerRow) === uid; }",
                    arg=last_uid)
                check("drag reorder of a structural row still works", item_order(page)[0].endswith(last_uid))
                page.keyboard.press("Control+z")
                page.wait_for_function(
                    "count => document.querySelectorAll('[data-show-step-row],[data-show-divider-row]').length === count",
                    arg=len(rows_before))

                check("no page-level horizontal overflow at 1280px", no_horizontal_overflow(page))
                page.screenshot(path=str(HERE / "review-1280-show.png"), full_page=True)

                # ------------------------------------------------------------
                # Inline step name -- desktop mouse + keyboard.
                # ------------------------------------------------------------
                page.locator('[data-show-step-row="11111111"]').click()
                title = page.locator('[data-show-step-name="11111111"]')
                check("bold inspector title shows the step name", title.inner_text().strip() == "alpha")
                title.click()
                name_input = page.locator('[data-show-step-name-input="11111111"]')
                check("click on title swaps in a focused single-line input",
                      name_input.count() == 1
                      and page.evaluate("document.activeElement === document.querySelector('[data-show-step-name-input]')"))
                name_input.fill("Renamed Alpha")
                page.keyboard.press("Enter")
                page.wait_for_selector('[data-show-step-name="11111111"]')
                check("Enter commits the new name",
                      page.locator('[data-show-step-name="11111111"]').inner_text().strip() == "Renamed Alpha")

                # Escape restores the prior value without committing.
                page.locator('[data-show-step-name="11111111"]').click()
                page.locator('[data-show-step-name-input="11111111"]').fill("should not stick")
                page.keyboard.press("Escape")
                page.wait_for_selector('[data-show-step-name="11111111"]')
                check("Escape restores the prior name",
                      page.locator('[data-show-step-name="11111111"]').inner_text().strip() == "Renamed Alpha")

                # Blur commits -- move focus to a sibling field in the same
                # step's editor (not another row/step, which would swap the
                # whole inspector to a different step and never re-show this
                # title at all).
                page.locator('[data-show-step-name="11111111"]').click()
                page.locator('[data-show-step-name-input="11111111"]').fill("Blurred Name")
                page.locator('[data-show-step-editor="11111111"] [data-duration-part="h"]').click()
                page.wait_for_selector('[data-show-step-name="11111111"]')
                check("blur commits the new name",
                      page.locator('[data-show-step-name="11111111"]').inner_text().strip() == "Blurred Name")

                # Blank commits to the untitled/null state.
                page.locator('[data-show-step-row="11111111"]').click()
                page.locator('[data-show-step-name="11111111"]').click()
                page.locator('[data-show-step-name-input="11111111"]').fill("")
                page.keyboard.press("Enter")
                page.wait_for_selector('[data-show-step-name="11111111"]')
                check("blank name commits to the Untitled step state",
                      page.locator('[data-show-step-name="11111111"]').inner_text().strip() == "Untitled step")

                # F2 opens edit while the title is keyboard-focused.
                page.locator('[data-show-step-name="11111111"]').focus()
                page.keyboard.press("F2")
                check("F2 opens inline edit on the focused title",
                      page.locator('[data-show-step-name-input="11111111"]').count() == 1)
                page.locator('[data-show-step-name-input="11111111"]').fill("F2 Named")
                page.keyboard.press("Enter")
                page.wait_for_selector('[data-show-step-name="11111111"]')
                check("committed name persists across reload",
                      page.locator('[data-show-step-name="11111111"]').inner_text().strip() == "F2 Named")
                page.reload()
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.locator('[data-show-step-row="11111111"]').click()
                page.wait_for_selector('[data-show-step-name="11111111"]')
                check("renamed step alias persists to disk",
                      page.locator('[data-show-step-name="11111111"]').inner_text().strip() == "F2 Named")

                # ------------------------------------------------------------
                # Narrow (768px): icon-only bar, touch rename.
                # ------------------------------------------------------------
                context.close()

                narrow_context = browser.new_context(
                    viewport={"width": 768, "height": 900}, has_touch=True)
                narrow = narrow_context.new_page()
                narrow_errors = []
                narrow.on("pageerror", lambda error: narrow_errors.append(str(error)))
                narrow.goto(base_url)
                narrow.wait_for_selector("#ws-status.online", state="attached")
                narrow.click("#tab-button-show")
                narrow.wait_for_selector('[data-show-step-row="11111111"]')

                narrow_bar = narrow.locator(".show-edit-bar")
                check("narrow layout hides the text label",
                      not narrow_bar.locator(
                          '[data-edit-bar-action="add-step"] .show-edit-bar-label').is_visible())
                narrow_box = narrow_bar.locator('[data-edit-bar-action="add-step"]').bounding_box()
                check("narrow icon-only buttons stay touch-sized (>=40px)",
                      narrow_box["width"] >= 40 and narrow_box["height"] >= 40, repr(narrow_box))
                narrow_aria = narrow_bar.locator(
                    '[data-edit-bar-action="add-step"]').get_attribute("aria-label")
                check("narrow icon-only button keeps its aria-label", bool(narrow_aria), repr(narrow_aria))
                check("no page-level horizontal overflow at 768px", no_horizontal_overflow(narrow))
                narrow.screenshot(path=str(HERE / "review-768-show.png"), full_page=True)

                narrow.locator('[data-show-step-row="11111111"]').tap()
                narrow.locator('[data-show-step-name="11111111"]').tap()
                narrow_input = narrow.locator('[data-show-step-name-input="11111111"]')
                check("tap on title opens inline edit on narrow/touch", narrow_input.count() == 1)
                narrow_input.fill("Touch Named")
                narrow.keyboard.press("Enter")
                narrow.wait_for_selector('[data-show-step-name="11111111"]')
                check("touch rename commits",
                      narrow.locator('[data-show-step-name="11111111"]').inner_text().strip() == "Touch Named")
                check("narrow client emitted no console/page errors", not narrow_errors, repr(narrow_errors))

                # ------------------------------------------------------------
                # Empty show: bar disables Duplicate/Delete, + Step appends
                # into an empty list.
                # ------------------------------------------------------------
                narrow.evaluate("""() => {
                    const select = document.querySelector('#show-switch-select');
                    select.value = 'empty-set';
                    select.dispatchEvent(new Event('change', {bubbles: true}));
                }""")
                narrow.click("#show-switch-load")
                narrow.wait_for_function("() => document.querySelector('.show-edit-bar') "
                                         "&& document.querySelectorAll('[data-show-step-row]').length === 0")
                empty_duplicate = narrow.locator('[data-edit-bar-action="duplicate"]')
                empty_delete = narrow.locator('[data-edit-bar-action="delete"]')
                check("empty show: Duplicate/Delete disabled (nothing to select)",
                      empty_duplicate.is_disabled() and empty_delete.is_disabled())
                narrow.locator('[data-edit-bar-action="add-step"]').click()
                narrow.wait_for_selector('[data-show-step-row]')
                check("empty show: + Step appends the first row",
                      narrow.locator('[data-show-step-row]').count() == 1)

                check("browser (wide) emitted no page errors", not page_errors, repr(page_errors))

                narrow_context.close()
                peer_context.close()
                browser.close()
        finally:
            stop(server)
            log.close()
        if FAILURES:
            print("\nserver log tail:\n", log_path.read_text(encoding="utf-8")[-4000:])

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
