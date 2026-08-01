# 8-docs-and-handoff worklog — 2026-07-18

- `dashboard/README.md`: tab list updated (Sequencer → Show) and a new
  "The Show tab" section: steps/sections/messages naming, playback
  semantics summary (durations, play-n-times, then-actions incl. shuffle-bag
  "other", goto fallback), inspector/message builder, target chip picker,
  structural editing, show-file location (`shows/` beside the state file,
  schema pointer to `.notes/show-tab-design-2026-07-18.md`), and both
  consoles with the filter syntax (`/p/* !/sync`).
- `docs/GETTING-STARTED.md`: the "Sequencer is a reserved placeholder"
  sentence replaced with the Show description.
- `CLAUDE.md`: stage 9 recorded complete (with the deferred list: musical
  time, curves, point motion, visualisation view, multi-column — all staying
  with the gated `scene-sequencing` co-design); stage 10
  (patch-workflow-friction) is now Active.
- Simfleet audit: the only thread need was stitch 3's cue-recv type
  logging, already landed there; 5b–7 required no simulator changes. Wire
  compatibility unchanged (target lists fan out to the same per-selector
  datagrams), noted in the handoff.
- `.notes/handoff-2026-07-18-show-tab.md`: what shipped, verify-script
  index with the cross-stitch amendments, deferred items, open co-design
  decisions, and the friction-thread layout gotcha (friction-0..1 don't
  exist in the loom yet; only friction-0a was ever tied).

## Verify

- `grep -rin sequencer dashboard/ docs/ README.md CLAUDE.md`: remaining
  hits are deliberate historical references (README "previously the
  reserved Sequencer placeholder", CLAUDE.md close-out note and the
  brainstorm-gating sentence). No stale UI/doc references.
- Spot-check: re-ran `.loom/tied/4-tab-ui/verify_show_tab.py` against the
  final tree — 0 failures (and all seven show-thread verifies were re-run
  green earlier this session at stitch 7).
