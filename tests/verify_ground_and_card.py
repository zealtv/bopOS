#!/usr/bin/env python3
"""Design-language §12 (ground and card) as a living invariant.

Bob, 2026-07-30, from a tab-by-tab review of the shipped app: `--bg` is the
workspace ground and is visible ONLY as gutter between cards. Content lives on
a card. A control sitting straight on the ground, or a bordered region with no
background, is the specific mistake -- "the pink defines the workspace from the
chrome", and anything more reads as unfinished.

WHY THIS IS A BROWSER JOURNEY AND NOT A SOURCE GUARD. The obvious cheap check
is `05d`'s shape: grep for `background:var(--bg)` outside `html`/`body`.
`11-ground-and-card-audit` ran exactly that, and it caught NEITHER of the two
real defects on the tree:

  * the Assets tab's refresh button had no rule at all -- `03-chrome-reclamation`
    deleted the heading it used to sit beside, leaving the button alone on the
    ground. The offending declaration is the one nobody wrote;
  * the Show tab's inspector shell inherited `border-right` from a bare `aside`
    rule left over from the retired two-column `.layout` shell, painting a 1px
    line on the ground down the full height of the tab. The rule names neither
    `--bg` nor the Show tab.

Both are only visible once the cascade has resolved against real markup, so the
check has to run in a browser. What it asks of every painted element is the one
question §12 answers: walk up to the first ancestor that paints a background,
and if that ancestor is the page, this thing is on the ground.

Two allowances, both narrow and both named rather than pattern-matched:
`.initial-loading` is a full-viewport boot overlay -- while it is up it IS the
page -- and `.tab-panel` is deliberately transparent, because it is the
ground's window and the fix is always to give the CONTENT a card.

Owned by code surface (style.css, facilitator.css and the component
stylesheets; index.html's tab markup).
"""

import json
import os
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = parent

FAILURES = []
RESERVED = set()
UID_A = "02:53:49:4d:00:01"
UID_B = "02:53:49:4d:00:02"

# A control paints its own face, so "does it have a background?" cannot be the
# filter for one -- every button carries `background:var(--control)`. The first
# draft of this probe skipped self-painted elements and reported the Assets
# button as fine. Containers keep that filter (a container that paints its own
# face IS a card); controls are always resolved against their ancestors.
PROBE = r"""
() => {
  const page = getComputedStyle(document.documentElement).backgroundColor;
  const opaque = (c) => c && c !== "transparent" &&
                        !/rgba\(0,\s*0,\s*0,\s*0\)/.test(c);
  const label = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += "#" + el.id;
    if (el.className && typeof el.className === "string")
      s += "." + el.className.trim().split(/\s+/).slice(0, 3).join(".");
    return s;
  };
  const CONTROL = "button,input,select,textarea,a,summary,[role=button]";
  const ALLOWED = ".initial-loading";
  const out = [];
  for (const el of document.querySelectorAll("body *")) {
    if (el.closest(ALLOWED)) continue;
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") continue;
    const box = el.getBoundingClientRect();
    if (box.width < 2 || box.height < 2) continue;
    // A closed <details> suppresses its contents with `content-visibility`,
    // not `display:none`, so they still report a box (gotcha 21). They are not
    // painted, so they are not on the ground.
    if (el.closest("details:not([open]) > :not(summary)")) continue;
    if (el.closest("[hidden]")) continue;

    const isControl = el.matches(CONTROL);
    const edge = cs.borderTopWidth !== "0px" || cs.borderLeftWidth !== "0px" ||
                 cs.borderBottomWidth !== "0px" ||
                 cs.borderRightWidth !== "0px" || cs.borderRadius !== "0px";
    if (!isControl && !edge) continue;
    if (!isControl && opaque(cs.backgroundColor)) continue;

    let host = el.parentElement, hostBg = null;
    while (host && host !== document.documentElement) {
      const hb = getComputedStyle(host).backgroundColor;
      if (opaque(hb)) { hostBg = hb; break; }
      host = host.parentElement;
    }
    if (hostBg === null) { host = document.documentElement; hostBg = page; }
    if (hostBg !== page) continue;

    out.push({
      el: label(el), host: label(host),
      kind: isControl ? "control" : "edge",
      rect: [Math.round(box.x), Math.round(box.y),
             Math.round(box.width), Math.round(box.height)],
    });
  }
  return { page, findings: out };
}
"""


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""), flush=True)
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
    raise RuntimeError("could not reserve a local port")


