# boundary-5 decisions

Stage 5 of the ratified engine-boundary migration
(`.loom/tied/engine-boundary-ratification/ratification.md`). Implemented
2026-07-12.

## Run context: shape and delivery

- New `python/runcontext.py` is the bopOS-owned generation step: `seed`
  (integer 0..999999 — at most six significant figures, so it survives PD's
  32-bit floats exactly) and `run_id` (opaque string,
  `<patch>-<YYYYMMDD>-<HHMMSS>-<seed>`, PD-symbol- and shell-safe).
- Delivery is atomic at launch, per the ratification:
  - PD: `start-engine.sh` (and `start-laptop.sh`) `-send` the messages
    `bopos-context seed <n>`, `bopos-context run-id <s>`,
    `bopos-context patch <name>`, `bopos-context assets <path>`. PD's `-send`
    targets the receive symbol directly, so this lands on the same
    `bopos-context` bus `[bopos]` uses for `id <n>` — **no PD edit was
    needed**; patches opt in with `[r bopos-context]` + `[route ...]`.
    Context bus vocabulary is now: `id`, `seed`, `run-id`, `patch`, `assets`.
  - Non-PD engines: environment — `BOPOS_SEED`, `BOPOS_RUN_ID`,
    `BOPOS_ACTIVEPATCH`, `BOPOS_ASSETS`, `BOPOS_ENGINE_PORT` (default 6661).
- Legacy `RANDOM`/`STARTTIME`/`STARTDATE`/`ACTIVEPATCH`/`ASSETS` sends and
  `BOPOS_RANDOM`/`BOPOS_STARTDATE`/`BOPOS_STARTTIME` env are removed (clean
  break; boundary-4 verified no shipped patch consumes them).
- Civil time: deliberately NOT delivered. `run_id` embeds a timestamp for
  humans reading logs but is documented as opaque — engines must not parse
  civil time out of it. The ratified civil-time request/event API stays open.
- Degradation: launcher falls back to bash-generated seed/run-id if python
  fails (a node never falls silent); a standalone `sclang main.scd` self-
  generates a seed and a `standalone-*` run id.

## SuperCollider starter

- Retrying `/config`: a Routine sends `/config` to 127.0.0.1:7770 every 2 s
  until `/id` arrives. Indefinite by design — the framework may come up
  later; standalone runs just keep identity -1.
- The engine binds `BOPOS_ENGINE_PORT` (default 6661) via
  `thisProcess.openUDPPort`; every OSCdef uses that port. This removes the
  audition fixed-port bind attempts for SC: N sclang instances no longer all
  try 6661.
- Added a `/notify` OSCdef so the ratified engine surface is fully present.

## Audition relay topology

- Address shaping is now shared with the production helper via new
  `python/relay.py` (`shape_provided_term`). This is the "unify where
  evidence shows practical" call: the evidence was real drift — audition
  still relayed the retired `/identify` spelling and `/os/mute`. Sockets and
  selector matching remain per-side (topology equivalence, not library
  identity); full library unification was not justified.
- `/<sel>/os/identify [uid]` now relays as `/notify identify`, honoring the
  optional uid filter like the production helper does.
- `/os/mute` is no longer relayed to engines: mute is framework-enforced
  below the engine (production: hardware mixer / engine stop). The audition
  rig currently has no local mute action; if composers need one it should be
  a rig-level feature, not an engine message.

## Honest limits

- PD audition instances still transiently attempt the default 6661 bind at
  loadbang before the `-send BOPOS_ENGINE_PORT <port>` override rebinds
  them: `-send` is delivered after load, so this is unavoidable without a
  `.pd` change. It is noise (one bind warning), not a failure — the override
  path works. A noise-free option (e.g. `[bopos <port>]` creation arg) is a
  possible future Bob-owned PD edit; not requested here.
- `pd/bopos.pd`'s `[r BOPOS_ENGINE_PORT]` naming predates this stitch and is
  a PD receive symbol, not an env var; left as-is.

## For boundary-6 (contract v1.2)

- §9's "an `ASSETS` startup message alongside the existing
  `ACTIVEPATCH`/`RANDOM` sends" is superseded by the `bopos-context` bus and
  the `BOPOS_*` environment set above; fold into v1.2.
- Record the run-context vocabulary (`id`, `seed`, `run-id`, `patch`,
  `assets`) and the opaque-run-id rule in the engine-facing section.
