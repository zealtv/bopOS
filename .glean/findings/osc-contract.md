# The OSC contract is ratified; amend it, don't relitigate it

When touching anything on the wire, work from `docs/OSC-CONTRACT.md` (v1.21 as of 2026-10-04) — its §15 revision history is the authoritative record of how it got there.

- Wire changes are Bob's to ratify: propose, mark the stitch `.waiting`, surface it.
- Each change gets a §15 entry. Prefer additive; when a hard break is right, take it cleanly (no compatibility shim — the `/cue` retirement in v1.15 is the precedent) and say what breaks.
- Keep `docs/PORTS.md` in step with the contract's ports section.
- New protocol behaviour lands in `tools/simfleet.py` in the same stitch.
- v1.19 retires Git patch deployment; push converts existing clones through staged, validated replacement with rollback. Framework Git administration stays.
- v1.20 adds exact-device Wi-Fi configuration: ordered WPA-Personal profiles and country, argument-less privileged helper, redacted reports/receipts, LAN-broadcast passphrase warning. Provision on an operator-controlled workshop network; Pi network-manager backend and physical switchover verification remain pending.
- v1.21 ships IO control (`io-scan`, `io-write`, the `io` report object and unsolicited peripheral errors), manifest-owned modules, remembered global Performance mode and leased development IO streams. `/all/os/performance <0|1>` confirms through boolean `/os/report.performance`; host mode is independent of projects, with no timeout and never-locked exit. `bopos.development_allowed` gates writes (including queued writes) and streams; scans stay allowed. `performance` is an administrative refusal, never a module fault, and the existing patch/Wi-Fi refusal phase. `/os/io-stream` receipts carry `{active,error}`; `/io/stream <uid:string> <bundle:OSC blob>` values use unicast 5551. Leases last ten seconds on both node and bridge; Performance closes streams immediately. Dashboard consumers share one device and renew only while consumed. Hardware stream/audio verification and actual Pi SD-write cessation remain pending.
- Per-module Re-init ships under ratified §8d: `io-reinit <name>` / `/os/io-reinit <uid> <ok|err> {name,error}`; local `/io/reinit` and `/io/reinitialized`. Declared modules only, type/address from the active device manifest, repair shares the write FIFO/bridge IO lock and stays allowed in Performance. Existing IO reasons and the same receipt timeouts; undeclared/malformed requests do not fault a live instance.
- Planes: `/p/*` params with generator automation (§3.2), `/e/*` events (every event forward-syncs; `"0"` fires on arrival), `/pt` points, `/os/*` and `/admin` for device management. The host-side saved-parameter facility is retired (§8.1); no wire form was added. §6 has no general telemetry or meter plane. Bob ratified the bounded development-only IO stream in `59/0a` (2026-10-04); transport ships in 59/8, module panels and editor input follow. Don't stream outside that.

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
