#!/usr/bin/env python3
"""Playwright + simfleet verification for divider rule styling (stitch 19/03).

Bob's two complaints against `18-show-chrome-density/04-named-section-dividers`:
the named divider's rules ran full bleed across the row, and the unnamed divider
was a gradient. `decisions.md` rules short fixed-length rules flanking a centred
name, and a flat 1px `--strong-line` rule (no gradient) for the unnamed row.

Covers:

1. Named divider: both `.show-divider-line` elements are exactly 28px wide and
   far narrower than the row -- with a short name and again with a very long
   name (the long name truncates rather than stretching the rules).
2. Named divider: the name is horizontally centred in the row (small tolerance)
   and the two rules flank it (one entirely left, one entirely right).
3. Unnamed divider: computed `background-image` is `none` (gradient gone), and
   the `::after` rule exists at 1px high, pointer-transparent, inset clear of
   the `.show-divider-drag` grab handle's rect.
4. The named divider's name is still click-to-edit through the inspector title
   (click row, click title, commit, the row shows the new name).
5. Both rows keep their existing `aria-label`s (and the handle keeps its own).
6. Focus outline + drop-shadow classes still resolve on a divider row.
7. Retained screenshots: named + unnamed dividers, light and dark.

Playwright house rules honoured: `#ws-status` waited for with state="attached";
no `scroll_into_view_if_needed`/actionability scrolls on Show rows; every
position comparison gathered in a single `page.evaluate` from one scroll state;
one type-aware dialog handler; `wait_for_function` args passed via `arg=`.
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

LONG_NAME = ("A VERY LONG SECTION NAME THAT KEEPS GOING AND GOING SO IT MUST "
             "TRUNCATE INSTEAD OF STRETCHING THE FLANKING RULES OUTWARD")


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
    (patch / "main.bin").write_bytes(b"divider-rules-verifier")
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
        "schema": 1, "name": "Divider rules verifier",
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
    step = {"kind": "step", "uid": "00000000", "alias": "opening",
            "messages": [
                {"uid": "aaaa0001", "alias": "house-fade", "address": "/p/gain",
                 "args": [{"type": "f", "value": 0.61}], "target": ["all"]},
            ],
            "duration_s": 5, "play_count": 1, "then_actions": []}
    step2 = dict(step, uid="00000001", alias="second", messages=[])
    step3 = dict(step, uid="00000002", alias="third", messages=[])
    show = {
        "schema": 1, "name": "opening-set",
        "items": [
            # d0000001: unnamed (flat rule + grab handle).
            {"kind": "divider", "uid": "d0000001"},
            step,
            # d0000002: short name; d0000003: a name that must truncate.
            {"kind": "divider", "uid": "d0000002", "alias": "MOVEMENT ONE"},
            step2,
            {"kind": "divider", "uid": "d0000003", "alias": LONG_NAME},
            step3,
        ],
    }
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows_dir / "opening-set.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


def title_sel(kind, uid):
    return f'[data-show-name-title][data-show-name-kind="{kind}"][data-show-name-uid="{uid}"]'


def input_sel(kind, uid):
    return f'[data-show-name-input][data-show-name-kind="{kind}"][data-show-name-uid="{uid}"]'


# One page.evaluate, one scroll state: every rect for a divider row (gotcha 9).
NAMED_GEOMETRY = """(u) => {
    const row = document.querySelector(`[data-show-divider-row="${u}"]`);
    if (!row) return null;
    const lines = [...row.querySelectorAll('.show-divider-line')];
    const name = row.querySelector('.show-divider-name');
    const handle = row.querySelector('.show-divider-drag');
    const r = (el) => { const b = el.getBoundingClientRect();
                        return {x: b.x, y: b.y, w: b.width, h: b.height,
                                left: b.left, right: b.right,
                                top: b.top, bottom: b.bottom}; };
    return {
        row: r(row),
        lines: lines.map(r),
        lineFlex: lines.map(l => getComputedStyle(l).flexBasis),
        name: name ? r(name) : null,
        nameText: name ? name.textContent : null,
        nameTruncated: name ? name.scrollWidth > name.clientWidth + 1 : null,
        handle: handle ? r(handle) : null,
        ariaLabel: row.getAttribute('aria-label'),
        handleAria: handle ? handle.getAttribute('aria-label') : null,
        backgroundImage: getComputedStyle(row).backgroundImage,
    };
}"""

UNNAMED_GEOMETRY = """(u) => {
    const row = document.querySelector(`[data-show-divider-row="${u}"]`);
    if (!row) return null;
    const handle = row.querySelector('.show-divider-drag');
    const rb = row.getBoundingClientRect();
    const hb = handle ? handle.getBoundingClientRect() : null;
    const a = getComputedStyle(row, '::after');
    const num = (v) => { const n = parseFloat(v); return Number.isFinite(n) ? n : null; };
    const insetLeft = num(a.left), insetRight = num(a.right);
    return {
        backgroundImage: getComputedStyle(row).backgroundImage,
        afterContent: a.content,
        afterHeight: num(a.height),
        afterBackground: a.backgroundColor,
        afterPointerEvents: a.pointerEvents,
        afterPosition: a.position,
        ruleLeft: insetLeft === null ? null : rb.left + insetLeft,
        ruleRight: insetRight === null ? null : rb.right - insetRight,
        afterWidth: num(a.width),
        ruleCentre: (() => {
            const raw = a.left;
            const off = raw.endsWith('%') ? rb.width * parseFloat(raw) / 100 : num(raw);
            return off === null ? null : rb.left + off;
        })(),
        row: {left: rb.left, right: rb.right, width: rb.width, height: rb.height},
        handle: hb ? {left: hb.left, right: hb.right, width: hb.width} : null,
        ariaLabel: row.getAttribute('aria-label'),
        handleAria: handle ? handle.getAttribute('aria-label') : null,
        hasLines: row.querySelectorAll('.show-divider-line').length,
    };
}"""


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-divider-rules-") as root:
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
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = context.new_page()
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                # One type-aware dialog handler for the whole run.
                page.on("dialog", lambda d: (d.accept("verifier")
                                             if d.type == "prompt" else d.accept()))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-divider-row="d0000001"]')
                page.wait_for_selector('[data-show-divider-row="d0000003"]')

                # ---------------------------------------------------------
                # 1/2. Named dividers: bounded rules, centred flanked name.
                # ---------------------------------------------------------
                for uid, label, expect_truncate in (
                        ("d0000002", "short name", False),
                        ("d0000003", "long name", True)):
                    geo = page.evaluate(NAMED_GEOMETRY, uid)
                    check(f"named divider ({label}) renders two rules and a name",
                          geo and len(geo["lines"]) == 2 and geo["name"], repr(geo))
                    if not geo or len(geo["lines"]) != 2 or not geo["name"]:
                        continue
                    widths = [round(l["w"], 2) for l in geo["lines"]]
                    check(f"named divider ({label}) rules are exactly 28px wide",
                          all(abs(w - 28) < .5 for w in widths),
                          f"widths={widths} flexBasis={geo['lineFlex']}")
                    check(f"named divider ({label}) rules are far narrower than the row",
                          all(w < geo["row"]["w"] / 4 for w in widths),
                          f"widths={widths} row={geo['row']['w']}")
                    # Name centred on the row's centre line.
                    row_mid = geo["row"]["left"] + geo["row"]["w"] / 2
                    name_mid = geo["name"]["left"] + geo["name"]["w"] / 2
                    check(f"named divider ({label}) name is horizontally centred",
                          abs(name_mid - row_mid) <= 4,
                          f"name_mid={name_mid:.1f} row_mid={row_mid:.1f}")
                    left_line, right_line = geo["lines"]
                    check(f"named divider ({label}) rules flank the name",
                          left_line["right"] <= geo["name"]["left"] + .5
                          and right_line["left"] >= geo["name"]["right"] - .5,
                          repr([left_line, geo["name"], right_line]))
                    check(f"named divider ({label}) rules stay adjacent to the name",
                          (geo["name"]["left"] - left_line["right"]) <= 12
                          and (right_line["left"] - geo["name"]["right"]) <= 12,
                          repr([left_line, geo["name"], right_line]))
                    if expect_truncate:
                        check("long divider name truncates instead of stretching the rules",
                              geo["nameTruncated"] is True, repr(geo["nameTruncated"]))
                        check("long divider name keeps the full text in the DOM",
                              geo["nameText"] == LONG_NAME, repr(geo["nameText"]))
                    check(f"named divider ({label}) has no gradient background",
                          "gradient" not in (geo["backgroundImage"] or ""),
                          repr(geo["backgroundImage"]))
                    check(f"named divider ({label}) keeps its row aria-label",
                          (geo["ariaLabel"] or "").startswith("Section divider:"),
                          repr(geo["ariaLabel"]))
                    check(f"named divider ({label}) keeps its drag-handle aria-label",
                          (geo["handleAria"] or "").startswith("Drag section:"),
                          repr(geo["handleAria"]))

                # ---------------------------------------------------------
                # 3. Unnamed divider: no gradient, flat 1px ::after rule.
                # ---------------------------------------------------------
                un = page.evaluate(UNNAMED_GEOMETRY, "d0000001")
                check("unnamed divider row exists with no rule/name spans",
                      un and un["hasLines"] == 0, repr(un))
                check("unnamed divider has no background-image (gradient dropped)",
                      un and un["backgroundImage"] == "none", repr(un["backgroundImage"] if un else None))
                check("unnamed divider draws an ::after rule",
                      un and un["afterContent"] not in (None, "none")
                      and un["afterPosition"] == "absolute", repr(un))
                check("unnamed divider ::after rule is 1px high",
                      un and un["afterHeight"] == 1, repr(un["afterHeight"] if un else None))
                check("unnamed divider ::after rule is pointer-transparent",
                      un and un["afterPointerEvents"] == "none",
                      repr(un["afterPointerEvents"] if un else None))
                check("unnamed divider still has a grab handle",
                      un and un["handle"] and un["handle"]["width"] > 0, repr(un))
                # Superseded by 24-show-divider-and-glyph-repass/01 (Bob,
                # 2026-07-21: the unnamed divider gets "only a short rule,
                # centered where their alias would go"). This stitch's
                # full-width span assertion is inverted here rather than left
                # permanently red; the flat-not-gradient ruling still stands.
                check("unnamed divider rule is short and centred, not a full-width span",
                      un and un["afterWidth"] is not None
                      and un["afterWidth"] < un["row"]["width"] * .2
                      and un["ruleCentre"] is not None
                      and abs(un["ruleCentre"] - (un["row"]["left"] + un["row"]["width"] / 2)) <= 1,
                      repr(un))
                check("unnamed divider rule does not overlap the grab handle",
                      un and un["handle"] and un["ruleCentre"] is not None
                      and un["ruleCentre"] - un["afterWidth"] / 2 >= un["handle"]["right"],
                      f"ruleCentre={un and un['ruleCentre']} handleRight="
                      f"{un and un['handle'] and un['handle']['right']}")
                check("unnamed divider keeps its row aria-label",
                      un and un["ariaLabel"] == "Section divider", repr(un["ariaLabel"] if un else None))
                check("unnamed divider keeps its drag-handle aria-label",
                      un and un["handleAria"] == "Drag section divider",
                      repr(un["handleAria"] if un else None))

                # ---------------------------------------------------------
                # 6. Focus outline still lands on a divider row.
                # ---------------------------------------------------------
                page.locator('[data-show-divider-row="d0000002"]').click()
                page.wait_for_function(
                    """() => { const r = document.querySelector('[data-show-divider-row="d0000002"]');
                               return r && r.classList.contains('focused'); }""")
                outline = page.evaluate(
                    """() => { const r = document.querySelector('[data-show-divider-row="d0000002"]');
                               const cs = getComputedStyle(r);
                               return {w: parseFloat(cs.outlineWidth) || 0, s: cs.outlineStyle}; }""")
                check("focused divider row keeps a visible outline",
                      outline["w"] > 0 and outline["s"] != "none", repr(outline))

                # ---------------------------------------------------------
                # 4. The named divider name is still click-to-edit.
                # ---------------------------------------------------------
                page.wait_for_selector(".show-inspector-panel " + title_sel("divider", "d0000002"),
                                       state="attached")
                page.locator(title_sel("divider", "d0000002")).click()
                page.wait_for_selector(input_sel("divider", "d0000002"), state="attached")
                page.locator(input_sel("divider", "d0000002")).fill("RENAMED SECTION")
                page.keyboard.press("Enter")
                page.wait_for_function(
                    """() => (document.querySelector(
                        '[data-show-divider-row="d0000002"] .show-divider-name') || {})
                        .textContent === 'RENAMED SECTION'""")
                renamed = page.evaluate(NAMED_GEOMETRY, "d0000002")
                check("committed divider name shows on the row",
                      renamed["nameText"] == "RENAMED SECTION", repr(renamed["nameText"]))
                check("renamed divider keeps 28px rules",
                      all(abs(l["w"] - 28) < .5 for l in renamed["lines"]),
                      repr([l["w"] for l in renamed["lines"]]))
                check("renamed divider row aria-label follows the new name",
                      renamed["ariaLabel"] == "Section divider: RENAMED SECTION",
                      repr(renamed["ariaLabel"]))

                check("no page-level horizontal overflow at 1280px",
                      page.evaluate("() => document.documentElement.scrollWidth "
                                    "<= document.documentElement.clientWidth + 1"))

                # ---------------------------------------------------------
                # 7. Retained screenshots, both themes.
                # ---------------------------------------------------------
                for theme in ("dark", "light"):
                    page.select_option("#theme-select", theme)
                    page.wait_for_function(
                        "(t) => document.documentElement.getAttribute('data-theme') === t",
                        arg=theme)
                    page.wait_for_timeout(150)
                    page.screenshot(path=str(HERE / f"dividers-1280-{theme}.png"),
                                    full_page=True)
                    box = page.evaluate(
                        """() => { const b = document.querySelector('.show-rows-box')
                                     .getBoundingClientRect();
                                   return {x: b.x, y: b.y, width: b.width,
                                           height: Math.min(b.height, 320)}; }""")
                    page.screenshot(path=str(HERE / f"divider-rows-{theme}.png"), clip=box)

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
