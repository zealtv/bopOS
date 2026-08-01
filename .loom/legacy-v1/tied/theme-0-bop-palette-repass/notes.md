# theme-0 notes

Bob's 2026-07-20 feedback ratified the moves the tied
`dashboard-bop-accents` safe core held back. Applied per `spec.md`
(implementation: codex/GPT 5.5; review + verification here):

- **Q1 (signature):** all range inputs → `--accent-cyan`; live/member
  checkboxes → `--accent-warm`. Zero `accent-color:var(--green)` left
  in either stylesheet.
- **Q2:** live value readouts (`.live-param output`, `#master-control
  output`) → `--accent-cyan-soft`.
- **Q4:** `.show-pill-0` retuned to a cyan trio; pills 1–7 untouched.
- Decorative green retired from `.eyebrow` → `--accent-soft`. All
  semantic greens (online dots, heartbeat, in-sync, current badges,
  playing/remaining, cue ramp) deliberately kept and verified.

**Flagged for Bob, not changed:** the four Okabe-Ito group swatches and
Show pills 1–7 stay categorical/colour-blind-safe. If "think groups"
meant retinting those four swatches into the bop family, say so — it
trades CVD safety and felt like your call, not autopilot's.

## Verify

`verify_bop_palette.py` — 14 checks, all PASS (2026-07-20): computed
`accent-color`/`color` on both pages resolve to the exact token values,
online dot stays `--green`, `data-theme="light"` flips the range accent
to the light cyan, pill-0 trio exact / pill-1 unchanged, no console
errors. Run: `~/.venvs/bopos/bin/python verify_bop_palette.py`.

Two waits in the codex-written script needed the house hardening
(`.dot.online` lives in a hidden tab panel → `state="attached"`;
devices-ready via `installation.devices`). Review screenshots:
`review-facilitator.png`, `review-dashboard.png`, `review-show-tab.png`.

theme-1 (surface tokens + the actual light/dark toggle) is the next
stitch; the light accent values remain provisional until its surfaces
land (proposal Q6).
