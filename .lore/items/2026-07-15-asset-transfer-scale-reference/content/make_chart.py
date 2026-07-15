#!/usr/bin/env python3
"""Generate transfer-times.svg: fleet asset transfer time on 2.4 GHz Wi-Fi.

Model: total wall time = pack_gb * devices * 8000 / mbps seconds, because
AP airtime is shared -- concurrency does not multiply aggregate goodput.
Stdlib only; rerun after editing:  python3 make_chart.py
"""

import math
import os

MBPS = 20.0            # typical effective aggregate goodput, shared 2.4 GHz airtime
FLEETS = [1, 5, 10, 20, 50]
# ordinal blue ramp (light mode), lightest = smallest fleet; validated with
# the dataviz palette validator (--ordinal, light surface #fcfcfb)
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]

SURFACE, BORDER = "#fcfcfb", "rgba(11,11,11,0.10)"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
FONT = 'system-ui, -apple-system, &quot;Segoe UI&quot;, sans-serif'

W, H = 940, 580
X0, X1, Y0, Y1 = 70, 740, 116, 516         # plot box (Y0 top, Y1 bottom)
GB_MIN, GB_MAX = 0.25, 10.0
H_MIN, H_MAX = 0.02, 70.0                  # hours

X_TICKS = [0.25, 0.5, 1, 2, 5, 10]
Y_TICKS = [(2 / 60, "2 min"), (5 / 60, "5 min"), (15 / 60, "15 min"),
           (1, "1 h"), (4, "4 h"), (8, "8 h"), (24, "24 h"), (48, "48 h")]
BELIEF_GB = 1.15


def hours(gb, devices, mbps=MBPS):
    return gb * devices * 8000.0 / mbps / 3600.0


def sx(gb):
    t = (math.log10(gb) - math.log10(GB_MIN)) / (math.log10(GB_MAX) - math.log10(GB_MIN))
    return X0 + t * (X1 - X0)


def sy(h):
    t = (math.log10(h) - math.log10(H_MIN)) / (math.log10(H_MAX) - math.log10(H_MIN))
    return Y1 - t * (Y1 - Y0)


def text(x, y, s, size=11, fill=MUTED, anchor="start", weight=None, extra=""):
    w = f' font-weight="{weight}"' if weight else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}"'
            f' fill="{fill}" text-anchor="{anchor}"{w}{extra}>{s}</text>')


parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"'
         f' viewBox="0 0 {W} {H}" role="img"'
         ' aria-label="Total transfer wall time versus asset pack size, one line per fleet size">',
         f'<rect width="{W}" height="{H}" fill="{SURFACE}" stroke="{BORDER}"/>']

parts.append(text(X0, 34, "Fleet asset transfer time on 2.4 GHz Wi-Fi",
                  16, INK, weight="600"))
parts.append(text(X0, 54, f"Total wall time to send one asset pack to every device at "
                          f"{MBPS:.0f} Mbps effective aggregate goodput", 12, INK2))
parts.append(text(X0, 70, "(shared airtime, so concurrency does not add throughput). "
                          "Halve times at 40 Mbps, double at 10 Mbps.", 12, INK2))

# legend row (identity also carried by direct end labels)
lx = X0
for n, color in zip(FLEETS, RAMP):
    parts.append(f'<rect x="{lx:.1f}" y="84" width="10" height="10" rx="2" fill="{color}"/>')
    label = f"{n} device" + ("s" if n > 1 else "")
    parts.append(text(lx + 14, 93, label, 11, INK2))
    lx += 14 + 8 * len(label) + 18

# gridlines + axis labels
for gb in X_TICKS:
    x = sx(gb)
    parts.append(f'<line x1="{x:.1f}" y1="{Y0}" x2="{x:.1f}" y2="{Y1}" stroke="{GRID}"/>')
    label = f"{gb:g}"
    parts.append(text(x, Y1 + 18, label, 11, MUTED, anchor="middle"))
for h, label in Y_TICKS:
    y = sy(h)
    parts.append(f'<line x1="{X0}" y1="{y:.1f}" x2="{X1}" y2="{y:.1f}" stroke="{GRID}"/>')
    parts.append(text(X0 - 8, y + 3.5, label, 11, MUTED, anchor="end"))
parts.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="{AXIS}"/>')
parts.append(text((X0 + X1) / 2, Y1 + 40, "asset pack size, GB (log scale)",
                  11, MUTED, anchor="middle"))
parts.append(text(16, Y0 - 10, "total wall time (log scale)", 11, MUTED))

# reference guides
y8 = sy(8)
parts.append(f'<line x1="{X0}" y1="{y8:.1f}" x2="{X1}" y2="{y8:.1f}"'
             f' stroke="{MUTED}" stroke-dasharray="4 3"/>')
parts.append(text(X0 + 6, y8 - 6, "overnight window (8 h)", 11, INK2))
xb = sx(BELIEF_GB)
parts.append(f'<line x1="{xb:.1f}" y1="{Y0}" x2="{xb:.1f}" y2="{Y1}"'
             f' stroke="{MUTED}" stroke-dasharray="4 3"/>')
parts.append(text(xb + 6, Y0 + 14, "Belief System pack (1.15 GB)", 11, INK2))

# series: straight in log-log, sampled at tick values anyway
for n, color in zip(FLEETS, RAMP):
    points = " ".join(f"{sx(gb):.1f},{sy(hours(gb, n)):.1f}" for gb in X_TICKS)
    parts.append(f'<polyline points="{points}" fill="none" stroke="{color}"'
                 ' stroke-width="2" stroke-linejoin="round"/>')
    parts.append(f'<circle cx="{xb:.1f}" cy="{sy(hours(BELIEF_GB, n)):.1f}" r="3"'
                 f' fill="{color}" stroke="{SURFACE}" stroke-width="2"/>')
    ye = sy(hours(GB_MAX, n))
    parts.append(f'<line x1="{X1}" y1="{ye:.1f}" x2="{X1 + 6}" y2="{ye:.1f}"'
                 f' stroke="{color}" stroke-width="2"/>')
    label = f"{n} device" + ("s" if n > 1 else "")
    parts.append(text(X1 + 10, ye + 3.5, label, 12, INK2))

parts.append("</svg>")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transfer-times.svg")
with open(out, "w") as f:
    f.write("\n".join(parts) + "\n")
print("wrote", out)
