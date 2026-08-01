# Results — 3-event-plane-wire

Contract **v1.14**. `/e/*` exists on the wire; `/cue` is untouched and still
works (child 4 deletes it).

## What shipped

- `python/sync_node.py` — `CueScheduler` generalized to `EventScheduler`
  carrying `(shared_ns, identity, elements)`. `SyncState`, the slew, the pong
  reply and the ping cadence are untouched — one clock path, as specified.
  `CueScheduler = EventScheduler` alias keeps `/cue`'s import alive for one
  stitch. `CUE_LATE_GRACE_NS` unchanged (it governs scheduled event fires).
- `python/bopos.py` — `/<selector>/e/<identity>` dispatch with selector
  matching and the `/p/*` identity grammar; `fire_event_to_engine` sends the
  bare, selector-free, time-free `/e/<identity>` with 0–3 floats. Reported
  `contract_version` → `1.14`.
- `dashboard/osc_bridge.py` — `fire_event(selector, identity, elements,
  lead_ms)`; `lead_ms == 0` sends the `"0"` sentinel. `fire_cue`/`fire_cue_now`
  left intact for child 4.
- `dashboard/state.py`, `server.py`, `show_engine.py`, `show.js`,
  `facilitator.js`, `facilitator.html` — `cue_lead_ms` → `event_lead_ms` with
  a load-time fallback read of the old key, and the lower bound relaxed from
  100 ms to **0** everywhere so the sentinel is reachable from the UI.
- `tools/simfleet.py`, `tools/audition.py` — parity in this stitch, per the
  house rule. Both honour the sentinel and the three selectors.
- `docs/OSC-CONTRACT.md` — new §3.2 (renumbering automation to §3.3), the
  split-owner planes row, the §4.1/§4.2 entries, §8 `events` rewritten from
  "declared but not wired", and the v1.14 changelog row.
- `.notes/pd-edits-for-bob.md` — the `bopos~.pd` / `babs.blineseq.pd` receiver
  change Bob owes. **No `.pd` file was edited.**

## Defect found in review

The delegate generalized the scheduler to call `fire(identity, elements)` but
left `fire_cue_to_engine(cue_id)` at arity 1. Every `/cue` fire would have
raised `TypeError` inside the scheduler thread at its deadline — a cue that
silently never fires, on the one plane this stitch promised not to disturb.

Its own `/cue` test could not see this: it mocks `cue_scheduler.schedule`, so
the fire callback is never invoked. Fixed
(`fire_cue_to_engine(cue_id, elements=())`) and covered by a new test,
`test_cue_fire_callback_accepts_the_generalized_payload`, which exercises the
real callback. Confirmed the test fails with the old signature
(`TypeError: fire_cue_to_engine() takes 1 positional argument but 2 were
given`) and passes with the fix.

**Carry-forward:** mocking the scheduler is the right unit boundary for
dispatch tests, but it means any signature change to a scheduler's fire
callback needs a separate test that calls the real callback.

## Verification (run here, not taken on report)

    $ tools/run-tests.sh fast
    Ran 194 tests — OK

    $ grep -rn '"1.13"' python dashboard tools tests
    (none)

    $ ~/.venvs/bopos/bin/python \
        .loom/tied/3-event-plane-wire/verify_event_wire.py
    PASS: /e/* reaches simulated nodes at all/seat selectors, arity 0-3,
          the "0" sentinel fires on arrival, a lead fires at its deadline,
          and a group selector matching nobody reaches nobody.

`verify_event_wire.py` is the stitch's own socket-level check: it launches the
real `tools/simfleet.py` on non-default ports and sends genuine UDP datagrams,
because the delegate's sandbox forbids binding UDP and could only exercise the
handler in-process. Repo root is found by marker, so it survives the `tie`
move.

Group selection asserts the negative (`/g0/e/*` reaches nobody) — simfleet
nodes boot ungrouped and there is no dashboard in this harness to author
membership. The positive group case is covered by the control-panel journey in
child 4, which has a dashboard.

**Not verified here:** real Pure Data reception. That is child 5 (Bob's `.pd`
edits plus the Finn Jet / Ciro Toast rig check), as the instructions specify.

## Notes for child 4

- `set_cue_lead` / `fire_cue` / `fire_editor_cue` websocket command *names* are
  unchanged this stitch; only the persisted key moved. Child 4 renames them.
- The facilitator's lead field now accepts 0, but `fire_cue` still clamps to
  100 ms internally, so 0 is only meaningful for `/e/*`. Resolves itself when
  `fire_cue` is deleted.
- Two scheduler threads run concurrently (event + cue) sharing one `SyncState`.
  Child 4 removes the cue one.
