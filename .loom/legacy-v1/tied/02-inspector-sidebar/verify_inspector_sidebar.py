#!/usr/bin/env python3
"""Playwright + simfleet verification for the collapsible Show inspector sidebar.

Covers 02-inspector-sidebar: the inspector becomes a collapsible sidebar whose
footprint can never move the OSC consoles or the step list. Checks:

1. Footprint stability -- growing the inspector (many then-actions) leaves the
   #show-consoles and the step-list shell bounding rects untouched (same scroll
   state).
2. Collapse -> the step-list shell reclaims the width; expand -> width restored;
   the collapsed state survives a document re-render but a page reload resets to
   expanded.
3. Collapsed single click on a row selects silently (row gains .focused, sidebar
   stays collapsed); double-click on a step row and on a message pill expands the
   sidebar onto that item's inspector.
4. The toggle control is keyboard-focusable and operable (Enter/Space); its
   aria-expanded is correct collapsed and expanded.
5. 1280px + 768px layouts have no page-level horizontal overflow; light and dark
   screenshots retained.
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
    (patch / "main.bin").write_bytes(b"inspector-sidebar-verifier")
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
        "schema": 1, "name": "Inspector sidebar verifier",
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
            {"kind": "step", "uid": "11111111", "alias": "first step",
             "messages": [
                 {"uid": "aaaa0001", "alias": "gain up", "address": "/p/gain",
                  "args": [{"type": "f", "value": 0.61}], "target": ["all"]},
             ],
             "duration_s": 5, "play_count": 1,
             "then_actions": [], "forward_sync": False},
            {"kind": "step", "uid": "22222222", "alias": "second step",
             "messages": [
                 {"uid": "bbbb0001", "alias": "cue snap", "address": "/cue",
                  "args": [{"type": "s", "value": "snap"}], "target": ["all"]},
             ],
             "duration_s": 5, "play_count": 1,
             "then_actions": [], "forward_sync": False},
        ],
    }
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows_dir / "opening-set.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


def no_horizontal_overflow(page):
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def open_consoles(page):
    for kind in ("out", "in"):
        panel = page.locator(f'[data-console="{kind}"]')
        if not panel.evaluate("node => node.open"):
            panel.locator("summary").click()
    page.wait_for_function(
        """() => document.querySelector('[data-console="out"]').open
             && document.querySelector('[data-console="in"]').open""")


def anchored_rects(page):
    """All rects gathered from ONE scroll state (top) in a single evaluate."""
    return page.evaluate("""() => {
        window.scrollTo(0, 0);
        const rect = sel => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const box = el.getBoundingClientRect();
            return {top: box.top, left: box.left, width: box.width, height: box.height};
        };
        return {
            consoles: rect('#show-consoles'),
            list: rect('.show-list-shell'),
        };
    }""")


def close(a, b, tol=1):
    return a is not None and b is not None and abs(a - b) < tol


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-inspector-sidebar-") as root:
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
                "--devices", "2", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.12", "--boot-secs", "0.1",
                "--state-dir", str(state_dir), "--manifest", str(manifest_path),
                "--patches-dir", str(patches), "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page_errors = []

                # ------------------------------------------------------------
                # Desktop (1280px).
                # ------------------------------------------------------------
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = context.new_page()
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="11111111"]')
                open_consoles(page)

                # Focus a step so the inspector shows the then-actions editor.
                page.locator('[data-show-step-row="11111111"]').click()
                page.wait_for_selector(".show-inspector-panel .show-step-name")
                check("expanded sidebar has aria-expanded=true toggle",
                      page.locator(".show-inspector-toggle").get_attribute("aria-expanded") == "true")

                # ---- 1. Footprint stability while the inspector grows. ----
                before = anchored_rects(page)
                add_row = page.locator("[data-add-then-action]")
                target_rows = 14
                for _ in range(target_rows):
                    add_row.click()
                    page.wait_for_timeout(60)
                page.wait_for_function(
                    "(n) => document.querySelectorAll('.show-then-row').length >= n",
                    arg=target_rows)
                grown_panel = page.evaluate(
                    """() => {
                        const p = document.querySelector('.show-inspector-panel');
                        return {scrollH: p.scrollHeight, clientH: p.clientHeight};
                    }""")
                check("inspector content grew beyond the panel's capped height (scrolls internally)",
                      grown_panel["scrollH"] > grown_panel["clientH"], repr(grown_panel))
                after = anchored_rects(page)
                check("OSC consoles bounding rect unchanged while inspector grows",
                      close(before["consoles"]["top"], after["consoles"]["top"])
                      and close(before["consoles"]["left"], after["consoles"]["left"])
                      and close(before["consoles"]["width"], after["consoles"]["width"])
                      and close(before["consoles"]["height"], after["consoles"]["height"]),
                      repr((before["consoles"], after["consoles"])))
                check("step-list shell bounding rect unchanged while inspector grows",
                      close(before["list"]["top"], after["list"]["top"])
                      and close(before["list"]["height"], after["list"]["height"])
                      and close(before["list"]["width"], after["list"]["width"]),
                      repr((before["list"], after["list"])))

                # ---- 2. Collapse/expand reclaims width; state survival. ----
                expanded_list_width = anchored_rects(page)["list"]["width"]
                expanded_consoles = anchored_rects(page)["consoles"]
                page.locator(".show-inspector-toggle").click()
                page.wait_for_selector(".show-inspector-rail")
                collapsed = anchored_rects(page)
                check("collapse widens the step-list shell",
                      collapsed["list"]["width"] > expanded_list_width + 100,
                      repr((expanded_list_width, collapsed["list"]["width"])))
                check("collapsed rail reports aria-expanded=false",
                      page.locator(".show-inspector-rail").get_attribute("aria-expanded") == "false")
                check("consoles do not move when the sidebar collapses",
                      close(collapsed["consoles"]["top"], expanded_consoles["top"])
                      and close(collapsed["consoles"]["width"], expanded_consoles["width"]),
                      repr((expanded_consoles, collapsed["consoles"])))

                # State survives a document re-render (add a step via edit bar).
                before_add = page.locator(".show-step-row").count()
                page.locator('[data-edit-bar-action="add-step"]').click()
                page.wait_for_function(
                    "(n) => document.querySelectorAll('.show-step-row').length > n",
                    arg=before_add)
                check("collapsed state survives a document re-render",
                      page.locator(".show-inspector-rail").count() == 1
                      and page.locator(".show-inspector-panel").count() == 0)

                # Expand round-trip restores the list width.
                page.locator(".show-inspector-rail").click()
                page.wait_for_selector(".show-inspector-panel")
                restored = anchored_rects(page)
                check("expanding restores the step-list shell width",
                      close(restored["list"]["width"], expanded_list_width, tol=2),
                      repr((expanded_list_width, restored["list"]["width"])))

                # Reload resets to expanded (module-only state).
                page.reload()
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="11111111"]')
                check("page reload resets the sidebar to expanded",
                      page.locator(".show-inspector-panel").count() == 1
                      and page.locator(".show-inspector-rail").count() == 0)

                # ---- 3. Collapsed focus: single selects, double expands. ----
                page.locator(".show-inspector-toggle").click()
                page.wait_for_selector(".show-inspector-rail")
                page.locator('[data-show-step-row="22222222"]').click()
                page.wait_for_function(
                    """() => document.querySelector('[data-show-step-row="22222222"]')
                             .classList.contains('focused')""")
                check("collapsed single click selects the row silently (stays collapsed)",
                      page.locator(".show-inspector-rail").count() == 1
                      and page.locator(".show-inspector-panel").count() == 0)

                page.locator('[data-show-step-row="22222222"]').dblclick()
                page.wait_for_selector(".show-inspector-panel")
                panel_name = page.locator(".show-inspector-panel .show-step-name").inner_text()
                check("double-click a step row expands the sidebar onto that step",
                      "second step" in panel_name.lower(), repr(panel_name))

                # Collapse again, double-click a message pill -> message inspector.
                page.locator(".show-inspector-toggle").click()
                page.wait_for_selector(".show-inspector-rail")
                page.locator('[data-show-message-focus="bbbb0001"]').dblclick()
                page.wait_for_selector(".show-inspector-panel")
                check("double-click a message pill expands onto the message inspector",
                      page.locator('.show-inspector-panel [data-show-message-editor="bbbb0001"]').count() == 1)

                # ---- 4. Keyboard operability + aria correctness. ----
                page.locator(".show-inspector-toggle").focus()
                check("toggle button is keyboard-focusable",
                      page.evaluate(
                          "() => document.activeElement && document.activeElement.classList.contains('show-inspector-toggle')"))
                page.keyboard.press("Enter")
                page.wait_for_selector(".show-inspector-rail")
                check("Enter on the toggle collapses the sidebar",
                      page.locator(".show-inspector-rail").get_attribute("aria-expanded") == "false")
                page.locator(".show-inspector-rail").focus()
                page.keyboard.press("Space")
                page.wait_for_selector(".show-inspector-panel")
                check("Space on the rail expands the sidebar (aria-expanded=true)",
                      page.locator(".show-inspector-toggle").get_attribute("aria-expanded") == "true")

                check("no page-level horizontal overflow at 1280px expanded",
                      no_horizontal_overflow(page))
                page.locator(".show-inspector-toggle").click()
                page.wait_for_selector(".show-inspector-rail")
                check("no page-level horizontal overflow at 1280px collapsed",
                      no_horizontal_overflow(page))
                page.locator(".show-inspector-rail").click()
                page.wait_for_selector(".show-inspector-panel")

                # ---- 5. Themes retained. ----
                page.select_option("#theme-select", "dark")
                page.wait_for_function(
                    "() => document.documentElement.getAttribute('data-theme') === 'dark'")
                page.wait_for_timeout(150)
                page.screenshot(path=str(HERE / "review-1280-dark.png"), full_page=True)
                page.select_option("#theme-select", "light")
                page.wait_for_function(
                    "() => document.documentElement.getAttribute('data-theme') === 'light'")
                page.wait_for_timeout(150)
                page.screenshot(path=str(HERE / "review-1280-light.png"), full_page=True)
                page.select_option("#theme-select", "dark")
                page.wait_for_function(
                    "() => document.documentElement.getAttribute('data-theme') === 'dark'")
                context.close()

                # ------------------------------------------------------------
                # Narrow (768px): single-column, static; toggle still works;
                # no horizontal overflow.
                # ------------------------------------------------------------
                narrow_context = browser.new_context(
                    viewport={"width": 768, "height": 900}, has_touch=True)
                narrow = narrow_context.new_page()
                narrow.on("pageerror", lambda error: page_errors.append(f"narrow: {error}"))
                narrow.goto(base_url)
                narrow.wait_for_selector("#ws-status.online", state="attached")
                narrow.click("#tab-button-show")
                narrow.wait_for_selector('[data-show-step-row="11111111"]')
                narrow.locator('[data-show-step-row="11111111"]').click()
                narrow.wait_for_selector(".show-inspector-panel")
                stacked = narrow.evaluate("""() => {
                    const list = document.querySelector('.show-list-shell').getBoundingClientRect();
                    const shell = document.querySelector('.show-inspector-shell').getBoundingClientRect();
                    return {listBottom: list.bottom, shellTop: shell.top,
                            listWidth: list.width, shellWidth: shell.width};
                }""")
                check("768px stacks the inspector below the step list (single column)",
                      stacked["shellTop"] >= stacked["listBottom"] - 2, repr(stacked))
                check("768px toggle still collapses the sidebar",
                      (narrow.locator(".show-inspector-toggle").click() or True)
                      and (narrow.wait_for_selector(".show-inspector-rail") or True)
                      and narrow.locator(".show-inspector-rail").count() == 1)
                check("no page-level horizontal overflow at 768px",
                      no_horizontal_overflow(narrow))
                narrow.locator(".show-inspector-rail").click()
                narrow.wait_for_selector(".show-inspector-panel")
                narrow.screenshot(path=str(HERE / "review-768-inspector.png"), full_page=True)
                narrow_context.close()

                check("browser emitted no page errors across all widths", not page_errors,
                      repr(page_errors))
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
