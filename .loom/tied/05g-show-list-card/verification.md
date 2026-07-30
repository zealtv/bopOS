# Verification

Passed on 2026-07-30:

```text
./tools/run-tests.sh fast
Ran 255 tests — OK

./tools/run-tests.sh browser
19/19 browser verifiers passed
  (verify_show_reference_foundation.py and verify_show_generator_drawer.py both
   drive the real step list)
```

## Screenshots — the actual evidence

§12 is a visual invariant, so a computed-style diff proves nothing a picture
doesn't. `shoot_show.py before|after` produced four matched pairs at 1440×1000:

| file | shows |
|---|---|
| `before-show-light.png` | the reported defect: pink through the box and between every row |
| `after-show-light.png` | rows butted on a `--panel` card, single 1px gridlines |
| `before-list-dark.png` / `after-list-dark.png` | the same in dark |
| `before-list-light.png` / `after-list-light.png` | list-only crops |

The harness sets **both** theme keys (`bopos-theme` and `bopos.theme`) because
`03-chrome-reclamation` recorded that `shoot.py` wrote the wrong one and turned
every dark shot light. The dark shots here are genuinely dark.

Read the after shots for three things specifically, all present: no ground
visible inside the list's footprint, no gap between adjacent steps, and dividers
still reading as breaks rather than as gaps.

## Not verified

- **State rows were not photographed.** `focused`, `active`, `paused` and the
  armed pulse all tint `border-color`, and the `z-index:2` fix for collapsed
  borders is reasoned rather than observed — a focused row's bottom edge could
  still be overpainted if some other rule stacks above it. Driving the Show
  transport into a playing state and shooting it is the missing check; the
  browser suite exercises those classes functionally but does not look at them.
- **Resize and scroll were not exercised.** `.show-rows-box` is
  `resize:vertical` with an inset ring now over a filled background; the grip and
  scroll edges are unchanged by inspection but untested by hand.
- No Firefox, no touch, no physical device, no Pure Data, no audible checks. CSS
  only — no JS or markup changed.

## Follow-up rulings (Bob, same session)

```text
tests/verify_show_reference_foundation.py
[PASS] dividers are the same height as steps
[PASS] a selected divider rings like a step, un-clippable

./tools/run-tests.sh fast     → Ran 255 tests, OK
./tools/run-tests.sh browser  → 19/19
```

Row heights before → after: steps 34/34/34…, unnamed divider **18 → 34**, named
dividers **26 → 34**. All eleven rows now report one height.

`05g-final-list-light.png` and `05g-final-list-dark.png` show a **named** divider
selected — the worst-clipped case — with the ring complete on all four sides.

This also closes part of the "state rows were not photographed" gap noted above:
`focused` is now both measured and photographed. `active`, `paused` and the armed
pulse remain reasoned-not-observed.
