# PD edits for Bob — the live list

The one place every pending `.pd` change lives (Bob's ruling 2026-07-10: PD
edits must be really visible). Surfaced on the loom as the top-level
`pd-edits-for-bob.waiting` stitch. Agents append here as stitches hit new
edits; Python-side work never waits on these. Detailed step-by-step specs for
items 1–4 live in `.loom/tied/osc-schema-contract/pd-edits-for-bob.md` (the
original running list, now historical); this file is the index of record.

**Context shift (Bob, 2026-07-10):** existing patches will be **rewritten**
for this version of bopOS — backwards compatibility is a non-goal. So these
are no longer incremental edits to keep old patches limping; they are the
spec for **one rewrite wave** of `pd/bopos.osc.pd` + the reference patch /
starter kit.

## A. OS layer — `pd/bopos.osc.pd`

1. **Forward `restart-engine` to helper** — add to the `process-helper-messages`
   route list, treated like `reboot`. helper's handler already exists; the verb
   is unreachable from the LAN until this lands. (Spec: tied file §1.)
2. **Identify chirp** — route `identify` off the 6661 netreceive → audible
   chirp (+ optional `s identify`). Proves the audio chain on install day.
   (Spec: tied file §2.)
3. **Retire PD's own heartbeat + aloha emitters** — helper.py sends the
   contract `/hb` now; PD's `/rpt hb`/version metro and boot `aloha` are wire
   noise. Under the rewrite ruling, simply don't carry them forward. (Spec:
   tied file §3.)
4. **Route the patch plane (`route p`)** — insert `route p` on the
   post-selector remainder so `/5/p/gain 0.5` reaches the patch as `gain 0.5`.
   (Spec: tied file §4.)
5. **Pass `/os/master` through to the patch** — ratified (contract v1.1 §4.1)
   and live since seam-2 (2026-07-11): the dashboard broadcasts
   `/all/os/master <0..1>` on 6660 on every master change, and unicasts it
   per-device in the params catch-up push. The OS layer routes it to a
   patch-visible receive (feeds `bopos.out~`, item B1); the framework never
   composes it into a patch param — the wire carries raw mixes only.
   Routed-single-receiver style per Bob's 7.2 ruling.
6. **Deliver point scalars to the patch** — ratified and live since seam-3
   (2026-07-11): helper computes per-element proximity and sends flat args
   `/pt <pointId> <element> <v>` to PD on 6661. `element` is **0-based**
   (Bob's 2026-07-11 ruling: indices default to 0-indexing), ordered by the
   assignment's position pairs (element 0 = first pair — matches PD
   `[clone]`'s 0-based voice `$1`). A
   point that is cleared or vanishes from a frame is released with one
   final `v=0`. The OS layer routes it to a patch-visible receive (feeds
   `bopos.point`, item B2).
7. **Audition-rig local port** — macOS stock PD cannot share UDP 6660 across
   instances (tied `audition-0-port-spike`). Add an audition startup control,
   recommended `BOPOS_ENGINE_PORT <port>`, which sends `listen <port>` to an
   initially unbound UDP binary `netreceive` feeding a **selector-free** local
   engine surface. With no startup value, normal node behavior stays
   unchanged. The audition relay has already matched the virtual-node selector;
   this inlet must carry the rewrite-wave `/p/*`, `/os/master`, `/pt`, `/cue`,
   and `/id` routes without selecting again. Exact Mac acceptance steps live
   in `audition-1b-pd-mac-gate.waiting` under the audition-rig thread.

## B. Reference patch / starter kit (PD **and SuperCollider** — SC is
first-class; agents write the SC side, `.pd` is yours)

1. **`bopos.out~`** — the sink abstraction, dropped before `dac~`: master
   multiply (from A5) with declick ramp, mute-honor belt-and-suspenders,
   optional post-master level echo as `role:"meter"` (`/<id>/p/level`).
2. **`bopos.point <id>`** — outputs the 0→1 proximity scalar for one point
   (internally routes the A6 receive). Clone-friendly: under the multi-element
   ruling the patch `[clone]`s its element voice and each clone reads its own
   element's values.
3. **`/cue` receiver** — helper fires bare `/cue <cueId>` to PD on 6661 at the
   synced deadline (clock-sync, 2026-07-09); the reference patch needs the
   receiver so cues can fire something audible.
4. **Level meter sender** — the default-patch `role:"meter"` sender from the
   meters surface (2026-07-08); subsumed by B1's level echo if that ships.

## C. Observations (no edit requested — carried from the tied file)

- Heartbeat `value version` is dead wiring (every device reports version 0);
  superseded by helper's `/hb`.
- `route-by-id` boot mismatch: unconfigured device reports id 0 but answers −1.
- `process-helper-messages` route list omits `checkout`.
- Engine-side persistence store (§10) is plumbed in helper; PD needs
  store/load routing + a **local** `/load` reply path whenever a patch first
  wants it.
