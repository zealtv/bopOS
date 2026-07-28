# 47-live-param-kinds-flake

`tests/verify_live_param_kinds.py` fails intermittently in `tools/run-tests.sh
browser`, always on one of the two adjacent slider assertions:

    [FAIL] slider change-commit reaches the wire numerically
           -- fleet log missing p/density=0.21
    [FAIL] an integer row steps by one to the wire
           -- fleet log missing p/steps=3

Observed 2026-07-28 during `desktop-ui-overhaul/04-event-fire-affordance`:
it failed in three consecutive full-suite runs (twice on `density`, once on
`steps`), **including a run on clean `main` with that stitch's changes
stashed**, and passed 2/2 in isolation on the changed tree. So it is a
pre-existing flake that only shows under full-suite load, not a regression —
which is exactly why it needs its own thread rather than a fix smuggled into
whatever UI stitch happens to trip it.

Same family as the tied `46-control-surface-probe-race`: a Playwright step
racing the facilitator's heartbeat re-render.

## The likely mechanism (unverified — the diagnosis is stitch 1's job)

`verify_live_param_kinds.py` around line 279 does

    page.locator(slider).press("ArrowRight")

and the comment above it records that `focus()` + `keyboard.press()` was this
file's *previous* intermittent failure, fixed by moving to `press` because it
re-checks actionability. That fix is evidently incomplete. The suspect is
CLAUDE.md Playwright gotcha (16): `bindParams` reassigns `oninput`/`onchange`
onto freshly rendered nodes after **every** heartbeat re-render, so
actionability passing is not the same as the handler being attached. A
keystroke delivered in the window between `renderCards()` writing new DOM and
`bindParams()` binding it lands on an unbound node and silently sends nothing —
and under full-suite CPU load that window widens, which fits the
only-fails-in-the-suite signature.

If that is the mechanism, the fix follows the gotcha's own advice: wait on the
*binding* (`page.wait_for_function("() => !!document.querySelector(…)?.oninput")`)
before pressing, not merely on the element. Confirm before applying — a
plausible mechanism that matches the symptom is not a diagnosis.

## Scope

1. Reproduce under load (run the browser suite in a loop, or run the journey
   with competing load) and confirm the mechanism from the page side — e.g.
   instrument whether the pressed node still carries its handler.
2. Fix the journey, not the app, unless the diagnosis turns up a real
   binding-window defect in `control-surface.js` that a live operator could
   also hit. If it *is* an app defect, say so and re-scope: an operator
   nudging a slider during a heartbeat and having it silently not send is a
   real bug, and `43-live-param-checkbox-nosend` was exactly that shape.
3. Check whether the neighbouring assertions in this file (and the same
   `press`-after-render pattern elsewhere in `tests/`) share the hole.

Verify: the browser suite green across at least 5 consecutive full runs.
