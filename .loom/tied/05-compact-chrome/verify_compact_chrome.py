#!/usr/bin/env python3
"""Playwright + simfleet verification for the compact-chrome pass (stitch 05).

Show-tab-only CSS density pass driven by the new `--chrome-*` :root variables.
Covers:

1. The `--chrome-*` variables resolve on documentElement to the decisions.md
   values (radius panel/control/small, control-height, control-pad, panel-pad,
   gap).
2. Representative controls consume them (computed getComputedStyle, px compared):
   edit-bar button, step row, inspector panel, console, inspector input.
3. The rows scrollbox has a visible border + control radius, the edit bar is
   pinned above it, and the box is a bounded scroll region (scrollHeight >
   clientHeight with a full show).
4. Touch safety at 768px: every touch-relevant control keeps an effective
   >=44px hit target in both axes (visual box + ::after inset expansion).
5. Inputs/selects fall back to a >=44px min-height at the <=760px mobile layout
   (no ::after possible on form controls).
6. Keyboard :focus-visible outline still lands on a focused edit-bar button.
7. Light + dark Show-tab screenshots at 1280 and 768, retained here.
8. No page-level horizontal overflow at 1280 or 768.

Playwright house rules honoured: non-active-panel elements waited for with
state="attached"; sizes read without relying on actionability/stability scrolls
(getBoundingClientRect size is scroll-independent); position-comparison rects
gathered in a single page.evaluate from one scroll state; one type-aware dialog
handler; wait_for_function args via arg=.
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
    (patch / "main.bin").write_bytes(b"compact-chrome-verifier")
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
        "schema": 1, "name": "Compact chrome verifier",
        "current_show": "dense-set",
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
    # A full show so the rows box overflows and must scroll: one divider, then
    # a stack of steps (first carries a named message for the inspector pills).
    items = [{"kind": "divider", "uid": "d0000001", "alias": "MOVEMENT ONE"}]
    for i in range(24):
        uid = f"{i:08d}"
        messages = []
        if i == 0:
            messages = [{"uid": "aaaa0001", "alias": "house-fade",
                         "address": "/p/gain",
                         "args": [{"type": "f", "value": 0.61}],
                         "target": ["all"]}]
        items.append({
            "kind": "step", "uid": uid, "alias": f"step {i}",
            "messages": messages, "duration_s": 5, "play_count": 1,
            "then_actions": [],
        })
    show = {"schema": 1, "name": "dense-set", "items": items}
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows_dir / "dense-set.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


def no_horizontal_overflow(page):
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def css_var(page, name):
    return page.evaluate(
        "(n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim()", name)


def style_of(page, selector, props):
    """Computed style props (px strings) for the first match of `selector`."""
    return page.evaluate(
        """([sel, props]) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const cs = getComputedStyle(el);
            const out = {};
            for (const p of props) out[p] = cs[p];
            return out;
        }""", [selector, props])


def px(value):
    try:
        return float(str(value).replace("px", "").strip())
    except (TypeError, ValueError):
        return None


def effective_hit(page, selector):
    """Visual box + ::after inset expansion, in both axes, for a touch target."""
    return page.evaluate(
        """(sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const r = el.getBoundingClientRect();
            const a = getComputedStyle(el, '::after');
            const num = (v) => { const n = parseFloat(v); return Number.isFinite(n) ? n : 0; };
            // negative insets extend the pseudo beyond the box edges
            const top = num(a.top), bottom = num(a.bottom);
            const left = num(a.left), right = num(a.right);
            return {
                w: r.width, h: r.height, content: a.content,
                effW: r.width - left - right,
                effH: r.height - top - bottom,
            };
        }""", selector)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-compact-chrome-") as root:
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
                # Desktop (1280px): variables + representative controls.
                # ---------------------------------------------------------
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = context.new_page()
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="00000000"]')

                # ---- :root variables resolve to the ratified values. ----
                wanted = {
                    "--chrome-radius-panel": "6px",
                    "--chrome-radius-control": "4px",
                    "--chrome-radius-small": "3px",
                    "--chrome-control-height": "32px",
                    "--chrome-control-pad": "4px 8px",
                    "--chrome-panel-pad": "12px",
                    "--chrome-gap": "12px",
                }
                for name, expect in wanted.items():
                    got = css_var(page, name)
                    check(f"{name} resolves to {expect}", got == expect, repr(got))

                # ---- Representative controls consume them. ----
                eb = style_of(page, '[data-edit-bar-action]',
                              ["borderTopLeftRadius", "minHeight",
                               "paddingTop", "paddingLeft"])
                check("edit-bar button radius is 4px", eb and px(eb["borderTopLeftRadius"]) == 4, repr(eb))
                # The edit-bar button min-height stays 40px: the ratified 02
                # edit-bar suite pins it >=40px, and the spec's height mapping
                # named 44px controls only (this one was already 40px). It still
                # takes the chrome radius + control padding.
                check("edit-bar button min-height stays 40px (02 edit-bar pin)",
                      eb and px(eb["minHeight"]) == 40, repr(eb))
                check("edit-bar button padding is 4px 8px",
                      eb and px(eb["paddingTop"]) == 4 and px(eb["paddingLeft"]) == 8, repr(eb))

                row = style_of(page, '[data-show-step-row="00000000"]',
                               ["borderTopLeftRadius", "minHeight"])
                check("step row radius is 4px", row and px(row["borderTopLeftRadius"]) == 4, repr(row))
                check("step row min-height is 32px", row and px(row["minHeight"]) == 32, repr(row))

                # Select the first step so the inspector form renders.
                page.locator('[data-show-step-row="00000000"]').click()
                page.wait_for_selector('.show-inspector-form[data-show-step-editor="00000000"]',
                                       state="attached")
                panel = style_of(page, ".show-inspector-panel",
                                 ["borderTopLeftRadius", "paddingTop", "paddingLeft"])
                check("inspector panel radius is 6px", panel and px(panel["borderTopLeftRadius"]) == 6, repr(panel))
                check("inspector panel padding is 12px",
                      panel and px(panel["paddingTop"]) == 12 and px(panel["paddingLeft"]) == 12, repr(panel))

                inp = style_of(page, '.show-inspector-form input[data-duration-part="s"]',
                               ["borderTopLeftRadius", "minHeight",
                                "paddingTop", "paddingLeft"])
                check("inspector input radius is 4px", inp and px(inp["borderTopLeftRadius"]) == 4, repr(inp))
                check("inspector input min-height is 32px", inp and px(inp["minHeight"]) == 32, repr(inp))
                check("inspector input padding is 4px 8px",
                      inp and px(inp["paddingTop"]) == 4 and px(inp["paddingLeft"]) == 8, repr(inp))

                console = style_of(page, ".show-console", ["borderTopLeftRadius"])
                check("console radius is 6px", console and px(console["borderTopLeftRadius"]) == 6, repr(console))

                # ---- Rows scrollbox: visible bound, radius, pinned edit bar, bounded. ----
                # The bound is a 1px inset box-shadow rather than a `border`: the
                # show.js height-persistence (reads clientHeight, writes it back
                # as the box's height each re-render) would ratchet a real border
                # smaller every frame. An inset shadow is outside the box model,
                # honours border-radius, and is CSS-only (no JS change).
                box = style_of(page, ".show-rows-box",
                               ["boxShadow", "borderTopLeftRadius"])
                check("rows box has a visible 1px inset bound (box-shadow)",
                      box and "inset" in box["boxShadow"] and box["boxShadow"] != "none", repr(box))
                check("rows box radius is 4px", box and px(box["borderTopLeftRadius"]) == 4, repr(box))
                pinned = page.evaluate(
                    """() => {
                        const bar = document.querySelector('.show-edit-bar');
                        const box = document.querySelector('.show-rows-box');
                        if (!bar || !box) return null;
                        const b = bar.getBoundingClientRect();
                        const x = box.getBoundingClientRect();
                        return {above: b.bottom <= x.top + 1,
                                scrolls: box.scrollHeight > box.clientHeight + 1,
                                scrollHeight: box.scrollHeight, clientHeight: box.clientHeight};
                    }""")
                check("edit bar is pinned above the rows box", pinned and pinned["above"], repr(pinned))
                check("rows box is a bounded scroll region (scrollHeight > clientHeight)",
                      pinned and pinned["scrolls"], repr(pinned))

                # ---- Keyboard :focus-visible outline on an edit-bar button. ----
                first_eb = page.locator('[data-edit-bar-action]').first
                first_eb.focus()
                page.keyboard.press("Shift+Tab")
                page.keyboard.press("Tab")
                focus_state = page.evaluate(
                    """() => {
                        const el = document.activeElement;
                        if (!el || !el.matches('[data-edit-bar-action]')) return null;
                        const cs = getComputedStyle(el);
                        return {fv: el.matches(':focus-visible'),
                                outline: parseFloat(cs.outlineWidth) || 0,
                                style: cs.outlineStyle};
                    }""")
                check("keyboard focus lands back on an edit-bar button",
                      focus_state is not None, repr(focus_state))
                check("edit-bar button keeps a visible :focus-visible outline",
                      focus_state and focus_state["fv"] and focus_state["outline"] > 0
                      and focus_state["style"] != "none", repr(focus_state))

                check("no page-level horizontal overflow at 1280px", no_horizontal_overflow(page))

                # ---- Light + dark screenshots at 1280. ----
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
                context.close()

                # ---------------------------------------------------------
                # Touch layout (768px): effective >=44px hit targets.
                # ---------------------------------------------------------
                touch_ctx = browser.new_context(
                    viewport={"width": 768, "height": 900}, has_touch=True)
                tp = touch_ctx.new_page()
                tp.on("pageerror", lambda error: page_errors.append(f"768: {error}"))
                tp.goto(base_url)
                tp.wait_for_selector("#ws-status.online", state="attached")
                tp.click("#tab-button-show")
                tp.wait_for_selector('[data-show-step-row="00000000"]')
                # Select a step so the inspector form + its buttons exist
                # (synthetic click: a touch tap is swallowed by drag logic).
                tp.eval_on_selector('[data-show-step-row="00000000"]', "e => e.click()")
                tp.wait_for_selector('.show-inspector-form[data-show-step-editor="00000000"]',
                                     state="attached")

                touch_targets = {
                    "edit-bar button": '[data-edit-bar-action]',
                    "transport icon button": '.show-transport-actions .show-icon-button',
                    "step-row transport icon button": '.show-step-transport .show-icon-button',
                    "inspector collapse toggle": '.show-inspector-toggle',
                    "console summary": '.show-console summary',
                    "inspector-form button": '.show-inspector-form button',
                }
                for label, sel in touch_targets.items():
                    hit = effective_hit(tp, sel)
                    ok = hit and hit["effW"] >= 44 - 0.5 and hit["effH"] >= 44 - 0.5
                    check(f"touch target >=44px both axes: {label}", ok, repr(hit))

                check("no page-level horizontal overflow at 768px", no_horizontal_overflow(tp))

                # ---- Light + dark screenshots at 768. ----
                tp.select_option("#theme-select", "dark")
                tp.wait_for_function(
                    "() => document.documentElement.getAttribute('data-theme') === 'dark'")
                tp.wait_for_timeout(150)
                tp.screenshot(path=str(HERE / "review-768-dark.png"), full_page=True)
                tp.select_option("#theme-select", "light")
                tp.wait_for_function(
                    "() => document.documentElement.getAttribute('data-theme') === 'light'")
                tp.wait_for_timeout(150)
                tp.screenshot(path=str(HERE / "review-768-light.png"), full_page=True)
                touch_ctx.close()

                # ---------------------------------------------------------
                # Mobile layout (<=760px): inputs/selects fall back to >=44px.
                # ---------------------------------------------------------
                mob_ctx = browser.new_context(
                    viewport={"width": 500, "height": 900}, has_touch=True)
                mp = mob_ctx.new_page()
                mp.on("pageerror", lambda error: page_errors.append(f"500: {error}"))
                mp.goto(base_url)
                mp.wait_for_selector("#ws-status.online", state="attached")
                mp.click("#tab-button-show")
                mp.wait_for_selector('[data-show-step-row="00000000"]')
                # A synthetic click on the row's own handler -- a touch tap at
                # this width is swallowed by the drag gesture logic.
                mp.eval_on_selector('[data-show-step-row="00000000"]', "e => e.click()")
                mp.wait_for_selector('.show-inspector-form[data-show-step-editor="00000000"]',
                                     state="attached")
                mob_inp = style_of(mp, '.show-inspector-form input[data-duration-part="s"]',
                                   ["minHeight"])
                check("inspector input keeps a >=44px min-height at <=760px",
                      mob_inp and px(mob_inp["minHeight"]) >= 44, repr(mob_inp))
                check("no page-level horizontal overflow at 500px", no_horizontal_overflow(mp))
                mob_ctx.close()

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
