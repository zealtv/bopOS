# 06-application-core

The one preset application path (R1). Every caller — Control tab, Device
panel, editor recall (08), Show expansion (09) — goes through this service.
**Needs 05 tied.** This stitch is server-side; it ships no UI.

Authority: `../design-addendum.md` §4/§5/§7, `.loom/tied/3-addendum-review/review-2.md`
F3/F4/F6/F7/F8, proposal §3. The old `load_preset`
(`dashboard/server.py:821`) is the partial prior art being replaced — read
it, don't extend it (it retires in stitch 10).

## The apply pipeline

`apply_preset(patch, name, scope, target_id, duration_ms=None, curve=None)`:

1. **Load** the validated preset through the 05 store cache. Malformed →
   refused with the store's error.
2. **Resolve to concrete seats first** (D4): reuse the existing scope
   machinery (`live_param_target` / `_selector_seats`,
   `dashboard/osc_bridge.py:473-485`).
3. **Effective patch per seat**: the bound device's pin
   (`state.device_patch_for`) else the staged fleet patch —
   `live_scope_patch` (`dashboard/server.py:1543-1555`) diverges only for
   device scope today; this generalizes that per seat. Seats whose effective
   patch ≠ the preset's patch are **skipped and reported** — derived,
   non-blocking, never an error.
4. **Per-entry drift resolution** against each seat's effective patch
   manifest, using 05's pure function: apply / clamp / drop.
5. **Kind-aware timed apply** (the morph-drop rule, ruled 2026-07-29): with a
   duration, `float`/`int` entries emit the existing fade form
   (`[dest, dur]` + trailing `c:<n>` when a curve is given); `toggle`,
   `enum`, `text`, and generator (`lfo`/`loop`) entries are sent full-state
   at t=0 and counted **snapped** in the report. Without a duration,
   everything is a plain full-state send. Enums must never ride a fade — the
   int crossing path would audibly step through every intermediate option.
6. **Fan-out with honest coalescing** (F3): send per-seat, coalescing to the
   original `all`/`gN` selector **only when no seat was skipped** — and
   record in a code comment + `decisions.md` that this is an *optimization
   with a named delta*, not an equivalence: `selector_matches`
   (`python/groups.py:55-73`) matches `all` on unassigned devices too, which
   per-seat fan-out never reaches. That matches how every other all-scoped
   control behaves and is accepted; `gN` membership-sync lag is the second
   accepted transient delta.
7. **Durable + automation state**: seat/device param mirrors updated with
   the canonicalized applied value (fade entries store the destination, as
   `_store_fade_destination` does today, `osc_bridge.py:487-499`); generator
   entries recorded in the automation table with args + `sent_at` exactly as
   `set_param` does (`osc_bridge.py:426-469`).
8. **Provenance per concrete seat** (A7): `applied_preset {patch, name}`,
   runtime-only (forgotten on dashboard restart, like automation). Set on
   apply, overwritten by a later apply to that seat, cleared by an explicit
   recall-none. No ledger.
9. **Report**: per-target counts — applied / clamped / snapped / dropped /
   skipped — returned to the caller and broadcast. One structure, reused by
   every caller's UI.
10. **Atomicity**: one persist + one broadcast per apply, via the existing
    serialized WS mutation discipline.

## Canonicalization (U4)

One shared function at the durable write boundary: floats formatted exactly
as `_datagram` sends them (`.6g`, `osc_bridge.py:390-397`), ints floored.
Used by apply, capture, clamping, and dirty comparison — store exactly the
value sent. Audit the existing live-write path (`clean_editor_value`,
`dashboard/server.py:1761-1784`, persists raw before send) and route it
through the same function so the mirror can never hold `0.1234567` while the
node received `0.123457`.

## Generator-aware replay (D6 + F6)

`replay_live_params_for_seat` (`dashboard/server.py:1512-1518`) currently
replays only durable scalars. Repair for *all* automation, not just presets:
per seat/identity, replay the automation entry's full args when it is
**active**, else the durable scalar. Active is **derived, not stored**
(nothing ever removes a completed fade from the table): `loop`/`lfo` are
always active; a fade is active only while `sent_at + total duration` has
not elapsed. Replay must **preserve the original `sent_at`** — a fresh
timestamp would resurrect a nearly-expired fade. (Resending a synced LFO is
idempotent node-side and the browser marker logic already tolerates it,
`control-surface.js:100-125`.)

## Honest stop (F7 — option 1, ruled by the review)

The Stop path keeps sending `stop` on the wire, and additionally evaluates
the generator at stop time server-side (LFO from `sent_at`/phase math, fades
from segments) and writes the result durably, so capture and replay stop
lying. Free/`sh`/`drift` LFOs are documented estimates — the node's value is
unknowable (device-local phase, `paramgen.py:272,291-295`). All UI/doc
language: "dashboard state", never "what the engine is playing" (U3).

## Capture

The capture function (used by save in 07/08 and capture-as-step in 09), per
proposal §1's table: durable value → `[v]`; running lfo/loop → args
verbatim; fade in flight → destination (already durable); mixed across an
aggregate target → omitted; text → `["…"]`; events never. Plus the
projection helpers 07/09 need: card agreement (a card shows a preset when
**all** its seats carry it, else mixed — same idiom as `aggregateValue`,
`control-surface.js:71-81`) and capture target derivation (seat set = all
seats → `all`; = a group's membership → that group, **tie-break lowest group
id** when two groups have identical membership; else a seat list).

## Derived dirtiness

Derive server-side and publish per seat alongside `applied_preset` (C3:
cards get the selected preset + dirty flag, never the preset-list bodies).
Compare captured entries against current durable values + automation args at
canonical precision; generator entries compare by argument list.

## Verify and tie

Fast-tier tests: drift resolution matrix, patch-mismatch skip, coalescing
rule (skipped ⇒ per-seat), timed-apply kind table, replay expiry (completed
fade replays scalar; loop/LFO replay verbatim with original `sent_at`), stop
estimate write, canonicalization round-trip, provenance projection +
tie-break. Use simfleet (`--sim-no-engine`) where a live node matters.
`tools/run-tests.sh fast` green. Decisions in `decisions.md`.
