#!/usr/bin/env python3
"""Playwright + simfleet verification: the Show inspector's collapse toggle must
never overlap the edit bar's delete button (thread 19, stitch 01).

Defect (Bob, 2026-07-21): at narrow widths the expanded inspector's collapse
toggle rendered on top of the edit bar's delete button.

Assertions:

1. Narrow (900px) with the inspector expanded: the toggle's *effective* rect
   (visual box grown by its ``::after{inset:-8px}`` touch expansion) does not
   intersect the delete button's effective rect -- for a short inspector
   (divider focused) and a tall one (message with an LFO generator focused).
2. Same at 768px.
3. Wide (1280px): the toggle is contained within the inspector panel's rect and
   still does not intersect the delete button.
4. Retained light + dark screenshots of the narrow expanded state.

Playwright house rules honoured: ``#ws-status`` waited for with
state="attached"; non-active-panel elements likewise; all comparison rects
gathered in a SINGLE page.evaluate from one scroll state (gotcha 9); no
scroll_into_view_if_needed / actionability waits on Show rows; one type-aware
dialog handler; wait_for_function args passed via arg=.
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

DIVIDER_UID = "d0000001"
STEP_UID = "11111111"
LFO_MESSAGE_UID = "aaaa0002"


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
    state_dir = root / "sim-state"
    shows = root / "shows"
    patch = patches / "alpha"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"toggle-overlap-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [{"name": "gain", "type": "f", "min": 0, "max": 1,
                    "default": .4, "facilitator": True}],
        "cues": [{"id": "snap", "label": "Snap"}], "caps": [], "slots": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Toggle overlap verifier",
        "current_show": "overlap", "params_patch": "alpha",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "seats": {"0": {"id": 0, "name": "Front", "positions": [[1, 1]],
                        "groups": [], "bound": None, "patch": "alpha",
                        "params": {}}},
        "groups": {}, "next_group_id": 0,
    }
    messages = [
        {"uid": "aaaa0001", "alias": "fade", "address": "/p/gain",
         "target": ["all"],
         "args": [{"type": "f", "value": 1}, {"type": "s", "value": "5s"}]},
        {"uid": LFO_MESSAGE_UID, "alias": "wobble", "address": "/p/gain",
         "target": ["all"],
         "args": [{"type": "s", "value": "lfo"}, {"type": "s", "value": "sine"},
                  {"type": "f", "value": 0}, {"type": "f", "value": 1},
                  {"type": "s", "value": "2s"}]},
    ]
    items = [
        {"kind": "divider", "uid": DIVIDER_UID, "alias": "MOVEMENT ONE"},
        {"kind": "step", "uid": STEP_UID, "alias": "opening",
         "messages": messages, "duration_s": 10, "play_count": 1,
         "then_actions": [{"type": "stop"}]},
    ]
    for i in range(12):
        items.append({"kind": "step", "uid": f"{i:08d}", "alias": f"step {i}",
                      "messages": [], "duration_s": 5, "play_count": 1,
                      "then_actions": []})
    show = {"schema": 1, "name": "overlap", "items": items}
    (shows / "overlap.json").write_text(json.dumps(show, indent=2) + "\n",
                                        encoding="utf-8")
    state_path = root / "installation.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


# All comparison rects come out of this ONE evaluate (gotcha 9): the toggle's
# effective rect (grown by the negative ::after insets), the delete button's
# effective rect, and the inspector panel's rect -- from a single scroll state.
RECTS_JS = """() => {
    const num = (v) => { const n = parseFloat(v); return Number.isFinite(n) ? n : 0; };
    const eff = (el) => {
        if (!el) return null;
        const r = el.getBoundingClientRect();
        const a = getComputedStyle(el, '::after');
        const has = a.content && a.content !== 'none';
        const t = has ? num(a.top) : 0, b = has ? num(a.bottom) : 0;
        const l = has ? num(a.left) : 0, rr = has ? num(a.right) : 0;
        return {x: r.left + l, y: r.top + t,
                width: r.width - l - rr, height: r.height - t - b,
                rawX: r.left, rawY: r.top, rawW: r.width, rawH: r.height};
    };
    const plain = (el) => {
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return {x: r.left, y: r.top, width: r.width, height: r.height};
    };
    return {
        toggle: eff(document.querySelector('.show-inspector-toggle')),
        del: eff(document.querySelector('[data-edit-bar-action="delete"]')),
        panel: plain(document.querySelector('.show-inspector-panel')),
        scrollY: window.scrollY,
    };
}"""


def intersects(a, b):
    if not a or not b:
        return True  # missing element is a failure, not a pass
    return not (a["x"] + a["width"] <= b["x"] + .5
                or b["x"] + b["width"] <= a["x"] + .5
                or a["y"] + a["height"] <= b["y"] + .5
                or b["y"] + b["height"] <= a["y"] + .5)


def contains(outer, inner, slack=1.0):
    if not outer or not inner:
        return False
    return (inner["x"] >= outer["x"] - slack
            and inner["y"] >= outer["y"] - slack
            and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + slack
            and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + slack)


def open_show(page, base_url):
    page.goto(base_url)
    page.wait_for_selector("#ws-status.online", state="attached")
    page.click("#tab-button-show")
    page.wait_for_selector(f'[data-show-step-row="{STEP_UID}"]')


def focus_divider(page):
    page.eval_on_selector(f'[data-show-divider-row="{DIVIDER_UID}"]', "e => e.click()")
    page.wait_for_selector(f'[data-show-divider-editor="{DIVIDER_UID}"]', state="attached")


def focus_lfo_message(page):
    page.eval_on_selector(f'[data-show-message-focus="{LFO_MESSAGE_UID}"]', "e => e.click()")
    page.wait_for_selector(f'[data-show-message-editor="{LFO_MESSAGE_UID}"]', state="attached")
    page.wait_for_selector('[data-param-lfo="period"]', state="attached")


def assert_no_overlap(page, width, label):
    rects = page.evaluate(RECTS_JS)
    check(f"{width}px {label}: collapse toggle exists", rects["toggle"] is not None,
          repr(rects))
    check(f"{width}px {label}: delete button exists", rects["del"] is not None,
          repr(rects))
    check(f"{width}px {label}: toggle hit area does not intersect delete button",
          not intersects(rects["toggle"], rects["del"]), repr(rects))
    return rects


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-toggle-overlap-") as root:
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

                for width in (900, 768):
                    context = browser.new_context(
                        viewport={"width": width, "height": 900})
                    page = context.new_page()
                    page.on("pageerror",
                            lambda error, w=width: page_errors.append(f"{w}: {error}"))
                    page.on("dialog", lambda dialog: (
                        dialog.accept("x") if dialog.type == "prompt" else dialog.accept()))
                    open_show(page, base_url)

                    focus_divider(page)
                    short = assert_no_overlap(page, width, "short inspector (divider)")

                    focus_lfo_message(page)
                    tall = assert_no_overlap(page, width, "tall inspector (LFO message)")
                    check(f"{width}px: LFO inspector is taller than the divider inspector",
                          short["panel"] and tall["panel"]
                          and tall["panel"]["height"] > short["panel"]["height"],
                          repr((short["panel"], tall["panel"])))
                    check(f"{width}px: toggle sits inside the inspector panel",
                          contains(tall["panel"], {"x": tall["toggle"]["rawX"],
                                                   "y": tall["toggle"]["rawY"],
                                                   "width": tall["toggle"]["rawW"],
                                                   "height": tall["toggle"]["rawH"]}),
                          repr(tall))

                    if width == 900:
                        page.select_option("#theme-select", "dark")
                        page.wait_for_function(
                            "() => document.documentElement.getAttribute('data-theme') === 'dark'")
                        page.wait_for_timeout(150)
                        page.screenshot(path=str(HERE / "narrow-900-dark.png"),
                                        full_page=True)
                        page.select_option("#theme-select", "light")
                        page.wait_for_function(
                            "() => document.documentElement.getAttribute('data-theme') === 'light'")
                        page.wait_for_timeout(150)
                        page.screenshot(path=str(HERE / "narrow-900-light.png"),
                                        full_page=True)
                    context.close()

                # ---- Wide layout unchanged: toggle inside panel, no overlap. ----
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = context.new_page()
                page.on("pageerror", lambda error: page_errors.append(f"1280: {error}"))
                page.on("dialog", lambda dialog: (
                    dialog.accept("x") if dialog.type == "prompt" else dialog.accept()))
                open_show(page, base_url)

                focus_divider(page)
                wide_short = assert_no_overlap(page, 1280, "short inspector (divider)")
                check("1280px: toggle is contained by the inspector panel",
                      contains(wide_short["panel"],
                               {"x": wide_short["toggle"]["rawX"],
                                "y": wide_short["toggle"]["rawY"],
                                "width": wide_short["toggle"]["rawW"],
                                "height": wide_short["toggle"]["rawH"]}),
                      repr(wide_short))

                focus_lfo_message(page)
                wide_tall = assert_no_overlap(page, 1280, "tall inspector (LFO message)")
                check("1280px: toggle stays pinned to the panel's top-right",
                      wide_tall["toggle"] and wide_tall["panel"]
                      and abs((wide_tall["panel"]["x"] + wide_tall["panel"]["width"])
                              - (wide_tall["toggle"]["rawX"] + wide_tall["toggle"]["rawW"])) <= 12
                      and abs(wide_tall["toggle"]["rawY"] - wide_tall["panel"]["y"]) <= 12,
                      repr(wide_tall))

                heading_pad = page.evaluate(
                    """() => {
                        const el = document.querySelector(
                            '.show-inspector-panel > h3, .show-inspector-panel > .show-step-name');
                        return el ? getComputedStyle(el).paddingRight : null;
                    }""")
                check("1280px: inspector heading keeps its 34px toggle reservation",
                      heading_pad == "34px", repr(heading_pad))

                check("browser emitted no page errors", not page_errors, repr(page_errors))
                context.close()
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
