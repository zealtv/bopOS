# Horizon: the bopOS architecture refactor

**Status: a marker, not a plan.** Nothing here is ratified and nothing is
queued. Bob set the ordering on 2026-08-16: **the i2c work goes first**
(`59-i2c-inventory`, gated on `0a-io-design-review`), and this is recorded so
the direction survives the intervening sessions.

## What it is

`62-split-elements` (a device runs one engine instance per element, each
taking its own Seat) is the visible tip of something larger. Bob, 2026-08-16:
*"i think the split elements is pointing to a larger refactor that clarifies
and streamlines the bopOS architecture … as a marker of where we are heading,
i think a refactor is on the horizon"*, and, in the same breath: *"engine
agnosticism should be brought into this as well, we are going to want both pd
and super collider as working engines."*

Those are one refactor, not two, because they attack the same seam. The
framework currently assumes a device has **exactly one engine**, and that the
engine is **very probably Pure Data**. Split breaks the first assumption;
SuperCollider-as-a-peer breaks the second; both land on the same handful of
files.

## Force 1 — the routable unit is the device

Measured inventory in `.loom/threads/62-split-elements/instructions.md`;
summarised here so this note stands alone. Contract §5 states it as a
definition: *"device = the computer (one uid, one heartbeat, one engine
instance)"*. Downstream of that single sentence: one id in `NodeState`, one id
on the heartbeat, one group set, one `selector_matches` call per datagram, one
`OSCClient` to `127.0.0.1:6661` in `bopos.py`, one `engine.pid`, one
`engine_alive()` boolean, and a dashboard that enforces one Seat per uid in
three separate places.

The refactor's version of this is that **the engine instance is the routable
unit** and the device is what owns the uid, the audio hardware, the i2c bus,
the patch and the network presence. Most of the current 1:1 code is not wrong
so much as it is *unaware there is a distinction to make*.

## Force 2 — engine agnosticism

The boundary is already designed and mostly built: `engine-boundary-design`
and `patch-seam` are tied, run context is launch-delivered and engine-neutral
(`python/runcontext.py`, contract §4.2), the manifest carries an arbitrary
`engine` string (`python/manifest.py:102`), `patches/demo-sc/` exists and
declares `sclang`, and `README.md` already says *"a patch — Pure Data or
SuperCollider"*.

What is **not** neutral, measured 2026-08-16:

- `bash/start-engine.sh:140` branches on `[ "$ENGINE" = "pd" ]` and the two
  arms are not equivalent. The PD arm hands run context over `-send` on the
  `bopos-context` bus and **ignores `BOPOS_ENGINE_PORT`**; the non-PD arm
  passes context through the environment and honours it. So the one mechanism
  a second instance needs already exists — for every engine except the one
  that is actually deployed.
- `python/bopos.py` special-cases PD in liveness: `process_is_pd` (`:285`),
  `expected_engine_name()` falling back to `"pd"` (`:310`), and a `pd.pid`
  branch in `engine_alive()` (`:326`). `/os/report` defaults `engine` to
  `"pd"` (`:1302`).
- Defaults assume PD where a default is needed at all: `manifest.py:102`,
  `dashboard/server.py:2600` (the minimal manifest), `tools/simfleet.py:479`.
  Individually reasonable; collectively they mean an SC fleet is the exception
  path everywhere.
- `tools/audition.py` resolves a **Pd binary** specifically (`:79`, `:99`,
  `:277`, `:316`) — thread `61` hardened that resolution but did not
  generalise it. An SC audition rig is unbuilt.
- `install-device.sh:62` installs `puredata` and not SuperCollider.
- Verification: `.notes/handoff-2026-07-12-engine-boundary-complete.md`
  records the SC starter as **text-verified only** — `sclang` has never
  launched under the framework, on a Pi or a laptop. That is the single
  biggest unknown in this force, and it is a hardware/environment gate, not a
  design one.

The *why* is in `.notes/architecture-review-2026-07-05.md` §11 and has not
changed: scsynth is more agent-friendly than PD (text code, OSC-native
server), agent-coded composition is a target workflow, hand-patched PD + bop
remains its own first-class workflow, and Kite Choir will probably prefer SC.
Engine is a per-patch choice and both should coexist in one fleet.

## Why they are one refactor

- **The same file is the hinge.** `start-engine.sh` is where "which engine"
  and "how many instances" both get decided, and its PD arm is the one that
  cannot currently be told a port.
- **The same abstraction is missing.** There is no first-class notion of *an
  engine instance* — a thing with an identity, a port, a channel assignment, a
  liveness state and an engine kind. `bopos.py` has that state spread across
  module globals, a pid file and a name file. Both forces want it named.
- **The same precedent already solves half of it.** `tools/audition.py`
  already runs N engines on one host with per-instance ports and an
  `--engine-command` template that is engine-neutral by construction. The
  production launcher is the thing that lags.
- **The same risk.** Both touch the launch path on every node in the field,
  and `58`'s Ciro Toast and Finn Jet incidents are the standing reminder that
  a break in that path reaches the fleet as a **crash-loop**, at the speed of
  patch distribution, not at the speed of the sweep that caused it.

## Ordering, as set by Bob

1. **i2c first** — `59-i2c-inventory`, gated on `0a-io-design-review`. That
   gate now also carries the split-elements constraint on peripheral
   ownership, so it is doing part of this work already.
2. `62-split-elements` — `.waiting`, design gate, four children.
3. The refactor proper — unscoped, unratified, no thread yet. It should not
   get one until `0a` and `62/1` have ruled, because those two rulings are
   most of its input.

Standing constraint, unchanged: the system works today and must keep working;
prefer small ordered changes over rewrites.
