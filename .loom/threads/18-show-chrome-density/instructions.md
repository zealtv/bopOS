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

Work in order:

1. `01-ux-review-step-rows-and-chrome` — expert UX review + Bob ratification
   gate. Nothing else implements past it except `02-inspector-sidebar`,
   whose core behavior is already ratified by the braindump.
2. `02-inspector-sidebar` — collapsible inspector sidebar with its own
   space.
3. `03-collapsible-steps` — fold-up step rows per the ratified row anatomy.
4. `04-named-section-dividers` — divider names + section styling.
5. `05-compact-chrome` — corners, button density, bounded lists, at the
   ratified scope (Show tab vs app-wide).

Show schema changes are allowed here only as small additive fields (e.g.
divider `alias`, persisted collapse state if ratified); playback semantics
and the message model are untouched. Lanes/scenes stay with the Bob-gated
`scene-sequencing` co-design.
