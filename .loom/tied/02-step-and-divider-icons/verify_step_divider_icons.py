#!/usr/bin/env python3
"""Playwright + simfleet verification for the step/divider glyph fix (stitch 02).

Both edit-bar "add" buttons now carry an inline SVG: a plus followed by a shape
naming what is added (rounded rect = step, horizontal rule = divider), so the
additive sense survives label-less rendering at narrow widths.

Covers:

1. Both buttons still resolve by accessible name (`Add step`, `Add divider`) at
   1280px and 768px.
2. Clicking `Add step` adds a step row; clicking `Add divider` adds a divider
   row -- the right item kind each time, read back from the DOM.
3. Each button's glyph span contains an `svg`, both SVGs are non-empty and
   distinct from each other; both inherit currentColor.
4. At 768px (labels hidden) both buttons are visible, do not overlap their
   neighbours, and the edit bar produces no horizontal page overflow.
5. Retained screenshots of the edit bar at 1280 and 768, light and dark.

Playwright house rules honoured: non-active-panel elements waited for with
state="attached"; `#ws-status` waited for attached; no scroll_into_view /
actionability waits on Show rows -- rects gathered in a single page.evaluate
from ONE scroll state; one type-aware dialog handler; wait_for_function args
passed via arg=.
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
    (patch / "main.bin").write_bytes(b"step-divider-icons-verifier")
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
        "schema": 1, "name": "Glyph verifier",
        "current_show": "glyph-set",
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
    items = []
    for i in range(4):
        items.append({
            "kind": "step", "uid": f"{i:08d}", "alias": f"step {i}",
            "messages": [], "duration_s": 5, "play_count": 1,
            "then_actions": [],
        })
    show = {"schema": 1, "name": "glyph-set", "items": items}
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows_dir / "glyph-set.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


def no_horizontal_overflow(page):
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def dialog_handler(dialog):
    # One type-aware handler: prompts answer with text, everything else accepts.
    if dialog.type == "prompt":
        dialog.accept("glyph")
    else:
        dialog.accept()


def glyph_info(page):
    """Per-button glyph markup + computed colour, in one evaluate."""
    return page.evaluate(
        """() => {
            const out = {};
            for (const action of ['add-step', 'add-divider']) {
                const btn = document.querySelector(`[data-edit-bar-action="${action}"]`);
                if (!btn) { out[action] = null; continue; }
                const span = btn.querySelector('.show-edit-bar-glyph');
                const svg = span ? span.querySelector('svg') : null;
                out[action] = {
                    ariaLabel: btn.getAttribute('aria-label'),
                    title: btn.getAttribute('title'),
                    spanHidden: span ? span.getAttribute('aria-hidden') : null,
                    hasSvg: !!svg,
                    svg: svg ? svg.outerHTML : null,
                    shapes: svg ? svg.querySelectorAll('path, rect, line, circle').length : 0,
                    stroke: svg ? getComputedStyle(svg).stroke : null,
                    color: getComputedStyle(btn).color,
                    glyphWidth: span ? getComputedStyle(span).width : null,
                };
            }
            return out;
        }""")


def row_kinds(page):
    return page.evaluate(
        """() => [...document.querySelectorAll('[data-show-step-row],[data-show-divider-row]')]
                 .map(el => el.hasAttribute('data-show-divider-row') ? 'divider' : 'step')""")


def edit_bar_layout(page):
    """All edit-bar button rects from ONE scroll state, plus overflow flags."""
    return page.evaluate(
        """() => {
            const bar = document.querySelector('.show-edit-bar');
            if (!bar) return null;
            const btns = [...bar.querySelectorAll('[data-edit-bar-action]')].map(b => {
                const r = b.getBoundingClientRect();
                const cs = getComputedStyle(b);
                return {
                    action: b.dataset.editBarAction,
                    x: r.x, y: r.y, w: r.width, h: r.height,
                    right: r.right, bottom: r.bottom,
                    visible: r.width > 0 && r.height > 0 &&
                             cs.visibility !== 'hidden' && cs.display !== 'none',
                };
            });
            return {
                btns,
                barOverflows: bar.scrollWidth > bar.clientWidth + 1,
                barW: bar.clientWidth, barScrollW: bar.scrollWidth,
            };
        }""")


def overlaps(a, b):
    return not (a["right"] <= b["x"] + 0.5 or b["right"] <= a["x"] + 0.5
                or a["bottom"] <= b["y"] + 0.5 or b["bottom"] <= a["y"] + 0.5)


def check_names_and_glyphs(page, width):
    for name in ("Add step", "Add divider"):
        loc = page.get_by_role("button", name=name, exact=True)
        check(f"{width}px: button resolves by accessible name {name!r}",
              loc.count() == 1, f"count={loc.count()}")

    info = glyph_info(page)
    step, div = info.get("add-step"), info.get("add-divider")
    check(f"{width}px: add-step glyph span contains an svg",
          bool(step and step["hasSvg"]), repr(step))
    check(f"{width}px: add-divider glyph span contains an svg",
          bool(div and div["hasSvg"]), repr(div))
    check(f"{width}px: add-step svg is non-empty (>=2 shapes)",
          bool(step and step["shapes"] >= 2), repr(step and step["shapes"]))
    check(f"{width}px: add-divider svg is non-empty (>=2 shapes)",
          bool(div and div["shapes"] >= 2), repr(div and div["shapes"]))
    check(f"{width}px: the two svgs are distinct",
          bool(step and div and step["svg"] and div["svg"] and step["svg"] != div["svg"]),
          repr((step and step["svg"], div and div["svg"])))
    check(f"{width}px: glyph spans stay aria-hidden",
          bool(step and div and step["spanHidden"] == "true" and div["spanHidden"] == "true"),
          repr((step and step["spanHidden"], div and div["spanHidden"])))
    check(f"{width}px: svg strokes resolve to the button's currentColor",
          bool(step and div and step["stroke"] == step["color"]
               and div["stroke"] == div["color"]),
          repr((step and (step["stroke"], step["color"]),
                div and (div["stroke"], div["color"]))))
    check(f"{width}px: glyph slot widened to 20px",
          bool(step and step["glyphWidth"] == "20px"), repr(step and step["glyphWidth"]))
    return info


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-glyph-icons-") as root:
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

                # ---------------------------------------------------------
                # Desktop (1280px): names, glyphs, and behaviour.
                # ---------------------------------------------------------
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = context.new_page()
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.on("dialog", dialog_handler)
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="00000000"]')

                check_names_and_glyphs(page, 1280)

                before = row_kinds(page)
                check("fixture starts as 4 step rows, no dividers",
                      before == ["step"] * 4, repr(before))

                # ---- Add step adds a step row. ----
                page.get_by_role("button", name="Add step", exact=True).click()
                page.wait_for_function(
                    "(n) => document.querySelectorAll("
                    "'[data-show-step-row],[data-show-divider-row]').length === n",
                    arg=len(before) + 1)
                after_step = row_kinds(page)
                check("Add step appended exactly one row",
                      len(after_step) == len(before) + 1, repr(after_step))
                added_step = [k for k in after_step if k == "step"]
                check("Add step added a STEP row (no divider appeared)",
                      len(added_step) == 5 and after_step.count("divider") == 0,
                      repr(after_step))

                # ---- Add divider adds a divider row. ----
                page.get_by_role("button", name="Add divider", exact=True).click()
                page.wait_for_function(
                    "(n) => document.querySelectorAll("
                    "'[data-show-step-row],[data-show-divider-row]').length === n",
                    arg=len(after_step) + 1)
                after_div = row_kinds(page)
                check("Add divider appended exactly one row",
                      len(after_div) == len(after_step) + 1, repr(after_div))
                check("Add divider added a DIVIDER row (step count unchanged)",
                      after_div.count("divider") == 1 and after_div.count("step") == 5,
                      repr(after_div))

                layout_1280 = edit_bar_layout(page)
                check("1280px: all four edit-bar buttons visible",
                      layout_1280 and len(layout_1280["btns"]) == 4
                      and all(b["visible"] for b in layout_1280["btns"]),
                      repr(layout_1280))
                check("no page-level horizontal overflow at 1280px",
                      no_horizontal_overflow(page))

                # ---- Light + dark screenshots at 1280 (edit bar cropped). ----
                for theme in ("dark", "light"):
                    page.select_option("#theme-select", theme)
                    page.wait_for_function(
                        "(t) => document.documentElement.getAttribute('data-theme') === t",
                        arg=theme)
                    page.wait_for_timeout(150)
                    page.screenshot(path=str(HERE / f"review-1280-{theme}.png"),
                                    full_page=True)
                    page.locator(".show-edit-bar").screenshot(
                        path=str(HERE / f"edit-bar-1280-{theme}.png"))
                context.close()

                # ---------------------------------------------------------
                # Narrow (768px): labels hidden, glyphs only.
                # ---------------------------------------------------------
                narrow = browser.new_context(
                    viewport={"width": 768, "height": 900}, has_touch=True)
                np_ = narrow.new_page()
                np_.on("pageerror", lambda error: page_errors.append(f"768: {error}"))
                np_.on("dialog", dialog_handler)
                np_.goto(base_url)
                np_.wait_for_selector("#ws-status.online", state="attached")
                np_.click("#tab-button-show")
                np_.wait_for_selector('[data-show-step-row="00000000"]')

                labels_hidden = np_.evaluate(
                    "() => [...document.querySelectorAll('.show-edit-bar-label')]"
                    ".every(el => getComputedStyle(el).display === 'none')")
                check("768px: edit-bar labels are hidden (the reported condition)",
                      labels_hidden)

                check_names_and_glyphs(np_, 768)

                layout = edit_bar_layout(np_)
                check("768px: all four edit-bar buttons visible",
                      layout and len(layout["btns"]) == 4
                      and all(b["visible"] for b in layout["btns"]), repr(layout))
                pairs = []
                btns = (layout or {}).get("btns", [])
                for i in range(len(btns)):
                    for j in range(i + 1, len(btns)):
                        if overlaps(btns[i], btns[j]):
                            pairs.append((btns[i]["action"], btns[j]["action"]))
                check("768px: no edit-bar button overlaps a neighbour", not pairs, repr(pairs))
                check("768px: the edit bar itself does not overflow",
                      layout and not layout["barOverflows"], repr(layout))
                check("no page-level horizontal overflow at 768px",
                      no_horizontal_overflow(np_))

                for theme in ("dark", "light"):
                    np_.select_option("#theme-select", theme)
                    np_.wait_for_function(
                        "(t) => document.documentElement.getAttribute('data-theme') === t",
                        arg=theme)
                    np_.wait_for_timeout(150)
                    np_.screenshot(path=str(HERE / f"review-768-{theme}.png"),
                                   full_page=True)
                    np_.locator(".show-edit-bar").screenshot(
                        path=str(HERE / f"edit-bar-768-{theme}.png"))
                narrow.close()

                check("browser emitted no page errors across all widths",
                      not page_errors, repr(page_errors))
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
