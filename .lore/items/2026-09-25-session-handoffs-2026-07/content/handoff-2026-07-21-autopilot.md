# Handoff — 2026-07-21 autopilot session

Orchestrated session (Fable orchestrating **Opus 4.8** implementation
sub-agents — the codex weekly budget was spent, per Bob, so no codex this
session). All three workable `18-show-chrome-density` stitches are tied
and committed on `main`; the tree is clean apart from the deliberately
untracked `dashboard/shows/`.

## State of play

The Show tab now has its full chrome pass: the inspector lives in a
collapsible sidebar that can never push the terminals around, sections
are nameable with the wireframe's lines-either-side presentation, all
three inspectors share the one click-to-edit title pattern, and the tab
wears the compact chrome (sharper corners, tight buttons, bounded step
list) through shared `--chrome-*` variables. Bob has not yet seen any of
it live — the compact-chrome values especially are variable-driven
proposals derived from the ratified wireframe, one place to re-tune.

## Tied and committed

- `75af010` — **02-inspector-sidebar**: absolute-positioned sidebar out of
  the document-height equation; sticky viewport-capped internally
  scrolling panel; 40px collapse rail. Bob's in-session rulings honoured:
  expand on double-click only (manual <400ms detection — the first
  click's re-render defeats native `dblclick`), session-only persistence
  (reload resets to expanded). 22-check suite + both tied suites at 0
  failures, re-run independently.
- `3723b36` — **04-named-section-dividers**: additive divider `alias`
  through a new `update_divider` op riding the existing mutation
  plumbing; named rows render centred name with flanking lines; the
  click-to-edit title generalized (`nameTitleBlock`/`commitName`) across
  step/divider/message inspectors per Bob's 2026-07-21 ruling; message
  alias input removed in favour of the title; pill hashing untouched.
  36-check suite + tied suites at 0 failures.
- `d79ffae` — **05-compact-chrome**: Show-tab-only (Bob's scope ruling);
  seven `--chrome-*` variables in `:root`, consumed only by Show rules.
  Two recorded deviations (tied stitch `verification.md`): edit-bar
  button keeps its tied 40px pin; the step-list bound is an inset
  box-shadow because a real border ratchets the `clientHeight`-persisted
  box height smaller every re-render. New suite + all four tied Show
  suites at 0 failures.

## Loom state / next session

`18-show-chrome-density` has no workable loose ends left:

- `01-ux-review…` / `03-collapsible-steps` — paused by Bob pending the
  lanes/scenes design (`scene-sequencing/show-lanes-and-scenes-design.waiting`).
- `06-chrome-app-wide-assessment.waiting` — **new this session**, per
  Bob's ruling ("leave a stitch to assess doing the rest of the app or
  whether to stage adoption"). Gated on Bob living with the Show chrome.

Everything else on the loom is unchanged and `.waiting` (Bob- or
hardware-gated). The recommended next work is the **host-loom
patch-workflow documentation/starter-kit close-out**
(`~/repos/.loom/threads/patch-workflow-friction/`, stage 12) — bopOS's
own loom has nothing claimable.

## Decisions awaiting Bob

- **Look at the Show tab.** The compact-chrome values
  (`.loom/tied/05-compact-chrome/decisions.md`) and the sidebar/divider
  interaction defaults (`.loom/tied/02-inspector-sidebar/decisions.md`)
  were his in-session rulings plus orchestrator-proposed defaults; all
  easy to re-tune.
- `06-chrome-app-wide-assessment` when ready.
- Standing: the `bopos~.pd` receiver edit (`.notes/pd-edits-for-bob.md`).

## Gotchas discovered (healed where marked)

- Tied-verifier guard re-runs regenerate their retained screenshots in
  `.loom/tied/` — restore with `git checkout -- .loom/tied/` before
  staging. *(Healed: loom-autopilot Learnings.)*
- A `__pycache__/` inside a stitch dir blocks `loom.sh tie` as an
  "unresolved child" — delete it first. *(Healed: same.)*
- Native `dblclick` never fires on Show rows (first click re-renders);
  recorded in the tied 02 stitch.
- A real border on `.show-rows-box` fights `show.js`'s
  clientHeight-persistence (~2px shrink per re-render); recorded in the
  tied 05 stitch with the fix path if a border is ever wanted.
- Opus 4.8 sub-agents as the implementation lane: three stitches, zero
  redos, ~150k tokens each. *(Recorded: delegate Learnings.)*

## Usage at stop (2026-07-21, session end)

- 5-hour session: **95%** (the binding cap; resets ~19:20 UTC) — wound
  down at the threshold with all planned work complete.
- Weekly all-models: **19%**; weekly Fable: **14%** (both reset
  2026-07-27 ~09:00 UTC). A next session can start as soon as the
  session cap resets.
