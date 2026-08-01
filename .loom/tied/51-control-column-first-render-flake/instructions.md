# 51-control-column-first-render-flake

`verify_show_capture.py` intermittently times out waiting for the Control tab's
default column to paint its first card, under full-suite load only.

## The captured failure

Thread `50`, 2026-08-01, `tools/run-tests.sh browser`, on an otherwise clean
tree (run 2 of 2; run 3 immediately after was 21/21 green, and this journey
passes standalone):

```
File "tests/verify_show_capture.py", line 215, in main
    ).wait_for()
playwright._impl._errors.TimeoutError: Locator.wait_for: Timeout 15000ms exceeded.
Call log:
  - waiting for locator("#control-column-host .live-card[data-live-scope=\"all\"]") to be visible
```

The step before it is `page.wait_for_selector("#ws-status.online")`, so the
socket was open and 15 s elapsed with no card.

## Why this is not thread 50's fix

`50` found and fixed a genuine host-scoping defect in the preset journeys'
`open_authoring` helper — a gotcha-16 binding wait that reached page-wide. That
is a *handler-binding* race on an element that exists. This is different: the
element never appears at all, and there is no binding wait involved. Fixing one
does not address the other, and `50` did not claim it did.

## Where to look first (hypotheses, not conclusions)

The column's first paint is gated twice, and either gate could hold:

1. **`venueKnown` in `control-host.js:276`.** Columns render only after the
   first `state` message; `device_update` deliberately cannot trigger a first
   render (that gate is `08/4/3-chrome-demotions`, and it is correct — removing
   it re-erases stored layouts). `#ws-status.online` says the socket opened, not
   that `state` arrived. Check whether the server's on-connect `state` can be
   delayed or dropped under load.
2. **`isInteracting?.()` in `control-column.js:354`.** `renderCards` returns
   early while the host reports an interaction, and `47-live-param-kinds-flake`
   (`edb0a5f`) *widened* that guard to cover keyboard focus, including a
   deferred reassertion. A guard stuck true would suppress every subsequent
   heartbeat render too, which matches a 15 s silence better than a single
   missed message does. Whether it can be held on a freshly loaded page with no
   focused control is the question.
3. **Empty `declarations`.** `available` is `declarations.length > 0`; a card
   still renders without them, so this most likely does *not* explain a missing
   element — confirm rather than assume.

Distinguish (1) from (2) before changing anything: instrument, do not patch.
The difference matters because (1) is a test that needs a better wait, while (2)
would be an **operator-facing defect** — a Control tab that silently never
paints — which is exactly the call `47` got right the first time.

## Scope note

Diagnose first. If it is (1), the fix belongs in the journey. If it is (2), the
fix belongs in `control-column.js`/`control-host.js` and needs a guard of its
own. Do not "fix" it by lengthening the timeout.

## Prior art

* `46-control-surface-probe-race` (tied) — the first of this family.
* `47-live-param-kinds-flake` (tied, `edb0a5f`) — the keyboard-focus render
  guard; its `decisions.md` explains the interaction guard this stitch suspects.
* `50-state-broadcast-argument` — captured this failure; see its
  `verification.md` for the four-run record and which runs are void as evidence.
