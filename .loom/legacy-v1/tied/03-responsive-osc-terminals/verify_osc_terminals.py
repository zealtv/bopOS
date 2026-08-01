#!/usr/bin/env python3
"""Playwright + simfleet verification for the responsive Show OSC terminals.

Covers 03-responsive-osc-terminals: equal-width side-by-side columns at
wide/tablet widths (ratified breakpoint: 900px viewport width), outgoing-
then-incoming stacking below the breakpoint, a shared fixed ~320px expanded
panel height that never grows under sustained live traffic, independent
internal log scrolling, independent collapse/expand, retained filter/pause/
clear/count/auto-scroll controls, long-frame containment (no page-level
horizontal overflow), and light/dark contrast.
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
    (patch / "main.bin").write_bytes(b"osc-terminals-verifier")
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
        "schema": 1, "name": "OSC terminals verifier",
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
    long_arg = "x-frame-" + ("A" * 400)
    show = {
        "schema": 1, "name": "opening-set",
        "items": [
            {"kind": "step", "uid": "11111111", "alias": "console probe",
             "messages": [
                 {"uid": "aaaa0001", "alias": "gain up", "address": "/p/gain",
                  "args": [{"type": "f", "value": 0.61}], "target": ["all"]},
             ],
             "duration_s": 0.3, "play_count": 1,
             "then_actions": [], "forward_sync": False},
            {"kind": "step", "uid": "22222222", "alias": "long frame probe",
             "messages": [
                 {"uid": "bbbb0001", "alias": "long", "address": "/cue",
                  "args": [{"type": "s", "value": long_arg}], "target": ["all"]},
             ],
             "duration_s": 0.3, "play_count": 1,
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


def panel_rects(page):
    return page.evaluate("""() => {
        const rect = kind => {
            const el = document.querySelector(`[data-console="${kind}"]`);
            const box = el.getBoundingClientRect();
            return {top: box.top, left: box.left, width: box.width, height: box.height,
                    open: el.open};
        };
        return {out: rect('out'), in: rect('in')};
    }""")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-osc-terminals-") as root:
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
                # Desktop (1280px): equal columns, fixed height, stability,
                # independent scroll/collapse, controls, long frame, themes.
                # ------------------------------------------------------------
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = context.new_page()
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="11111111"]')

                open_consoles(page)
                page.wait_for_function(
                    """() => document.querySelector(
                         '[data-console="out"] [data-console-log]'
                       ).textContent.includes('/sync/ping')""")
                page.wait_for_function(
                    """() => document.querySelector(
                         '[data-console="in"] [data-console-log]'
                       ).textContent.includes('/sync/pong')""")

                rects = panel_rects(page)
                check("both panels open and equal top y-coordinate at 1280px",
                      rects["out"]["open"] and rects["in"]["open"]
                      and abs(rects["out"]["top"] - rects["in"]["top"]) < 1,
                      repr(rects))
                check("both panels share the same fixed expanded height at 1280px",
                      abs(rects["out"]["height"] - rects["in"]["height"]) < 1
                      and 300 <= rects["out"]["height"] <= 340,
                      repr(rects))
                check("panels sit in two side-by-side equal-width columns at 1280px",
                      rects["in"]["left"] > rects["out"]["left"]
                      and abs(rects["out"]["width"] - rects["in"]["width"]) < 2,
                      repr(rects))
                check("no page-level horizontal overflow at 1280px", no_horizontal_overflow(page))

                # -------------------------------------------------------
                # Stable panel height under sustained live traffic.
                # -------------------------------------------------------
                before_height = rects["out"]["height"]
                for _ in range(3):
                    page.locator(
                        '.show-step-row[data-show-step-row="11111111"] '
                        '[data-show-action="step_start"]').click()
                    page.wait_for_timeout(500)
                page.wait_for_timeout(1000)
                after_rects = panel_rects(page)
                check("panel height unchanged after sustained OSC traffic",
                      abs(after_rects["out"]["height"] - before_height) < 1
                      and abs(after_rects["in"]["height"] - before_height) < 1,
                      repr((before_height, after_rects)))

                # -------------------------------------------------------
                # Independent internal log scrolling.
                # -------------------------------------------------------
                page.wait_for_function("""() => {
                    const log = document.querySelector('[data-console="in"] [data-console-log]');
                    return log.scrollHeight > log.clientHeight;
                }""", timeout=8000)
                page.evaluate("""() => {
                    const log = document.querySelector('[data-console="out"] [data-console-log]');
                    log.scrollTop = 0;
                    log.dispatchEvent(new Event('scroll', {bubbles: true}));
                }""")
                page.wait_for_timeout(400)
                scroll_state = page.evaluate("""() => {
                    const outLog = document.querySelector('[data-console="out"] [data-console-log]');
                    const inLog = document.querySelector('[data-console="in"] [data-console-log]');
                    return {
                        outTop: outLog.scrollTop,
                        inNearBottom: inLog.scrollTop + inLog.clientHeight >= inLog.scrollHeight - 30,
                        docScrollTop: document.scrollingElement.scrollTop,
                    };
                }""")
                check("scrolling one log to top does not affect the other's auto-scroll",
                      scroll_state["outTop"] == 0 and scroll_state["inNearBottom"],
                      repr(scroll_state))
                check("scrolling a log does not scroll the page",
                      scroll_state["docScrollTop"] == 0, repr(scroll_state))
                geometry_after_scroll = panel_rects(page)
                check("panel geometry stable while a log is mid-scroll",
                      abs(geometry_after_scroll["out"]["height"] - before_height) < 1,
                      repr(geometry_after_scroll))

                # -------------------------------------------------------
                # Independent collapse/expand.
                # -------------------------------------------------------
                page.locator('[data-console="out"] summary').click()
                page.wait_for_function(
                    "() => !document.querySelector('[data-console=\"out\"]').open")
                collapsed_rects = panel_rects(page)
                check("collapsing outgoing leaves incoming open at full height",
                      not collapsed_rects["out"]["open"] and collapsed_rects["in"]["open"]
                      and collapsed_rects["in"]["height"] > 300, repr(collapsed_rects))
                check("collapsed outgoing panel shrinks to summary height",
                      collapsed_rects["out"]["height"] < 100, repr(collapsed_rects))
                page.locator('[data-console="out"] summary').click()
                page.wait_for_function(
                    "() => document.querySelector('[data-console=\"out\"]').open")
                reopened_rects = panel_rects(page)
                check("re-expanding outgoing restores the shared fixed height",
                      abs(reopened_rects["out"]["height"] - before_height) < 1,
                      repr(reopened_rects))

                # -------------------------------------------------------
                # Retained controls: filter, pause, clear, counts.
                # -------------------------------------------------------
                def log_text(kind):
                    return page.locator(f'[data-console="{kind}"] [data-console-log]').inner_text()

                def fill_filter(kind, value):
                    page.locator(f'[data-console="{kind}"] [data-console-filter]').fill(value)

                fill_filter("out", "/all/p/*")
                page.wait_for_function("""() => {
                    const lines = document.querySelector(
                      '[data-console="out"] [data-console-log]'
                    ).textContent.split('\\n').filter(Boolean);
                    return lines.length > 0 && lines.every(line => line.includes('/all/p/'));
                }""")
                check("wildcard filter narrows the outgoing view", True)
                fill_filter("out", "")

                fill_filter("in", "!/sync*")
                page.wait_for_function("""() => {
                    const lines = document.querySelector(
                      '[data-console="in"] [data-console-log]'
                    ).textContent.split('\\n').filter(Boolean);
                    return lines.length > 0 && lines.every(line => !line.includes('/sync/'));
                }""")
                check("negation filter hides matching incoming traffic", True)
                fill_filter("in", "")

                page.locator('[data-console="in"] [data-console-pause]').click()
                frozen = log_text("in")
                page.wait_for_timeout(1200)
                check("pause freezes the incoming view under live traffic",
                      log_text("in") == frozen)
                page.locator('[data-console="in"] [data-console-pause]').click()
                page.wait_for_function(
                    """(before) => document.querySelector(
                         '[data-console="in"] [data-console-log]'
                       ).textContent !== before""", arg=frozen)
                check("resume catches the incoming view back up", True)

                page.locator('[data-console="in"] [data-console-clear]').click()
                cleared = page.evaluate(
                    """() => document.querySelector(
                         '[data-console="in"] [data-console-log]').textContent""")
                check("clear empties the console", cleared == "", repr(cleared[-200:]))
                page.wait_for_function(
                    """() => document.querySelector(
                         '[data-console="in"] [data-console-log]'
                       ).textContent.length > 0""")
                check("cleared console refills from live traffic", True)

                out_count = page.locator('[data-console="out"] [data-console-count]').inner_text()
                check("outgoing count summary still populated", "shown" in out_count and "seen" in out_count,
                      out_count)

                pos_before_scroll_check = page.evaluate("""() => {
                    const log = document.querySelector('[data-console="in"] [data-console-log]');
                    return log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
                }""")
                check("incoming log auto-scrolls to bottom by default", pos_before_scroll_check)

                # -------------------------------------------------------
                # Long OSC frame stays contained; no page-level overflow.
                # -------------------------------------------------------
                page.locator(
                    '.show-step-row[data-show-step-row="22222222"] '
                    '[data-show-action="step_start"]').click()
                page.wait_for_function(
                    """() => document.querySelector(
                         '[data-console="out"] [data-console-log]'
                       ).textContent.includes('x-frame-')""")
                check("no page-level horizontal overflow after a very long OSC frame",
                      no_horizontal_overflow(page))
                long_frame_rects = panel_rects(page)
                check("panel geometry stable after a very long OSC frame",
                      abs(long_frame_rects["out"]["height"] - before_height) < 1,
                      repr(long_frame_rects))

                page.screenshot(path=str(HERE / "review-1280-dark.png"), full_page=True)

                # -------------------------------------------------------
                # Theme contrast: dark (default) already captured; light next.
                # -------------------------------------------------------
                page.select_option("#theme-select", "light")
                page.wait_for_function(
                    "() => document.documentElement.getAttribute('data-theme') === 'light'")
                page.wait_for_timeout(150)
                page.screenshot(path=str(HERE / "review-1280-light.png"), full_page=True)
                light_colors = page.evaluate("""() => {
                    const log = document.querySelector('[data-console="out"] [data-console-log]');
                    const style = getComputedStyle(log);
                    return {bg: style.backgroundColor, fg: style.color};
                }""")
                check("light theme console log has distinct background/text colors",
                      light_colors["bg"] != light_colors["fg"], repr(light_colors))
                page.select_option("#theme-select", "dark")
                page.wait_for_function(
                    "() => document.documentElement.getAttribute('data-theme') === 'dark'")
                page.wait_for_timeout(150)
                dark_colors = page.evaluate("""() => {
                    const log = document.querySelector('[data-console="out"] [data-console-log]');
                    const style = getComputedStyle(log);
                    return {bg: style.backgroundColor, fg: style.color};
                }""")
                check("dark theme console log has distinct background/text colors",
                      dark_colors["bg"] != dark_colors["fg"], repr(dark_colors))
                check("light and dark themes render visibly different console backgrounds",
                      light_colors["bg"] != dark_colors["bg"], repr((light_colors, dark_colors)))

                context.close()

                # ------------------------------------------------------------
                # Tablet (1024px): still two columns, consistent with the
                # 900px breakpoint.
                # ------------------------------------------------------------
                tablet_context = browser.new_context(viewport={"width": 1024, "height": 900})
                tablet = tablet_context.new_page()
                tablet.on("pageerror", lambda error: page_errors.append(f"tablet: {error}"))
                tablet.goto(base_url)
                tablet.wait_for_selector("#ws-status.online", state="attached")
                tablet.click("#tab-button-show")
                tablet.wait_for_selector('[data-show-step-row="11111111"]')
                open_consoles(tablet)
                tablet_rects = panel_rects(tablet)
                check("1024px (>=900px breakpoint) keeps two side-by-side equal columns",
                      abs(tablet_rects["out"]["top"] - tablet_rects["in"]["top"]) < 1
                      and tablet_rects["in"]["left"] > tablet_rects["out"]["left"]
                      and abs(tablet_rects["out"]["width"] - tablet_rects["in"]["width"]) < 2,
                      repr(tablet_rects))
                check("no page-level horizontal overflow at 1024px", no_horizontal_overflow(tablet))
                tablet_context.close()

                # ------------------------------------------------------------
                # Narrow (768px): stacked, outgoing above incoming, full width.
                # ------------------------------------------------------------
                narrow_context = browser.new_context(
                    viewport={"width": 768, "height": 900}, has_touch=True)
                narrow = narrow_context.new_page()
                narrow.on("pageerror", lambda error: page_errors.append(f"narrow: {error}"))
                narrow.goto(base_url)
                narrow.wait_for_selector("#ws-status.online", state="attached")
                narrow.click("#tab-button-show")
                narrow.wait_for_selector('[data-show-step-row="11111111"]')
                open_consoles(narrow)
                narrow_rects = panel_rects(narrow)
                check("768px stacks outgoing above incoming (source order)",
                      narrow_rects["in"]["top"] > narrow_rects["out"]["top"] + narrow_rects["out"]["height"] - 2,
                      repr(narrow_rects))
                narrow_container_width = narrow.evaluate(
                    "() => document.getElementById('show-consoles').getBoundingClientRect().width")
                check("stacked panels each span the full container width at 768px",
                      abs(narrow_rects["out"]["width"] - narrow_container_width) < 2
                      and abs(narrow_rects["in"]["width"] - narrow_container_width) < 2,
                      repr((narrow_rects, narrow_container_width)))
                check("both stacked panels share the same fixed expanded height at 768px",
                      abs(narrow_rects["out"]["height"] - narrow_rects["in"]["height"]) < 1
                      and 300 <= narrow_rects["out"]["height"] <= 340, repr(narrow_rects))
                check("no page-level horizontal overflow at 768px", no_horizontal_overflow(narrow))
                narrow.screenshot(path=str(HERE / "review-768-stacked.png"), full_page=True)
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
