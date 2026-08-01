# 1-design-and-schema

Produce the design note every later stitch in this thread consumes. Read the
parent `instructions.md` + `braindump-2026-07-18.md` first; they fix naming
(Show tab / step / section / message) and semantics — this stitch records and
completes them, it does not reopen them.

Deliverable: `.notes/show-tab-design-2026-07-18.md` containing:

1. **Braindump ↔ brainstorm comparison.** Map each braindump element onto
   `.notes/sequencer-brainstorm-2026-07-15/` (§02 grid model, §05 rungs, §08
   decision list): what this slice adopts (follow actions, shows-as-files,
   backend interpreter, takeover semantics), what it simplifies (one column;
   rows of concrete messages instead of scripted clips), what it defers
   (musical time/tempo, clip types, curves, point motion, `/field`,
   scene language — all still gated or later). Note which §08 decisions this
   slice answers de facto and which remain open for the co-design.
2. **Show file schema.** JSON schema for a show: ordered list of steps and
   dividers; step {uid, alias, messages[], duration_s (stored as seconds,
   edited as h/m/s), play_count, then_actions[], forward_sync}; message
   {uid, alias, address, args (typed), target selector}. Decide storage
   location by inspecting existing dashboard persistence conventions
   (presets, groups, aliases — see `dashboard/state.py` / `server.py`) and
   follow them; shows must be git-friendly single-file JSON. Include
   then-action serialization (list of tagged actions; `goto` carries a step
   uid, display resolves alias). Keep the schema single-column-agnostic
   (steps carry no column field yet, but nothing should preclude adding one).
3. **Internal API sketch.** WS message surface between tab and backend
   (show CRUD, step/message edits, transport commands, playback state
   broadcast, OSC console taps) — names and payload shapes, matching the
   conventions of the existing WS protocol in `dashboard/osc_bridge.py` /
   `static/js/ws.js`.
4. **Playback semantics spec.** The parent's semantics section expanded to
   implementable precision: state machine (stopped/playing/paused), duration
   timing, play-n-times, then-action resolution incl. `any` (uniform in
   section), `other` (shuffle-bag per section, reset on exhaustion; bag
   resets when playback in that section stops), multi-then random pick,
   section boundary rules (dividers delimit; leading/trailing/adjacent
   dividers produce empty sections that are skipped by next/previous
   section), edge cases (goto to a deleted step, empty section targets,
   step deleted while playing). Forward-sync: how a flagged step's messages
   ride the existing clock-sync scheduled delivery; unsupported message
   kinds fall back to immediate send.

No product code in this stitch. Verification: the note exists, is complete
against the checklist above, and the stitch directory records anything
discovered that changes later stitches (update their instructions if so).
