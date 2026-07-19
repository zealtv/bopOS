# p1-zero-value-and-transport-bugs

Two operator-facing bugs Bob hit, plus two small transport annoyances in
the same code.

1. **Parameter values can't be set to 0.** Almost certainly falsy-chain
   fallbacks in `show.js` — `renderParamBuilder` does
   `argValue(message.args?.[0]) || declaration.default || ""`, so a stored
   `0` falls through to the default (and `applyModeDefault` /
   `renderRawArg` have sibling `||` chains worth auditing). Fix with
   null-coalescing throughout the message builder; audit every `||` on a
   value that can legitimately be `0`. Check the live-controls surfaces
   share no copy of this bug.
2. **Transport clicks lost right after a click.** Clicking play then
   immediately stop does nothing until the WS round-trip lands —
   investigate: the row re-renders replace the buttons on every `show`/
   `show_playback` broadcast, and a click between broadcasts targets a
   button whose `data-show-action` still reflects stale state (play sends
   `step_start` twice, etc.). Make the transport honest under rapid
   clicking: either optimistic local state or verb-from-current-engine
   truth server-side (a `step_stop` on a stopped uid is already harmless —
   the fix may be as simple as sending the *intended* verb, not the
   stale-rendered one, or engine-side idempotent verb mapping). Prove with
   a rapid play→stop click pair in the verify.
3. **Next glyph legibility.** The third button while playing is "trigger
   next action now" but its glyph is too small to read as `>|` (Bob
   mistook it for play). Make the glyph legible at the compact size —
   `>>` or `>|` visibly distinct from the play triangle.
4. **Step title must not move when the transport cluster changes.** The
   pause/next buttons appearing on play currently reflow the row; reserve
   the space (fixed-width transport cell for the three-button worst case).

Verify: `verify_show_polish_bugs.py` (house pattern): set a param message
value to 0 and assert the wire sends `0` and the inspector re-renders with
0 (not the default); rapid play-then-stop leaves the step stopped; row
title x-position identical stopped vs playing; no page errors. Re-run tied
4/5/5b/5c/6 verifies; amend + log if selectors moved.
