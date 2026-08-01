#!/usr/bin/env python3
"""Live §12 probe: what is actually painted on the ground?

The source scan finds `background:var(--bg)` written down. This finds the other
half of §12 — content sitting ON the ground because nothing gave it a card —
which no source pattern can see, because the offending rule is the one that was
never written.

For every painted thing on a tab it walks up to the first ancestor with a
non-transparent background and asks whether that ancestor is the page. If it
is, the thing is on the ground. §12 permits exactly one relationship to the
ground: gutter. A control, a bordered box or a text block resolving to the page
is a finding.

Usage: probe.py [output.json]
"""
import json, os, random, socket, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
REPO = os.path.realpath(os.path.dirname(__file__))
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    _parent = os.path.dirname(REPO)
    if _parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = _parent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shoot import free_port, wait_http, make_fixture, populate_show, new_page  # noqa: E402

OUT = os.path.realpath(sys.argv[1]) if len(sys.argv) > 1 else None

# Reported per element: tag, id/class, why it counts, and the ancestor chain up
# to the page, so a finding can be read without opening the browser.
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
  const out = [];
  for (const el of document.querySelectorAll("body *")) {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") continue;
    const box = el.getBoundingClientRect();
    if (box.width < 2 || box.height < 2) continue;
    // Skip anything inside a closed <details> (gotcha 21) and anything the
    // page is not currently showing.
    if (el.closest("details:not([open]) > :not(summary)")) continue;
    if (el.closest("[hidden]")) continue;

    const isControl = el.matches(CONTROL);
    const edge = (cs.borderTopWidth !== "0px" || cs.borderLeftWidth !== "0px" ||
                  cs.borderBottomWidth !== "0px" ||
                  cs.borderRightWidth !== "0px") ||
                 cs.borderRadius !== "0px";
    if (!isControl && !edge) continue;
    // A CONTAINER that paints its own face IS a card — nothing to report. A
    // CONTROL that paints its own face is still a control sitting on the
    // ground, which is the half of §12 the first run of this probe missed:
    // every button carries `background:var(--control)`, so skipping
    // self-painted elements skipped every control there is.
    if (!isControl && opaque(cs.backgroundColor)) continue;

    // First painted ancestor.
    let host = el.parentElement, hostBg = null;
    while (host && host !== document.documentElement) {
      const hb = getComputedStyle(host).backgroundColor;
      if (opaque(hb)) { hostBg = hb; break; }
      host = host.parentElement;
    }
    if (hostBg === null) { host = document.documentElement; hostBg = page; }
    if (hostBg !== page) continue;               // sits on a card: fine

    out.push({
      el: label(el), host: label(host), bg: hostBg,
      control: isControl, edge: edge,
      border: [cs.borderTopWidth, cs.borderRightWidth, cs.borderBottomWidth,
               cs.borderLeftWidth].join(" "),
      radius: cs.borderRadius, self: cs.backgroundColor,
      rect: [Math.round(box.x), Math.round(box.y),
             Math.round(box.width), Math.round(box.height)],
    });
  }
  return { page, findings: out };
}
"""


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-probe-") as temp:
        state_path = make_fixture(temp)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base = f"http://127.0.0.1:{http_port}"
        log = open(os.path.join(temp, "log.txt"), "w", encoding="utf-8")
        server = fleet = None
        report = {}
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", os.path.join(temp, "assets"),
                "--patches-dir", os.path.join(temp, "patches"),
                "--public-url", base,
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "2", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.5", "--boot-secs", "0.2",
                "--state-dir", os.path.join(temp, "sim-state"),
                "--manifest", os.path.join(temp, "patches", "bonks-pd",
                                           "bopos.patch.json"),
                "--patches-dir", os.path.join(temp, "patches"),
                "--assets-dir", os.path.join(temp, "assets"),
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                for theme in ("light", "dark"):
                    page = new_page(browser, 900, 1250, theme)
                    page.goto(base + "/facilitator")
                    page.wait_for_selector('.live-card[data-live-scope="all"]')
                    time.sleep(1.5)
                    report[f"remote/{theme}"] = page.evaluate(PROBE)
                    page.close()

                    for width in (1280, 1680):
                        page = new_page(browser, width, 950, theme)
                        page.goto(base)
                        for tab in ("control", "show", "seats", "devices",
                                    "patches", "assets"):
                            page.click(f"#tab-button-{tab}")
                            time.sleep(2.5 if tab == "control" else 1.2)
                            if tab == "show":
                                populate_show(page)
                            if tab == "seats":
                                row = page.query_selector(
                                    "#seat-roster .device-row small")
                                if row:
                                    row.click()
                                    time.sleep(.8)
                            report[f"{tab}/{width}/{theme}"] = page.evaluate(PROBE)
                        page.click("[data-monitor-collapse]")
                        page.click('[data-monitor-tab="globals"]')
                        time.sleep(1.0)
                        report[f"monitor/{width}/{theme}"] = page.evaluate(PROBE)
                        page.close()
                browser.close()
        finally:
            for p in (fleet, server):
                if p and p.poll() is None:
                    p.terminate()
                    try:
                        p.wait(timeout=5)
                    except Exception:
                        p.kill()
            log.close()

    for surface, data in report.items():
        found = data["findings"]
        print(f"\n== {surface}  (ground {data['page']})  {len(found)} on ground ==")
        seen = set()
        for f in found:
            key = (f["el"], f["host"])
            if key in seen:
                continue
            seen.add(key)
            kind = "control" if f["control"] else "edge"
            print(f"   [{kind}] {f['el']}\n         in {f['host']}  at {f['rect']}"
                  f"  border {f['border']} radius {f['radius']}")
    if OUT:
        with open(OUT, "w", encoding="utf-8") as t:
            json.dump(report, t, indent=2)
        print("\nwrote", OUT)


main()
