# 14-show-tab — Show tab, first slice

Bob's 2026-07-18 braindump (verbatim in `braindump-2026-07-18.md` beside this
file) authorizes the first implemented slice of the tab the IA reserves as
"Sequencer". This thread is the decomposition. It continues the accepted sweep
numbering after `13-diagnostic-density` and takes priority over
`patch-workflow-friction` until tied.

## Relationship to the sequencer brainstorm

Compared against `.notes/sequencer-brainstorm-2026-07-15/` (full comparison to
be recorded by stitch 1):

- This **is** the brainstorm's recommended first slice in spirit — Rung 1's
  follow-action generative autonomy ("Belief System's self-running quality")
  with no contract change — but with a simpler layout: **one column of rows**
  instead of tracks × clips. A row merges "clip" and "scene": it fires a set
  of OSC messages together, then its duration/follow-actions drive flow.
- Rows holding **concrete OSC messages** (built in an inspector) instead of
  scripted clips deliberately sidesteps the Bob-gated scene-language work.
  **No syntax invention anywhere in this thread** — `scene-sequencing` stays
  paused and gated. Decomposed curves and point-motion specs are named by the
  braindump as *future* residents of the message inspector; they are out of
  scope here.
- Follow actions match the brainstorm's vocabulary (§02) plus extensions Bob
  added: `go to (alias/uid)`, next/previous *collection*, and multiple
  then-actions with random choice among them.
- Time is plain h/m/s per row for now; the brainstorm's optional musical
  time / tempo transport is explicitly later.
- "More columns later to be more Ableton like" — keep the data model and DOM
  from hard-coding single-column assumptions, but build only one column.

## Naming (Bob delegated: "feel free to choose better terms")

- **Tab: "Show"** (replaces "Sequencer"). It is the primary performance
  control tab, and it matches the brainstorm's shows-are-files philosophy.
  Internal key stays lowercase `show`.
- **Row → "step"**. Reads naturally with next/previous/trigger semantics.
- **Collection (rows delimited by empty rows) → "section"**. "Any step in
  this section" reads exactly as intended. Empty rows are **dividers** —
  structural, insertable, orderable.
- OSC message units stay **"messages"**, rendered as pills.
- Stitch 1 may refine these if something better emerges while writing the
  design note, but these are the working defaults; don't reopen naming later
  than stitch 1.

## Semantics (fixed for this slice; stitch 1 records the full spec)

- Step: uid, optional alias, ordered messages[], duration (h/m/s), play n
  times, then-actions[], forward-sync flag. Message: uid, optional alias,
  address, typed args, target selector.
- Then-action vocabulary: stop, play again, next step, previous step, any
  step in section (uniform random), other step in section (shuffle-bag —
  Ableton "other": excludes already-played steps in the section, resets when
  exhausted), go to (target step by alias/uid), next section, previous
  section. Multiple then-actions on a step → uniform random pick among them.
- Step states: stopped / playing / paused. Per-step trigger button shows
  state and offers start, stop, pause, and "trigger next action now".
  A global transport strip is allowed where it genuinely helps (stop-all,
  what's-playing indicator).
- Playback engine lives dashboard-backend-side (asyncio, like sync/points),
  as a **separable module** per brainstorm §02 — talks to the relay through
  the same internal API the tabs use, testable headless against simfleet.
- Wire discipline unchanged: full-state idempotent writes, last-writer-wins;
  cue-plane forward scheduling (existing clock-sync provisions) used when a
  step's forward-sync flag is set. PD float precision and 0-indexing house
  rules apply.
- Shows persist as files (git-friendly JSON), consistent with existing
  dashboard persistence conventions — stitch 1 fixes the schema and location.

## Stitch order

1. `1-design-and-schema` — design note + brainstorm comparison + show-file
   schema + internal API sketch. Everything later stitches consume.
2. `2-model-and-persistence` — backend model, load/save, CRUD surface.
3. `3-playback-engine` — transport state machine + OSC emission (headless
   simfleet verify).
4. `4-tab-ui` — the Show tab itself (Playwright verify).
5. `5-inspector` — context-sensitive step/message inspector + message
   builder (Playwright verify).
5b. `5b-compact-rows` — Bob's 2026-07-18 screenshot feedback: Ableton/QLab
   density — short rows, icon transport, summaries move to the inspector,
   alias-hash colour-coded pills (Playwright verify + screenshots).
5c. `5c-target-model-and-picker` — multi-target messages (seats, groups,
   mixes) and a chip/tap picker replacing the dropdown (schema + engine +
   UI, Playwright + simfleet verify).
6. `6-message-editing` — copy/cut/paste/move/delete of messages; step/divider
   insert, move, delete (Playwright verify).
7. `7-osc-consoles` — outgoing + incoming OSC consoles with `*` wildcard and
   `!` negation filtering (Playwright verify).
8. `8-docs-and-handoff` — docs, CLAUDE.md thread-ordering update, handoff.

Each dashboard stitch ships a `verify_*.py` per the house pattern (copy the
newest tied one as template; `~/.venvs/bopos` venv; simfleet on non-default
ports).