def stop_process(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def wait_http(url, process):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before serving HTTP")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not serve HTTP")


def make_fixture(root):
    patches = os.path.join(root, "patches")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(os.path.join(root, "assets"))
    os.makedirs(os.path.join(root, "sim-state"))
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"ground-and-card")
    # Every parameter KIND, so no control shape goes unrendered: a bare float
    # never exercises the toggle box, the enum select or the string field.
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({
            "engine": "test", "entrypoint": "main.bin",
            "params": [
                {"name": "gain", "kind": "float", "min": 0, "max": 1,
                 "default": .8, "dashboard": True},
                {"name": "enable-fx", "kind": "toggle", "default": 1,
                 "dashboard": True},
                {"name": "steps", "kind": "int", "min": 0, "max": 127,
                 "default": 64, "dashboard": True},
                {"name": "mode", "kind": "enum",
                 "options": ["one", "two"], "default": 0, "dashboard": True},
                {"name": "size", "kind": "float", "min": 0, "max": 1,
                 "default": .4, "path": ["reverb"], "dashboard": True},
            ],
            "events": [{"name": "strike", "arity": 2, "defaults": [64, 127],
                        "dashboard": True}],
            "caps": [], "slots": [],
        }, target)

    def seat(seat_id, name, uid, params):
        return {"id": seat_id, "name": name, "positions": [[seat_id + 1, 1]],
                "groups": [0], "bound": uid, "patch": "alpha",
                "params": params}

    base = {"gain": .8, "enable-fx": 1, "steps": 64, "mode": 0,
            "reverb/size": .4}
    state = {
        "schema": 1, "name": "Ground and card", "params_patch": "alpha",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "assets": []},
        "facilitator_commands": ["restart-engine", "reboot"],
        "groups": {"0": {"id": 0, "name": "Front"}},
        "seats": {"0": seat(0, "Freda", UID_A, dict(base)),
                  "1": seat(1, "Sparks", UID_B, dict(base, gain=.2))},
        "venue": {"width": 8, "depth": 6, "origin": [0, 0]},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path


def themed_page(browser, width, height, theme):
    page = browser.new_page(viewport={"width": width, "height": height})
    page.set_default_timeout(20000)
    page.on("dialog", lambda dialog: dialog.dismiss())
    # theme.js reads `bopos-theme` and applies it as it evaluates, so the key
    # has to be planted before the document's scripts run. Setting it after
    # `goto` -- what the archived shoot harness did -- measures the theme the
    # page booted in, not the one asked for.
    page.add_init_script(
        "try { localStorage.setItem('bopos-theme', %r); } catch (e) {}" % theme)
    return page


def report(surface, data):
    findings = data["findings"]
    detail = "; ".join(
        "{} {} at {}".format(f["kind"], f["el"], f["rect"])
        for f in findings[:6])
    check("§12: nothing sits on the ground -- " + surface,
          not findings, detail)


def report_header_controls(page, width, theme):
    """Keep every header control inside a visibly taller chrome row."""
    page.set_viewport_size({"width": width, "height": 950})
    measured = page.evaluate("""
    () => {
      const height = selector =>
        document.querySelector(selector).getBoundingClientRect().height;
      const header = height("header");
      const theme = height("#theme-select");
      const execution = height("#execution-target");
      return {header, theme, execution, tallest:Math.max(theme, execution)};
    }
    """)
    check(
        f"header clears its tallest control -- {width}px/{theme}",
        measured["header"] > measured["tallest"],
        "header={header}px, theme={theme}px, execution={execution}px".format(
            **measured))


