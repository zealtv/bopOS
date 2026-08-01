# Delegate spec — 4-cue-retirement, lane B (browser UI)

Lane B is the browser surface. **Lane A is running concurrently on the Python
backend, docs and patch manifests. Touch only `dashboard/static/`.** If a
Python file seems to need a change, leave it and say so in your summary —
lane A owns it.

## Goal

Remove `/cue` from every browser surface and put event firing on the control
panel, targetable at all seats / a group / one seat.

## Files you may touch

    dashboard/static/js/control-surface.js
    dashboard/static/js/show.js
    dashboard/static/js/facilitator.js
    dashboard/static/js/dashboard.js
    dashboard/static/facilitator.html
    dashboard/static/index.html
    dashboard/static/css/*.css

Nothing else. No Python, no `.pd`, nothing under `.loom/`, not
`dashboard/shows/`.

## Websocket contract (lane A is implementing exactly this)

- `set_event_lead` — `{ms}`, 0..10000. (was `set_cue_lead`)
- `fire_event` — `{selector, identity, elements: [float], lead_ms}`.
  `selector` is a wire selector string: `"all"`, `"g<id>"`, or `"<seatId>"`.
  Broadcast back: `event_scheduled` `{selector, identity, elements,
  shared_time_ns, lead_ms}`. (was `fire_cue`)
- `fire_editor_event` — `{identity, elements}`, edit-mode gated, fires with
  the `lead_ms: 0` sentinel. Broadcast back: `editor_event_fired`
  `{identity, shared_time_ns}`. (was `fire_editor_cue`)

State key `cue_lead_ms` is already `event_lead_ms` (previous commit).

## 1. `control-surface.js` — wire the event row

`eventRow` (~line 299) currently renders an inert row: value boxes, a `sync`
toggle, a `send` button, all `disabled`, with a "not wired yet" title. Make it
live:

- **Delete the `sync` toggle entirely.** Bob's ruling: every event
  forward-syncs, so a per-row sync choice cannot exist. One fire button per
  row. Global lead time `0` is the only sync-off and it lives elsewhere.
  This deliberately supersedes what the tied stitch `6-non-float-kinds`
  shipped.
- Value boxes become **editable number inputs**, seeded from `defaults`,
  one per `arity` (arity may now be **0**, in which case the row is just the
  fire button and the name).
- The `send` button fires. Keep the ratified reading order — trigger, then
  the elements it will send, then the name.
- Remove the `disabled` attributes and the "not wired yet" `title`.
- Preserve the existing `aria-label` discipline; a disabled-control
  `aria-describedby` note is no longer needed once the row is live.

Firing goes through a new host callback, mirroring the existing
`context.send({scope, id, name, value})` seam:

    context.sendEvent?.({scope, id, identity, elements})

`scope` is `"all"` / `"group"` / `"seat"` / `"device"` and `id` the group or
seat id, exactly as `scopeAttrs` already encodes them. Each host maps that to
the wire selector and calls `ws.send("fire_event", …)`.

Add the parameters/events **section split** Bob ruled: the panel renders a
parameters section and an events section, not one interleaved list.

## 2. `dashboard.js` — Control tab host + manifest editor

- Implement `sendEvent` in the control-surface context it constructs,
  mapping scope→selector (`all` → `"all"`, `group` → `"g<id>"`,
  `seat`/`device` → `String(id)`).
- The manifest editor's cue rows (`cueManifestRow`, `#manifest-cues`,
  `manifest-add-cue`, `data-remove-cue`, and the `cues:` fields of
  `manifestDraft` / `save_patch_manifest`) are **replaced by event rows**:
  `name`, `arity` (0–3), per-element `labels` and `defaults`, `dashboard`.
- The patch editor's cue fire buttons (`#editor-declared-cues`,
  `#editor-cue-id`, `#editor-cue-fire`, `#editor-cue-status`,
  `editor_cue_fired`) become event equivalents using `fire_editor_event` /
  `editor_event_fired`.
- Update `index.html` ids/labels to match.

## 3. `facilitator.js` + `facilitator.html` — the Cues panel

The standalone facilitator's `#cue-panel` becomes an **events** panel:
`liveCueSchema` → the manifest's `events`, `cueButton` → an event button,
`data-live-cue` → `data-live-event`, `fire_cue` → `fire_event` honouring the
existing `targetFilter`. The `#cue-lead` field reads `event_lead_ms` and
sends `set_event_lead`. Rename ids and copy from "cue" to "event".

## 4. `show.js` — the step builder and the pill

- `inferMessageMode`: `/cue` → `/e/` returning `"event"`.
- The pill category `cue: {code: "CUE", label: "cue"}` is **renamed** to
  `event: {code: "EV", label: "event"}`. **The flat set stays eight
  categories** — do not add a ninth; the tied `25-message-pill-encoding`
  taxonomy must survive intact. Arity is not encoded in the pill.
- The cue builder (`renderCueBuilder`, `#show-cue-picker`, the `mode === "cue"`
  branches, `manifest.cues`) becomes an event builder: pick a declared event
  identity, then edit its 0–3 element values. Address becomes
  `/e/<identity>`.
- Events are **targetable**, unlike cues: `targetDisabled` must no longer
  include the event mode (it stays true for `point`).
- The transport's `#show-cue-lead` field → `#show-event-lead`, label
  "event lead · ms", sending `set_event_lead`. Keep the existing
  focus-preserving draft logic.
- The `/cue` address summary at line ~81 becomes the `/e/<identity>` summary.

## Boundaries

- Hard break: no shim, no alias, no fallback for a `/cue` message.
- Do not add a ninth pill category.
- Do not touch Python — lane A owns it.

## Acceptance checks

- `grep -rn cue dashboard/static/` returns nothing (case-insensitive check
  too: `grep -rni cue dashboard/static/`).
- `node --check` each modified `.js` file.
- Report which Playwright journeys under `tests/` reference the ids you
  renamed — do **not** edit them; the orchestrator will.

Report what you changed, how you verified it, and anything you could not do.
If you could not complete the task, say so explicitly.
