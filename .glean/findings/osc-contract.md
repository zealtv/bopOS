# The OSC contract is ratified; amend it, don't relitigate it

When touching anything on the wire, work from `docs/OSC-CONTRACT.md` (v1.21 as of 2026-10-04) — its §15 revision history is the authoritative record of how it got there.

- Wire changes are Bob's to ratify: propose, mark the stitch `.waiting`, surface it.
- Each change gets a §15 entry. Prefer additive; when a hard break is right, take it cleanly (no compatibility shim — the `/cue` retirement in v1.15 is the precedent) and say what breaks.
- Keep `docs/PORTS.md` in step with the contract's ports section.
- New protocol behaviour lands in `tools/simfleet.py` in the same stitch.
- v1.19 retires Git patch deployment; push converts existing clones through staged, validated replacement with rollback. Framework Git administration stays.
- v1.20 adds exact-device Wi-Fi configuration: ordered WPA-Personal profiles and country, argument-less privileged helper, redacted reports/receipts, LAN-broadcast passphrase warning. Provision on an operator-controlled workshop network; Pi network-manager backend and physical switchover verification remain pending.
- v1.21 adds remembered global Performance mode: `/all/os/performance <0|1>`, boolean `/os/report.performance`, device-side development gates and RAM logging; host mode is independent of projects. No timeout, never-locked exit. `bopos.development_allowed` is the gate for later IO handlers; actual Pi SD-write cessation remains a hardware check.
- Planes: `/p/*` params with generator automation (§3.2), `/e/*` events (every event forward-syncs; `"0"` fires on arrival), `/pt` points, `/os/*` and `/admin` for device management. The host-side saved-parameter facility is retired (§8.1); no wire form was added. §6 has no general telemetry or meter plane. Bob ratified the bounded development-only IO stream in `59/0a` (2026-10-04); its transport/panels ship in later `59` stitches and must enforce Performance. Don't stream outside that.

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
