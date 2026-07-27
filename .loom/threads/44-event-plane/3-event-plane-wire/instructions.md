# 3-event-plane-wire

Build the `/e/*` plane. Authority: tied `1-event-plane-design` (proposal §§2–4,
7). Contract revision **v1.14**. After child `2`.

## Wire

Leader → fleet (6660):

```
/<selector>/e/<identity>  <sharedTimeNs:string> [<e0:float> [<e1> [<e2>]]]
```

Node → engine (localhost 6661), at the local deadline — selector-free and
**time-free**:

```
/e/<identity>  [<e0> [<e1> [<e2>]]]
```

`<identity>` uses the `/p/*` segment grammar (`[A-Za-z0-9_-]+`, ≤8 segments,
≤255 bytes, nesting allowed). The fixed `sharedTimeNs` comes **first** because
the element list is variable-length. It is the decimal string of an integer
nanosecond count (§12) — never a 32-bit float. A zero-element event is the
bare `/e/<identity>` with no arguments.

## The `"0"` sentinel

`sharedTimeNs == "0"` means **fire on arrival**, bypassing the scheduler
entirely. This is what makes Bob's "global lead time 0 is sync-off" exact: a
0-lead fire scheduled normally arrives already late by one network hop and
survives only because the hop is under `CUE_LATE_GRACE_NS` (50 ms,
`python/sync_node.py:22`), which on a congested rig is a fire button that
silently does nothing. A real `monotonic_ns()` is never 0, so the sentinel is
unambiguous and costs no extra argument. The late-grace policy then governs
only genuinely scheduled fires.

## Scope

- `python/sync_node.py` — generalize `CueScheduler.schedule(shared_ns,
  cue_id)` to carry an identity and an element list. `SyncState`, the offset
  slew, the pong reply, and the ping cadence are **untouched** — no second
  clock path.
- `python/bopos.py` — route `/e/*` (`parts[0] == "e"`) through the scheduler;
  `fire_cue_to_engine` → `fire_event_to_engine` sending the bare relative
  fire.
- `dashboard/osc_bridge.py` — `fire_cue(cue_id, lead_ms)` →
  `fire_event(selector, identity, elements, lead_ms)`; delete `fire_cue_now`
  (the sentinel replaces "earliest deadline").
- `dashboard/state.py` — `cue_lead_ms` → `event_lead_ms`, with a load-time
  fallback read of the old key. Settings loading, not a wire shim.
- Undeclared identities: the framework **schedules any well-formed `/e/*` fire
  without consulting the manifest** (as it never filtered cue IDs); the
  dashboard **badges** an undeclared identity, per the `/p/*` precedent.
- `tools/simfleet.py` and `tools/audition.py` parity **in this stitch** —
  house rule: protocol features land in the simulator together. Both must
  honour the sentinel.
- `docs/OSC-CONTRACT.md` — the new §3 planes row (note the **split owner**:
  patch-declared identities, framework-scheduled — the first such plane), the
  arity 0–3 wire shape, and the sentinel. Bump the reported `contract_version`
  in lockstep across bopos/simfleet/audition and the tests that pin it.
- Write the `bopos~.pd` / `babs.blineseq.pd` receiver change into
  `.notes/pd-edits-for-bob.md` — **do not edit `.pd` files.** Adoption is
  child `5`.

`/cue` still exists after this stitch; child `4` deletes it. Keeping the two
apart means the risky wire work can be reverted without touching the
retirement, and vice versa.

Verify: headless throughout — simfleet with `--sim-no-engine`, asserting the
fire reaches a simulated node at all three selectors (all / group / seat),
each arity 0–3, and that a `"0"` sentinel fires on arrival while a normal lead
fires at its deadline. Real PD reception is child `5`.
