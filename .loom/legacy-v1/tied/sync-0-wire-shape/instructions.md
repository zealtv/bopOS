# sync-0-wire-shape

Pin the `/sync/*` and `/cue` wire format and land it in the simulator. Parent
`../instructions.md` has the mechanism; contract §3 reserves `/sync/*` and `/cue`
"shaped by the clock-sync thread" — shaping is delegated here, record the final
shape **additively** in `docs/OSC-CONTRACT.md` (no re-ratification needed; flag it
in the next handoff for Bob's awareness).

- [x] Define `/sync/ping` / `/sync/pong` encodings — `wire-shape.md`, contract §3.1.
- [x] Define `/cue <cueId> <sharedTime>` encoding — same string-ns rule.
- [x] simfleet grew sync support: `--sync-skew-ms`/`--sync-jitter-ms`, answers
      ping, stores pushed offset, honors `/cue` by logging the fire (with real
      `fire_mono` for coherence checking).
- [x] Shape + rationale written into contract §3.1 and `wire-shape.md`.
- [x] `verify_sync.py` (pure-socket leader; no browser — sync plane is LAN/engine
      only): asserts well-formed pongs and coherent cross-device cue firing.
      Results + recipe in `results.md`.

Implementer's calls (recorded in `wire-shape.md`):
- Encoding: **integer nanoseconds as a decimal string** (over int-pair) — §12
  already documents `/cue <sharedTime-as-string>`; exact across the two Python
  endpoints; self-describing in logs; full `monotonic_ns()` resolution.
- Offset math lives **leader-side** (only it sees RTT); node applies it (cues are
  broadcast, so each node holds its own offset). A third message
  `/<id>/sync/offset <offsetNs>` (full-state, idempotent, node slews) carries it.
