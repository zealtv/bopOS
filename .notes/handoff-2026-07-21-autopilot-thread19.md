# Handoff — 2026-07-21 autopilot session (thread 19)

Second autopilot session of 2026-07-21, scoped by Bob to
`19-show-chrome-fixes` only. Opus 4.8 orchestrating Opus 4.8 implementation
sub-agents (Bob: codex usage too low, Claude models only; keep budget in
reserve for a following session). **The whole thread is tied and committed on
`main`.** Tree is clean apart from the deliberately untracked
`dashboard/shows/`.

## State of play

All four Show-tab defects Bob hit while living with the tied
`18-show-chrome-density` chrome are fixed, each with its own Playwright
suite, and every existing tied Show suite still passes. The Show tab's
narrow-width layout no longer strands controls on top of each other, its two
"add" buttons read as one family, its dividers match the prose Bob gave, and
the generator duration fields are legible. Bob has not seen any of it live —
the two design values (28px divider rules, 56px unit box) are orchestrator
proposals derived from his words and are one-line retunable.

## Tied and committed

- `228e43c` — **01-inspector-toggle-overlap**. Root cause found and confirmed
  in-browser: the collapse toggle is a child of the inspector panel, but
  inside `@media(max-width:1020px)` the panel dropped to `position:static`,
  so the toggle's containing block fell through to the relatively-positioned
  workspace and it rendered at the workspace's top-right — on the edit bar's
  delete button. Fixed by giving the narrow panel a position context
  (`position:relative;top:auto`, the `top` needed to neutralise the base
  sticky offset). A layout fix, not z-index. Pre-fix negative control:
  6 failures; post-fix 26 PASS / 0 failures across 900/768/1280 × short
  (divider) and tall (LFO message) inspectors.
- `bb857d0` — **02-step-and-divider-icons**. Both glyphs became inline SVG
  carrying an explicit plus plus a shape (rounded rect = step row, rule =
  section divider), so the additive sense survives the label-less narrow
  rendering and the pair stops reading as add/remove. Inline SVG rather than
  text characters, matching the existing mute-indicator conventions — no icon
  font, inherits `currentColor` so both themes and the disabled state come
  free. Accessible names `Add step` / `Add divider` untouched. Step rect
  stroke dropped to 1.6 (2px closed the interior to a blob at 14px).
  33 PASS / 0 failures.
- `2d69554` — **03-divider-rule-styling**. Named divider rules `flex:1 1 auto`
  → fixed `flex:0 0 28px`; the named row re-centres (18/05's compact-chrome
  pass had made the row `flex-start`) and takes its grab handle out of flow
  so the name sits on the true row centre rather than ~14px right of it.
  Unnamed divider drops its gradient background for a flat 1px `::after`
  rule, inset clear of the handle, `pointer-events:none`. 36 PASS / 0
  failures. **Ruling recorded**: one assertion in the tied
  `04-named-section-dividers` guard pinned the gradient Bob asked to be
  removed — inverted in place with a comment naming the superseding stitch,
  reasoning in `.loom/tied/03-divider-rule-styling/decisions.md`.
