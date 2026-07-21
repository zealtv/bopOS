# 21-theme-cyan-tint — decisions

Bob, 2026-07-21: *"The green tint that is throughout the website on the light
theme, for example on the named steps, I'd like to shift that a bit towards
cyan, so really it's more purple and cyan than it is purple and green."*

Successor to `theme-0-bop-palette-repass`. A retune, not a redesign: the same
tokens keep the same jobs, they just move ~15° round the hue wheel.

## 1. Semantic enumeration (done first, per the brief)

Every `var(--green)` call site in both stylesheets, with its meaning:

| Call site | Meaning |
| --- | --- |
| `.dot.online`, `.dot.ok` (facilitator) | device online |
| `.online` | online text |
| `.heartbeat-blip` + its keyframe glow | heartbeat liveness |
| `#ws-status.online::before` | socket connected |
| `.sync-status.in-sync` | clock in sync |
| `.copy-feedback` | success flash |
| `.patch-badge-current`, `.asset-inventory-note.current`, `.asset-state-current` | up-to-date |
| `.show-step-row.active`, `.show-state-playing`, `.show-remaining` | transport running |

**Ruling: `--green` is already a purely semantic token.** There is not one
decorative use left — `theme-0` retired the last of them (`.eyebrow` →
`--accent-soft`). So the conditional in the brief ("if `--green` should stop
being a hue and become a semantic token, do that") does **not** fire as a
rename: the token's *value* is already gated to success/online/playing, and
renaming it (`--green` → `--ok`) would touch two stylesheets and three tied
guards that resolve it by name, for zero visual or structural gain. Recorded
here instead as the standing invariant: **`--green` is semantic-only; new
decorative work reaches for `--accent-*`.**

Other greens deliberately left alone because they are semantic:
`--status-ok-*` (light: bg `#dcefe4`, border `#2b8054`, text `#0f6f3f`),
`--cue-progress-*`/`--cue-flash-*`, `.show-step-progress`
`rgba(63,185,120,.14)`.

## 2. What actually reads green in the light theme

Sampled from the before screenshots rather than guessed:

- **`--accent-cyan` `#147772`** — hue **177°**, i.e. on the *green* side of
  cyan. This is the biggest offender by area: every `input[type=range]`
  accent (Master, All/Group/Seat live controls, facilitator), `.seat-row
  input:focus`, `.bop-beats` bar 2.
- **`--accent-cyan-soft` `#116864`** — hue 177°. Live value readouts.
- **`--surface-alt` `#e9eef2`** — Bob's cited example. It is the background of
  `.show-divider-row + .show-step-row` (the first step under a section
  divider — the "named steps"), of `#fleet-patch-panel`, and of the
  facilitator `#cue-panel`. Nominally a blue-grey (hue 207°) but at chroma 9
  it reads as an indeterminate cold grey next to the warm purple `--bg`
  `#f4f1f8`, which is what lands as "green tint".

## 3. Change — token layer only, light theme only

| Token | Before | After | Hue |
| --- | --- | --- | --- |
| `--accent-cyan` | `#147772` | `#0E728C` | 177° → 192° |
| `--accent-cyan-soft` | `#116864` | `#0C647F` | 177° → 194° |
| `--surface-alt` | `#e9eef2` | `#e4eff2` | 207° → 193° |

Applied identically in both `style.css` and `facilitator.css`, in both the
`@media (prefers-color-scheme: light)` block and the `:root[data-theme=light]`
block. **No new hex at any call site.** Nothing else in either stylesheet
changed.

`--surface-alt` moves *toward* the accent rather than away: at chroma 14 and
hue 193 it is now a recognisable pale wash of the same cyan as the sliders,
instead of an ambiguous cold grey. That is the one judgement call here — it is
one token with exactly three call sites, so it is cheap for Bob to veto
independently if he preferred the neutral.

## 4. Dark theme

Not in scope and not touched. `--accent-cyan`/`--accent-cyan-soft`/
`--surface-alt` are the same token *names* in both themes but carry separate
values per theme block, so the light retune cannot reach dark. Dark keeps
`#8FE3DE` / `#C9F2F0` / `#172027`. Both tied dark-theme guards re-run green,
and the retained dark review screenshots are unchanged. **Flagged:** dark
`--accent-cyan` is still at hue 176°, so dark now sits a family apart from
light. If Bob wants the two themes to agree, that is a follow-up, not this
stitch.

## 5. Semantic separation preserved

The point of the enumeration was to make sure success-green and accent-cyan do
not converge. They diverge instead:

- green-vs-cyan hue gap **before: 27°** (`#0f6f3f` 150° vs `#147772` 177°)
- green-vs-cyan hue gap **after: 42°** (`#0f6f3f` 150° vs `#0E728C` 192°)

An online dot and a slider fill are now clearly different hues rather than two
shades of the same teal. Purple `--accent` sits at 246°, so the light theme
reads purple / cyan / green-for-status, in that order of prominence.

## 6. WCAG contrast, before → after

Full run in `contrast.txt`. Every touched pair holds or improves:

| Pair | Before | After |
| --- | --- | --- |
| live readout (`--accent-cyan-soft`) on `--panel` `#fff` | 6.59:1 | **6.68:1** |
| live readout on `--input` `#fbfafe` | 6.34:1 | **6.43:1** |
| live readout on `--subpanel` `#f5f2f8` | 5.94:1 | **6.02:1** |
| `--accent-cyan` mark on `#fff` (non-text; AA-large ≥3:1) | 5.37:1 | **5.52:1** |
| `--text` on `--surface-alt` | 13.29:1 | 13.25:1 |
| `--muted-strong` on `--surface-alt` | 7.59:1 | 7.57:1 |
| `--dim` on `--surface-alt` | 5.58:1 | 5.57:1 |
| `--surface-alt` vs `--bg` (surface separation) | 1.04:1 | 1.05:1 |

The three `--surface-alt` text pairs move by ≤0.04 — below any threshold, all
still far above AA (4.5:1) and AAA (7:1) where they were before. The two
foreground tokens were deliberately picked to *exceed* their old ratio rather
than merely match it (the naive hue rotation `#0F7590` would have dropped
`--accent-cyan` to 5.29:1; `#0E728C` was chosen instead).

## 7. Tied guards re-run

Re-run unmodified first, from copies inside this stitch directory:

- `dashboard-light-theme-feedback/verify_light_feedback.py` — **12/12 PASS**,
  untouched.
- `03-divider-rule-styling/verify_divider_rules.py` — **PASS**.
- `02-plain-step-divider-glyphs/verify_plain_glyphs.py` — **PASS**.
- `theme-0-bop-palette-repass/verify_bop_palette.py` and
  `theme-1-surfaces-and-toggle/verify_theme.py` — three assertions failed
  because they pin the literal light `--accent-cyan` hex. That is exactly the
  "it was asserting on a colour" case the brief anticipated. Repaired in place
  per the house rule, with inline comments naming this stitch.

**Two pre-existing guard regressions found while doing that** (both red on
`main` before any change of mine — verified by stashing the CSS and re-running;
same family as the loose `23-waveform-marker-guard-regression`):

1. `verify_bop_palette.py`'s light-range check pinned `rgb(30, 138, 132)`,
   which never was the value of `#147772` (`rgb(20, 119, 114)`). The assertion
   has been red since it was written. Corrected to the new value.
2. Both guards' `.show-pill-0` / `.show-pill-1` checks assert the **dark**
   pill trios, but since `theme-1` made pages follow the system preference —
   and headless Chromium reports *light* — the pages were in light theme by
   the time the pills were read. Repaired by stamping the theme those checks
   were written against (`select_option`/dataset), which restores their
   original intent. Guard mechanics only; no colour ruling, the categorical
   pill palette is untouched.

After the repairs both suites are green.

## 8. Explicitly not changed (flagged for Bob)

- **`.show-pill-0`–`.show-pill-7`** — the categorical Show message-pill
  palette, including pill-0's teal (`#2e8a84`, hue 176°) that `theme-0`
  nudged cyan-ward. These are call-site hex in a colour-blind-safe
  categorical set, not tokens; pill-7 is already at 187°, so re-tinting
  pill-0 to true cyan would collide with it. Same call `theme-0` made:
  categorical sets are Bob's, not autopilot's.
- **Drag-and-drop indicators `#79d6a3`** (`.show-drop-before/-after`,
  `.show-drop-row` outline) — a hardcoded green, decorative rather than
  semantic, and therefore arguably in the spirit of the ask. Left alone
  because it is not a token and the brief said token layer only. Easy
  follow-up if Bob wants it.
- Dark theme values (see §4).

## 9. Verification artefacts

- `shots.py` — the screenshot harness, `python shots.py before|after` (real `dashboard/server.py` +
  `tools/simfleet.py` on free loopback ports, Show/seat/group fixture,
  `data-theme=light` stamped, all six tabs plus the facilitator page).
- `before-*.png` / `after-*.png` — full-page light-theme captures of all six
  tabs plus the facilitator page.
- `compare-*.png` — the same seven views stitched side by side, before on the
  left.
- `contrast.py` / `contrast.txt` — the WCAG and hue arithmetic above.
