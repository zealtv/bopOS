# 2-venue-wide-capture

Make capture-as-Show-step venue-wide, unparameterised, local, and dialog-free.

Authority is `.loom/tied/1-columns-design/decisions.md` D1–D3, with the
reasoning in `judgment.md`. `mockup-armed-dark.png` / `mockup-armed-light.png`
are the visual target. Read the parent `4-n-columns/instructions.md` first.

Needs `1-columns-layout` for the tab strip slot to land in; everything else here
is independent of how many columns exist, which is why it is its own stitch.

## Why this is a removal, not a widening

The consult answered "what scope should a per-column capture take?" with
**neither**. Per-column capture is not merely harder — it is **wrong today**: a
group column sends `scope:"groups"`, and `_capture_show_seats` then captures
every grouped seat in the venue, so three of the five column shapes capture
something other than what the column shows.

The arrangement was never carried by the scope. It is rebuilt from per-seat
`applied_preset` by `_captured_show_preset_messages`. So venue-wide capture
deletes vocabulary rather than adding it — and that is the test of whether this
stitch is being done right.

## The work

- **Delete `scope`/`id`** from `preview_show_preset_capture` and
  `capture_show_preset_step` (`dashboard/server.py`), and collapse
  `_capture_show_seats` to `list(self.state.seats.values())`.
- **Delete `presetScope()`** from `js/control-column.js` — with capture off the
  column it has no other caller. Check that before deleting; the preset row's
  own scope is `ControlSurface`'s, not this.
- **The round trip can go.** The client already holds `applied_preset` on every
  seat (`presetProvenance()` reads it, `control-surface.js`), and since
  `3-iframe-retirement` the Control document receives `show`/`shows`
  (`server.py`) directly. So the count and the show-loaded check are both local.
  `preview_show_preset_capture` existed only because the iframe could see
  neither — it is a message that outlived its reason.
- **One affordance per surface, never inside a column.** `1` leaves a slot on
  the right of the Control tab strip: fill it with `capture step · 12/16`. The
  Show tab's edit bar gains `✛ Capture` beside `✛ Step` — same words, same
  unparameterised behaviour.
- **No dialogs.** The two `alert()`s and the `confirm()` in
  `control-column.js`'s `handleShowCapturePreview` come out. Ambient count →
  click **arms** → non-modal preview listing the messages the server would mint
  → commit → `captured "…" · undo` in the same slot for ~8s.
- The preview marks **dirty** rows ("captures the preset, not the edits") and
  **site-bound** seat-id targets vs portable `group:<name>` ones — both ratified
  behaviour that nothing currently says out loud.
- **Disabled states, not alerts**: no show loaded, and nothing applied. The
  nothing-applied case must distinguish its causes — after a dashboard restart
  the venue sounds identical but provenance is gone (`state.py`), and the
  operator needs a different sentence for that than for "nothing has been
  applied yet".
- **Name the step.** Derive the alias from content (`dusk + bloom + solo`)
  instead of `"Captured presets"` (`show_model.py`, never overridden) and hand
  the new step to the Show tab's click-to-edit rename (`show.js`).
- **Undo** sends the existing `undo_show`. It undoes the *last show mutation*,
  whatever it was — so either clear the affordance on any intervening show
  mutation or check the top of the undo stack before firing.

## Verify

`tools/run-tests.sh fast` and `browser`. The server-side removal is browser-free
and belongs in the `tests/` module that owns show capture — assert that a
capture with grouped seats now captures exactly the seats carrying provenance,
which is the case the old `scope:"groups"` path got wrong.

Browser: arm from the Control tab strip, check the preview lists the messages
and marks a dirty row, commit, confirm the step lands with a derived name, and
undo it. Then the same from the Show tab's edit bar, and confirm both disabled
states say the right sentence.
