# The OSC contract is ratified; amend it, don't relitigate it

When touching anything on the wire, work from `docs/OSC-CONTRACT.md` (v1.17 as of 2026-09) — its §15 revision history is the authoritative record of how it got there.

- Wire changes are Bob's to ratify: propose, mark the stitch `.waiting`, surface it.
- Each change gets a §15 entry. Prefer additive; when a hard break is right, take it cleanly (no compatibility shim — the `/cue` retirement in v1.15 is the precedent) and say what breaks.
- Keep `docs/PORTS.md` in step with the contract's ports section.
- New protocol behaviour lands in `tools/simfleet.py` in the same stitch.
- Planes as of v1.17: `/p/*` params with generator automation (§3.2), `/e/*` events (every event forward-syncs; `"0"` fires on arrival), `/pt` points, `/os/*` and `/admin` for device management. Presets are not a wire concept. There is no streamed telemetry or meter plane, by design (§6).

## Triggers

- OSC-CONTRACT
- contract amendment
- /e/
- /p/
- /os/probe
- PORTS.md

## Associations

- [[decision-gates]]
- [[manifest-and-patch-distribution]]
- [[pd-float-precision]]
