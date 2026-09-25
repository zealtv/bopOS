# 0a-io-design-review

**Status:** ready · first in queue · **design gate** — ends in a proposal Bob
ratifies; mark `.waiting` when ready. Don't implement past it.
**Goal:** one design for the I2C/peripheral layer — architecture and operator
workflow together — before building the rest of `59`.

Bob, 2026-08-05: *"we need to be able to simulate i2c devices locally to aid
patching, as well as read / debug i2c devices in some kind of usable workflow
while keeping the system architecture clean. requires some thorough thought and
clear thinking."*

## Why one design

Root cause: the io bridge is localhost-only and talks only to the engine
(one hardcoded client to `127.0.0.1:6662`). So nothing it knows reaches anyone
but Pure Data — `/io/error` goes unrouted, `/io/report` is a `print()`, the scan
is unreachable. Stitches `1`, `3`, `4`, `5` would each solve a piece of the same
transport. Decide it once.

## Decide

1. **Transport** — one answer for scan, create/destroy, registry report,
   errors, test capture and injection. Candidates from `1-scan-transport`:
   `bopos.py` scans itself; `bopos.py` ↔ bridge relay on 8880; a field in
   `/os/report`. Known constraints:
   - `bopos.py` can't see the bridge's registry, so its own scan can't `skip`
     live peripherals. Whether that disturbs them is a **rig measurement**.
   - A relay needs a reply route; say what the bridge's reply model becomes.
   - No streaming (§6).
2. **Ownership** — who owns a peripheral: patch, operator, or (with split
   elements) **which engine instance**? Today the patch creates them on
   `loadbang` and re-creates on restart; dashboard creates would collide.
   - Phrase the answer so it survives N engine instances per device (`62`).
     "The engine owns its peripherals" assumes one engine.
   - Bob's starting idea (input, not decision): *"i2c modules are declared in
     the manifest, and any element instance can choose to hook into them or
     control them."* Weigh: manifests are fleet-wide but peripherals are
     per-device — the asset-slot pattern (manifest declares slots, device
     supplies content) is the precedent. And say what happens when two instances
     write to one peripheral.
3. **Debugging workflow** — walk it end to end: chip arrives → on the bus →
   instantiated → numbers visible → patched against. Say where each step is
   surfaced (Device tab, Monitor dock, …). Must cover **readout** (units *and*
   verbatim as PD receives it) and **identification**. Should read as a
   replacement for `ads.py` and `watch.py`.
4. **Local simulation** — first-class "patch with no hardware". `tools/iosim.py`
   works today. Must stream continuously at poll rate, and rest polarity is per
   channel. Say where it runs, how a simulated peripheral is distinguishable
   from a real one, and whether simulator and bridge share a peripheral
   definition. simfleet has no peripheral model (`has_i2c: False`).
5. **Out of scope** — state plainly what this layer won't become, especially
   whether "no streaming" holds under a "watch this sensor" workflow.

## Evidence

- `../session-2026-08-05-ciro-toast.md`, `../ads.py`, `../watch.py` — primary.
- `../instructions.md` — measured starting state.
- `feature-backlog/60-io-dispatch-silence` — same failure family; test whether
  the design would have surfaced it.
- `python/io/README.md` — current namespace (`/io/<verb>`, `/io/<name> <cmd>`).

## Deliver

- `proposal.md`: transport (with rejected alternatives), ownership ruling,
  workflow walkthrough, simulation model, out-of-scope list.
- The contract amendment this implies (proposed, not written).
- Revised sequencing for `1`–`5`.

Then mark `.waiting` and surface to Bob.
