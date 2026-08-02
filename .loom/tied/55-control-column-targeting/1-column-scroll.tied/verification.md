# verification — 1-column-scroll

Level: **living browser guard + full fast suite**. No hardware needed; this is
CSS layout on two documents the headless browser serves for real.

## The guard fails against the unfixed tree

`tests/verify_control_column_scroll.py` was written first and run against clean
`main` before the CSS changed, so it is a guard and not a description:

```
[FAIL] the cards body is a real scrollport -- client 1316 === scroll 1316
[FAIL] scrolling the body moves it -- scrollTop stayed at 0
[FAIL] the last parameter row is reachable inside the host
       -- last row bottom 1454 vs host bottom 830
```

That is the defect stated as its consequence. The assertion is deliberately NOT
"the cards element has `overflow-y: auto`" — it had that throughout, which is
exactly what let the bug survive review.

## After the fix

```
[PASS] the rig actually overflows the column
[PASS] the cards body is a real scrollport (scrollHeight > clientHeight)
[PASS] the column does not overflow its host
[PASS] scrolling the body moves it
[PASS] the last parameter row is reachable inside the host
[PASS] Remote's column body is a real scrollport
[PASS] Remote's column stays within the viewport
[PASS] Remote scrolls its body, not the document
[PASS] no page errors
```

Rig: real `dashboard/server.py` + `tools/simfleet.py` on free ports, headless
Chromium 1440 × 900, 40-param manifest (overflow forced from the MANIFEST, not
from the target count, so the guard stays honest if `2-multi-target-model`
collapses cards into one panel), 2 seats, 1 group.

## Remote is a regression guard, not a repair

The three Remote assertions pass **both** before and after the fix, with
identical metrics (`cardsClient 501`, `cardsScroll 1242`, `columnHeight 640`).
They are in the file because the risk of a grid-track change is that it breaks
the host that was already working — see `decisions.md` for why the instructions'
stated Remote constraint turned out to be false.

An earlier draft of this file asserted the *comment's* claim about Remote
(grows with the page, document scrolls) and failed on the unfixed tree. That
failure was the guard being wrong, not Remote — corrected before the fix landed,
which is why the pre-fix output above shows only the three Control-tab failures.

## Neighbours

* `tests/verify_control_tab.py` — **passes**. The nearest journey on the same
  surface, including its Remote half.
* `./tools/run-tests.sh fast` — **268 tests, OK.**

## Not covered

Real iPad touch behaviour on Remote. Playwright's `pointer:coarse` emulation is
not a finger, and that pass is `feature-backlog/49-remote-ipad-restyle`, which
is hardware-gated. Nothing here changes Remote's metrics, so 49 inherits no new
debt.
