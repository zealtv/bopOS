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

## Fresh-context starting points (audited 2026-07-19)

- Authority: `docs/OSC-CONTRACT.md` §3.2 and the ratified lore item, not the
  pre-ratification draft. Engine/parser truth is `python/paramgen.py`;
  `.loom/tied/automation-1-engine-and-parity/verify_param_automation.py`
  captures accepted and rejected forms (32/32 baseline).
- UI seam: `dashboard/static/js/show.js` — `renderParamBuilder`, the
  message-editor `change` handler, `typedArg`, and `wirePreview`. Show messages
  already persist ordered typed args and playback already sends them unchanged;
  this stitch should not invent a second backend automation model.
- Only manifest-declared `f`/`i` params get generator choices. String params
  remain a plain constant value control. Keywords/options/durations with units
  are OSC strings; numeric values use the declaration's numeric type. Emit
  canonical short options (`c:`/`p:`/`f`) even when accepting long aliases on
  round-trip.
- A real `loop` needs at least two destination/duration pairs (the parser
  deliberately treats the short one-pair form as an ordinary fade). Phase and
  free are LFO-only; curve is invalid on a constant; odd segment lists reject.
- Re-render must infer every supported generator from existing typed args
  without rewriting the message merely by focusing it. Preserve an honest raw
  fallback for invalid or hand-authored forms rather than silently coercing
  them.
- Start the browser verifier from the newest Show harnesses:
  `.loom/tied/p3-global-transport-and-cue-lead/verify_show_transport.py` for
  two-client/real-server transport and
  `.loom/tied/p5-inspector-defaults/verify_show_inspector_defaults.py` for the
  current inspector conventions. Re-run
  `.loom/tied/show-transport-spot-fixes/verify_show_transport_spot_fixes.py`
  so the builder does not regress stable transport DOM or CSS progress.
