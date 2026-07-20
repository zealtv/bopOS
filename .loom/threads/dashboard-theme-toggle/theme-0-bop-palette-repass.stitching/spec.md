# theme-0 spec — resolve the held-back bop palette moves

Bob's 2026-07-20 feedback ("still green in the website… slider colors,
highlights, holistic") ratifies the signature moves the safe-core pass
(`.loom/tied/dashboard-bop-accents/`, `4e2f78d`) deliberately held for
his look. Tokens already exist in both stylesheets. This stitch applies
the remaining §6 resolutions:

**Q1 — YES (the signature move).**
- `dashboard/static/css/facilitator.css`: `input[type=range]`
  `accent-color: var(--green)` → `var(--accent-cyan)`;
  `.live-param input[type=checkbox]` `accent-color` → `var(--accent-warm)`.
- `dashboard/static/css/style.css`: both `#master-control input`
  `accent-color` rules → `var(--accent-cyan)`;
  `.membership-check input` `accent-color` → `var(--accent-warm)`.
- Sweep: any other `accent-color:var(--green)` → cyan (ranges) / warm
  (checkboxes). After this, `accent-color:var(--green)` must not appear
  in either file.

**Q2 — tint live value readouts.**
- facilitator: `.live-param output` color → `var(--accent-cyan-soft)`
  (add to the existing `.live-param output` rule; mixed state keeps its
  `--dim` override).
- style.css: `#master-control output` color → `var(--accent-cyan-soft)`.
- Do NOT touch Show-console/other outputs — live values only.

**Q4 — pill-0 cyan nudge.**
- `.show-pill-0{border-color:#3e7ba3;background:#122736;color:#9fd4f5}`
  → cyan-leaning: `border-color:#2e8a84;background:#0f2b29;color:#a8ebe6`.
  Pills 1–7 unchanged.

**Decorative green retirement.**
- `.eyebrow` color `var(--green)` → `var(--accent-soft)` (section label,
  not a status).
- KEEP green where semantic: `.dot.online/.ok`, heartbeat pulse,
  `.sync-status.in-sync`, `.copy-feedback` (success flash),
  `.patch-badge-current`, `.asset-state-current`, `.show-remaining`,
  `.show-state-playing`, step progress fills, cue scheduling ramp,
  listener heading tip. Do not touch amber/red anywhere.

**Explicitly out of scope** (flagged to Bob instead): the four
Okabe-Ito `.show-target-group` swatches (ratified colour-blind-safe
categorical set) and Show pills 1–7; `--bg/--panel/--line` surfaces
(that's theme-1); `--auto` (freshly re-ratified in ap-3).

**Verify** (new `verify_bop_palette.py`, house pattern — copy
`.loom/tied/dashboard-bop-accents/verify_bop_accents.py` shape):
1. facilitator range input computed `accent-color` == resolved
   `--accent-cyan`; live checkbox == `--accent-warm`; live output color
   == `--accent-cyan-soft`.
2. dashboard `#master-control input` == `--accent-cyan`; `.eyebrow`
   color == `--accent-soft`.
3. Zero occurrences of `accent-color:var(--green)` in either
   stylesheet (read the files).
4. `.dot.online` still resolves to `--green` (semantics intact) on the
   dashboard.
5. `data-theme="light"` stamped on root flips the range input's
   accent-color to the light `--accent-cyan` value.
6. Show tab: `.show-pill-0` border/color are the new cyan trio; pill-1
   unchanged.
7. No console errors on either page.
