#!/usr/bin/env python3
"""Real Dashboard + simfleet Playwright verification for show management (6b).

Covers: create a new show from the loaded state, add content, switch between
shows with persistence intact on both sides, switch-while-playing stops the
transport, rename, delete, active-show survival across a server restart, and
second-client convergence.
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
    (patch / "main.bin").write_bytes(b"show-management-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": 0.4, "facilitator": True},
        ],
        "cues": [], "caps": [], "slots": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Show management verifier",
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
            {"kind": "step", "uid": "11111111", "alias": "intro drone",
             "messages": [
                 {"uid": "aaaa0001", "alias": "gain up", "address": "/p/gain",
                  "args": [{"type": "f", "value": 0.6}], "target": ["all"]},
             ],
             "duration_s": 60.0, "play_count": 1,
             "then_actions": [{"type": "stop"}], "forward_sync": False},
        ],
    }
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows_dir / "opening-set.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


def server_args(http_port, listen_port, send_port, state_path, assets, patches, base_url):
    return [
        sys.executable, str(ROOT / "dashboard" / "server.py"),
        "--host", "127.0.0.1", "--port", str(http_port),
        "--listen-port", str(listen_port), "--send-port", str(send_port),
        "--osc-target", "127.0.0.1", "--state-file", str(state_path),
        "--assets-dir", str(assets), "--patches-dir", str(patches),
        "--public-url", base_url,
    ]


def open_show_tab(page, base_url):
    page.goto(base_url)
    page.wait_for_selector("#ws-status.online")
    page.click("#tab-button-show")
    page.wait_for_selector(".show-transport-strip")


def current_title(page):
    return page.locator(".show-transport-strip h2").inner_text().strip()


def select_names(page):
    return page.eval_on_selector_all(
        "#show-switch-select option", "options => options.map(option => option.value)")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-management-") as root:
        patches, assets, state_dir, manifest_path, state_path = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log_path = Path(root, "server.log")
        fleet_log_path = Path(root, "fleet.log")
        server_log = server_log_path.open("w", encoding="utf-8")
        fleet_log = fleet_log_path.open("w", encoding="utf-8")
        args = server_args(http_port, listen_port, send_port,
                           state_path, assets, patches, base_url)
        server = fleet = None
        prompt_text = {"value": ""}
        try:
            server = subprocess.Popen(args, cwd=ROOT, stdout=server_log,
                                      stderr=subprocess.STDOUT)
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
                    viewport={"width": 900, "height": 1100}, has_touch=True,
                    is_mobile=True, device_scale_factor=1,
                )
                page = context.new_page()
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def handle_dialog(dialog):
                    if dialog.type == "prompt":
                        dialog.accept(prompt_text["value"])
                    else:
                        dialog.accept()

                page.on("dialog", handle_dialog)

                page2 = context.new_page()
                page2.on("pageerror", lambda error: page_errors.append(str(error)))

                open_show_tab(page, base_url)
                open_show_tab(page2, base_url)
                page.wait_for_selector('.show-step-row[data-show-step-row="11111111"]')
                check("management cluster renders with the active show selected",
                      page.locator("#show-switch-select").input_value() == "opening-set"
                      and current_title(page) == "opening-set")

                # Create a new show; it becomes active and is empty.
                prompt_text["value"] = "second-set"
                page.click("#show-manage-new")
                page.wait_for_function(
                    "() => document.querySelector('.show-transport-strip h2')"
                    "?.textContent.trim() === 'second-set'")
                check("new show becomes the active show",
                      page.locator("#show-switch-select").input_value() == "second-set")
                check("new show starts empty with an add affordance",
                      page.locator(".show-step-row").count() == 0
                      and page.locator('[data-item-add-end="step"]').count() == 1)

                # Add content to the new show.
                page.click('[data-item-add-end="step"]')
                page.wait_for_selector(".show-step-row")

                # Switch back and forth; content persists on both sides.
                page.select_option("#show-switch-select", "opening-set")
                page.click("#show-switch-load")
                page.wait_for_selector('.show-step-row[data-show-step-row="11111111"]')
                check("switching restores the first show's content",
                      current_title(page) == "opening-set")
                page.select_option("#show-switch-select", "second-set")
                page.click("#show-switch-load")
                page.wait_for_function(
                    "() => document.querySelector('.show-transport-strip h2')"
                    "?.textContent.trim() === 'second-set'")
                page.wait_for_selector(".show-step-row")
                check("switching back restores the new show's added step",
                      page.locator(".show-step-row").count() == 1)

                # Switch while playing stops the transport (confirm accepted).
                page.click('.show-step-row [data-show-action="step_start"]')
                page.wait_for_function(
                    "() => document.querySelector('#show-playing-indicator')"
                    "?.textContent.startsWith('1 playing')")
                page.select_option("#show-switch-select", "opening-set")
                page.click("#show-switch-load")
                page.wait_for_selector('.show-step-row[data-show-step-row="11111111"]')
                page.wait_for_function(
                    "() => document.querySelector('#show-playing-indicator')"
                    "?.textContent.trim() === '0 playing'")
                check("switching while playing stops the transport",
                      page.locator("#show-playing-indicator").inner_text().strip()
                      == "0 playing")

                # Rename the active show.
                prompt_text["value"] = "opening-renamed"
                page.click("#show-manage-rename")
                page.wait_for_function(
                    "() => document.querySelector('.show-transport-strip h2')"
                    "?.textContent.trim() === 'opening-renamed'")
                names = select_names(page)
                check("rename keeps content and drops the old name",
                      "opening-renamed" in names and "opening-set" not in names
                      and page.locator(
                          '.show-step-row[data-show-step-row="11111111"]').count() == 1)

                # Delete a non-active show.
                page.select_option("#show-switch-select", "second-set")
                page.click("#show-manage-delete")
                page.wait_for_function(
                    "() => ![...document.querySelectorAll('#show-switch-select option')]"
                    ".some(option => option.value === 'second-set')")
                check("delete removes the show from the catalog",
                      current_title(page) == "opening-renamed")

                # Second client converges on the same active show.
                page2.wait_for_function(
                    "() => document.querySelector('.show-transport-strip h2')"
                    "?.textContent.trim() === 'opening-renamed'")
                check("second client agrees on the active show",
                      page2.locator("#show-switch-select").input_value()
                      == "opening-renamed")

                # Active show survives a server restart.
                time.sleep(1.6)  # debounced state save
                stop(server)
                server = subprocess.Popen(args, cwd=ROOT, stdout=server_log,
                                          stderr=subprocess.STDOUT)
                wait_http(base_url, server)
                open_show_tab(page, base_url)
                page.wait_for_selector('.show-step-row[data-show-step-row="11111111"]')
                check("active show survives a server restart",
                      current_title(page) == "opening-renamed"
                      and page.locator("#show-switch-select").input_value()
                      == "opening-renamed")

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

    failed = len(FAILURES)
    print(f"\n{failed} failure(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
