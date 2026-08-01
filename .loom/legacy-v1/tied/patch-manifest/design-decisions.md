# patch-manifest — design decisions (2026-07-07)

Contract §8 (manifest, params), §6 (`/os/report`), §2 (declared facts), §1
(never fall silent). Implemented by hand — codex hit "model at capacity"
twice today; the delegation economics only work when the provider is up.

## 1. `patches/default/bopos.patch.json`

Contract §8's example, made real for the default patch: engine `pd`,
entrypoint `main.pd`, the legacy three params (`gain`, `backing`, `echo` —
per the stitch instruction and the contract example; `gain2` stays a
wire-level legacy command, not a declared param of this patch), `caps: []`,
`slots: ["samplepacks"]` (the patch's bopos.config carries SAMPLEPACKSURL
today — the slot name lines up with §9's landing convention).

## 2. `python/manifest.py` — one validator, three consumers

`load(patch_path)` → `(manifest, error)`: JSON object; `engine` non-empty
string (default `pd`); `entrypoint` exists in the patch dir; params are
`{name, type, min, max, default, group}` with name `[A-Za-z0-9_-]+`, type in
`i f s`, and min ≤ default ≤ max when numeric. First failure wins, error is a
human sentence. `raw(patch_path)` returns the verbatim file text (what
`/os/params` serves — §8 says verbatim, so the node never re-serializes).
CLI mode prints eval-able `ENGINE=`/`ENTRYPOINT=` lines for the launcher:
exit 0 valid manifest, exit 3 no-manifest-but-main.pd (legacy), exit 1
invalid.

**Invalid manifest does NOT refuse to start.** §8 wants the launcher to
validate before start; §1 says a node never falls silent. A JSON typo on a
standalone installation must not kill the sound, so: loud error, legacy
`main.pd` launch, and `/os/params` still serves the broken file verbatim so
the dashboard can badge it. Drift is loudly visible, audio survives.

## 3. Launcher generalisation (`bash/start-engine.sh`, `stop-engine.sh`)

- Engine/entrypoint come from `manifest.py` (legacy defaults on exit 3).
- `pd` keeps today's exact launch line (jack + `-send` startup messages).
  Any other engine launches as `<engine> <entrypoint>` with the same
  facts as env vars (`BOPOS_ACTIVEPATCH`, `BOPOS_RANDOM`, `BOPOS_STARTDATE`,
  `BOPOS_STARTTIME`) since `-send` is PD-specific. Jack still starts first
  either way (scsynth wants it on a Pi; a per-engine jack policy is an
  engine-strategy call — Bob's gate, parked).
- Pidfiles: `run/engine.pid` + `run/engine.name` (comm basename) always;
  `pd.pid` kept when the engine is pd so nothing that learned the
  node-contract-fixes names breaks. stop-engine.sh kills engine.pid and
  falls back to `pkill -x <engine.name>`, then handles pd/jackd as before.

## 4. helper.py

- `/<sel>/os/params` → unicast `/os/params <verbatim-json>` to (src, 5550);
  no manifest → reply with **no** json arg (the legal empty answer the
  dashboard turns into the "undeclared" badge + legacy sliders).
- `/<sel>/os/report` → unicast `/os/report <json>` with exactly the §6
  facts: engine, has_i2c (sys_i2c.have_bus), has_wifi (/proc/net/wireless
  non-empty), audio_channels (declared: `AUDIO_CHANNELS` node-config key,
  default 2 — probed channel counts are hardware assumptions, §2 forbids
  them), screen (`"screen" in caps`), patch, uptime (sys_info), git_rev
  (NodeState.version), update_model, contract_version "1.0", plus uid for
  reply correlation.
- `/patch` switch validation: manifest valid **or** main.pd present —
  rejects only when neither exists (was: main.pd only).
- engine-alive generalised: comm target comes from `run/engine.name`, else
  the active manifest's engine basename, else `pd`. pd.pid fallback kept.

## 5. `/p/*` plane — nothing to do in Python, spec'd for Bob

Param values flow `/<sel>/p/<name> <value>` straight to PD; helper never
touches the patch plane. The `route p` edit and the §13 question are in
pd-edits-for-bob.md: per Bob's 2026-07-07 relaxation, the bare
`/gain`→`/p/gain` one-release aliases should be **skipped** and §13 revised
(proposal text in the stitch dir, contract edit awaits Bob's ratification).

## 6. simfleet

- v1 members `params` and `report`: unicast the same JSON shapes helper
  sends (per-device manifest = the default-patch manifest; report facts from
  sim state: engine pd, has_i2c false, has_wifi = not wired, uptime = sim
  clock, git_rev = fake sha, update_model per --ephemeral).
- `/<sel>/p/<name> <value>`: declared params (plus the legacy four column
  names) apply to a per-device params dict and the TUI columns; an
  undeclared name is logged and dropped — mirroring PD's route behaviour
  (the badge is the dashboard's job, the node doesn't guess).

## Out of scope (parked where)

- Dashboard rendering from declarations + undeclared badge → dashboard-1
  (the verify line "dashboard renders sliders from declared params" can only
  be half-verified until then; simfleet serves the JSON now).
- `ASSETS` env/startup message → fetch-landing (§9).
- Per-engine jack policy, SC proof-of-concept → Bob's engine-strategy gate.
- PD edits (`route p`) → pd-edits-for-bob.md §4.
