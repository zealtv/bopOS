# Decisions — 08-control-tab-columns/4-n-columns/2-venue-wide-capture

D1–D3 of `.loom/tied/1-columns-design/decisions.md`, shipped. What follows is
what the implementation had to rule on top of them.

## It was a removal, and it stayed one

The stitch's own test — "does this delete vocabulary or add it?" — passes.
Gone: `scope`/`id` from `capture_show_preset_step`, the whole
`preview_show_preset_capture` verb and its `show_preset_capture_preview`
producer, the `show_preset_capture_preview` broadcast, `_capture_show_seats`,
two `alert()`s and one `confirm()`. `presetScope()` was already gone —
`2-control-column-component` took it when the column stopped owning capture, so
this stitch had nothing to delete there.

Added on the wire: **nothing**. `capture_show_preset_step` now takes `{}`.

## One thing WAS added to state, deliberately: `preset_provenance_seen`

D2 asks the nothing-applied state to distinguish its causes, and the venue
cannot do that on its own. `durable()` strips `applied_preset`, so after a
restart the venue sounds applied and captures nothing — and a client that
reloaded after that restart has no history to reason from either.

So `state.data` carries one runtime-only boolean, false at process start,
sticky true from the first successful apply, reset on venue load (a loaded
venue's seats carry no provenance either), rolled back with the params if the
apply's save fails. It is in `public()` and out of `durable()` for the same
reason provenance itself is.

**What it can and cannot tell apart, stated plainly.** It separates *"applied
during this session, then cleared"* from *"not applied during this session"*.
It does **not** separate a fresh venue from a restarted one — both are the
second case. That is not a gap worth closing: both take the same action
(re-apply what you want captured), and the sentence says so. The two sentences
are:

- `· nothing applied this session` — "No preset has been applied since the
  dashboard started. Applied-preset provenance is never saved, so a restart
  clears it even though the venue still sounds the same — re-apply the presets
  you want to capture."
- `· nothing applied` — "No Seat currently has a preset applied."

Terse in the control, full in the title. D2 says "the reason in place", and a
reason only a tooltip carries is not in place.

## The preview is derived, not fetched — and that is why the round trip died

`_captured_show_preset_messages` groups seats by `applied_preset` and hands
each set to `preset_application.capture_target`. `js/show-capture.js` mirrors
that grouping and that function. The mirror is ~30 lines and is the whole
reason the wire lost a verb rather than gaining a shaped one.

The server stays authoritative for what is minted: the client never sends the
plan, only `capture_show_preset_step`. Drift between the two therefore shows up
as a preview that disagrees with the step that lands — visible and wrong in the
right direction — not as a wrong capture.

## `current_show` is not timely; `shows` is

Found while wiring the disabled state. `set_current_show` broadcasts `shows`
and `show` but **not** a full `state`, so `installation.current_show` does not
follow a freshly created or loaded show.

**Measured, because "it lags" was the wrong word.** There is no periodic
full-`state` broadcast at all — heartbeats go out as `device_update`, and
`offline_sweep` broadcasts only `device_offline`. With two simulated nodes
heartbeating every 0.5s, a browser that created a show saw **zero** `state`
messages in 20 seconds and `installation.current_show` was still `null`. It is
not stale for a moment; it is stale until some unrelated state mutation
happens to trigger a broadcast.

The component therefore tracks the `shows` catalog's `current` and falls back
to `state.current_show` only until the first `shows` message arrives.

**The other consumer is wrong today**, and this stitch did not fix it because
it is not this stitch's surface: `monitor.js:699` renders the Monitor System
panel's `show` row from `installation.current_show`, so with `opening` loaded
the panel reads `none loaded` — confirmed in the same measurement above,
indefinitely. It is one display line and the fix is one broadcast in
`set_current_show` (and the `delete_show` branch that clears it), but a
diagnostic panel that lies about which show is loaded is worth its own
change rather than a drive-by inside a capture stitch.

## Undo withdraws on any intervening mutation

`undo_show` pops the last show mutation, whatever it was. An undo offer that
outlives an intervening edit does not undo the capture — it silently discards
that edit. The component clears the offer when its step is no longer the last
item (deleted, undone elsewhere, or buried under a later append), which is the
cheap version of "check the top of the undo stack" the instructions allowed.
Pinned in the browser journey, because it is the failure nobody would notice
until it cost them an edit.

## The derived name lives server-side

D3's alias is minted in `show_model.captured_step_alias`, not in the client, so
the wire stays at `{}` and both surfaces get the same name. Distinct preset
names in mint order, `" + "`-joined, capped at three with `+N`. `"Captured
presets"` survives only as the honest fallback for messages with no alias. An
explicit `alias=` still wins — nothing passes one today.

## Chrome

`css/show-capture.css` is the app's **sixth** component stylesheet, registered
in `tests/test_css_component_ownership.py` as `show-capture` / `.show-capture`.
Loaded by `index.html` only: capture is desktop authoring, and Remote fires
shows rather than writing them.

Both hosts render strings, so the component hands back HTML and takes clicks
back rather than owning DOM. That is a deviation from `TargetPicker`'s
mount-into-a-host shape and it is deliberate: `show.js` rebuilds its whole root
on every render, so a mounted component inside the edit bar would be destroyed
by its own host several times a second.

## Verify

`tools/run-tests.sh fast` — 260, green (three new server-side tests:
venue-wide capture ignores grouping, the derived alias, the provenance flag).
`tools/run-tests.sh browser` — 21 journeys, all green, including the new
`tests/verify_show_capture.py` (19 checks) and the known-flaky
`verify_live_param_kinds.py`.

Visual check against `1-columns-design/mockup-armed-{dark,light}.png` at 1280,
both themes, from the real running app. One correction the mockup did not
predict: the row's label cells wrap (`→ Seat 1` over two lines) once a note is
long, so the notes column takes the slack and the three label columns are
`nowrap`.
