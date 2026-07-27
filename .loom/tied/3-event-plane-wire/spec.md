# Delegate spec — 3-event-plane-wire

Written by the orchestrator before delegating. Also the review checklist.

## Goal

Add the `/e/*` event plane to the wire, alongside (not replacing) `/cue`.
Contract revision v1.14. Cue deletion is a separate later stitch — `/cue` must
keep working exactly as it does today.

## Wire

Leader → fleet (6660):

    /<selector>/e/<identity>  <sharedTimeNs:string> [<e0:float> [<e1> [<e2>]]]

Node → engine (localhost 6661), at the local deadline, selector-free and
time-free:

    /e/<identity>  [<e0> [<e1> [<e2>]]]

`<identity>` uses the `/p/*` segment grammar. `sharedTimeNs` is a decimal
string of integer nanoseconds — never a float. `sharedTimeNs == "0"` is the
**fire-on-arrival sentinel**: bypass the scheduler entirely and send to the
engine immediately.

## Files and changes

1. `python/sync_node.py`
   - `CueScheduler.schedule(shared_ns, cue_id)` →
     `schedule(shared_ns, identity, elements)`; pending entries carry
     `[shared_ns, identity, elements]`; `self._fire(identity, elements)`.
   - Keep `CUE_LATE_GRACE_NS`, `SyncState`, slew, thread name semantics.
     Rename the class to `EventScheduler` with `CueScheduler = EventScheduler`
     left as an alias so `/cue` keeps working this stitch.
   - `/cue`'s call site adapts by passing `elements=[]`.

2. `python/bopos.py`
   - Route `parts[1] == "e"` (i.e. `/<selector>/e/<identity...>`) when the
     selector matches this node: parse `args[0]` as the shared-time string,
     remaining args as floats. `"0"` → fire immediately; else schedule.
   - Identity is the remaining address segments joined by `/`.
   - `fire_cue_to_engine` stays; add `fire_event_to_engine(identity, elements)`
     sending `/e/<identity>` with float args.
   - Bump `"contract_version"` to `"1.14"`.

3. `dashboard/osc_bridge.py`
   - Add `fire_event(selector, identity, elements, lead_ms=500)`:
     clamps lead to 0..10000; `lead_ms == 0` sends `"0"`, else
     `str(monotonic_ns() + lead_ms*1e6)`; sends
     `/<selector>/e/<identity>` with `[str(shared), float(e0)...]`.
     Returns `(shared_time_ns, lead_ms)`.
   - Leave `fire_cue`/`fire_cue_now` alone (stitch 4 deletes them).

4. `dashboard/state.py`, `dashboard/server.py`, `dashboard/static/js/*.js`
   - Rename the settings key `cue_lead_ms` → `event_lead_ms` everywhere
     (state defaults, clean_*, public(), the `set_cue_lead` handler's write,
     show_engine's accessor, and JS reads).
   - On load, fall back to a stored `cue_lead_ms` when `event_lead_ms` is
     absent. This is settings loading, not a wire shim.
   - `event_lead_ms` valid range becomes **0..10000** (0 = sync off).

5. `tools/simfleet.py`, `tools/audition.py`
   - Handle `/<selector>/e/<identity>` with selector matching, the `"0"`
     sentinel, and the same deadline arithmetic as `/cue`. Log lines in the
     existing style (`event <identity> fired ...`). Keep `/cue` handling.
   - Bump their `contract_version` to `"1.14"`.

6. `docs/OSC-CONTRACT.md`
   - Version header → 1.14; new `/e/*` row in the §3 planes table with the
     **split owner** (patch-declared identities / framework scheduling);
     §3.x subsection giving the two wire shapes, arity 0–3, and the `"0"`
     sentinel; a changelog row `| 1.14 | 2026-07-28 | ... | thread
     44-event-plane |`.

7. `.notes/pd-edits-for-bob.md`
   - Append the receiver change Bob owes: `bopos~.pd` / `babs.blineseq.pd`
     must route `/e/<identity>` alongside the existing `/cue`.
   - **Do NOT edit any `.pd` file.**

8. Tests pinning `contract_version` `"1.13"`: `tests/test_device_enabled.py`,
   `tests/verify_log_destination.py`, `tests/verify_device_control_modes.py`.

## Boundaries

- Do not touch `.loom/` state, `.pd` files, or anything under `.loom/tied/`.
- Do not delete or alter `/cue` behaviour.
- Do not touch `dashboard/shows/test.json`.

## Acceptance checks

- `tools/run-tests.sh fast` green.
- `grep -rn '"1.13"' python dashboard tools tests` returns nothing.
- New unit test `tests/test_event_plane.py` covering: scheduler fires
  identity+elements at the deadline; the `"0"` sentinel fires immediately;
  arity 0/1/2/3 round-trip; `/cue` still schedules.
