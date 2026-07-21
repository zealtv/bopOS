#!/usr/bin/env python3
"""Playwright + simfleet verification for named section dividers (stitch 04).

Covers 04-named-section-dividers plus the shared click-to-edit name pattern
extended to divider and message inspectors:

1. Divider naming via the click-to-edit inspector title -- pointer + Enter/F2
   paths, Enter/blur commit, Escape restores, blank -> Untitled section; the
   "Section divider" context line stays.
2. Message alias via the new click-to-edit title (the visible `alias` input is
   gone) with identical commit/cancel/blank semantics; the derived
   messageLabel() is the unset-state placeholder/display.
3. Pill colour class: same alias yields the same `show-pill-N` class it did
   before the rename (round-trip), a different alias re-hashes to a different
   class, and blank clears the colour.
4. Named divider row renders the name centred with a rule line either side
   (two `.show-divider-line`, no gradient background); an unnamed divider keeps
   the plain gradient rule. Screenshots in light + dark.
5. Persistence across reload; a second browser context sees the alias
   broadcast; duplicate on a named divider copies the alias with a fresh uid.
6. Long names truncate/ellipsize with no page-level horizontal overflow at
   768px; divider drag-reorder and click selection still work.

Playwright house rules honoured: non-active-panel elements are waited for with
state="attached"; rects are gathered in a single page.evaluate from one scroll
state; `wait_for_function` passes its argument via arg=; no reliance on
actionability/stability auto-scroll for the drag (one-shot evaluate for
geometry, mouse steps for the gesture).
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
    (patch / "main.bin").write_bytes(b"named-divider-verifier")
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
        "schema": 1, "name": "Named divider verifier",
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
    # Deliberate opening layout: an UNNAMED divider (click-to-edit target),
    # a step + one named message, and a pre-NAMED divider (row rendering,
    # duplicate, truncation).
    show = {
        "schema": 1, "name": "opening-set",
        "items": [
            {"kind": "divider", "uid": "d0000001", "alias": None},
            {"kind": "step", "uid": "11111111", "alias": "first step",
             "messages": [
                 {"uid": "aaaa0001", "alias": "house-fade", "address": "/p/gain",
                  "args": [{"type": "f", "value": 0.61}], "target": ["all"]},
             ],
             "duration_s": 5, "play_count": 1, "then_actions": []},
            {"kind": "divider", "uid": "d0000002", "alias": "MOVEMENT ONE"},
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


def title_sel(kind, uid):
    return f'[data-show-name-title][data-show-name-kind="{kind}"][data-show-name-uid="{uid}"]'


def input_sel(kind, uid):
    return f'[data-show-name-input][data-show-name-kind="{kind}"][data-show-name-uid="{uid}"]'


def title_text(page, kind, uid):
    return page.locator(title_sel(kind, uid)).inner_text().strip()


def commit_name(page, kind, uid, value):
    """Click the title, fill the input, press Enter, wait for the title back."""
    page.locator(title_sel(kind, uid)).click()
    page.wait_for_selector(input_sel(kind, uid), state="attached")
    page.locator(input_sel(kind, uid)).fill(value)
    page.keyboard.press("Enter")
    page.wait_for_selector(title_sel(kind, uid), state="attached")


def pill_colour(page, uid):
    return page.evaluate(
        """(u) => {
            const pill = document.querySelector(`[data-show-message-focus="${u}"]`);
            if (!pill) return null;
            return [...pill.classList].find(c => /^show-pill-\\d$/.test(c)) || "";
        }""", uid)


def item_order(page):
    return page.evaluate(
        """() => [...document.querySelectorAll('[data-show-step-row],[data-show-divider-row]')]
                   .map(r => r.dataset.showStepRow || r.dataset.showDividerRow)""")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-named-dividers-") as root:
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
                # Desktop (1280px).
                # ---------------------------------------------------------
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = context.new_page()
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-divider-row="d0000001"]')

                # ---- Named vs unnamed row rendering. ----
                def named_row_shape(uid):
                    return page.evaluate(
                        """(u) => {
                            const row = document.querySelector(`[data-show-divider-row="${u}"]`);
                            if (!row) return null;
                            const lines = row.querySelectorAll('.show-divider-line');
                            const name = row.querySelector('.show-divider-name');
                            const bg = getComputedStyle(row).backgroundImage;
                            // line, name, line ordering check
                            const kids = [...row.children].map(c => c.className);
                            return {lines: lines.length, name: name ? name.textContent : null,
                                    named: row.classList.contains('show-divider-named'),
                                    hasGradient: bg && bg.includes('gradient'), kids};
                        }""", uid)

                unnamed = named_row_shape("d0000001")
                # Superseded by 19-show-chrome-fixes/03-divider-rule-styling
                # (Bob, 2026-07-21: "get rid of that gradient... it can just be
                # a blank line"). The unnamed divider now draws a flat 1px rule
                # via ::after, so the gradient assertion is inverted here rather
                # than left permanently red.
                check("unnamed divider row keeps a plain rule, no gradient (no name/lines)",
                      unnamed["lines"] == 0 and unnamed["name"] is None
                      and not unnamed["named"] and not unnamed["hasGradient"], repr(unnamed))
                named = named_row_shape("d0000002")
                check("named divider row shows the name with a rule line either side",
                      named["lines"] == 2 and named["name"] == "MOVEMENT ONE"
                      and named["named"], repr(named))
                check("named divider row drops the plain gradient background",
                      not named["hasGradient"], repr(named))
                order_ok = page.evaluate(
                    """() => {
                        const row = document.querySelector('[data-show-divider-row="d0000002"]');
                        const kids = [...row.children];
                        const li = kids.findIndex(c => c.classList.contains('show-divider-line'));
                        const ni = kids.findIndex(c => c.classList.contains('show-divider-name'));
                        const li2 = kids.map(c => c.classList.contains('show-divider-line')).lastIndexOf(true);
                        return li < ni && ni < li2;
                    }""")
                check("named divider lines flank the name (line - name - line)", order_ok)

                # ---- Divider naming via click-to-edit inspector title. ----
                page.locator('[data-show-divider-row="d0000001"]').click()
                page.wait_for_selector(".show-inspector-panel " + title_sel("divider", "d0000001"))
                check("divider inspector title shows the Untitled placeholder when unset",
                      title_text(page, "divider", "d0000001") == "Untitled section",
                      title_text(page, "divider", "d0000001"))
                check("divider inspector keeps the 'Section divider' context line",
                      "Section divider" in page.locator(
                          ".show-inspector-panel .show-inspector-context").inner_text())
                check("no visible legacy 'Divider inspector' static heading",
                      page.evaluate(
                          """() => ![...document.querySelectorAll('.show-inspector-panel h3')]
                                     .some(h => h.textContent.trim() === 'Divider inspector')"""))

                # Pointer commit.
                page.locator(title_sel("divider", "d0000001")).click()
                page.wait_for_selector(input_sel("divider", "d0000001"), state="attached")
                check("click on the divider title swaps in a focused input",
                      page.evaluate(
                          "(s) => document.activeElement === document.querySelector(s)",
                          input_sel("divider", "d0000001")))
                page.locator(input_sel("divider", "d0000001")).fill("OPENING")
                page.keyboard.press("Enter")
                page.wait_for_selector(title_sel("divider", "d0000001"), state="attached")
                check("Enter commits the divider name",
                      title_text(page, "divider", "d0000001") == "OPENING")
                page.wait_for_function(
                    """() => { const r = document.querySelector('[data-show-divider-row="d0000001"]');
                              return r && r.classList.contains('show-divider-named'); }""")
                check("naming a divider promotes its row to the named (lines) treatment",
                      named_row_shape("d0000001")["lines"] == 2)

                # Escape restores.
                page.locator(title_sel("divider", "d0000001")).click()
                page.locator(input_sel("divider", "d0000001")).fill("SCRATCH")
                page.keyboard.press("Escape")
                page.wait_for_selector(title_sel("divider", "d0000001"), state="attached")
                check("Escape restores the prior divider name",
                      title_text(page, "divider", "d0000001") == "OPENING")

                # Blank -> untitled + row reverts to plain rule.
                page.locator(title_sel("divider", "d0000001")).click()
                page.locator(input_sel("divider", "d0000001")).fill("")
                page.keyboard.press("Enter")
                page.wait_for_selector(title_sel("divider", "d0000001"), state="attached")
                check("blank commits the divider back to Untitled section",
                      title_text(page, "divider", "d0000001") == "Untitled section")
                page.wait_for_function(
                    """() => { const r = document.querySelector('[data-show-divider-row="d0000001"]');
                              return r && !r.classList.contains('show-divider-named'); }""")
                check("clearing a divider name reverts the row to the plain rule",
                      named_row_shape("d0000001")["lines"] == 0)

                # F2 keyboard path opens the editor.
                page.locator(title_sel("divider", "d0000001")).focus()
                page.keyboard.press("F2")
                page.wait_for_selector(input_sel("divider", "d0000001"), state="attached")
                check("F2 opens inline edit on the focused divider title",
                      page.locator(input_sel("divider", "d0000001")).count() == 1)
                page.locator(input_sel("divider", "d0000001")).fill("OPENING")
                page.keyboard.press("Enter")
                page.wait_for_selector(title_sel("divider", "d0000001"), state="attached")
                # Enter keyboard path opens the editor (from focused title).
                page.locator(title_sel("divider", "d0000001")).focus()
                page.keyboard.press("Enter")
                page.wait_for_selector(input_sel("divider", "d0000001"), state="attached")
                check("Enter opens inline edit on the focused divider title",
                      page.locator(input_sel("divider", "d0000001")).count() == 1)
                page.keyboard.press("Escape")
                page.wait_for_selector(title_sel("divider", "d0000001"), state="attached")

                # ---- Message alias via the new click-to-edit title. ----
                page.locator('[data-show-message-focus="aaaa0001"]').click()
                page.wait_for_selector(".show-inspector-panel " + title_sel("message", "aaaa0001"))
                check("message inspector title shows the alias",
                      title_text(page, "message", "aaaa0001") == "house-fade")
                check("message inspector no longer has the visible alias input",
                      page.locator("#show-message-alias").count() == 0)
                colour_before = pill_colour(page, "aaaa0001")
                check("aliased message pill carries a colour class", bool(colour_before),
                      repr(colour_before))

                # Rename to a different alias -> pill re-hashes.
                commit_name(page, "message", "aaaa0001", "swell-env")
                check("Enter commits the message alias via the title",
                      title_text(page, "message", "aaaa0001") == "swell-env")
                colour_diff = pill_colour(page, "aaaa0001")
                check("a different message alias re-hashes to a different pill colour",
                      colour_diff and colour_diff != colour_before,
                      repr((colour_before, colour_diff)))

                # Rename back -> same alias, same colour class as before.
                commit_name(page, "message", "aaaa0001", "house-fade")
                colour_restored = pill_colour(page, "aaaa0001")
                check("the same message alias yields the same pill colour class as before",
                      colour_restored == colour_before,
                      repr((colour_before, colour_restored)))

                # Escape restores; blank -> derived label + no colour.
                page.locator(title_sel("message", "aaaa0001")).click()
                page.locator(input_sel("message", "aaaa0001")).fill("NOPE")
                page.keyboard.press("Escape")
                page.wait_for_selector(title_sel("message", "aaaa0001"), state="attached")
                check("Escape restores the prior message alias",
                      title_text(page, "message", "aaaa0001") == "house-fade")
                commit_name(page, "message", "aaaa0001", "")
                check("blank message alias falls back to the derived label placeholder",
                      title_text(page, "message", "aaaa0001") == "gain",
                      title_text(page, "message", "aaaa0001"))
                check("clearing the message alias clears the pill colour",
                      pill_colour(page, "aaaa0001") == "", repr(pill_colour(page, "aaaa0001")))
                commit_name(page, "message", "aaaa0001", "house-fade")

                # ---- Duplicate a named divider copies the alias, fresh uid. ----
                page.locator('[data-show-divider-row="d0000002"]').click()
                page.wait_for_selector(".show-inspector-panel " + title_sel("divider", "d0000002"))
                before_dupe = page.evaluate(
                    """() => [...document.querySelectorAll('[data-show-divider-row]')]
                               .map(r => r.dataset.showDividerRow)""")
                page.locator('[data-edit-bar-action="duplicate"]').click()
                page.wait_for_function(
                    "(n) => document.querySelectorAll('[data-show-divider-row]').length > n",
                    arg=len(before_dupe))
                dupe = page.evaluate(
                    """(before) => {
                        const rows = [...document.querySelectorAll('[data-show-divider-row]')];
                        const fresh = rows.map(r => r.dataset.showDividerRow)
                                          .filter(u => !before.includes(u));
                        const named = rows.filter(r => (r.querySelector('.show-divider-name') || {}).textContent === 'MOVEMENT ONE');
                        return {freshCount: fresh.length, fresh: fresh,
                                namedCount: named.length,
                                freshIsNamed: fresh.length === 1 && named.some(r => r.dataset.showDividerRow === fresh[0])};
                    }""", before_dupe)
                check("duplicating a named divider mints exactly one fresh uid",
                      dupe["freshCount"] == 1 and dupe["fresh"][0] not in before_dupe, repr(dupe))
                check("the duplicated divider copies the alias (two MOVEMENT ONE rows)",
                      dupe["namedCount"] == 2 and dupe["freshIsNamed"], repr(dupe))

                # ---- Drag reorder + selection still work. ----
                page.locator('[data-show-divider-row="d0000001"]').click()
                page.wait_for_function(
                    """() => document.querySelector('[data-show-divider-row="d0000001"]')
                             .classList.contains('focused')""")
                check("clicking a divider row selects it (focused)",
                      page.locator('[data-show-divider-row="d0000001"].focused').count() == 1)
                before_order = item_order(page)
                geo = page.evaluate(
                    """() => {
                        const box = document.querySelector('.show-rows-box');
                        box.scrollTop = 0;
                        const h = document.querySelector('[data-show-divider-row="d0000001"] [data-drag-item]').getBoundingClientRect();
                        const t = document.querySelector('[data-show-step-row="11111111"]').getBoundingClientRect();
                        return {hx: h.left + h.width / 2, hy: h.top + h.height / 2,
                                tx: t.left + t.width / 2, ty: t.bottom - 3};
                    }""")
                page.mouse.move(geo["hx"], geo["hy"])
                page.mouse.down()
                page.mouse.move(geo["hx"], geo["hy"] + 12, steps=3)  # cross activation threshold
                page.mouse.move(geo["tx"], geo["ty"], steps=8)
                page.mouse.up()
                page.wait_for_function(
                    """() => { const rows = [...document.querySelectorAll('[data-show-step-row],[data-show-divider-row]')]
                                 .map(r => r.dataset.showStepRow || r.dataset.showDividerRow);
                               return rows[0] === '11111111'; }""")
                after_order = item_order(page)
                check("dragging a divider reorders it (d0000001 moved after the step)",
                      after_order.index("d0000001") > after_order.index("11111111")
                      and before_order != after_order,
                      repr((before_order, after_order)))

                check("no page-level horizontal overflow at 1280px", no_horizontal_overflow(page))

                # ---- Themes: screenshots with a named divider on screen. ----
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

                # ---- Persistence across reload (divider + message alias). ----
                page.reload()
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-divider-row="d0000002"]')
                reloaded_named = page.evaluate(
                    """() => (document.querySelector('[data-show-divider-row="d0000002"] .show-divider-name') || {}).textContent""")
                check("named divider persists to disk across reload",
                      reloaded_named == "MOVEMENT ONE", repr(reloaded_named))
                page.locator('[data-show-message-focus="aaaa0001"]').click()
                page.wait_for_selector(title_sel("message", "aaaa0001"), state="attached")
                check("message alias persists to disk across reload",
                      title_text(page, "message", "aaaa0001") == "house-fade")

                # ---- Second browser context sees the alias broadcast. ----
                context_b = browser.new_context(viewport={"width": 1280, "height": 900})
                page_b = context_b.new_page()
                page_b.on("pageerror", lambda error: page_errors.append(f"ctxB: {error}"))
                page_b.goto(base_url)
                page_b.wait_for_selector("#ws-status.online", state="attached")
                page_b.click("#tab-button-show")
                page_b.wait_for_selector('[data-show-divider-row="d0000001"]')
                page.locator('[data-show-divider-row="d0000001"]').click()
                page.wait_for_selector(".show-inspector-panel " + title_sel("divider", "d0000001"))
                commit_name(page, "divider", "d0000001", "BROADCAST")
                page_b.wait_for_function(
                    """() => { const n = document.querySelector('[data-show-divider-row="d0000001"] .show-divider-name');
                               return n && n.textContent === 'BROADCAST'; }""")
                check("a second client sees the divider alias broadcast",
                      page_b.evaluate(
                          """() => (document.querySelector('[data-show-divider-row="d0000001"] .show-divider-name') || {}).textContent""") == "BROADCAST")
                context_b.close()
                context.close()

                # ---------------------------------------------------------
                # Narrow (768px): truncation + no horizontal overflow.
                # ---------------------------------------------------------
                narrow_context = browser.new_context(
                    viewport={"width": 768, "height": 900}, has_touch=True)
                narrow = narrow_context.new_page()
                narrow.on("pageerror", lambda error: page_errors.append(f"narrow: {error}"))
                narrow.goto(base_url)
                narrow.wait_for_selector("#ws-status.online", state="attached")
                narrow.click("#tab-button-show")
                narrow.wait_for_selector('[data-show-divider-row="d0000002"]')
                long_name = "MOVEMENT ONE " + "very-long-section-name " * 6
                narrow.locator('[data-show-divider-row="d0000002"]').click()
                narrow.wait_for_selector(title_sel("divider", "d0000002"), state="attached")
                commit_name(narrow, "divider", "d0000002", long_name.strip())
                trunc = narrow.evaluate(
                    """() => {
                        const n = document.querySelector('[data-show-divider-row="d0000002"] .show-divider-name');
                        if (!n) return null;
                        const cs = getComputedStyle(n);
                        return {scrollW: n.scrollWidth, clientW: n.clientWidth,
                                ellipsis: cs.textOverflow, overflow: cs.overflow};
                    }""")
                check("a long divider name truncates/ellipsizes (scrollWidth > clientWidth)",
                      trunc and trunc["scrollW"] > trunc["clientW"]
                      and trunc["ellipsis"] == "ellipsis", repr(trunc))
                check("no page-level horizontal overflow at 768px with a long divider name",
                      no_horizontal_overflow(narrow))

                # Touch rename path on a divider title.
                narrow.locator('[data-show-divider-row="d0000001"]').tap()
                narrow.wait_for_selector(title_sel("divider", "d0000001"), state="attached")
                narrow.locator(title_sel("divider", "d0000001")).tap()
                narrow.wait_for_selector(input_sel("divider", "d0000001"), state="attached")
                narrow.locator(input_sel("divider", "d0000001")).fill("TOUCH")
                narrow.keyboard.press("Enter")
                narrow.wait_for_selector(title_sel("divider", "d0000001"), state="attached")
                check("touch tap on a divider title commits a rename",
                      title_text(narrow, "divider", "d0000001") == "TOUCH")
                narrow.screenshot(path=str(HERE / "review-768-named-dividers.png"), full_page=True)
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
