#!/usr/bin/env python3
"""WCAG contrast + hue report for the 21-theme-cyan-tint token retune."""
import colorsys


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lum(h):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
    r, g, b = rgb(h)
    return .2126 * ch(r) + .7152 * ch(g) + .0722 * ch(b)


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + .05) / (lo + .05)


def hue(h):
    r, g, b = [c / 255 for c in rgb(h)]
    hh, ls, ss = colorsys.rgb_to_hls(r, g, b)
    return hh * 360


PAIRS = [
    # label, fg, bg-before, bg-after  (or fg before/after)
    ("live value readout on --panel (#fff)", ("#116864", "#0C647F"), "#ffffff"),
    ("live value readout on --input (#fbfafe)", ("#116864", "#0C647F"), "#fbfafe"),
    ("live value readout on --subpanel (#f5f2f8)", ("#116864", "#0C647F"), "#f5f2f8"),
    ("--accent-cyan as ink on --panel (#fff)", ("#147772", "#0E728C"), "#ffffff"),
    ("--accent-cyan fill vs --panel (#fff) [non-text]",
     ("#147772", "#0E728C"), "#ffffff"),
]

SURFACES = [
    ("--text on --surface-alt", "#27222d", ("#e9eef2", "#e4eff2")),
    ("--dim on --surface-alt", "#625b69", ("#e9eef2", "#e4eff2")),
    ("--muted-strong on --surface-alt", "#4f4756", ("#e9eef2", "#e4eff2")),
    ("--surface-alt vs --bg (#f4f1f8) [surface separation]",
     "#f4f1f8", ("#e9eef2", "#e4eff2")),
]

print("== foreground token retunes (light theme) ==")
for label, (before, after), bg in PAIRS:
    print(f"{label}\n   before {before} on {bg}: {ratio(before, bg):.2f}:1"
          f"   after {after} on {bg}: {ratio(after, bg):.2f}:1")

print("\n== surface token retune (light theme) ==")
for label, fg, (before, after) in SURFACES:
    print(f"{label}\n   before bg {before}: {ratio(fg, before):.2f}:1"
          f"   after bg {after}: {ratio(fg, after):.2f}:1")

print("\n== hue separation: accent cyan vs semantic green ==")
for name, h in [("--accent-cyan before", "#147772"),
                ("--accent-cyan after", "#0E728C"),
                ("--accent-cyan-soft before", "#116864"),
                ("--accent-cyan-soft after", "#0C647F"),
                ("--green (light, unchanged)", "#0f6f3f"),
                ("--status-ok-border (unchanged)", "#2b8054"),
                ("--surface-alt before", "#e9eef2"),
                ("--surface-alt after", "#e4eff2"),
                ("--accent (purple, unchanged)", "#5A4FB8")]:
    print(f"   {name:32s} {h}  hue {hue(h):6.1f} deg")
print(f"\n   green-vs-cyan hue gap before: {hue('#147772') - hue('#0f6f3f'):.1f} deg")
print(f"   green-vs-cyan hue gap after:  {hue('#0E728C') - hue('#0f6f3f'):.1f} deg")
