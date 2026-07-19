# Handoff — 2026-07-20: parameter automation complete, bop accents landed

## State of play

Thread `16-param-automation` is **fully tied**. The Show tab authors every
§3.2 generator kind through a real builder GUI; playback delivers full
automation arg lists to the wire (a truncation bug the previous handoff's
"playback already forwards args unchanged" claim hid — fixed in
`show_engine.py`/`osc_bridge.py`); the bridge tracks the last-sent generator
per Seat/param (runtime-only) and the facilitator cards carry the **ratified**
app-wide automation treatment: static kind glyphs in the `--auto` token,
honest `auto·mixed` aggregation, offline dimming, pure-CSS phase-anchored
value-axis markers for deterministic kinds (never `sh`/`drift` — their values
are device-seeded PRNG draws the dashboard cannot know), take-over
freeze-then-drain, and a static SVG generator preview in the Show inspector.
Separately, the dashboard's accents now draw on Bob's bop.casio~ palette
(safe core only), and a `dashboard-theme-toggle` thread is filed for the
coming light/dark switch.

## Tied this session (chronological, with commits)

- `automation-2-show-builder-gui` — `fefe36b`. Codex-implemented builder +
  27-check Playwright suite; orchestrator fixed the `/p/*` playback
  truncation the delegate correctly refused to cross the file-allowlist for.
- `automation-4-waveform-ux-gate` — `1d881c9`. Design council (3 Opus
  designer lenses + verifying UI/UX judge). **Bob pre-ratified this gate**;
  the design authority is `.loom/tied/automation-4-waveform-ux-gate/judgment.md`
  (see `ratification.md` there; the one flagged reversible default: muted
  devices keep their marker moving, desaturated).
- `automation-3-animated-takeover` — `1a08fed`. Generator tracking,
  shared `paramspec.js` parser, Slice-1 static treatment, take-over;
  13-check suite.
- `automation-5-waveform-marker` — `26668d1`. Slices 2+3: CSS markers,
  fade progress, numeric outputs, Show-inspector preview; 17-check suite.
- `dashboard-bop-accents` — `4e2f78d`. Opus design proposal + safe-core
  token migration (9-check suite). **Open questions for Bob** in the tied
  `proposal.md` §6 — notably the signature cyan-slider/cream-toggle
  `accent-color` move, deliberately not applied without his look.

All verification commands and results are in each tied stitch's `notes.md`.
Verifies ran from `~/.venvs/bopos` with real server + simfleet + headless
Chromium; all suites green at handoff.

## Known wart (pre-existing, not from this session)

`.loom/tied/show-transport-spot-fixes/verify_show_transport_spot_fixes.py`
fails one check ("progress uses a continuous CSS animation") **identically on
unmodified `96202eb`** in this environment (3/3 runs; the progress element
detaches mid-measure). Everything else in that suite passes. Either an
environment/Chromium timing difference or a genuinely flaky check — worth a
look before trusting it as a gate again.

## Next work

1. Stage 12 — the host-loom `patch-workflow-friction` docs/starter-kit
   close-out (`~/repos/.loom/threads/patch-workflow-friction/`), now that
   thread 16 is finished and the docs can describe the final system.
2. `dashboard-theme-toggle` (new thread, instructions written) and the bop
   accent open questions once Bob has looked at the landed safe core.
3. Loom cosmetics: `16-param-automation` still lists as a goal/loose end
   with all children tied — close/retire the thread goal per protocol.
4. Long-standing waits unchanged (hardware gates, `scene-sequencing`
   co-design, `zero-*`, fleet distribution design).

## Session notes

- Delegation: all four implementation lanes went to GPT 5.6 Sol via codex
  (zero redos; one honest partial that exposed a real spec error). Designer
  council + accent proposal ran on Opus agents. Fable did specs, review,
  seam fixes, and all socket-bound verification.
- Healed this session: CLAUDE.md Playwright/fixture gotchas 5–7 (empty
  `#ws-status` needs `state="attached"`; stability-waiting scrolls die
  against animated controls — one-shot JS scroll; manifest validator only
  allows numeric param defaults), codex-implement and loom-autopilot skill
  learnings, and the tied a3 verifier's scroll wait.
- Bob's untracked `dashboard/shows/` briefly got swept into the a5 commit by
  a broad `git add`; caught and amended out immediately (file untouched on
  disk). Loom-autopilot skill now warns about this.

## Usage at stop (2026-07-19T~15:40Z)

- 5-hour session: 86% (resets ~19:10Z — this cap only matters mid-session)
- weekly (Fable): 83% — resets 2026-07-20T09:00Z
- weekly (all models): 59% — resets 2026-07-20T09:00Z
- codex 1-week: 57% — resets 2026-07-25T03:40Z (Bob's 20%-free rule: ceiling
  80%, comfortably honored)
