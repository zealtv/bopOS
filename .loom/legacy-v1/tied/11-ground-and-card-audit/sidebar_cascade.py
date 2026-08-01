#!/usr/bin/env python3
"""Did re-anchoring the relic `aside` rule change the two sidebars?

`05c` established the pattern: when a rule moves, measure the rendered result
rather than reasoning about specificity. The `aside` element rule reached three
elements; two of them (`.seat-sidebar`, `.device-sidebar`) must not move, and
one (`.show-inspector-shell`) is the whole point of the change.

Serves the app from a fabricated origin with `page.route` so it needs no server
at all, and swaps only `style.css` between the two measurements — the before
copy comes from `git show HEAD:`.

Usage: sidebar_cascade.py
"""
import os, subprocess, sys
from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
REPO = os.path.realpath(os.path.dirname(__file__))
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    REPO = os.path.dirname(REPO)
STATIC = os.path.join(REPO, "dashboard", "static")

PROPS = ["display", "flexDirection", "padding", "border", "borderRadius",
         "background-color", "width", "height", "margin", "gap",
         "alignItems", "justifyContent", "position", "boxSizing"]

MEASURE = """
(props) => {
  const out = {};
  for (const sel of [".seat-sidebar", ".device-sidebar",
                     ".show-inspector-shell", "#tab-devices", "#tab-seats"]) {
    const el = document.querySelector(sel);
    if (!el) { out[sel] = null; continue; }
    const cs = getComputedStyle(el);
    const r = {};
    for (const p of props) r[p] = cs[p] ?? cs.getPropertyValue(p);
    out[sel] = r;
  }
  return out;
}
"""

# The Show inspector shell only exists once show.js has rendered, and that needs
# a socket. Rather than boot the stack, inject a stand-in with the same tag and
# class — the question is purely which CSS rules match an <aside class=...>.
FIXTURE = """
<div class="tab-stage">
  <section id="tab-seats" class="tab-panel seats-tab">
    <aside class="seat-sidebar"><div>x</div><footer><button>a</button></footer></aside>
  </section>
  <section id="tab-devices" class="tab-panel devices-tab">
    <aside class="device-sidebar"><div>x</div><footer><button>a</button></footer></aside>
  </section>
  <div class="show-tab"><div class="show-workspace">
    <aside class="show-inspector-shell"><div class="show-inspector-panel">y</div></aside>
  </div></div>
</div>
"""


def measure(css_text):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 950})

        def handler(route):
            url = route.request.url
            if url.endswith("/style.css"):
                route.fulfill(status=200, content_type="text/css", body=css_text)
            elif url.endswith("/"):
                route.fulfill(status=200, content_type="text/html", body=(
                    '<!doctype html><html data-theme="light"><head>'
                    # control-panel.css declares --pad-panel/--row-h/--gap at
                    # :root and is the file BOTH documents load. Without it
                    # every var() here resolves to nothing and a padding delta
                    # measures as 0 -> 0, which is a vacuous pass.
                    '<link rel="stylesheet" href="/css/control-panel.css">'
                    '<link rel="stylesheet" href="/css/style.css">'
                    '</head><body>' + FIXTURE + '</body></html>'))
            else:
                name = url.split("/css/")[-1]
                path = os.path.join(STATIC, "css", name)
                if os.path.isfile(path):
                    route.fulfill(status=200, content_type="text/css",
                                  body=open(path, encoding="utf-8").read())
                else:
                    route.fulfill(status=404, body="")

        page.route("**/*", handler)
        page.goto("http://ground-audit.invalid/")
        result = page.evaluate(MEASURE, PROPS)
        browser.close()
        return result


head = subprocess.check_output(
    ["git", "show", "HEAD:dashboard/static/css/style.css"], cwd=REPO).decode()
work = open(os.path.join(STATIC, "css", "style.css"), encoding="utf-8").read()

before, after = measure(head), measure(work)
changed = 0
for sel in before:
    b, a = before[sel], after[sel]
    if b is None or a is None:
        print(f"{sel}: MISSING ({b is None} -> {a is None})")
        continue
    deltas = {p: (b[p], a[p]) for p in b if b[p] != a[p]}
    changed += len(deltas)
    print(f"\n{sel}: {len(deltas)} of {len(b)} properties changed")
    for p, (x, y) in deltas.items():
        print(f"    {p}: {x}  ->  {y}")
print(f"\ntotal changed properties: {changed}")
