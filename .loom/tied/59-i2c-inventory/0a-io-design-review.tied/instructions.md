# 0a-io-design-review

**Status:** ready · **design gate** — ends in a proposal Bob ratifies; mark
`.waiting` when ready. Don't implement past it.
**Goal:** one design for the I2C/peripheral layer — architecture and operator
workflow together — before building the rest of `59`.

Bob, 2026-08-05: *"we need to be able to simulate i2c devices locally to aid
patching, as well as read / debug i2c devices in some kind of usable workflow
while keeping the system architecture clean."* And 2026-10-03: live streaming
of sensor values, including into Patch edit (see parent).

## Why one design

The io bridge talks only to its local engine, so nothing it knows reaches
anyone else: `/io/error` goes nowhere, `/io/report` is a `print()`, the scan is
unreachable, and values can't leave the device. Stitches `1`, `3`, `4`, `5`,
`6` each need a piece of the same path. Decide it once.

## Decide

1. **Transport** — one answer for scan, create/destroy, registry, errors, value
   streaming and injection. Candidates: `bopos.py` relays to the bridge on
   8880; the bridge sends to more than one destination; something else. Say
   what the bridge's reply model becomes. Note that `bopos.py` scanning on its
   own can't skip live peripherals — whether that disturbs them is a rig
   measurement.
   **Error vocabulary is part of this** (moved here 2026-10-03): fold in
   `67-repair-pass/3-io-bridge-hardening.waiting/wire-proposal.md` — which
   reasons `/io/error` carries (`create-failed` is shipped but undocumented;
   proposed `invalid-arguments`, `unknown-command`, `write-failed`), what
   `<name>` a bridge-wide error uses, and where those errors end up once the
   transport is decided. The bridge currently only logs these cases.
2. **Streaming** (new, 2026-10-03) — who can open a stream, to where (dashboard
   view, the editor's audition engine, both), at what rate, and how it's
   bounded (one device at a time? stops when Patch edit closes?). It must not
   load a show's Wi-Fi. Write the §6 amendment that allows it.
3. **Ownership** — who owns a peripheral: the patch, the operator, or (with
   split elements) which engine instance? Today the patch creates peripherals
   on `loadbang`; dashboard creates would collide. Phrase it to survive N
   engine instances per device (`62`). Bob's starting idea, input not
   decision: *"i2c modules are declared in the manifest, and any element
   instance can choose to hook into them or control them."* Manifests are
   fleet-wide but peripherals are per-device — the asset-slot pattern is the
   precedent. Say what happens when two instances write to one peripheral.
4. **Workflow** — walk it end to end: chip arrives → seen on the bus →
   instantiated → values visible → patched against live. Say where each step
   lives in the UI. Show values both in units and verbatim as the patch
   receives them. Should replace `ads.py` and `watch.py`.
5. **Simulation** — "patch with no hardware" as a first-class case.
   `tools/iosim.py` works today (stream continuously at poll rate; per-channel
   rest polarity). Live device and simulator should feed the editor the same
   way — say how they're told apart.
6. **Out of scope** — what this layer won't become.

## Evidence

- `../session-2026-08-05-ciro-toast.md`, `../ads.py`, `../watch.py`.
- `67-repair-pass/3-io-bridge-hardening` (absorbed `60`) — same failure family; would this
  design have surfaced it? Its `wire-proposal.md` is the starting point for the
  error vocabulary in decision 1.
- `python/io/README.md` — current namespace (`/io/<verb>`, `/io/<name> <cmd>`).
- Contract §6 (no streamed telemetry, and why) and §11 (io plane).

## Deliver

- `proposal.md`: the six decisions, with rejected alternatives.
- The contract amendment it implies (proposed, not written).
- Revised sequencing for `1`–`6`.

Then mark `.waiting` and surface to Bob.
