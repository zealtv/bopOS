# automation-2-show-builder-gui

The Show-tab message-builder GUI for automation: construct fades, loops, and
LFOs without memorising the §3.2 syntax. The builder is a **compiler to the
wire grammar** and doubles as the grammar's completeness test.

**Dashboard stitch — runs after `15-show-polish` is tied** (it reworks the
same message-inspector panels the polish sweep touches). Requires
`automation-1-engine-and-parity` (simfleet must speak the grammar).

Scope:

- Param message builder grows a generator-type selector (constant / fade /
  loop / LFO / stop) with type-appropriate fields: segment list editing with
  durations in the string units, curve exponent, LFO shape/min/max/period,
  phase, free toggle.
- Authoring-layer niceties stay out of the wire: the builder emits canonical
  short options (`c:` `p:` `f`) and ms-or-string-unit durations only.
  Musical units are out of scope (deferred with `scene-sequencing`).
- Wire preview shows the exact compiled message.
- Show engine playback delivers the compiled args unchanged (targets/selector
  behaviour untouched).
- Verify: house Playwright pattern — build each generator kind in the GUI,
  assert the outgoing OSC console / simfleet receipt shows the canonical
  compiled form, and a round-trip re-render preserves the builder state.

Inspector defaults and layout follow the p5/p6 polish rulings — don't
reintroduce retired affordances (per-step forward_sync, cut/copy buttons).