def populate_show(page):
    if page.query_selector("#show-create-form"):
        page.fill("#show-create-name", "ground")
        page.click("#show-create-form button[type=submit]")
        page.wait_for_selector(".show-edit-bar")
    elif page.query_selector("#show-load-button"):
        page.click("#show-load-button")
        page.wait_for_selector(".show-edit-bar")
    page.click('[data-edit-bar-action="add-step"]')
    time.sleep(.5)
    row = page.query_selector(".show-step-row")
    if row:
        row.click()
    time.sleep(.6)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-ground-") as temp:
        state_path = make_fixture(temp)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log = open(os.path.join(temp, "server.log"), "w",
                          encoding="utf-8")
        fleet_log = open(os.path.join(temp, "fleet.log"), "w",
                         encoding="utf-8")
        server = fleet = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port),
                "--send-port", str(send_port), "--osc-target", "127.0.0.1",
                "--state-file", state_path,
                "--assets-dir", os.path.join(temp, "assets"),
                "--patches-dir", os.path.join(temp, "patches"),
                "--public-url", base_url,
            ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "2", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port",
                str(send_port), "--hb-interval", "0.5", "--boot-secs", "0.2",
                "--state-dir", os.path.join(temp, "sim-state"),
                "--manifest", os.path.join(temp, "patches", "alpha",
                                           "bopos.patch.json"),
                "--patches-dir", os.path.join(temp, "patches"),
                "--assets-dir", os.path.join(temp, "assets"),
            ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                # Both themes, because §12 drifted per-THEME once already: the
                # 2026-07-30 light repaint missed `:root[data-theme="light"]`
                # entirely. One width only -- `11-ground-and-card-audit`
                # measured 1280 and 1680 and they agreed on every surface, and
                # this invariant is about which ancestor paints, not about
                # where the box landed.
                for theme in ("light", "dark"):
                    page = themed_page(browser, 900, 1250, theme)
                    page.goto(base_url + "/facilitator")
                    page.wait_for_selector(
                        '.live-card[data-live-scope="all"]')
                    time.sleep(1.2)
                    report(f"Remote/{theme}", page.evaluate(PROBE))
                    page.close()

                    page = themed_page(browser, 1280, 950, theme)
                    page.goto(base_url)
                    page.wait_for_selector("#ws-status.online")
                    for width in (1280, 900, 700):
                        report_header_controls(page, width, theme)
                    page.set_viewport_size({"width": 1280, "height": 950})
                    for tab in ("control", "show", "seats", "devices",
                                "patches", "assets"):
                        page.click(f"#tab-button-{tab}")
                        time.sleep(2.0 if tab == "control" else 1.0)
                        if tab == "show":
                            # An empty Show tab renders neither the edit bar,
                            # the step rows nor the inspector -- which is where
                            # the stray `aside` rule painted on the ground.
                            populate_show(page)
                        if tab == "seats":
                            seat_row = page.query_selector(
                                "#seat-roster .device-row small")
                            if seat_row:
                                seat_row.click()
                                time.sleep(.7)
                        report(f"{tab}/{theme}", page.evaluate(PROBE))
                    # The Monitor dock is app chrome and collapsed by default.
                    # Open it over the quietest tab, so a finding reported here
                    # is the dock's own rather than the last tab's reported a
                    # second time under a misleading name.
                    page.click("#tab-button-devices")
                    time.sleep(.6)
                    page.click("[data-monitor-collapse]")
                    page.click('[data-monitor-tab="globals"]')
                    time.sleep(.8)
                    report(f"monitor/{theme}", page.evaluate(PROBE))
                    page.close()
                browser.close()
        finally:
            stop_process(fleet)
            stop_process(server)
            server_log.close()
            fleet_log.close()

    print()
    if FAILURES:
        print("FAILED: " + "; ".join(FAILURES))
        return 1
    print("Ground and card (§12) checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
