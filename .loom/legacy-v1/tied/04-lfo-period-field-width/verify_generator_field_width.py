#!/usr/bin/env python3
"""Playwright + simfleet verification for the generator duration field width
(thread 19, stitch 04).

Defect (Bob, 2026-07-21): in the Show message inspector, an LFO's *period*
number box is obscured by the native increment/decrement spinner. The same
`.show-param-duration` grid renders every generator's duration field (LFO
period and every ramp/fade/loop segment duration), so one fix covers all of
them.

Fix under test, both in `dashboard/static/css/style.css`:

  * `.show-param-duration` unit column 70px -> 56px (the measured min-content
    width of the four-option ms/s/m/h select is 55px), plus `min-width:0` on
    the select so the narrower track actually shrinks it;
  * the `@container show-inspector (max-width:380px)` block moved *after* the
    base `.show-param-lfo` rule. It was authored before it, so its
    `.show-param-lfo{grid-template-columns:1fr}` never won the cascade and the
    LFO grid stayed two-up inside the 300px sidebar -- which is what squeezed
    the period input down to ~45px.

Checks:

1. `.show-param-duration` resolves to a 56px unit track and the LFO grid
   actually stacks inside the 300px inspector.
2. For every generator kind with a numeric duration/period arg (LFO period,
   fade segment duration, loop segment durations), a realistic multi-character
   value ("1250") is NOT clipped: Chromium reports
   `input.scrollWidth <= input.clientWidth` only when the value's text plus the
   inner spin button fit inside the input's content box. The measured text
   width + spinner width is also reported and asserted to fit.
3. The same at the inspector's normal (300px sidebar) width, with the sidebar
   collapsed + re-opened, and at 768px (stacked layout).
4. The unit select still shows "ms" untruncated (its rendered width is >= its
   own min-content width, and it does not overflow) and still carries exactly
   the four options ms/s/m/h.
5. Editing the period amount + unit still round-trips unchanged into the wire
   preview and the persisted `<amount><unit>` arg.
6. Retained light + dark screenshots of the LFO and the segment inspector.

Gotcha 10 is honoured: the fixture carries ONE message per generator kind and
the test selects each message instead of switching the generator <select>.
All comparison rects are gathered in a single page.evaluate from one scroll
state; non-active-panel elements are waited for with state="attached".
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
          + (f" -- {detail}" if detail else ""))
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


# uid -> (alias, args) : one message per generator kind, per gotcha 10.
FIXTURE_MESSAGES = [
    ("aaaa0001", "lfo period", [
        {"type": "s", "value": "lfo"}, {"type": "s", "value": "sine"},
        {"type": "f", "value": 0.0}, {"type": "f", "value": 1.0},
        {"type": "s", "value": "1250ms"},
    ]),
    ("aaaa0002", "fade segment", [
        {"type": "f", "value": 0.75}, {"type": "s", "value": "1250ms"},
    ]),
    ("aaaa0003", "loop segments", [
        {"type": "s", "value": "loop"},
        {"type": "f", "value": 0.2}, {"type": "s", "value": "1250ms"},
        {"type": "f", "value": 0.8}, {"type": "s", "value": "1250ms"},
    ]),
]


def make_fixture(root):
    root = Path(root)
    patches = root / "patches"
    assets = root / "assets"
    state_dir = root / "sim-state"
    shows = root / "shows"
    patch = patches / "widths"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"generator-field-width")
    manifest = {
        "engine": "test", "entrypoint": "main.bin", "caps": [], "slots": [],
        "params": [
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": .25, "facilitator": True},
        ],
        "cues": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    state = {
        "schema": 1, "name": "Generator field width verifier",
        "current_show": "widths", "params_patch": "widths",
        "fleet_patch": {"name": "widths", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "seats": {"0": {"id": 0, "name": "Zero", "positions": [[1, 1]],
                        "groups": [], "bound": None, "patch": "widths",
                        "params": {}}},
        "groups": {}, "next_group_id": 0,
    }
    messages = [{"uid": uid, "alias": alias, "address": "/p/gain",
                 "args": args, "target": ["all"]}
                for uid, alias, args in FIXTURE_MESSAGES]
    show = {
        "schema": 1, "name": "widths", "items": [{
            "kind": "step", "uid": "11111111", "alias": "generators",
            "messages": messages, "duration_s": 4, "play_count": 1,
            "then_actions": [{"type": "stop"}],
        }],
    }
    state_path = root / "installation.json"
    show_path = shows / "widths.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    show_path.write_text(json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path, show_path


# One evaluate, one scroll state: every duration field currently in the
# inspector, with the numbers needed to prove the value is not clipped.
MEASURE = """
() => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const out = [];
    for (const field of document.querySelectorAll('.show-param-duration')) {
        const input = field.querySelector('input[type=number]');
        const select = field.querySelector('select');
        if (!input || !select) continue;
        const ics = getComputedStyle(input);
        const scs = getComputedStyle(select);
        ctx.font = ics.font;
        const text = ctx.measureText(input.value).width;
        const padX = parseFloat(ics.paddingLeft) + parseFloat(ics.paddingRight);
        // Chromium lays the inner spin button out inside the input's content
        // box, so an intentionally-overflowing probe clone reports
        // scrollWidth = padding + text + spinner. (Reading the live input's
        // scrollWidth only yields that when it is already clipped.)
        const probe = input.cloneNode(true);
        const longValue = '1234567890123';
        probe.value = longValue;
        probe.style.position = 'absolute';
        probe.style.visibility = 'hidden';
        probe.style.width = '60px';
        probe.style.minWidth = '0';
        input.parentNode.appendChild(probe);
        const spinner = Math.max(
            0, probe.scrollWidth - padX - ctx.measureText(longValue).width);
        probe.remove();
        // Select intrinsic width: an off-DOM clone sized to min-content.
        const clone = select.cloneNode(true);
        clone.style.cssText = getComputedStyle(select).cssText;
        clone.style.position = 'absolute';
        clone.style.visibility = 'hidden';
        clone.style.width = 'min-content';
        clone.style.minWidth = '0';
        select.parentNode.appendChild(clone);
        const intrinsic = clone.getBoundingClientRect().width;
        clone.remove();
        out.push({
            label: input.dataset.paramLfo === 'period' ? 'lfo period'
                   : ('segment duration #' + out.length),
            kind: input.dataset.paramLfo === 'period' ? 'lfo' : 'segment',
            value: input.value,
            unit: select.value,
            inputClient: input.clientWidth,
            inputScroll: input.scrollWidth,
            inputRect: input.getBoundingClientRect().width,
            padX, text, spinner,
            clipped: input.scrollWidth > input.clientWidth + 0.5,
            selectRect: select.getBoundingClientRect().width,
            selectClient: select.clientWidth,
            selectScroll: select.scrollWidth,
            selectIntrinsic: intrinsic,
            selectOptions: [...select.options].map(o => o.value),
        });
    }
    return out;
}
"""


def shoot(page, selector, name):
    """Element screenshot of the generator fields (no actionability wait: the
    Show tab re-renders on every heartbeat, so nodes are never 'stable')."""
    page.evaluate("(sel) => document.querySelector(sel)"
                  ".scrollIntoView({block: 'center'})", selector)
    page.wait_for_timeout(120)
    box = page.evaluate(
        """(sel) => { const r = document.querySelector(sel).getBoundingClientRect();
            return {x: r.x, y: r.y, width: r.width, height: r.height}; }""", selector)
    page.screenshot(path=str(HERE / name), clip=box)


def assert_fields(page, context_label, expect_kinds):
    fields = page.evaluate(MEASURE)
    check(f"{context_label}: duration fields present ({expect_kinds})",
          len(fields) >= 1, repr([f["label"] for f in fields]))
    for field in fields:
        detail = (f"client={field['inputClient']:.1f} scroll={field['inputScroll']:.1f} "
                  f"pad={field['padX']:.1f} text={field['text']:.1f} "
                  f"spinner={field['spinner']:.1f}")
        check(f"{context_label}: {field['label']} value '{field['value']}' not clipped "
              f"by the spinner", not field["clipped"], detail)
        check(f"{context_label}: {field['label']} content box fits text+spinner+padding",
              field["inputClient"] + 0.5 >= field["padX"] + field["text"] + field["spinner"],
              detail)
        sdetail = (f"rect={field['selectRect']:.1f} client={field['selectClient']:.1f} "
                   f"scroll={field['selectScroll']:.1f} "
                   f"intrinsic={field['selectIntrinsic']:.1f} unit={field['unit']}")
        check(f"{context_label}: {field['label']} unit select not truncated",
              field["selectScroll"] <= field["selectClient"] + 0.5
              and field["selectRect"] + 0.5 >= field["selectIntrinsic"], sdetail)
        check(f"{context_label}: {field['label']} unit select keeps ms/s/m/h",
              field["selectOptions"] == ["ms", "s", "m", "h"],
              repr(field["selectOptions"]))
    return fields


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-generator-width-") as root:
        patches, assets, state_dir, manifest_path, state_path, show_path = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log_path = Path(root, "server.log")
        fleet_log_path = Path(root, "fleet.log")
        server_log = server_log_path.open("w", encoding="utf-8")
        fleet_log = fleet_log_path.open("w", encoding="utf-8")
        server = fleet = None
        measurements = []
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
                "--devices", "1", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.2", "--boot-secs", "0.2",
                "--state-dir", str(state_dir), "--manifest", str(manifest_path),
                "--patches-dir", str(patches), "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page_errors = []
                # one type-aware dialog handler
                context = browser.new_context(viewport={"width": 1280, "height": 1000})
                page = context.new_page()
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept("ok")
                        if dialog.type == "prompt" else dialog.accept())
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="11111111"]')

                def focus(uid):
                    page.locator(f'[data-show-message-focus="{uid}"]').click()
                    page.wait_for_selector(f'[data-show-message-editor="{uid}"]',
                                           state="attached")
                    page.wait_for_selector(".show-param-duration", state="attached")

                # ---- the fix itself ----
                # 1. Unit track is 56px once a duration field exists.
                focus("aaaa0001")
                grid = page.evaluate(
                    """() => {
                        const el = document.querySelector('.show-param-duration');
                        if (!el) return null;
                        const cs = getComputedStyle(el);
                        return {cols: cs.gridTemplateColumns, gap: cs.columnGap,
                                selMinWidth: getComputedStyle(el.querySelector('select')).minWidth};
                    }""")
                check("unit column track is 56px",
                      grid and grid["cols"].strip().endswith("56px"), repr(grid))
                check("unit select carries min-width:0",
                      grid and grid["selMinWidth"] in ("0px", "0"), repr(grid))

                # The @container rule that stacks the LFO grid at narrow
                # inspector widths must actually win the cascade (it was
                # authored before the base .show-param-lfo rule, so it never
                # applied -- that dead override is what left the period field
                # ~45px wide inside the 300px sidebar).
                lfo_cols = page.evaluate(
                    """() => {
                        const el = document.querySelector('.show-param-lfo');
                        return el ? getComputedStyle(el).gridTemplateColumns : null;
                    }""")
                check("LFO grid stacks to one column inside the 300px inspector",
                      lfo_cols and len(lfo_cols.split()) == 1, repr(lfo_cols))

                # ---- 2/3. Every generator kind, inspector at its normal width ----
                sidebar = page.evaluate(
                    "() => document.querySelector('.show-inspector-shell').getBoundingClientRect().width")
                check("inspector sidebar is at its normal 300px width",
                      abs(sidebar - 300) < 1.5, repr(sidebar))
                measurements.append(("1280px, sidebar open, lfo",
                                     assert_fields(page, "1280/lfo", "lfo period")))
                page.select_option("#theme-select", "dark")
                page.wait_for_function(
                    "() => document.documentElement.getAttribute('data-theme') === 'dark'")
                page.wait_for_timeout(150)
                shoot(page, ".show-param-lfo", "lfo-fields-1280-dark.png")

                focus("aaaa0002")
                measurements.append(("1280px, sidebar open, fade",
                                     assert_fields(page, "1280/fade", "segment duration")))
                focus("aaaa0003")
                measurements.append(("1280px, sidebar open, loop",
                                     assert_fields(page, "1280/loop", "segment durations")))
                shoot(page, ".show-param-segments", "segments-1280-dark.png")

                # light theme screenshots at the same state
                page.select_option("#theme-select", "light")
                page.wait_for_function(
                    "() => document.documentElement.getAttribute('data-theme') === 'light'")
                page.wait_for_timeout(150)
                shoot(page, ".show-param-segments", "segments-1280-light.png")
                measurements.append(("1280px, light theme, loop",
                                     assert_fields(page, "1280/light/loop", "segment durations")))
                focus("aaaa0001")
                page.wait_for_timeout(100)
                shoot(page, ".show-param-lfo", "lfo-fields-1280-light.png")
                measurements.append(("1280px, light theme, lfo",
                                     assert_fields(page, "1280/light/lfo", "lfo period")))
                page.select_option("#theme-select", "dark")
                page.wait_for_function(
                    "() => document.documentElement.getAttribute('data-theme') === 'dark'")

                # ---- collapse + re-open the inspector sidebar ----
                page.click("[data-inspector-toggle]")
                page.wait_for_selector(".show-workspace.show-inspector-collapsed",
                                       state="attached")
                collapsed = page.evaluate(
                    "() => document.querySelectorAll('.show-param-duration').length")
                check("collapsed sidebar hides the inspector form entirely",
                      collapsed == 0, repr(collapsed))
                page.click("[data-inspector-toggle]")
                page.wait_for_selector(".show-param-duration", state="attached")
                measurements.append(("1280px, re-opened sidebar, lfo",
                                     assert_fields(page, "1280/reopened/lfo", "lfo period")))

                # ---- 5. round-trip of amount + unit ----
                page.fill('[data-param-lfo="period"]', "1250")
                page.locator('[data-param-lfo="period"]').blur()
                page.select_option('[data-param-lfo="period-unit"]', "ms")
                page.wait_for_timeout(250)
                preview = page.locator("#show-wire-preview").inner_text()
                check("wire preview keeps the <amount><unit> period string",
                      "1250ms" in preview, repr(preview))
                page.select_option('[data-param-lfo="period-unit"]', "s")
                page.wait_for_timeout(250)
                preview = page.locator("#show-wire-preview").inner_text()
                check("changing the unit round-trips into the wire preview",
                      "1250s" in preview, repr(preview))
                saved = json.loads(show_path.read_text(encoding="utf-8"))
                args = [a["value"] for a in saved["items"][0]["messages"][0]["args"]]
                check("persisted LFO arg keeps the <amount><unit> grammar",
                      "1250s" in [str(a) for a in args], repr(args))
                # restore
                page.select_option('[data-param-lfo="period-unit"]', "ms")
                page.wait_for_timeout(200)
                measurements.append(("1280px, after edit, lfo",
                                     assert_fields(page, "1280/edited/lfo", "lfo period")))
                context.close()

                # ---- 768px stacked layout ----
                narrow = browser.new_context(viewport={"width": 768, "height": 1000},
                                             has_touch=True)
                np = narrow.new_page()
                np.on("pageerror", lambda error: page_errors.append(f"768: {error}"))
                np.on("dialog", lambda dialog: dialog.accept("ok")
                      if dialog.type == "prompt" else dialog.accept())
                np.goto(base_url)
                np.wait_for_selector("#ws-status.online", state="attached")
                np.click("#tab-button-show")
                np.wait_for_selector('[data-show-step-row="11111111"]')
                np.eval_on_selector('[data-show-step-row="11111111"]', "e => e.click()")
                np.wait_for_selector('[data-show-message-focus="aaaa0001"]', state="attached")
                np.eval_on_selector('[data-show-message-focus="aaaa0001"]', "e => e.click()")
                np.wait_for_selector(".show-param-duration", state="attached")
                measurements.append(("768px, lfo", assert_fields(np, "768/lfo", "lfo period")))
                np.eval_on_selector('[data-show-message-focus="aaaa0003"]', "e => e.click()")
                np.wait_for_selector(".show-param-duration", state="attached")
                measurements.append(("768px, loop",
                                     assert_fields(np, "768/loop", "segment durations")))
                check("no page-level horizontal overflow at 768px", np.evaluate(
                    "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
                narrow.close()

                check("browser emitted no page errors", not page_errors, repr(page_errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

        print("\n--- measurements ---")
        for label, fields in measurements:
            for field in fields:
                print(f"{label:38s} {field['label']:20s} "
                      f"input rect={field['inputRect']:.1f} client={field['inputClient']:.1f} "
                      f"scroll={field['inputScroll']:.1f} pad={field['padX']:.1f} "
                      f"text={field['text']:.1f} spinner={field['spinner']:.1f} | "
                      f"select rect={field['selectRect']:.1f} "
                      f"intrinsic={field['selectIntrinsic']:.1f}")

        if FAILURES:
            print("\nserver log tail:\n", server_log_path.read_text(encoding="utf-8")[-4000:])
            print("\nfleet log tail:\n", fleet_log_path.read_text(encoding="utf-8")[-4000:])

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
