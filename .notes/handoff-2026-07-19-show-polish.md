# Handoff — 2026-07-19: Show polish complete

## State of play

`15-show-polish` is fully tied through p8. The Show tab now behaves as one
coherent performance surface: legitimate zero values survive authoring, rapid
transport clicks are honest, playback is exclusive, progress and armed state
are visible, and the global transport owns one persisted cue lead used by every
Show cue. The ordered list scrolls/resizes independently, inspector defaults
state the persisted truth, items and message pills arrange directly by drag,
keyboard editing is primary, and Ctrl/Cmd+Z performs bounded global
server-authoritative undo.

Post-close transport spot fixes remove the redundant Stop-all/count UI under
exclusive playback, align divider and step grips, keep transport DOM stable
across unrelated fleet-state/countdown updates, and use the same CSS-keyframe
pattern as Dashboard cue scheduling for a smooth authoritative progress fill.

The adjacent Patch tab now calls manifest promotion `dashboard`, accepts and
normalizes the legacy `facilitator` key, rejects conflicting dual keys, ignores
and strips the retired presentation-only `group`, and gives the path field an
unmistakable example. OSC contract §8 records this as the ratified v1.8
amendment. No `.pd` files changed.

## Tied stitches and commits

- p1 zero values / transport bugs — `69753f8`
- p2 exclusive playback / progress — `c4d123b`
- p3 global transport / cue lead — `520b9cf`
- p4 step-list scrollbox — `5f75741`
- p5 inspector defaults — `5e93045`
- p6 drag / keyboard editing / global undo — `17aa08a`
- p7 Patch-tab tidy — `23bcc7c`
- p8 operator docs, reconciled design note, and this handoff — this commit

## Verification retained

The complete 16-script Show regression sweep is green. Run each with
`PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python`:

- `.loom/tied/2-model-and-persistence/verify_show_model.py`
- `.loom/tied/3-playback-engine/verify_show_engine.py`
- `.loom/tied/4-tab-ui/verify_show_tab.py`
- `.loom/tied/5-inspector/verify_show_inspector.py`
- `.loom/tied/5b-compact-rows/verify_show_compact.py`
- `.loom/tied/5c-target-model-and-picker/verify_show_targets.py`
- `.loom/tied/6-message-editing/verify_show_editing.py`
- `.loom/tied/6b-show-management/verify_show_management.py`
- `.loom/tied/7-osc-consoles/verify_show_consoles.py`
- `.loom/tied/p1-zero-value-and-transport-bugs/verify_show_polish_bugs.py`
- `.loom/tied/p2-exclusive-playback-and-progress/verify_show_exclusive.py`
- `.loom/tied/p3-global-transport-and-cue-lead/verify_show_transport.py`
- `.loom/tied/p4-step-list-scrollbox/verify_show_scrollbox.py`
- `.loom/tied/p5-inspector-defaults/verify_show_inspector_defaults.py`
- `.loom/tied/p6-drag-and-keyboard-editing/verify_show_drag_editing.py`
- `.loom/tied/p7-patch-tab-tidy/verify_patch_tab_tidy.py`

The sweep exercises the real dashboard on random loopback ports and headless
Chromium where UI behavior is involved. p7 additionally reran and amended the
tied PE-3 manifest-editor backend/browser verifies and nested-parameter
backend/browser verifies. Earlier polish stitches amended tied 5c target-picker,
6 message-editing, and related Show verifiers as their old affordances were
retired; each stitch worklog records the exact changes and counts.

No hardware, iPad/touch-device, audio, or audible PD gate was run. Bob's
untracked `dashboard/shows/` content remains deliberately untouched.

## Deferred by design

- Redo; p6 ships bounded undo only.
- Musical time, tempo/quantization, scheduled parameter writes, curves and
  decomposed point motion, polymorphic/script clips, multi-column layout, and
  the animated visualisation view remain with the Bob-gated
  `scene-sequencing` co-design.
- Parameter-automation string/mixed-array kind remains unnamed and without a
  wire plane.

## Next

Continue `16-param-automation` at `automation-2-show-builder-gui`, then
`automation-3-animated-takeover`; `automation-4-waveform-ux-gate` stops for
Bob's UX ratification before visualisation code. The host-loom
`patch-workflow-friction` documentation/starter-kit close-out resumes after
thread 16 so it documents the finished system.

Long-standing hardware and co-design waits are unchanged.
