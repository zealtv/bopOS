# Verification — 05-compact-chrome

Implementation delegated to an Opus 4.8 sub-agent against `spec.md` (codex
unavailable this session). Orchestrator reviewed the CSS diff and
independently re-ran all five suites from `~/.venvs/bopos` (2026-07-21):

- `verify_compact_chrome.py` — **0 failures**: `--chrome-*` variables
  resolve; representative controls carry the decisions.md values; rows
  box bounded with a visible edge and the edit bar pinned; six
  touch-relevant control classes keep ≥44px effective targets at 768px;
  keyboard focus outline intact; no horizontal overflow at 1280/768/500;
  light+dark screenshots at 1280 and 768 retained here.
- Tied suites re-run UNMODIFIED, all **0 failures**:
  `02-inspector-sidebar`, `04-named-section-dividers`,
  `02-edit-bar-and-inline-step-name`, `03-responsive-osc-terminals`.
  (Screenshots restored afterwards.)

Two deliberate deviations from the spec's literal wording, both reviewed
and endorsed by the orchestrator:

1. `.show-edit-bar-button` keeps `min-height:40px` (not 32px): the tied
   edit-bar suite pins ≥40px, and the button was 40px before the pass —
   the 44→32 mapping never covered it. Radius/padding/touch-inset did
   change.
2. The rows-box visible bound is `box-shadow: inset 0 0 0 1px var(--line)`
   rather than a real border: `show.js` re-persists `clientHeight` (which
   excludes borders) back into `style.height` on every re-render, so a
   border ratchets the box ~2px smaller per render (≈28px over the
   sidebar suite's grow sequence) and moves the consoles. The inset
   shadow is outside the box model, so the height-persistence loop stays
   stable, no JS change needed. If a real border is ever wanted here, the
   `show.js` persistence read must switch to a border-inclusive measure
   in the same change.

Bob has not yet seen the resulting chrome; the values are variable-driven
(one place to re-tune) and the app-wide question is parked in
`06-chrome-app-wide-assessment.waiting`.
