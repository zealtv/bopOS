# 01-ux-review-step-rows-and-chrome

**WAITING (Bob, 2026-07-20):** paused together with `03-collapsible-steps`
until the lanes/scenes picture is clearer — collapsible rows might work in a
single column but perhaps less well in a multi-lane grid. Revisit alongside
`scene-sequencing/show-lanes-and-scenes-design.waiting`. The review's
non-collapse questions (divider presentation, sidebar interaction, chrome
scope) were re-scoped into `02`/`04`/`05`, which proceed without this gate;
when resumed, this stitch covers only the collapse/row-anatomy questions
(items 1–2 below).

Get an expert UI/UX eye over the step-row anatomy and the chrome scope
before implementing `03`/`04`/`05`, then have Bob ratify the results.
Reference material: lore item `2026-07-20-show-chrome-density-braindump`,
the tied `.loom/tied/01-layout-review/` (wireframes + decisions), and the
current Show tab (`dashboard/static/js/show.js` `stepRow`/`dividerRow`,
`dashboard/static/css/style.css`).

## Questions the review must answer

1. **Collapsed-step row anatomy.** The row must carry: collapse indicator,
   drag grab bar, play/transport button, step name (alias), message pills
   (when expanded), duration/cue info. Recommend placement and ordering of
   the collapse indicator relative to the grab bar, play button, and name.
   Hard constraint from Bob: the current `⋮⋮` grab-bar icon stays. Weigh:
   hit-target separation (collapse vs drag vs play must not misfire on
   touch), scan-ability of names down the list, QLab/Ableton conventions,
   and what the indicator looks like during playback (a collapsed step that
   is playing must still show progress/armed state — see the playback
   visualisation from `15-show-polish`).
2. **Collapse behavior.** Click target (indicator only, or row
   double-click too?), keyboard affordance, whether collapse state persists
   in the show document or stays client-local, default state on load, and a
   collapse-all/expand-all affordance if warranted.
3. **Divider/section presentation.** Divider name rendering with lines
   either side; is the divider name inline-editable on the row (matching
   step-name behavior) or inspector-only? How do dividers read when
   adjacent steps are collapsed?
4. **Inspector sidebar interaction.** Collapsed/expanded affordance
   placement, expanded width, what happens to focus-driven inspector
   switching while hidden (e.g. selecting a pill while the sidebar is
   collapsed), and whether the collapsed state shows a minimal strip or
   nothing.
5. **Chrome scope.** Sharper corners, tighter button padding, bounded
   scroll regions: recommend concrete values (radius, padding, heights)
   consistent with the bop palette/theme system, and advise whether to
   apply Show-tab-only first or app-wide (Bob: "perhaps the app style
   broadly" — this is his call; give him a recommendation and the
   cost/risk of each).

## Deliverables

- A written review in this stitch (`ux-review.md`) with recommendations and
  reasoning, plus annotated wireframes/mockups for collapsed and expanded
  step rows, divider styling, and sidebar states at desktop width (mobile
  only as a sanity check — desktop-first; the facilitator tab is excluded
  from any app-wide chrome change until separately reviewed).
- Bob ratifies the decisions (record them in `decisions.md`, mirroring
  `.loom/tied/01-layout-review/decisions.md`); update the sibling stitch
  instructions if the rulings change their scope. Mark `.waiting` if Bob is
  not available. Do not implement here.
