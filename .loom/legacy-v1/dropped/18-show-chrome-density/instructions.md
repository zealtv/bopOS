# 18-show-chrome-density

Integrate the qualities Bob liked in the `01-layout-review` wireframe into
the real Show tab — and weigh extending the chrome language app-wide.
Authorized by lore item `2026-07-20-show-chrome-density-braindump` (verbatim
braindump in its `content/`).

What Bob wants, in his words' order: a bounded step list; buttons that wrap
tightly around their text; nameable dividers (dividers mark sections, so the
section can be named) with the lines-either-side divider styling; steps that
fold up to hide their message pills; sharper corners; a generally more
compact UI; and an inspector that owns its space as a collapsible sidebar —
fixing the annoyance where a taller message inspector pushes the OSC
terminals out of view (popped out while building a show, hidden while
running one).

Standing context: this is a **desktop-first** app, except the facilitator
tab (tablet first, then laptop/phone). Current mobile sizing is generally
fine — don't regress it, but don't design for it first.

Work in order (amended by Bob 2026-07-20: `01` and `03` are **paused** until
the lanes/scenes picture is clearer — collapsible rows might not survive a
multi-lane grid; the other style adoption points stand):

1. `02-inspector-sidebar` — collapsible inspector sidebar with its own
   space (core behavior ratified by the braindump; details decided
   in-stitch with Bob).
2. `04-named-section-dividers` — divider names + section styling; also
   applies the step inspector's click-to-edit name pattern to the divider
   and message inspectors (Bob, 2026-07-21).
3. `05-compact-chrome` — corners, button density, bounded lists (scope
   Show-tab vs app-wide is decided in-stitch with Bob).
4. `01-ux-review-step-rows-and-chrome.waiting` + `03-collapsible-steps.waiting`
   — resume alongside `scene-sequencing/show-lanes-and-scenes-design`.

Show schema changes are allowed here only as small additive fields (e.g.
divider `alias`, persisted collapse state if ratified); playback semantics
and the message model are untouched. Lanes/scenes stay with the Bob-gated
`scene-sequencing` co-design.
