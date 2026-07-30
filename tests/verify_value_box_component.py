#!/usr/bin/env python3
"""Focused browser checks for the shared numeric value-box component."""

import os
import sys

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "dashboard", "static", "js", "value-box.js")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = parent

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format(
        "PASS" if condition else "FAIL", label,
        " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_content("""
      <style>
        :root {
          --row-h:24px; --input:#10161b; --control-line:#74818c;
          --radius-small:3px; --text:#e8edf1;
        }
      </style>
      <input id="float" type="number" min="0" max="10" step="any" value="1">
      <input id="integer" type="number" min="0" max="10" step="1" value="2">
      <output id="precise">3</output>
      <!-- 05b: the drawer's arg boxes used to carry spinner suppression in
           control-panel.css. That rule is gone; the component must cover them. -->
      <div class="live-card"><input id="drawer" class="live-gen-num"
        type="number" min="0" max="10" step="any" value="4"></div>
    """)
    page.add_style_tag(path=os.path.join(
        REPO, "dashboard", "static", "css", "control-panel.css"))
    page.add_style_tag(path=os.path.join(
        REPO, "dashboard", "static", "css", "value-box.css"))
    page.add_script_tag(path=os.path.join(
        REPO, "dashboard", "static", "js", "value-box.js"))
    page.add_script_tag(path=os.path.join(
        REPO, "dashboard", "static", "js", "precision-field.js"))

    page.wait_for_function(
        "document.querySelectorAll('input.value-box').length === 3")
    float_box = page.locator("#float")
    integer_box = page.locator("#integer")
    check("native number fields adopt the component",
          float_box.evaluate("el => el.classList.contains('value-box')"))
    check("standard width is 58px",
          float_box.evaluate("el => getComputedStyle(el).width") == "58px")
    check("float boxes align left",
          float_box.evaluate("el => getComputedStyle(el).textAlign") == "left")
    check("integer boxes align right",
          integer_box.evaluate("el => getComputedStyle(el).textAlign") == "right")

    page.evaluate("""
      window.seen = null;
      window.inputSeen = null;
      document.querySelector('#float').onchange = event => {
        window.seen = event.target.value;
      };
      document.querySelector('#float').oninput = event => {
        window.inputSeen = event.target.value;
      };
      void 0;
    """)
    float_box.fill("1.23456789")
    float_box.press("Enter")
    check("float commits round to six significant figures",
          page.evaluate("window.seen") == "1.23457",
          str(page.evaluate("window.seen")))
    check("normalized commits update input-backed drafts",
          page.evaluate("window.inputSeen") == "1.23457",
          str(page.evaluate("window.inputSeen")))
    integer_box.fill("6.7")
    integer_box.press("Enter")
    check("integer commits round to whole values", integer_box.input_value() == "7")
    float_box.fill("99")
    float_box.press("Enter")
    check("commits clamp to declared bounds", float_box.input_value() == "10")

    page.evaluate("""
      const field = document.createElement('input');
      field.id = 'dynamic';
      field.type = 'number';
      field.step = 'any';
      document.body.append(field);
      void 0;
    """)
    page.wait_for_function(
        "document.querySelector('#dynamic').classList.contains('value-box')")
    check("dynamically rendered fields adopt the component",
          page.locator("#dynamic").evaluate(
              "el => getComputedStyle(el).width") == "58px")

    page.evaluate("""
      window.preciseCommit = null;
      PrecisionField.attach(document.querySelector('#precise'), {
        min: 0, max: 5, integer: false, value: 3, label: 'precision'
      }, value => { window.preciseCommit = value; });
      void 0;
    """)
    precise = page.locator("#precise")
    check("precision readouts use the same 58px face",
          precise.evaluate("el => getComputedStyle(el).width") == "58px")
    precise.click()
    editor = page.locator("input.precise-input")
    check("precision editor keeps value-box geometry",
          editor.evaluate("el => getComputedStyle(el).width") == "58px")
    editor.fill("7.123456")
    editor.press("Enter")
    check("precision commits share clamping",
          page.evaluate("window.preciseCommit") == 5)

    # 05b: one face, one appearance. Native inc/dec arrows showed on every
    # numeric entry except the generator drawer's, which suppressed them with a
    # surface-scoped rule of its own.
    # `getComputedStyle(el, '::-webkit-inner-spin-button')` cannot answer this:
    # Chromium mirrors the host element's own values onto that pseudo (it
    # reports the input's width, not a spinner box), and headless does not
    # paint the spinner at all, so a screenshot probe would pass vacuously
    # (CLAUDE.md gotcha 11). Assert the mechanism that removes the buttons.
    face = "el => getComputedStyle(el).webkitAppearance"
    check("value boxes carry the spinner-free textfield face",
          float_box.evaluate(face) == "textfield", str(float_box.evaluate(face)))
    check("drawer arg boxes inherit the face from the component",
          page.locator("#drawer").evaluate(face) == "textfield",
          str(page.locator("#drawer").evaluate(face)))
    check("dynamically rendered fields inherit the face too",
          page.locator("#dynamic").evaluate(face) == "textfield",
          str(page.locator("#dynamic").evaluate(face)))

    # Removing the buttons must not remove the behavior: the arrows are gone,
    # the keyboard step is not. Event lead steps 50, so step is read from the
    # declaration rather than assumed to be 1.
    integer_box.fill("2")
    integer_box.press("ArrowUp")
    check("keyboard up still steps an integer box",
          integer_box.input_value() == "3", integer_box.input_value())
    integer_box.press("ArrowDown")
    integer_box.press("ArrowDown")
    check("keyboard down still steps an integer box",
          integer_box.input_value() == "1", integer_box.input_value())
    browser.close()

# The WebKit pseudo-element rule is the other half of the suppression and no
# DOM assertion can observe it, so pin where it lives: on the component, and
# not re-scoped onto any single surface.
def read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as handle:
        return handle.read()


component = read("dashboard", "static", "css", "value-box.css")
panel = read("dashboard", "static", "css", "control-panel.css")
check("the component owns the webkit spinner rule",
      'input[type="number"]::-webkit-inner-spin-button' in component
      and 'input[type="number"]::-webkit-outer-spin-button' in component)
check("no surface re-scopes spinner suppression",
      "spin-button" not in panel
      and "appearance:textfield" not in panel.replace(" ", ""))

print("{} checks passed, {} failures".format(19 - len(FAILURES), len(FAILURES)))
raise SystemExit(1 if FAILURES else 0)
