#!/usr/bin/env python3
"""Dump computed styles for every generator-drawer element, in each host.

Behavioral verifiers cannot see a cascade slip: a rule that stops applying
leaves the DOM identical. This dumps the rendered result instead, so two runs
can be diffed across a selector rewrite.

    python cascade_probe.py <control-panel.css> > before.json   # old CSS
    python cascade_probe.py <control-panel.css> > after.json     # new CSS
    python cascade_probe.py --diff before.json after.json

The fourth context is a bare `<div>` — the mount point `06` (drawer in the
patch editor) and `08` (N columns) will create. Under the old host-scoped
selectors none of the drawer's 68 rules applied there.
"""
import json
import os
import sys

# Locate the repo by marker, not by `..` hops: tie MOVES this directory.
REPO = os.path.realpath(os.path.dirname(__file__))
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = parent
STATIC = os.path.join(REPO, "dashboard", "static")

PROPS = [
    "display", "width", "height", "minHeight", "padding", "margin",
    "marginLeft", "backgroundColor", "color", "borderColor", "borderWidth",
    "borderRadius", "fontSize", "fontWeight", "gap", "gridTemplateColumns",
    "flexDirection", "alignItems", "justifyContent", "textAlign", "opacity",
    "webkitAppearance", "position", "overflow", "boxShadow", "order",
]
HOSTS = ["live-card", "device-control", "show-inspector-section", "bare-div"]
KINDS = ["lfo", "fade", "loop"]


def diff(before_path, after_path):
    before = json.load(open(before_path))
    after = json.load(open(after_path))
    failures = 0
    for context in sorted(before):
        b, a = before[context], after[context]
        changed = [k for k in sorted(set(b) | set(a)) if b.get(k) != a.get(k)]
        print("{}: {} elements, {} differing".format(context, len(b), len(changed)))
        if not context.startswith("bare-div") and changed:
            failures += len(changed)
            for key in changed:
                print("    CHANGED", key)
    if failures:
        raise SystemExit("cascade changed in a real host: {}".format(failures))
    print("no rendered change in any real host")


def dump(css):
    from playwright.sync_api import sync_playwright
    result = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto("about:blank")
        page.add_style_tag(path=os.path.join(STATIC, "css", "style.css"))
        page.add_style_tag(path=css)
        page.add_style_tag(path=os.path.join(STATIC, "css", "value-box.css"))
        for script in ("paramspec.js", "value-box.js", "param-generator.js"):
            page.add_script_tag(path=os.path.join(STATIC, "js", script))
        for host in HOSTS:
            for kind in KINDS:
                page.evaluate(
                    """([host, kind]) => {
                      document.body.innerHTML = '';
                      const wrap = document.createElement('div');
                      if (host !== 'bare-div') wrap.className = host;
                      document.body.append(wrap);
                      const declaration = {
                        path: '/p/x', kind: 'float', min: 0, max: 10, default: 1,
                      };
                      const spec = window.ParamGenerator.blank(declaration, kind);
                      wrap.innerHTML = window.ParamGenerator.drawer(declaration, spec, {
                        actions: '<span class="live-param-gen-actions">' +
                                 '<button type="button">Value</button></span>',
                      });
                    }""",
                    [host, kind])
                result["{}/{}".format(host, kind)] = page.evaluate(
                    """(props) => {
                      const out = {};
                      const root = document.querySelector('.live-param-gen');
                      if (!root) return out;
                      [root, ...root.querySelectorAll('*')].forEach((el, index) => {
                        const style = getComputedStyle(el);
                        out[index + ':' + el.tagName.toLowerCase() + '.' +
                            (el.className || '')] =
                          props.map(p => p + '=' + style[p]).join('|');
                      });
                      return out;
                    }""",
                    PROPS)
        browser.close()
    return result


if __name__ == "__main__":
    if sys.argv[1] == "--diff":
        diff(sys.argv[2], sys.argv[3])
    else:
        print(json.dumps(dump(sys.argv[1]), indent=1, sort_keys=True))
