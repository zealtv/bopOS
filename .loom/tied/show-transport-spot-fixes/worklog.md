# Show transport spot-fixes worklog

## Logic checked

- Exclusive playback makes a second Stop-all control and a `0/1 playing`
  count redundant; the global active-step Stop remains.
- The divider grip was centered by CSS while step grips start at the row's
  left padding.
- Paused steps kept the 500 ms full-DOM countdown render alive, and unrelated
  fleet-state broadcasts also rebuilt the Show DOM. Either could replace a
  newly rendered Resume button between pointer-down and click.
- Progress width was updated only by those 500 ms rebuilds, hence the stepped
  appearance. The Dashboard cue surface already established the appropriate
  CSS-keyframe pattern.

## Outcome

- Removed Stop-all and the playing-count output; retained the single
  active-step global Stop.
- Divider and step grips now share the same x-position.
- Timed progress animates linearly in CSS from the authoritative current
  fraction to 100% over the server-reported remaining duration, freezes on
  pause, and honors reduced-motion preference.
- The 500 ms timer now updates only remaining-time text and stops while paused.
  Show DOM renders for installation state are filtered to cue lead, staged
  manifest, Seat target, and Group target changes, so heartbeat/device churn no
  longer replaces transport controls.
- Updated the final Show-polish handoff. No `.pd` files changed.

## Verification

- Focused real-dashboard/two-client browser verifier
  `verify_show_transport_spot_fixes.py` (amended tied p3 regression): 15/15
  passed. It proves continuous CSS movement on one connected element beyond
  the old 500 ms boundary, stable/immediately clickable Resume, redundant UI
  absence, exact grip alignment, transport behavior, cue scheduling and
  persistence, legacy normalization, and no browser errors.
- Amended tied p2 exclusive/progress verifier: 9/9 passed; visual progress is
  measured from rendered geometry rather than the authoritative inline start
  width, and paused fill remains frozen.
- Tied p4 scrollbox verifier: 12/12 passed; its two labels now say countdown
  “update” rather than the retired full render.
- Tied p6 drag/keyboard verifier: 11/11 passed, including divider drag.
- `node --check dashboard/static/js/show.js` and `git diff --check` passed.

No hardware, iPad/touch-device, audio, or audible PD verification was run.
Verifier-regenerated screenshots were restored; Bob's untracked
`dashboard/shows/` remains untouched.
