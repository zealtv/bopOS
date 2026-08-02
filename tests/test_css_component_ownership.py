#!/usr/bin/env python3
"""A component owns its own appearance; a surface may position it, not restyle it.

Four times in `desktop-ui-overhaul/02-component-unification` a rule belonging to
a component was written onto a surface that merely hosts it:

  * `02` — the `--chrome-*` / `--row-h` token split.
  * `05` — three Seats rules silently widening numeric fields to 64/80/88px.
  * `05b` — spinner suppression scoped to the generator drawer alone, so every
    other numeric entry in the app still painted native inc/dec arrows.
  * `05c` — all 68 of the drawer's rules scoped to the three containers it
    happened to be mounted in, so a fourth mount point would have lost the lot.

Each got past review with the principle *already written in a comment above the
offending rule*, which is why this is a check and not a fifth restatement.

WHAT MAKES IT NON-TRIVIAL: a host container is often also a component root.
`.live-card` and `.device-control` host the generator drawer AND are the control
panel's own roots, so roughly forty rules naming them are entirely legitimate.
Classifying by "does this selector name a container" produces a guard nobody
keeps. The question is whether a selector's SUBJECT belongs to the same
component as its ancestors.
"""

import os
import re
import unittest

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
CSS_DIR = os.path.join(REPO, "dashboard", "static", "css")

# Component registry. `owns` are class-name prefixes belonging to a component.
# Ownership resolves by LONGEST prefix, which is what stops `.live-param-gen`
# (the drawer) from being swallowed by `.live-param` (the control panel).
#
# Adding a component: give it its class prefixes. If a new component has no
# distinguishing prefix, give it one — a component whose classes cannot be told
# apart from its host's is the very problem this guard exists to catch.
COMPONENTS = {
    "control-panel": [".live-param", ".live-card", ".device-control"],
    "generator-drawer": [".live-param-gen", ".live-gen-"],
    "value-box": [".value-box", ".precise-input", ".precise-output"],
    "patch-editor": [".params"],
    "show-inspector": [".show-inspector-section", ".show-param"],
    "target-picker": [".target-picker", ".target-chip"],
    "control-column": [".control-column"],
}

# A surface legitimately PLACES what it hosts. These properties say where a
# thing sits, not what it looks like.
#
# Deliberately a property allowlist rather than an inline-comment opt-out: a
# comment escape hatch gets used the moment the guard is inconvenient, which is
# the failure mode this file exists to prevent.
POSITIONING = {
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "margin-block", "margin-inline", "margin-block-start", "margin-block-end",
    "margin-inline-start", "margin-inline-end",
    "order", "flex", "flex-grow", "flex-shrink", "flex-basis",
    "align-self", "justify-self", "place-self",
    "grid-area", "grid-column", "grid-row", "grid-column-start",
    "grid-column-end", "grid-row-start", "grid-row-end",
    "position", "top", "right", "bottom", "left", "inset",
    "inset-block", "inset-inline", "z-index",
}

# Known instances, kept out of the red rather than fixed inside this stitch.
# Both groups are owned by `05f-component-face-divergences`.
#
# 1. `PrecisionField`'s face (`.precise-input`, `.precise-output`) is defined in
#    FOUR places with three different widths (100%, 72px, 70px), two of them
#    painting a `--accent-cyan` border that the ratified palette reserves for
#    modulation. Consolidating changes what the control looks like OUTSIDE the
#    panel too — `PrecisionField.attach` has call sites in the Monitor dock's
#    globals — so it is an appearance change, which a guard stitch should not
#    be making.
#
# 2. The ∿ modulation glyph is deliberately DIVERGENT, not duplicated: the panel
#    draws design-language §5's bordered 18px circle, while the Show inspector
#    overrides it to a borderless transparent monospace glyph. §5 says "always
#    an 18px circle", so one of the two is wrong and only Bob can say which.
#
# Every entry names an owning stitch. An allowlist entry without an owner is a
# suppression, and `test_allowlist_entries_still_apply` stops these outliving
# their subject.
# EMPTY as of 05f (2026-07-30), and worth keeping that way. All ten entries were
# discharged rather than re-scoped: PrecisionField's face moved onto
# `value-box.css` (its cyan focus ring going purple app-wide, per §2/§5), and the
# ∿ glyph's §5 circle was re-anchored on `.live-param-mod` itself so "always an
# 18px circle" is deliverable — a rule scoped to two of the three surfaces that
# draw one is why the Show inspector could diverge at all.
ALLOWED = {}

COMMENT = re.compile(r"/\*.*?\*/", re.S)
CLASS = re.compile(r"\.-?[_a-zA-Z][\w-]*")
# Descendant, child, adjacent and general sibling combinators all separate one
# compound selector from the next.
COMBINATOR = re.compile(r"\s*[>+~]\s*|\s+")


def owner(class_name):
    """Which component owns this class, by longest matching prefix."""
    best, best_len = None, -1
    for name, prefixes in COMPONENTS.items():
        for prefix in prefixes:
            if class_name.startswith(prefix) and len(prefix) > best_len:
                best, best_len = name, len(prefix)
    return best


def rules(text):
    """Yield (selector_prelude, declaration_body) for every non-at-rule block.

    A hand-rolled walk rather than a CSS parser: the repo carries no CSS
    dependency, and this only has to understand the subset the app writes.
    """
    text = COMMENT.sub(" ", text)
    start = 0
    stack = []
    for index, char in enumerate(text):
        if char == "{":
            stack.append(text[start:index].strip())
            start = index + 1
        elif char == "}":
            body = text[start:index]
            prelude = stack.pop() if stack else ""
            # An at-rule's block holds further rules; a plain rule's holds
            # declarations. Only the latter is a rule we can judge.
            if prelude and not prelude.startswith("@") and "{" not in body:
                yield prelude, body
            start = index + 1


