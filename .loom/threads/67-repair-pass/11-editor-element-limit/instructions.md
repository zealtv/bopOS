# 11-editor-element-limit

**Status:** ready · tiny · Bob ruled 2026-10-03
**Goal:** the patch editor's two-element limit is documented as a deliberate
current limit, not an accident.

Bob: *"Devices at this stage only have one or two elements. More are
technically possible but not likely any time soon."* So keep the editor's
"send point values to: element 0 / element 1" choice as it is
(`#editor-point-target` in `index.html`, `set_editor_point_element` in
`server.py`, `set_editor_element` in `tools/audition.py`).

Say so where a reader would trip on it: a short comment at the server and
audition guards, and a sentence in the patch editor docs (wherever Point
preview is described). Wording: devices currently carry one or two elements;
positions themselves support any number; widen the editor when a device needs
more. No behaviour change. Background:
`../../70-dead-code-sweep/1-dead-code.tied/element-recommendation.md`.

Done when: comments + doc sentence land; fast tier green.
