# Results — 4-cue-retirement

`/cue` is gone. Contract **v1.15** (hard break; see `decisions.md` §3 for why a
new version rather than a v1.14 amendment).

## What went

Deleted outright, with no shim, alias or deprecation path:

- `python/bopos.py` — the `parts == ["cue"]` dispatch, `fire_cue_to_engine`,
  the second `cue_scheduler` instance and its start/stop.
- `python/sync_node.py` — the `CueScheduler = EventScheduler` alias.
  `CUE_LATE_GRACE_NS` **survives by name** (contract §3.1 cites it); its
  comment now says plainly that it governs scheduled `/e/*` fires and why the
  name is unchanged.
- `python/manifest.py` — the `cues` block and `CUE_ID`. Event `arity` widened
  to **0–3**: a cue is a zero-element event.
- `dashboard/osc_bridge.py` — `fire_cue`, `fire_cue_now`.
- `dashboard/show_engine.py` — the `/cue` branch; `/e/<identity>` now routes
  per-target through `fire_event`.
- `dashboard/server.py` — websocket verbs renamed `set_cue_lead` →
  `set_event_lead`, `fire_cue` → `fire_event`, `fire_editor_cue` →
  `fire_editor_event`, with identity/arity validation and the
  `event_scheduled` / `editor_event_fired` broadcasts.
- `tools/simfleet.py`, `tools/audition.py` — `handle_cue` / `schedule_cue` /
  `dispatch_due_cues` and the `/cue` dispatch.
- `dashboard/static/` — the whole cue-era browser surface (see below).
- `docs/OSC-CONTRACT.md` — planes row, §3.1 entry, §8 `cues` key, §4.2 term.
  The "two framework addresses that omit the selector" note is now one
  (`/sync/ping` alone). v1.15 changelog row added.

## Control panel

Event rows are live and targetable at all seats / a group / one seat — which
`/e/*` supports natively and `/cue` structurally never could. The panel now
splits into **Parameters** and **Events** sections, per Bob's ruling.

**The per-row `sync` toggle is gone**, superseding what tied stitch
`6-non-float-kinds` shipped (`decisions.md` §4). One fire button per row.

Pill category `cue`/`CUE` → `event`/`EV`, **renamed not added**: the flat set
stays eight, so the tied `25-message-pill-encoding` taxonomy survives.

## Things the instructions did not predict

Both recorded in full in `decisions.md`:

1. **The pre-check's premise was false.** Three patch manifests *did* declare
   `cues` (`bonks-pd`, `demo-pd`, `fire-button`), contradicting the design's
   measurement. Proceeded rather than stopping, because the gate's purpose —
   "has anything come to rely on cues?" — is still satisfied: no show document
   fires one, and both real ids are already valid address segments. Migrated
   to zero-arity events. **`bonks-pd` and `fire-button` are gitignored**, so
   their migration lives in the working copy only and is not committed.
2. **`tools/sync_measure.py` was not in the 15-file sweep table** but fires
   cues and parses the node log line, so deletion broke it outright. Migrated
   to `/all/e/m<n>` with `--events`.

## Defects found in review

- **Event rows ignored the `disabled` gate** every param row honours, so an
  offline or unbound target still offered a live fire button that would put a
  datagram on the wire for nobody. Fixed.
- **The event row's `data-param-path` had been renamed to
  `data-event-identity`**, breaking the row-selector convention every other
  kind shares — caught by `verify_control_surface_component.py` failing.
  Unified back onto `data-param-path`; the section split is what distinguishes
  an event, not a bespoke attribute.
- **Eight Playwright journeys still carried `"cues"` fixtures**, and
  `verify_control_tab.py` asserted on `#cue-panel`. Neither delegate lane
  owned them and the fast tier does not run them, so nothing caught this until
  the browser tier ran. Migrated.

## Verification (run here, not taken on report)

    $ tools/run-tests.sh all      # exit 0
    fast:    Ran 196 tests -- OK
    browser: 13/13 PASS, including the new verify_event_control_panel.py

    $ grep -rn cue python/ dashboard/*.py tools/
    python/sync_node.py:  CUE_LATE_GRACE_NS and its comment only

    $ grep -rni cue dashboard/static/
    (none)

    $ grep -rn '"cues"' patches/ python/ dashboard/*.py tests/
    (none)

    $ ~/.venvs/bopos/bin/python .loom/tied/3-event-plane-wire/verify_event_wire.py
    PASS  (the /e/* plane is undisturbed by the retirement)

New living journey `tests/verify_event_control_panel.py` is the stitch's
stated gate: it fires `strike` from the control panel's events section at
**all / a group / one seat**, and reads simfleet's stdout to confirm
`/all/e/strike`, `/g7/e/strike` and `/2/e/strike` reach exactly the right
devices, each carrying the typed floats after the leading shared-time string.

## A pre-existing flake, fixed in passing

`verify_control_surface_component.py`'s "choosing an enum option sends its
integer index" failed roughly one run in three. **Confirmed pre-existing** by
stashing this stitch and reproducing it on the previous commit (1 of 3 runs,
identical symptom), so it is not a regression here.

Cause: `bindParams` assigns `onchange` after every re-render, so the probe's
`change` dispatch could land on a freshly rendered, not-yet-bound `<select>`
and send nothing — leaving `__probeSent.at(-1)` holding the *previous*
interaction's `filter/cutoff` send. Fixed by waiting for the binding
(`?.onchange`) before dispatching, and by matching the entry by param name
rather than by position. Five consecutive clean runs, then a green full suite.

Worth carrying: on this UI, waiting for an *element* is not the same as
waiting for its *handler*.

## Not verified here

Real Pure Data reception. Child `5` is Bob's: the `.pd` receiver edits plus the
Finn Jet / Ciro Toast rig check. **The `.pd` receivers in `patches/bonks-pd`
and `patches/demo-pd` stop working the moment this lands** — that is thread
44's designed shape, not a surprise, but both are now named explicitly in
`.notes/pd-edits-for-bob.md` rather than left to be discovered on the rig.
