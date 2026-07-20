# theme-0-bop-palette-repass — the accents are still green; go holistic

**Bob, 2026-07-20:** "Have another pass at the Bop theme accents. Notice
that they're still green in the website. We're looking for something
holistic that captures the colors in the BOP screenshot… think groups,
the slider colors, any highlights, all of that sort of stuff. Also notice
the compact nature of the BOP UI — it takes cues from Ableton, so
compact, hard lines are okay, but really those colours are something we
want to capture into the interface."

This folds the `dashboard-bop-accents` repass INTO this thread (Bob's
call) — the tied safe-core pass (`.loom/tied/dashboard-bop-accents/`,
commit `4e2f78d`) deliberately held back the signature moves pending
Bob's look. This feedback **is** his look: he wants the full palette.

Reference: `.loom/threads/dashboard-theme-toggle/Screenshot 2026-07-20
at 09.43.48.png` — the `bop.casio~` PD UI. Palette cues: lavender/purple
panel surfaces, pale-cyan value fields and slider indicator ticks,
pastel-purple slider bodies, cream/pale-yellow toggle accents, hard
1px-ish borders, dense stacking.

## Do

- Re-open the tied proposal's §6 open questions and resolve them in the
  direction this feedback implies. In particular **Q1 is now answered
  yes**: move `accent-color` off `--green` — sliders cyan, toggles/
  checkboxes cream. Green retires as the default accent everywhere it's
  merely decorative; keep green only where it is *semantic* (online/OK
  status), and re-check each such use deliberately.
- Sweep the whole site (`index.html` + `facilitator.html`, `style.css` +
  `facilitator.css`): group chips/rails, slider tracks and fills, focus
  rings, selection/highlight states, active tabs, buttons, Show-tab
  pills/armed/progress states, spatial-view points, automation markers —
  every accent should come from the bop family. Amber/red semantics
  (crashed/paused/error) stay load-bearing; retune only if it sits badly
  next to the new family (proposal Q3 said leave — honour that unless it
  visibly clashes).
- Keep density and hard lines; this is a colour pass, not a layout pass.
- Every colour lands as a **token pair** (dark + light values) per the
  ratified theme-portability pattern — this stitch feeds theme-1
  directly; the light values may be provisional (proposal Q6) but must
  exist.
- Artifact: an updated palette note in the stitch (what changed vs the
  safe core, per-token), plus full-page screenshots of each tab for
  Bob's review. This is user-facing: Bob vetoes in review rather than
  gating up front, EXCEPT don't touch the Show pill 8-ramp beyond the
  proposal's pill-0 nudge (Q4) without flagging it.

## Verify

Extend the tied `verify_bop_accents.py` pattern: assert the new token
values are applied (computed styles on sliders/checkboxes/selection),
no remaining `--green` accent-color, semantic greens still present on
status badges, and contrast ≥ 4.5:1 text / 3:1 marks for the changed
pairs. Screenshots of every tab into the stitch.
