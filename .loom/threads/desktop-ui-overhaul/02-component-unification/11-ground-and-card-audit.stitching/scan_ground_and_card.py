#!/usr/bin/env python3
"""§12 ground-and-card source scan.

Two mechanical patterns from the stitch brief:
  A. `background:var(--bg)` on anything that is not html/body.
  B. a rule that draws a container edge (border / border-radius / inset shadow)
     and declares no background at all.

B is deliberately noisy — it is a candidate list to look at in the browser, not
a verdict. A is the real invariant.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve()
while not (ROOT / "tools" / "simfleet.py").exists():
    ROOT = ROOT.parent

CSS = sorted((ROOT / "dashboard" / "static" / "css").glob("*.css"))

RULE = re.compile(r"([^{}@]+)\{([^{}]*)\}")


def rules(text):
    """Yield (selector, body, line) for every plain declaration block."""
    for m in RULE.finditer(text):
        sel = m.group(1).strip()
        if not sel or sel.startswith("@") or sel.startswith("%") or sel[0].isdigit():
            continue
        line = text.count("\n", 0, m.start()) + 1
        yield sel, m.group(2), line


def decl(body, prop):
    m = re.search(rf"(?:^|;)\s*{prop}\s*:\s*([^;]+)", body)
    return m.group(1).strip() if m else None


PAGE = re.compile(r"^(html|body|html\s*,\s*body|body\s*,\s*html|:root)$")

a_hits, b_hits = [], []

for path in CSS:
    text = path.read_text()
    for sel, body, line in rules(text):
        bg = re.findall(r"(?:^|;)\s*background(?:-color)?\s*:\s*([^;]+)", body)
        if any("var(--bg)" in v for v in bg) and not PAGE.match(sel):
            a_hits.append((path.name, line, sel, body.strip()[:120]))

        has_bg = bool(bg)
        border = decl(body, "border") or decl(body, "border-top") or decl(body, "border-bottom")
        radius = decl(body, "border-radius")
        shadow = decl(body, "box-shadow")
        inset = shadow and "inset" in shadow
        edge = (border and border not in ("0", "none")) or radius or inset
        if edge and not has_bg:
            b_hits.append((path.name, line, sel, body.strip()[:120]))

print(f"== A. background:var(--bg) outside the page ({len(a_hits)}) ==")
for f, l, s, b in a_hits:
    print(f"  {f}:{l}  {s}\n      {{{b}}}")

print(f"\n== B. edge without background ({len(b_hits)}) ==")
for f, l, s, b in b_hits:
    print(f"  {f}:{l}  {s}\n      {{{b}}}")

sys.exit(0)
