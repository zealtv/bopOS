# sync-0-wire-shape

Pin the `/sync/*` and `/cue` wire format and land it in the simulator. Parent
`../instructions.md` has the mechanism; contract §3 reserves `/sync/*` and `/cue`
"shaped by the clock-sync thread" — shaping is delegated here, record the final
shape **additively** in `docs/OSC-CONTRACT.md` (no re-ratification needed; flag it
in the next handoff for Bob's awareness).

- [ ] Define `/sync/ping <seq> <leaderTime>` / `/sync/pong <seq> <leaderTime> <uid> <deviceTime>`
      encodings. **64-bit times as strings or int-pairs — never a single OSC float**
      (house rule: PD 32-bit floats; PD never sees these anyway, helper.py answers).
- [ ] Define `/cue <cueId> <sharedTime>` encoding (sharedTime same encoding rule).
- [ ] simfleet grows sync support in this stitch (CLAUDE.md: protocol features land
      in the simulator in the same stitch): reply to ping with configurable fake
      offset + jitter per sim device, honor `/cue` by logging fire-time.
- [ ] Write the shape into the contract; note the chosen encoding rationale here.
- [ ] verify_*.py per the dashboard pattern (copy newest tied template): ping the
      simfleet, assert well-formed pongs and cue fire logging.

Implementer's call (record it here): string vs int-pair encoding.
