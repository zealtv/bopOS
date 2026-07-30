#!/usr/bin/env python3
"""Computed styles for PrecisionField's readout and editor, in every host.

`PrecisionField.attach` decorates an `<output>` and swaps in an `<input>` on
click, and `ValueBox.decorate` puts `.value-box` on both. Four different
stylesheets were overriding that face; this measures what each host actually
renders, before and after consolidating it.

    python precision_probe.py --doc dashboard   > before-dashboard.json
    python precision_probe.py --doc facilitator > before-facilitator.json
    python precision_probe.py --diff before.json after.json
"""
import json
import os
import sys

REPO = os.path.realpath(os.path.dirname(__file__))
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = parent
STATIC = os.path.join(REPO, "dashboard", "static")

DOCS = {
    "dashboard": ["style.css", "param-generator.css", "control-panel.css",
                  "value-box.css"],
    "facilitator": ["facilitator.css", "param-generator.css",
                    "control-panel.css", "value-box.css"],
}
PROPS = [
    "width", "minWidth", "height", "minHeight", "padding", "boxSizing",
    "backgroundColor", "color", "borderColor", "borderWidth", "borderRadius",
    "fontSize", "textAlign", "fontVariantNumeric", "cursor", "outlineColor",
    "outlineWidth", "flexGrow", "flexShrink",
]

# The three real hosts of a precision field, plus a bare div for the future one.
# `.live-param` is the control panel's row; `.params` is the patch editor's list.
HOSTS = {
    "panel-row": '<div class="live-card"><div class="live-param">{}</div></div>',
    "device-row": '<div class="device-control"><div class="live-param">{}</div></div>',
    "patch-editor": '<div class="params">{}</div>',
    "bare-div": "<div>{}</div>",
}


def dump(doc):
    from playwright.sync_api import sync_playwright
    result = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto("about:blank")
        for sheet in DOCS[doc]:
            path = os.path.join(STATIC, "css", sheet)
            if os.path.isfile(path):
                page.add_style_tag(path=path)
        for script in ("value-box.js", "precision-field.js"):
            page.add_script_tag(path=os.path.join(STATIC, "js", script))

        for host, template in HOSTS.items():
            for state in ("readout", "editor", "focus"):
                page.evaluate(
                    """([html, state]) => {
                      document.body.innerHTML = html;
                      const out = document.querySelector('output');
                      PrecisionField.attach(out, {
                        min: 0, max: 10, integer: false, value: 1.5,
                        label: 'gain'
                      }, () => {});
                      if (state !== 'readout') {
                        document.querySelector('output.precise-output').click();
                      }
                      if (state === 'focus') {
                        const f = document.querySelector('input.precise-input');
                        if (f) f.focus();
                      }
                    }""",
                    [template.format("<output>1.5</output>"), state])
                result["{}/{}".format(host, state)] = page.evaluate(
                    """(props) => {
                      const el = document.querySelector(
                        'input.precise-input, output.precise-output');
                      if (!el) return {};
                      const style = getComputedStyle(el);
                      const out = {};
                      props.forEach(p => { out[p] = style[p]; });
                      return out;
                    }""",
                    PROPS)
        browser.close()
    return result


def diff(before_path, after_path):
    before = json.load(open(before_path))
    after = json.load(open(after_path))
    for context in sorted(set(before) | set(after)):
        b, a = before.get(context, {}), after.get(context, {})
        changed = [p for p in sorted(set(b) | set(a)) if b.get(p) != a.get(p)]
        if not changed:
            print("{}: unchanged".format(context))
            continue
        print("{}:".format(context))
        for prop in changed:
            print("    {}: {!r} -> {!r}".format(prop, b.get(prop), a.get(prop)))


if __name__ == "__main__":
    if sys.argv[1] == "--diff":
        diff(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "--doc":
        print(json.dumps(dump(sys.argv[2]), indent=1, sort_keys=True))
    else:
        raise SystemExit(__doc__)
