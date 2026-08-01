#!/usr/bin/env python3
"""No handler may be wired through a non-existent IDL attribute (52).

`element.onclick = fn` works because `onclick` is an event-handler IDL
attribute. `element.onfocusin = fn` does **not**: `onfocusin`/`onfocusout` are
not IDL attributes on any element, so the assignment quietly creates an ordinary
expando property, the handler is never called, and there is no error, no
warning, and nothing to see in the DOM. Measured, not assumed —
`'onfocusin' in document.createElement('div')` is `false` where `'onfocus' in
…` is `true` (asserted live in `tests/verify_interaction_guard.py`, which is
where this rule would be caught out if a browser ever added them).

That is how the Control surface shipped two drawers whose heartbeat render
guard had never once run, taking an operator's half-typed preset name with it.
The comments above both said the guard was the same one a working surface used;
they were sincere and wrong, which is exactly why prose is not the guard here.

Use `addEventListener("focusin", …)` when the event must bubble to a container,
or `onfocus`/`onblur` on the field itself when it need not.
"""

import re
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "dashboard" / "static" / "js"

# Names that LOOK like event-handler IDL attributes and are not. Assigning any
# of these is silently inert. Extend if another is found the hard way.
NOT_IDL_ATTRIBUTES = ("onfocusin", "onfocusout")


def code_only(line):
    """The line with any `//` comment removed.

    Necessary, not fussy: the fix for this defect documents the banned names in
    prose directly above the corrected code, and a naive scan flags its own
    explanation. `://` is spared so a URL in a comment-free line survives.
    """
    stripped = line.strip()
    if stripped.startswith(("//", "*", "/*")):
        return ""
    return re.sub(r"(?<!:)//.*$", "", line)


class DomEventHandlerTests(unittest.TestCase):
    def test_no_script_assigns_a_non_idl_handler(self):
        offenders = []
        pattern = re.compile(
            r"\.(" + "|".join(NOT_IDL_ATTRIBUTES) + r")\s*=")
        for script in sorted(SCRIPTS.glob("*.js")):
            for number, line in enumerate(
                    script.read_text().splitlines(), start=1):
                if pattern.search(code_only(line)):
                    offenders.append(
                        f"{script.name}:{number}: {line.strip()}")
        self.assertEqual(
            offenders, [],
            "these assignments wire nothing at all — use addEventListener "
            "for the bubbling form; see tests/test_dom_event_handlers.py")


if __name__ == "__main__":
    unittest.main()
