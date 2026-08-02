# 1-capture-retirement

**R5.** Remove `Capture as step` entirely. Bob, 2026-08-02:

> I'm actually thinking that we should remove the capture to step feature […]
> adding preset messages to show steps isn't particularly arduous. And when
> varying parameters start to become involved, I think we're getting into quite
> messy territory.

Pure deletion. No design gate, no replacement. Steps are hand-authored from the
Show inspector, which already builds both message kinds.

## What comes out

Located 2026-08-02; verify rather than trusting this list.

* `server.py` — `_captured_show_preset_messages` (:1830) and
  `capture_show_preset_step` (:1884), plus the ws verb that reaches them.
* `show_model.py` — `capture_preset_step` (:884) and `captured_step_alias`
  (:862), unless the Show inspector's own authoring path uses the alias
  derivation. **Check before deleting** — a derived name may be shared.
* `js/show-capture.js` and `css/show-capture.css` — the app's **sixth**
  component stylesheet, created by `4-n-columns/2-venue-wide-capture`. Both
  mounts go: the Control strip's right-hand slot and the Show edit bar.
* The Control strip's right-hand slot itself. `1-columns-layout` recorded that
  this slot *"is not a placeholder"* — it exists because capture had nowhere
  else to live. With capture gone it has no remaining tenant; do not leave an
  empty affordance behind.
* `preset_provenance_seen` (runtime-only state added by
  `2-venue-wide-capture`) — it exists ONLY so an empty capture could name its
  cause. Confirm no other reader before removing.
* The undo-offer withdrawal logic, if it is capture-specific.
* Any living guard whose subject is capture. `tests/` only; do not sweep
  `legacy-v1/`.

## What must NOT come out

* **`capture_params`** (`preset_application.py:206`) — this is PRESET SAVE, not
  step capture. It stays, along with the save drawer's per-identity `include`
  checkboxes (`control-surface.js:336`) and the server's `include` allowlist
  (`server.py:2008`).
* **`capture_target`** (`preset_application.py:246`) — the portable-selector
  derivation. Check for other callers before assuming it dies with capture.
* The `reference` message kind and `apply_preset`. Steps still fire presets;
  only the *automatic authoring* of those steps goes.

## Watch for

`4-n-columns/2-venue-wide-capture` made capture venue-wide and argument-free as
a deliberate REMOVAL, and deleted `preview_show_preset_capture` outright. That
work is not being reversed — it is being completed. Read its record first so
this deletion follows the same seam rather than reopening one.

## Verify

`fast` plus the Show and Control browser journeys. The positive assertion worth
adding somewhere durable: a step can still be hand-authored with a preset
reference from the Show inspector — that is the workflow R5 relies on, so pin
it rather than assuming it.
