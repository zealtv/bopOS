# sync-0 — `/sync/*` and `/cue` wire shape (v1, additive)

Pins the clock-sync plane the rest of the thread (`sync-1` leader, `sync-2`
helper cue, `sync-3` jitter harness) builds on. Written additively into
`docs/OSC-CONTRACT.md §3.1` — no re-ratification (contract §3 reserved
`/sync/*` and `/cue` "shaped by the clock-sync thread"). Flag for Bob's
awareness in the handoff.

## Messages

| address | dir | transport | args |
|---|---|---|---|
| `/sync/ping` | leader → fleet | broadcast → 6660 | `<seq:int32> <leaderTimeNs:string>` |
| `/sync/pong` | node → leader | unicast → 5550 | `<seq:int32> <leaderTimeNs:string> <uid:string> <deviceTimeNs:string>` |
| `/<id>/sync/offset` | leader → node | unicast → node | `<offsetNs:string>` |
| `/cue` | leader → fleet | broadcast → 6660 | `<cueId:string> <sharedTimeNs:string>` |

- **`/sync/ping`** — leader broadcasts every ~500±100 ms (HB-style, jittered to
  avoid lockstep bursts). No selector: sync is always fleet-wide, so `all`
  would be redundant noise.
- **`/sync/pong`** — helper.py answers unicast. It **echoes** `seq` and
  `leaderTimeNs` so the leader stays stateless and a lone packet in a log is
  self-describing (contract §3). `deviceTimeNs` is the node's
  `time.monotonic_ns()` at reply.
- **`/<id>/sync/offset`** — the leader's best current offset estimate for that
  one device, pushed unicast. Follows the normal
  `/<selector>/<plane>/<member>` grammar; selector is always a concrete `<id>`
  (`all` is meaningless — offset is per-device). **Full-state absolute value**,
  never a delta: re-sending is safe (contract §4 idempotency law). The node
  **slews** its working offset toward the received value while audio runs, never
  steps (HB gen-2 `adjustScheduleTime`); slew is node-internal, not wire state.
- **`/cue`** — one broadcast instant for the whole fleet. Each node converts
  locally with its stored offset and fires the bare `/cue <cueId>` to its engine
  on localhost at the deadline. The engine never sees absolute time (contract
  §12).

## Encoding — implementer's call: integer nanoseconds as a decimal string

All time-valued args (`leaderTimeNs`, `deviceTimeNs`, `offsetNs`,
`sharedTimeNs`) cross the wire as the decimal string of an integer number of
nanoseconds from `time.monotonic_ns()`. `seq` is a plain OSC int32; `cueId` is
a string label (allows named cues like `verse1`, not just numbers).

**String-ns over int-pair, chosen because:**

1. **House rule / §12.** A 64-bit time must never cross as a single 32-bit OSC
   float, and §12 already documents `/cue <sharedTime-as-string>` — string is
   the established pattern, so `/sync/*` and `/cue` stay uniform with it.
2. **Both endpoints are Python** (helper.py, dashboard backend). `int(s)` /
   `str(n)` is exact and trivial — no int32 hi/lo split, no unsigned-wrap
   hazard (OSC ints are signed int32).
3. **Self-describing wire.** The value is human-readable in a packet log, which
   the contract explicitly values (§3).
4. **Nanoseconds, not millis.** Costs nothing extra as a string and preserves
   full `monotonic_ns()` resolution for offset smoothing; the <10 ms jitter
   target keeps generous headroom.
5. **Idempotency.** Offset is pushed as an absolute value (not amount+duration)
   so the message obeys §4's full-state law; slewing is node-internal.

## Where the offset math lives — implementer's call: leader computes, node applies

Only the leader sees the round trip (it initiates the ping), so it owns the
`oneWay = RTT/2`, `offset = (deviceTime + oneWay) − leaderNow` smoothing. But
cues are **broadcast** (§4) carrying a single leader-clock instant, so each node
must hold its own offset to convert. Hence: **leader computes → pushes
`/<id>/sync/offset` → node slews + converts cues.** `offset ≡ deviceClock −
leaderClock`, so a leader-clock instant converts as
`deadlineNs = sharedTimeNs + offsetNs`.

## Grammar note (folded into §3.1)

`/sync/ping` and `/cue` are the two framework addresses that **omit the
selector** — broadcast-only and inherently fleet-wide. `/sync/pong` is a
node→controller 2-part like `/hb`. `/<id>/sync/offset` is normal 3-part. All
additive; §4 already lists `/cue` as broadcast.

## Simulator support (landed here, per CLAUDE.md)

`tools/simfleet.py` grew, under `--protocol v1`:
- per-device fake clock skew (`--sync-skew-ms`, random ± per device) and
  per-pong measurement jitter (`--sync-jitter-ms`); device clock =
  `monotonic_ns() + skew`.
- answers `/sync/ping` with a well-formed `/sync/pong`;
- stores a pushed `/<id>/sync/offset`;
- honors `/cue`: converts `sharedTime + offset → device-clock deadline`,
  schedules, and logs the fire with `dev_deadline` and real `fire_mono` so a
  test can prove cross-device coherence.

Because leader and sim share Linux's system-wide `CLOCK_MONOTONIC`, a correct
offset ≈ the device's fake skew, and all devices fire at one real instant —
the whole point of clock sync, demonstrable with zero hardware.

## Verify

`verify_sync.py` (pure-socket leader; no browser — the sync plane is
LAN/engine only). Launches simfleet on non-default ports with skew+jitter,
then: asserts well-formed pongs (seq + leaderTime echoed, uid = a device mac,
deviceTime parses as int-ns); learns mac→id from heartbeats; pushes computed
offsets; sends a `/cue` 1.5 s in the future; asserts both devices fired within
tolerance of each other AND of the intended instant (skew cancelled).
