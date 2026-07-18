# 5b-compact-rows worklog — 2026-07-18

Frontend-only redesign of the Show step table to Ableton/QLab density.

## What changed

- `dashboard/static/js/show.js`
  - `stepRow()` is now a single compact line: icon transport cluster, alias,
    message pills, terse duration or countdown. Dropped from the row:
    play-n-times, then-action summary, iteration, long-form duration, and the
    state word (all live in the inspector; state is shown by icon/colour).
    Dead helpers removed: `formatDuration`, `playCountSummary`, `thenSummary`,
    `transportLabel`, `primaryTransportVerb`.
  - `terseDuration()`: `90 → 1m30`, `3600 → 1h`, `45 → 45s` (trailing seconds
    after a larger unit carry no suffix, per the stitch example `1m30`).
  - `stepTransport()` renders CSS-glyph icon buttons (play/stop/pause/next)
    keeping the same `data-show-action` verbs and per-state visibility;
    labels moved to `title`/`aria-label`.
  - `pillColourClass()`: FNV-1a hash of the trimmed alias into 8 palette
    classes (`show-pill-0..7`). **Interpretation note:** the instructions say
    colour derives from "alias (fallback: address)" but also that unaliased
    messages stay neutral; I resolved the tension as *aliased ⇒ hashed
    colour, unaliased ⇒ neutral* (the address fallback already governs the
    pill label). Same alias ⇒ same class everywhere, sessions included
    (pure function of the string).
- `dashboard/static/css/style.css`
  - Row: 4-column grid (`transport | alias | pills | time`), min-height 32px,
    3px row gap; divider slimmed to 10px.
  - `.show-icon-button`: 28×26 visual, `::after{inset:-7px}` expands the hit
    target to ≥40px (QLab-style overlap); glyphs are CSS-drawn (triangle /
    square / bars / triangle+bar) in the existing dashboard idiom.
  - 8 pill palette classes tuned for the dark theme (hue border, dark tinted
    background, light tinted text), Okabe-Ito-adjacent hues consistent with
    the GROUP_SLOTS precedent.
  - Media queries no longer reference the removed facts/then columns; the
    compact row keeps one line at all widths.

## Verify

- `verify_show_compact.py` (this dir): seeded 20-step + divider show on the
  real server + simfleet, 768×1024 touch viewport. Asserts: row height ≤40px,
  everything fits the viewport unscrolled, icon-only play button, ≥40px hit
  target via the ::after inset, playing swaps to stop/pause/next + countdown,
  stop returns to play, pill colour equal for "gain up" across two steps,
  different for "sparkle", neutral for unaliased, focus behaviour intact, no
  page errors. **Run: 0 failures.** (Aliases chosen to land in different hash
  buckets: gain up→7, sparkle→5.)
- Amended tied verifies (UI legitimately moved):
  - `tied/4-tab-ui/verify_show_tab.py`: "playing" row check is structural
    (countdown + stop/pause icons) instead of row-text words. 0 failures.
  - `tied/5-inspector/verify_show_inspector.py`: persistence check reads the
    row's alias + terse duration and confirms play-count/goto in the
    inspector instead of the removed row summary. 0 failures.
- Screenshots: `before-compact.png` / `after-compact.png` (this dir).
- `snap_show.py` reuses the verify fixture for screenshots.
