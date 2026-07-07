# patch-manifest — verification (2026-07-08)

Simfleet-and-loopback proof on the laptop; **not hardware-verified on a real
Pi** (no rig this session). What a Pi run would add: real amixer/jackd/pd,
real /proc facts, DigiAMP channel counts.

## Unit suite

`test_patch_manifest.py` (this dir) — 22 checks, all passing:

```
PYTHONPATH=<pylib>:python:python/io python3 \
  .loom/threads/osc-schema-contract/patch-manifest*/test_patch_manifest.py
```

Covers: manifest.load validation matrix (7 cases), manifest CLI exit codes
0/3/1 with eval-able stdout in every case, helper `/os/params` verbatim +
legal-empty replies, `/os/report` shape and facts (11 keys,
AUDIO_CHANNELS honored), `/patch` accepting manifest-only and main.pd-only
dirs and rejecting neither, `engine_alive` via `run/engine.name` +
`engine.pid`, simfleet params/report replies, `/p/` declared-applies /
undeclared-drops / engine-dead-drops. The tied `assign-persistence` suite
still passes (no regression).

The pylib (pyOSC3 + pythonosc) survives at
`/tmp/claude-1000/-home-bob-repos-bopOS/acefa5c4-*/scratchpad/pylib`;
rebuild from PyPI sdists if gone (see tied dashboard-0-sim-fleet notes).

## Live loopback — real helper.py

`bopos.config` with `HB_TARGET=127.0.0.1`, listener on 5550, helper.py
running, requests sent to 6660:

- `/all/os/params` → `/os/params <exact bytes of patches/default/bopos.patch.json>`
  unicast from helper to (requester, 5550). Whitespace preserved — verbatim
  confirmed byte-for-byte against the file.
- `/all/os/report` → all 11 keys with real facts:
  `uid=28:7f:cf:58:f1:47` (laptop MAC), `engine=pd`, `has_i2c=true` (laptop
  has /dev/i2c), `has_wifi=true`, `audio_channels=2` (default),
  `screen=false`, `patch=default`, real uptime, `git_rev=e1ae066`,
  `update_model=persistent`, `contract_version=1.0`.
- `/hb` cadence unaffected (2 s unassigned, engine-alive 0 with no pd).

## Live loopback — simfleet

`simfleet.py --devices 3 --engine-dead 1 --target 127.0.0.1`:

- `/2/os/params` and `/2/os/report` → correct unicast replies (sim uid,
  sim facts, uptime = sim clock, git_rev = fake sha).
- `/1/p/gain 0.7` applied; `/1/p/nonsense 1` → `p/nonsense undeclared,
  dropped` in the log, state untouched.
- `/3/p/gain 0.9` (engine-dead device) silently dropped — PD applies params
  and a dead engine applies nothing.

## Launcher — scratch tree with fake pd/jackd/fakeengine binaries

Copied start/stop-engine.sh + manifest.py + patches/ into an isolated tree,
fake binaries logging argv + BOPOS_* env:

1. **pd manifest (default patch):** launch line byte-identical to legacy
   (`-nogui -jack -open … -send "; RANDOM …; STARTTIME …; STARTDATE …;
   ACTIVEPATCH default"`), `pd.pid` == `engine.pid`, `engine.name=pd`,
   comm of engine.pid is `pd`. stop-engine.sh kills all, removes all
   pidfiles, zero survivors.
2. **Custom engine (`fakeengine` / `app.txt`):** launched as
   `fakeengine <patch>/app.txt` with `BOPOS_ACTIVEPATCH/RANDOM/STARTDATE/
   STARTTIME` env vars; `engine.name=fakeengine`; **no** pd.pid; jack still
   started first; stop cleans.
3. **Broken manifest (`{ broken`):** `WARNING: INVALID PATCH MANIFEST;
   USING LEGACY LAUNCH` printed, manifest.py's specific JSON error passed
   through on stderr, pd launched anyway — loud error, audio survives
   (contract §1 beats a strict §8).

## Not verified (needs Bob / hardware)

- `route p` PD edit (specced in `../pd-edits-for-bob.md` §4) — until it
  lands, `/p/*` values reach PD but nothing routes them; bare spellings
  keep working.
- §13 revision (bare-alias removal) is a proposal in the same file —
  contract edit is Bob's ratification.
- Real-Pi launch (DigiAMP jack, real amixer), and a real non-pd engine.
