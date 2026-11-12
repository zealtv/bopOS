#!/usr/bin/env python3
"""Classify soak buckets as LOUD or QUIET by wall clock and compare the two.

The soak records bucket offsets from its own start; the audio driver records
absolute transition timestamps. Aligning by timestamp rather than assuming the
two started together means drift cannot silently mislabel a bucket -- which
would blunt exactly the contrast the paired design exists to measure.
"""
import json, sys

soak_start = float(open(sys.argv[1]).read().strip())
sched = []
for line in open(sys.argv[2]):
    p = line.split()
    if len(p) >= 2 and p[1] in ("LOUD", "QUIET", "END"):
        sched.append((float(p[0]), p[1]))
sched.sort()

def state_at(ts):
    s = None
    for t, kind in sched:
        if t <= ts:
            s = kind
        else:
            break
    return s if s in ("LOUD", "QUIET") else None

agg = {"LOUD": [0, 0, 0], "QUIET": [0, 0, 0]}   # buckets, txns, errors
unclassified = 0
for line in open(sys.argv[3]):
    try:
        e = json.loads(line)
    except ValueError:
        continue
    if e.get("event") != "bucket":
        continue
    mid = soak_start + e["t"] + 15.0
    st = state_at(mid)
    if st is None:
        unclassified += 1
        continue
    agg[st][0] += 1
    agg[st][1] += e.get("txns", 0)
    agg[st][2] += e.get("errors", 0)

print("{:<8} {:>8} {:>12} {:>8} {:>14}".format(
    "state", "buckets", "txns", "errors", "err rate"))
for st in ("LOUD", "QUIET"):
    b, t, err = agg[st]
    rate = (err / t) if t else 0.0
    print("{:<8} {:>8} {:>12} {:>8} {:>14.3e}".format(st, b, t, err, rate))
if unclassified:
    print("unclassified buckets:", unclassified)

lb, lt, le = agg["LOUD"]
qb, qt, qe = agg["QUIET"]
print()
if lt and qt:
    lr, qr = le / lt, qe / qt
    if le == 0 and qe == 0:
        print("RESULT: zero errors in BOTH states over {} transactions.".format(lt + qt))
        print("        No detectable coupling. The bound, not a claim of perfection:")
        print("        with 0/{} loud transactions, the 95% upper bound on the loud".format(lt))
        print("        error rate is ~{:.2e} (rule of three).".format(3.0 / lt))
    elif lr > qr:
        print("RESULT: LOUD error rate is {:.2f}x QUIET -- coupling detected.".format(
            lr / qr if qr else float("inf")))
    else:
        print("RESULT: no excess in LOUD buckets (loud {:.3e} vs quiet {:.3e}).".format(lr, qr))