def split_selector_list(prelude):
    """Split on top-level commas only, so `:is(.a,.b)` survives intact."""
    parts, depth, current = [], 0, []
    for char in prelude:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return [part.strip() for part in parts if part.strip()]


def properties(body):
    found = set()
    for part in body.split(";"):
        if ":" in part:
            found.add(part.split(":", 1)[0].strip().lower())
    return {p for p in found if p and not p.startswith("--")}


def scan(text, filename="<text>"):
    """Every rule in `text` that styles one component from another's surface."""
    found = []
    for prelude, body in rules(text):
        props = properties(body)
        if not props or props <= POSITIONING:
            continue
        # Split the selector LIST without splitting `:is(.a,.b)`. Getting this
        # wrong is not academic: the first version of this guard split on every
        # comma, which turned the real `:is(hosts) .live-gen-num` into
        # fragments whose host was the unregistered `.show-inspector-section`,
        # and the guard reported the 68-rule `05c` defect as clean.
        for selector in split_selector_list(prelude):
            selector = selector.strip()
            parts = [part for part in COMBINATOR.split(selector) if part]
            if len(parts) < 2:
                continue
            # The INNERMOST identified component owns the rule; any different
            # component further left is merely hosting it. Reading right to left
            # matters because most subjects are bare elements —
            # `:is(hosts) .live-param-gen input` is a drawer rule even though
            # its subject is an `input`, and keying off the last compound alone
            # missed 15 of `05c`'s 68 rules for exactly that reason.
            owned = [(class_name, owner(class_name))
                     for part in parts
                     for class_name in CLASS.findall(part)]
            owned = [(c, o) for c, o in owned if o]
            if not owned:
                continue
            subject = owned[-1][1]
            host = next(((c, o) for c, o in owned[:-1] if o != subject), None)
            if not host:
                continue
            found.append({
                "file": filename,
                "selector": selector,
                "host": host[0],
                "host_component": host[1],
                "subject_component": subject,
                "properties": sorted(props - POSITIONING),
            })
    return found


def scan_stylesheets():
    found = []
    for filename in sorted(os.listdir(CSS_DIR)):
        if not filename.endswith(".css"):
            continue
        with open(os.path.join(CSS_DIR, filename), encoding="utf-8") as handle:
            found.extend(scan(handle.read(), filename))
    return found


class ComponentOwnership(unittest.TestCase):
    """A component's rules must not be anchored on a surface that hosts it."""

    def test_no_surface_restyles_another_component(self):
        found = [item for item in scan_stylesheets()
                 if (item["file"], item["selector"]) not in ALLOWED]
        if not found:
            return
        report = "\n".join(
            "{file}: `{selector}`\n"
            "    {host} belongs to {host_component}, but this rule styles"
            " {subject_component}.\n"
            "    properties: {props}\n"
            "    fix: anchor the rule on {subject_component}'s own root so it"
            " travels with the component to every host."
            .format(props=", ".join(item["properties"]), **item)
            for item in found)
        self.fail(
            "{} rule(s) style a component from a surface that only hosts it:"
            "\n\n{}\n\nA surface may POSITION a component (see POSITIONING in"
            " this file); it may not restyle it. If an exception is genuinely"
            " right, add it to ALLOWED with the stitch that owns it."
            .format(len(found), report))

    def test_allowlist_entries_still_apply(self):
        """An allowlist outliving its subject is a lie about the code."""
        live = {(item["file"], item["selector"]) for item in scan_stylesheets()}
        stale = sorted(key for key in ALLOWED if key not in live)
        self.assertEqual(
            stale, [],
            "ALLOWED names rules that no longer violate anything. Delete these"
            " entries: {}".format(stale))

    def test_allowlist_entries_name_an_owner(self):
        unowned = sorted(key for key, stitch in ALLOWED.items() if not stitch)
        self.assertEqual(
            unowned, [],
            "an allowlist entry without an owning stitch is a suppression:"
            " {}".format(unowned))

    def test_detects_the_shapes_it_was_written_for(self):
        # The 05c shape, VERBATIM as it shipped before that stitch. An earlier
        # draft of this guard passed a two-host paraphrase of this and still
        # reported the real file as clean; only the exact selector catches the
        # comma-splitting and unregistered-host bugs together.
        self.assertTrue(
            scan(":is(.live-card,.device-control,.show-inspector-section)"
                 " .live-gen-num { appearance:textfield; -moz-appearance:textfield }"),
            "missed the 05c shape as it actually shipped")
        self.assertTrue(
            scan(":is(.live-card,.device-control) .live-gen-num"
                 " { appearance:textfield }"),
            "missed the 05c shape")
        # The 05b shape: one declaration, same defect.
        self.assertTrue(
            scan(".live-card .value-box { appearance:textfield }"),
            "missed the 05b shape")

    def test_does_not_flag_legitimate_rules(self):
        # A component styling itself.
        self.assertEqual(
            scan(".live-param-gen .live-gen-num { appearance:textfield }"), [],
            "flagged a component styling itself")
        # The control panel styling its own row control: `.live-card` is a
        # component root as well as a host, which is the whole difficulty.
        self.assertEqual(
            scan(".live-card .live-param-mod { border-radius:50% }"), [],
            "flagged the control panel styling its own control")
        # A surface merely placing what it hosts.
        self.assertEqual(
            scan(".live-card .live-gen-num { margin-left:12px; order:2 }"), [],
            "flagged a surface positioning what it hosts")
        # Bare element subjects carry no component identity.
        self.assertEqual(
            scan(".live-card button { border-radius:7px }"), [],
            "flagged a bare element subject")


if __name__ == "__main__":
    unittest.main()
