#!/usr/bin/env python3
"""Focused Playwright verification for pointer drag and keyboard Show editing."""

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
    root = Path(root)
    patches = root / "patches"
    assets = root / "assets"
    shows = root / "shows"
    patch = patches / "alpha"
    patch.mkdir(parents=True)
    assets.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"show-drag-editing")
    (patch / "bopos.patch.json").write_text(json.dumps({
        "engine": "test", "entrypoint": "main.bin",
        "params": [{"name": "gain", "type": "f", "min": 0, "max": 1,
                    "default": .4, "facilitator": True}],
        "cues": [], "caps": [], "slots": [],
    }), encoding="utf-8")
    state = {
        "schema": 1, "name": "Show drag editing verifier",
        "current_show": "opening-set", "params_patch": "alpha",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "seats": {}, "groups": {}, "next_group_id": 0,
    }

    def message(uid, alias, value):
        return {"uid": uid, "alias": alias, "address": "/p/gain",
                "args": [{"type": "f", "value": value}], "target": ["all"]}

    show = {"schema": 1, "name": "opening-set", "items": [
        {"kind": "step", "uid": "11111111", "alias": "alpha",
         "messages": [message("aaaa0001", "one", .1),
                      message("aaaa0002", "two", .2),
                      message("aaaa0003", "three", .3)],
         "duration_s": 5, "play_count": 1, "then_actions": [{"type": "stop"}]},
        {"kind": "step", "uid": "22222222", "alias": "bravo",
         "messages": [message("bbbb0001", "four", .4)],
         "duration_s": 5, "play_count": 1, "then_actions": [{"type": "stop"}]},
        {"kind": "divider", "uid": "dddd0001"},
        {"kind": "step", "uid": "33333333", "alias": "charlie",
         "messages": [], "duration_s": 5, "play_count": 1,
         "then_actions": [{"type": "stop"}]},
    ]}
    state_path = root / "installation.json"
    show_path = shows / "opening-set.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    show_path.write_text(json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_path, show_path


def drag(page, source, x, y):
    bounds = source.bounding_box()
    page.mouse.move(bounds["x"] + bounds["width"] / 2,
                    bounds["y"] + bounds["height"] / 2)
    page.mouse.down()
    page.mouse.move(x, y, steps=10)
    page.mouse.up()


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-drag-") as root:
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
                page = browser.new_page(viewport={"width": 1100, "height": 900})
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="11111111"]')

                def pill_order(step_uid):
                    return page.locator(
                        f'[data-show-step-row="{step_uid}"] [data-drag-message]').evaluate_all(
                            "nodes => nodes.map(node => node.dataset.dragMessage)")

                def item_order():
                    return page.locator(
                        "[data-show-step-row],[data-show-divider-row]").evaluate_all(
                            "nodes => nodes.map(node => node.dataset.showStepRow || `div:${node.dataset.showDividerRow}`)")

                first = page.locator('[data-drag-message="aaaa0001"]')
                first_box = first.bounding_box()
                drag(page, page.locator('[data-drag-message="aaaa0003"]'),
                     first_box["x"] + 2, first_box["y"] + first_box["height"] / 2)
                page.wait_for_function(
                    "() => document.querySelector('[data-show-step-row=\"11111111\"] [data-drag-message]')?.dataset.dragMessage === 'aaaa0003'")
                check("message drag reorders within a step",
                      pill_order("11111111") == ["aaaa0003", "aaaa0001", "aaaa0002"],
                      repr(pill_order("11111111")))

                target_row = page.locator('[data-show-step-row="22222222"]')
                target_box = target_row.bounding_box()
                drag(page, page.locator('[data-drag-message="aaaa0002"]'),
                     target_box["x"] + target_box["width"] * .72,
                     target_box["y"] + target_box["height"] / 2)
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-show-step-row=\"22222222\"] [data-drag-message]').length === 2")
                check("message drag moves between steps",
                      pill_order("11111111") == ["aaaa0003", "aaaa0001"]
                      and pill_order("22222222") == ["bbbb0001", "aaaa0002"],
                      repr((pill_order("11111111"), pill_order("22222222"))))

                first_row = page.locator('[data-show-step-row="11111111"]')
                first_row_box = first_row.bounding_box()
                drag(page, page.locator('[data-drag-item="33333333"]'),
                     first_row_box["x"] + 10, first_row_box["y"] + 1)
                page.wait_for_function(
                    "() => document.querySelector('[data-show-step-row]')?.dataset.showStepRow === '33333333'")
                check("step handle drags a step above another",
                      item_order()[0] == "33333333", repr(item_order()))

                bravo = page.locator('[data-show-step-row="22222222"]')
                bravo_box = bravo.bounding_box()
                drag(page, page.locator('[data-drag-item="dddd0001"]'),
                     bravo_box["x"] + 10, bravo_box["y"] + bravo_box["height"] - 1)
                page.wait_for_function(
                    "() => { const rows=[...document.querySelectorAll('[data-show-step-row],[data-show-divider-row]')]; return rows.findIndex(r=>r.dataset.showDividerRow==='dddd0001') === rows.findIndex(r=>r.dataset.showStepRow==='22222222') + 1; }")
                check("divider handle uses the same reorder model", True)

                page.locator('[data-drag-message="aaaa0001"]').click()
                removed = page.locator("[data-message-copy],[data-message-cut],"
                                       "[data-message-move],[data-message-move-step],"
                                       "[data-message-delete],[data-paste-message],"
                                       "[data-item-move]").count()
                check("retired edit and move buttons are absent", removed == 0, str(removed))

                page.keyboard.press("Control+x")
                page.wait_for_function(
                    "() => !document.querySelector('[data-drag-message=\"aaaa0001\"]')")
                page.locator('[data-show-step-row="22222222"]').focus()
                page.keyboard.press("Control+v")
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-show-step-row=\"22222222\"] [data-drag-message]').length === 3")
                check("keyboard cut and paste moves message content",
                      "one" in target_row.inner_text().lower())

                peer = browser.new_page(viewport={"width": 900, "height": 760})
                peer.on("pageerror", lambda error: page_errors.append(f"peer: {error}"))
                peer.goto(base_url)
                peer.wait_for_selector("#ws-status.online")
                peer.click("#tab-button-show")
                peer.wait_for_selector('[data-drag-message="bbbb0001"]')
                page.locator('[data-drag-message="bbbb0001"]').focus()
                page.keyboard.press("Delete")
                page.wait_for_function(
                    "() => !document.querySelector('[data-drag-message=\"bbbb0001\"]')")
                peer.wait_for_function(
                    "() => !document.querySelector('[data-drag-message=\"bbbb0001\"]')")
                check("keyboard delete removes the focused message", True)
                page.keyboard.press("Control+z")
                page.wait_for_selector('[data-drag-message="bbbb0001"]')
                peer.wait_for_selector('[data-drag-message="bbbb0001"]')
                check("Ctrl+Z restores the last global edit for both clients", True)

                before_reload = (item_order(), pill_order("11111111"), pill_order("22222222"))
                page.screenshot(path=str(HERE / "drag-editing.png"), full_page=False)
                page.reload()
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="33333333"]')
                after_reload = (item_order(), pill_order("11111111"), pill_order("22222222"))
                check("drag and keyboard edits persist across reload",
                      after_reload == before_reload,
                      repr({"before": before_reload, "after": after_reload}))
                saved = json.loads(show_path.read_text(encoding="utf-8"))
                check("persisted document starts with the dragged step",
                      saved["items"][0]["uid"] == "33333333")
                check("browser emitted no page errors", not page_errors, repr(page_errors))
                peer.close()
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