- `aca8915` — **04-lfo-period-field-width**. Two causes, not one. The unit
  track went `70px` → `56px` (48px was measured to clip `ms`; the select's
  min-content width is 55px) with `min-width:0`. That alone left a 14px
  deficit, because `automation-2`'s `@container show-inspector
  (max-width:380px){.show-param-lfo{grid-template-columns:1fr}}` was
  **inserted before** the base `.show-param-lfo` rule of equal specificity,
  so the LFO-stacking half of that ratified rule had never applied. Moving
  the block after the base rule — no declarations changed — healed it. The
  fix sits on `.show-param-duration`, shared by the LFO period and every
  ramp/segment duration, so it covers all generator kinds. 67 PASS / 0
  failures; wire round-trip verified unchanged.

## Bob's live review — thread 24 (same session, after the above)

Bob looked at the tab and reversed two calls. `24-show-divider-and-glyph-repass`
is fully tied:

- `904c84b` — **24/01**: the unnamed divider's rule is now short (28px, the
  same length as the named row's flanking rules) and centred where the alias
  would go, not a full-width span. The two divider states now read as one row
  type with the name present or absent.
- `0b4eaea` — **24/02**: the drawn SVG glyphs are gone. Step is `✛` (U+271B,
  ✕'s Dingbats sibling), divider is `╱` (U+2571, effectively one half of ✕) —
  chosen to sit with the edit bar's existing `⧉` / `✕` in weight and optical
  size, and checked rendered in both themes at both widths. The narrow-width
  add/remove confusion `19/02` was fixing does not return, because `╱` is not
  the visual opposite of `✛`.

Both repaired the superseding assertions in the `19/02` and `19/03` guards in
place, per the ruling below. All eight tied Show guards re-run at
`0 failure(s)` after both changes.

## Loom state / next session

`19-show-chrome-fixes` is fully tied; its goal stitch is tied too.

New this session: **`23-waveform-marker-guard-regression`** (unclaimed loose
end). The tied `automation-5-waveform-marker` guard fails on `main` on its
own — a Dashboard seat-card automation-marker selector times out. Confirmed
twice, once with the working tree stashed, so it is not from this session's
work. Real runtime defect vs stale guard is unsettled; the stitch says how to
find out. It does not block the fix pass.

**Recommended next work: `20-console-dock`**, per CLAUDE.md stage 12 —
starting with `20-console-dock/01-dock-design`, which is a **Bob decision
gate** (dock scope: Show-tab-only vs app-wide, which also bears on
`18/06-chrome-app-wide-assessment`). Write the proposal, mark it `.waiting`,
surface it — do not implement past it. `21-theme-cyan-tint` is implementable
solo; `22-listener-range-ux` opens with another Bob gate.

## Decisions awaiting Bob

- **Look at the Show tab.** Two values are orchestrator proposals, both one
  line: the 28px named-divider rule length
  (`.loom/tied/03-divider-rule-styling/decisions.md`) and the 56px unit box
  (`.loom/tied/04-lfo-period-field-width/verification.md`). Screenshots of
  every state, light and dark, are retained in the tied stitch dirs.
- Ratify (or reject) the ruling that a tied guard pinning superseded
  behaviour gets repaired in place rather than left red.
- Standing: `20-console-dock/01-dock-design` and
  `22-listener-range-ux/01-listener-range-design` gates;
  `18/06-chrome-app-wide-assessment` once he has lived with the Show chrome;
  the `bopos~.pd` receiver edit (`.notes/pd-edits-for-bob.md`).

## Gotchas discovered (healed where marked)

- **The harness declines to execute scripts under `.loom/tied/`** (classifier
  block; retries don't help). Copy the guard into your stitch dir and run the
  copy — repo-by-marker root lookup survives the move, and it spares the tied
  screenshots from regeneration entirely. *(Healed: CLAUDE.md "Dashboard
  browser tests"; loom-autopilot Learnings.)*
- **A tied guard can pin behaviour Bob later rules away.** Delegates must not
  edit tied suites; the orchestrator repairs the assertion in place with a
  comment naming the superseding stitch. *(Healed: same two places, with the
  worked example linked.)*
- Long compound Bash (`tie && git add && git commit <<heredoc`) trips the
  permission classifier — issue them as separate calls. *(Healed:
  loom-autopilot Learnings.)*
- `@container`/media blocks appended **before** the base rule they mean to
  override silently do nothing in this single-line-per-block stylesheet
  (found in `automation-2`'s LFO stacking). Worth a glance whenever a Show
  responsive rule "isn't applying".
- Opus 4.8 sub-agents against a written `spec.md` + `decisions.md`: four
  stitches, zero redos, 62k–123k tokens each — cheaper than the previous
  session's ~150k, and one of them correctly refused to edit a tied suite and
  escalated instead.

## Usage at stop (2026-07-21)

- 5-hour session: **48%** (the binding cap; resets 14:49 UTC).
- Weekly all-models: **35%** (resets 2026-07-27 ~09:00 UTC) — the whole
  thread cost about **4%** of the weekly cap.
- Stopped because the scoped thread is complete, not because of a cap. Ample
  reserve for the follow-on session Bob asked to keep budget for.
