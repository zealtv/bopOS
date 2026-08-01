# verification — engine-group-context

## What was run

1. `~/.venvs/bopos/bin/python .loom/threads/engine-group-context.stitching/verify_engine_group_context.py`
   (new, in-stitch, browser-free). **Result: 0 failures / all checks PASS.**
   Covers all six brief items:
   - (1) launch delivery — `runcontext.resolve_groups()`/`generate()` read the
     persisted `state/store/groups` file and return sorted OSC ints or the
     `[-1]` sentinel; `start-engine.sh` carries `BOPOS_GROUPS` into both the
     PD `-send` string and the non-PD env line; `audition.py`'s
     `engine_command()` builds the equivalent `-send` string from
     `node.groups`.
   - (2) replacing membership (`bopos.apply_groups`, and
     `/all/os/groups` through `audition.AuditionRig.relay`) emits exactly one
     new engine-bound message per change, carrying the complete sorted list.
   - (3) clearing membership (empty-tail `apply_groups`, `apply_assign` to a
     different Seat, `apply_unassign`, and their `audition.py` equivalents)
     emits exactly one engine message, `["/groups", ",i", -1]` /
     `("/groups", [-1])`.
   - (4) rejection paths: duplicate/invalid ids, UID mismatch, and a
     `store.put("groups", ...)` failure (`FailingStore`) all leave
     `bopos.client.sent` (resp. the audition capture socket) untouched and
     leave in-memory state unchanged — including the harder case of a
     `apply_assign` reassignment whose *group-clear* persistence step fails:
     the whole reassignment fails, the old id is kept, and nothing reaches
     the engine.
   - (5) no leakage across assignment/unassignment: reassigning to a
     different Seat clears membership durably and the *only* `/groups`
     message on the wire after the call is the `-1` clear (never the old
     Seat's list); reassigning to the *same* Seat sends no `/groups` message
     at all (membership untouched); unassign behaves like the cross-Seat
     clear. Verified for both `bopos.py` and `audition.py`.
   - (6) audition parity: the same replace/clear/reject/reassign/unassign
     scenarios run through `audition.AuditionRig` and are asserted to use
     the identical wire shape (`/groups <int...>` or `/groups -1`) that
     `bopos.py` emits.
   Also does light static checks (`bash -n start-engine.sh`, exact token
   presence in `start-engine.sh`, `demo-pd` manifest load) and
   `py_compile` on the four touched Python files.

2. `~/.venvs/bopos/bin/python .loom/tied/1-protocol-node/verify_group_protocol_node.py`
   — re-ran unmodified. **Pre-existing failure, not caused by this stitch:**
   it crashes with `AttributeError: 'AuditionRig' object has no attribute
   'param_declarations'` at the same `rig.relay(...)` call whether or not
   this stitch's changes are applied (confirmed via `git stash`/`stash pop`
   bisection — the traceback line number shifts only because of unrelated
   code already added to `tools/audition.py` since this verifier was tied;
   the failure point and cause are identical on `main` before this stitch).
   All checks *before* that crash point pass, including every
   assign/unassign/group-replace assertion this stitch's code path touches
   (`apply_assign`, `apply_unassign`, `apply_groups`, and their simfleet/
   audition equivalents).

3. `~/.venvs/bopos/bin/python .loom/tied/seat-groups-1-core-implementation/verify_group_core_integration.py`
   — re-ran unmodified. **PASS** (dashboard-to-simfleet group convergence
   and parameter fan-out unaffected; this path doesn't touch the engine
   context surface).

4. `~/.venvs/bopos/bin/python .loom/tied/boundary-5-launch-context-and-topology/verify_launch_context.py`
   — re-ran unmodified for reference. **Pre-existing failures/crash,
   unrelated to this stitch:** confirmed via the same stash bisection that
   `test_runcontext_cli` ("prints exactly two lines"), one
   `shape_provided_term` 4-part-address check, and a hard crash in
   `test_bash_launchers` (`bash/start-laptop.sh` no longer exists in the
   repo) all fail/crash identically with and without this stitch's changes.
   This verifier is stale relative to several already-tied amendments
   (version/patch-fingerprint context, the 4-part-address rejection
   behavior) that landed after it was tied, and predates this stitch. Not
   modified, per instructions — flagged here rather than "fixed in passing."

5. `py_compile` (also inside the new verifier, restated here for the
   record): `python/runcontext.py`, `python/groups.py`, `python/bopos.py`,
   `tools/audition.py` — all compile cleanly.

## Unverified boundaries

- **Real PD reference-patch receiver.** No `.pd` file was edited (house
  rule). `pd/bopos~.pd` does not yet route a `groups` branch of
  `[route id os audition]` into `bopos-context`; this is recorded for Bob in
  `.notes/pd-edits-for-bob.md` under "2026-07-20 — Seat-group membership on
  the bopos-context bus." Until that edit lands, a live PD engine receives
  the `/groups <int...>` OSC message on port 6661 (proven reaching the
  engine socket by the Python-side tests above) but has no wired consumer
  for it inside the patch graph.
- **Real hardware / audible verification.** Nothing here was run against a
  live Pi, real PD process, or real JACK/audio path — all coverage is
  protocol-level (fake OSC client/server substitution and captured
  sockets), matching the house convention for this class of stitch.
- **Non-PD engine (SC) consumption.** `demo-sc`'s `main.scd` was not changed
  or exercised; it already reads `BOPOS_*` env vars and can read `BOPOS_GROUPS`
  and/or the live `/groups` OSC message the same way it reads other
  `BOPOS_*`/engine-surface values, but no SC-side consumption code exists
  yet and none was added (out of scope — no SC patch declares interest in
  group membership today).
