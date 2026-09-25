# Handoff — next four software stitches

Date: 2026-07-20

## Current state

`audition-automation-parity` is fully tied and accepted on the real
macOS/CoreAudio workflow. The Loom has no claimed work. Execute the next four
software stitches in the order below, one stitch at a time, using the normal
claim → work → verify → tie protocol.

Bob's untracked `dashboard/shows/` is working material and must remain
untouched unless he explicitly puts it in scope.

## 1. Light/dark surfaces and theme toggle

Stitch: `dashboard-theme-toggle/theme-1-surfaces-and-toggle`

Read its stitch instructions before starting. Theme-0's bop palette is already
tied; this child completes the remaining surface tokenization and adds the
persistent system/light/dark toggle to both Dashboard pages.

Key outcomes:

- tokenize remaining hardcoded surface colors in both stylesheets;
- add the same persistent toggle to `index.html` and `facilitator.html`;
- default to system preference and update `data-theme` plus theme-color;
- verify text/mark contrast, spatial view, Show pills, and automation markers;
- retain dark and light screenshots for Bob's review.

Gate: focused Playwright coverage passes on both pages, including persistence
and emulated system preference. Tie the child, then tie the parent theme thread
if it has no remaining children.

## 2. Bopping initial-load spinner

Stitch: `dashboard-loading-spinner`

Build this after theme-1 so it uses the final light/dark tokens rather than
introducing provisional colors.

Key outcomes:

- render the loading treatment from initial HTML/CSS before application JS;
- keep it visible until the first WebSocket `state` has been applied;
- dismiss it permanently for the steady-state session;
- do not replace or duplicate the existing reconnect indication;
- provide a rhythmic CSS treatment and a reduced-motion alternative.

Gate: Playwright proves the spinner exists before delayed state, disappears
after state application, and does not return. Retain a review screenshot.

## 3. Automatic live-parameter catch-up

Stitch: `live-param-catchup`

Replay a Seat's staged-manifest live parameters when a newly appearing device
has converged on that Seat. Reuse the existing manual replay behavior and the
same convergence/rate-limit discipline as assignment and group catch-up.

Key outcomes:

- replay only identities in `live_control_declarations()`;
- send only after the matching-id heartbeat convergence gate;
- cover physical and Simulation/audition devices consistently;
- retain the manual Send all action;
- prevent steady-state heartbeats from forming a resend loop.

Gate: a focused simfleet regression demonstrates assignment followed by
parameter replay after reconnection, with no repeated steady-state sends.

## 4. Patch lifecycle `/notify`

Stitch: `notify-patch-lifecycle`

Add the already-ratified `/notify updatepatch` event to both active-patch pull
and patch-switch callbacks in `python/bopos.py`.

Key outcomes:

- notify the current engine before any stop/swap operation;
- use the same `updatepatch` symbol for update and switch;
- leave the six existing lifecycle notification symbols unchanged;
- do not edit `.pd` files. Record that Bob's reference patch route should
  recognize `updatepatch` if that note is not already sufficient.

Gate: browser-free verification proves notification reaches the engine surface
before `stop-engine.sh` is invoked for both callbacks.

## Working protocol

At each boundary:

1. Run `./.loom/loom.sh status` and claim only the next stitch above.
2. Follow `docs/VERIFICATION.md`; keep focused verification and exact results
   inside the stitch so they survive tying.
3. Preserve unrelated worktree changes and never edit `.pd` files.
4. Tie and commit the completed stitch before claiming the next one.

After stitch 4, return to the host Loom for the stage-12 documentation
close-out unless Bob changes the priority.
