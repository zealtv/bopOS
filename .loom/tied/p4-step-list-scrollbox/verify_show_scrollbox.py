#!/usr/bin/env python3
"""Real Dashboard + simfleet verification for the Show step-list scroll box."""

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
    shows_dir = Path(root, "shows")
    patch = patches / "alpha"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows_dir.mkdir()
    (patch / "main.bin").write_bytes(b"show-scrollbox-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin", "params": [],
        "cues": [], "caps": [], "slots": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Show scrollbox verifier", "current_show": "long-show",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha", "seats": {}, "groups": {}, "next_group_id": 0,
    }
    items = [{
        "kind": "step", "uid": f"{index:08x}", "alias": f"Step {index + 1}",
        "messages": [], "duration_s": 20.0, "play_count": 1,
        "then_actions": [{"type": "stop"}],
    } for index in range(30)]
    show = {"schema": 1, "name": "long-show", "items": items}
    state_path = Path(root, "installation.json")
    show_path = shows_dir / "long-show.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    show_path.write_text(json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-scrollbox-") as root:
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
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 768, "height": 1024}, has_touch=True,
                    is_mobile=True, device_scale_factor=1,
                )
                page = context.new_page()
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def handle_dialog(dialog):
                    dialog.accept("") if dialog.type == "prompt" else dialog.accept()

                page.on("dialog", handle_dialog)
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                page.wait_for_selector('.show-step-row[data-show-step-row="00000000"]')

                console_state = page.evaluate("""() => [...document.querySelectorAll('.show-console')].map(panel => ({
                    open: panel.open,
                    count: panel.querySelector('[data-console-count]').value,
                }))""")
                check("both consoles start collapsed with zero counters",
                      len(console_state) == 2
                      and all(not entry["open"] and entry["count"] == "0 shown · 0 seen"
                              for entry in console_state), repr(console_state))
                fleet = subprocess.Popen([
                    sys.executable, str(ROOT / "tools" / "simfleet.py"),
                    "--devices", "1", "--target", "127.0.0.1",
                    "--report-port", str(listen_port), "--cmd-port", str(send_port),
                    "--hb-interval", "0.2", "--boot-secs", "0.2",
                    "--state-dir", str(state_dir), "--manifest", str(manifest_path),
                    "--patches-dir", str(patches), "--assets-dir", str(assets),
                ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

                initial = page.evaluate("""() => {
                    const box = document.querySelector('.show-rows-box');
                    const add = document.querySelector('.show-add-bar').getBoundingClientRect();
                    const transport = document.querySelector('.show-transport-strip').getBoundingClientRect();
                    return {
                      scrollHeight: box.scrollHeight, clientHeight: box.clientHeight,
                      addY: add.y, addBottom: add.bottom,
                      transportTop: transport.top, transportBottom: transport.bottom,
                      viewportHeight: innerHeight,
                    };
                }""")
                check("30 rows scroll inside the fixed-height rows box",
                      initial["scrollHeight"] > initial["clientHeight"], json.dumps(initial))
                check("add bar and transport are fully inside the viewport",
                      initial["addY"] >= 0 and initial["addBottom"] <= initial["viewportHeight"]
                      and initial["transportTop"] >= 0
                      and initial["transportBottom"] <= initial["viewportHeight"],
                      json.dumps(initial))

                old_uids = page.locator("[data-show-step-row]").evaluate_all(
                    "rows => rows.map(row => row.dataset.showStepRow)")
                page.locator('[data-item-add-end="step"]').click()
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-show-step-row]').length === 31")
                new_uids = page.locator("[data-show-step-row]").evaluate_all(
                    "rows => rows.map(row => row.dataset.showStepRow)")
                new_uid = next(uid for uid in new_uids if uid not in old_uids)
                after_add = page.evaluate("""(uid) => {
                    const box = document.querySelector('.show-rows-box').getBoundingClientRect();
                    const row = document.querySelector(`[data-show-step-row="${uid}"]`).getBoundingClientRect();
                    const add = document.querySelector('.show-add-bar').getBoundingClientRect();
                    return {addY: add.y, rowTop: row.top, rowBottom: row.bottom,
                            boxTop: box.top, boxBottom: box.bottom,
                            focused: document.querySelector(`[data-show-step-row="${uid}"]`).classList.contains('focused')};
                }""", new_uid)
                check("adding a step does not move the add bar",
                      abs(after_add["addY"] - initial["addY"]) <= 1,
                      json.dumps(after_add))
                check("the newly focused step is scrolled into the rows box",
                      after_add["focused"] and after_add["rowTop"] >= after_add["boxTop"]
                      and after_add["rowBottom"] <= after_add["boxBottom"],
                      json.dumps(after_add))

                handle = page.locator(".show-rows-resize")
                handle_box = handle.bounding_box()
                before_height = page.locator(".show-rows-box").evaluate("box => box.clientHeight")
                page.mouse.move(handle_box["x"] + handle_box["width"] / 2,
                                handle_box["y"] + handle_box["height"] / 2)
                page.mouse.down()
                page.mouse.move(handle_box["x"] + handle_box["width"] / 2,
                                handle_box["y"] + handle_box["height"] / 2 + 120,
                                steps=8)
                page.mouse.up()
                after_height = page.locator(".show-rows-box").evaluate("box => box.clientHeight")
                check("pointer handle grows the rows box by about 120 px",
                      110 <= after_height - before_height <= 130,
                      f"before={before_height}, after={after_height}")

                page.locator(
                    f'.show-step-row[data-show-step-row="{new_uid}"] '
                    '[data-show-action="step_start"]').click()
                page.wait_for_selector(
                    f'.show-step-row[data-show-step-row="{new_uid}"].show-step-playing')
                page.evaluate("document.querySelector('.show-rows-box').scrollTop = 180")
                before_tick = page.evaluate("""() => ({
                    height: document.querySelector('.show-rows-box').clientHeight,
                    scrollTop: document.querySelector('.show-rows-box').scrollTop,
                })""")
                page.wait_for_timeout(750)
                after_tick = page.evaluate("""() => ({
                    height: document.querySelector('.show-rows-box').clientHeight,
                    scrollTop: document.querySelector('.show-rows-box').scrollTop,
                })""")
                check("resize height survives a later countdown render",
                      abs(after_tick["height"] - before_tick["height"]) <= 1,
                      json.dumps({"before": before_tick, "after": after_tick}))
                check("internal scroll position survives a later countdown render",
                      abs(after_tick["scrollTop"] - before_tick["scrollTop"]) <= 1,
                      json.dumps({"before": before_tick, "after": after_tick}))

                page.locator('.show-console[data-console="out"] summary').click()
                max_height = page.locator(
                    '.show-console[data-console="out"] [data-console-log]').evaluate(
                        "log => getComputedStyle(log).maxHeight")
                check("an opened console uses the 240 px default log maximum",
                      max_height == "240px", max_height)
                page.reload()
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                page.wait_for_selector(".show-rows-box")
                check("reload restores both consoles collapsed",
                      page.locator(".show-console[open]").count() == 0)

                width = page.evaluate("""() => ({
                    scrollWidth: document.documentElement.scrollWidth,
                    innerWidth: window.innerWidth,
                })""")
                check("page has no horizontal overflow at 768 px",
                      width["scrollWidth"] <= width["innerWidth"], json.dumps(width))
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
