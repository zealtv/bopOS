# boundary-5-launch-context-and-topology — verification results

Date: 2026-07-12
Venv: `~/.venvs/bopos/bin/python`

## New verify script

`verify_launch_context.py` (this directory) covers:

1. `python/runcontext.py` — `generate()` seed range, `run_id` shape (with/without
   patch, unsafe-character sanitizing, seed suffix), and distinctness across
   repeated calls; the CLI's two `BOPOS_SEED='...'`/`BOPOS_RUN_ID='...'` lines
   and their eval-ability through `bash -c 'eval "$(...)"'`.
2. `python/relay.py` — `shape_provided_term` unit cases for master, params,
   and all the "not a provided term" cases (`os/mute`, `os/identify`,
   2-part addresses, 4-part addresses, empty args, empty param name).
3. `python/helper.py` source: imports `relay`, calls `shape_provided_term`,
   and no longer inline-shapes `"/p/" + parts[2]`.
4. `tools/audition.py` end-to-end relay behavior with three fake UDP "engines"
   on 127.0.0.1:36661-36663 and the rig's real command socket on 26660/25550:
   catch-up `/id` per node, `/all/os/master` broadcast, `/2/p/gain` exact-id
   delivery, `/all/os/identify` (no uid → all, with uid → only the matching
   node) relaying `/notify ["identify"]`, and confirmation that
   `/all/os/mute` is relayed to no engine.
5. `AuditionRig.engine_command` for a `pd` engine against the real
   `patches/default/bopos.patch.json`: the `-send` string contains
   `BOPOS_ENGINE_PORT`, `bopos-context seed `, `bopos-context run-id `,
   `bopos-context patch default`, `bopos-context assets `, and none of the
   legacy tokens (` ID `, `RANDOM`, `STARTTIME`, `STARTDATE`, `ACTIVEPATCH`,
   `; ASSETS`).
6. `bash -n` on `bash/start-engine.sh` and `bash/start-laptop.sh`, plus text
   checks for `runcontext.py`/`bopos-context`/`BOPOS_RUN_ID`/the
   `BOPOS_ENGINE_PORT` default, and absence of the legacy `RANDOM $RND`/
   `STARTDATE`/`BOPOS_RANDOM` tokens.
7. `templates/supercollider-bopos/main.scd` text checks: env-driven
   `BOPOS_ENGINE_PORT`, `openUDPPort`, `recvPort: ~bopos.enginePort` (no
   hardcoded `recvPort: 6661`), the retrying `/config` routine, and the
   `BOPOS_SEED`/`BOPOS_RUN_ID`/`BOPOS_ACTIVEPATCH`/`BOPOS_ASSETS` env reads.
8. `py_compile` on `python/runcontext.py`, `python/relay.py`,
   `python/helper.py`, `tools/audition.py`.

### Command

```
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/engine-boundary-design/boundary-6-contract-v12-and-renames/boundary-5-launch-context-and-topology/verify_launch_context.py
```

### Result

**68 passed, 0 failed.**

### Bug found and fixed (in the verify script, not shipped code)

The first draft compared relayed OSC float args with `==`; OSC floats are
32-bit and `0.7` round-trips as `0.699999988079071`, so the `/2/p/gain`
exact-id-delivery case failed even though the relay itself was correct.
Manual reproduction (`tools/audition.py`'s `relay()` unchanged) confirmed
routing was right — only the assertion was wrong. Added an `approx_eq`
helper (1e-5 tolerance on float args) and used it for the two float-bearing
comparisons (`/all/os/master`, `/2/p/gain`). No shipped code was touched.

## Regressions

### 1. `.loom/tied/boundary-2-pd-parallel-relay/verify_pd_parallel_relay.py`

```
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/boundary-2-pd-parallel-relay/verify_pd_parallel_relay.py
```

**FAIL** — `FileNotFoundError: pd/bopos.osc.pd`. Investigated: `pd/bopos.osc.pd`
no longer exists; it was merged into `pd/bopos.pd` in commit `614882e`
("updating loom, removing bopos.notify~ and related sequences", Bob's own
commit, prior to and independent of this stitch's Python/bash/template
changes). `.loom/tied/engine-boundary-ratification/ratification.md` line 48
explicitly calls for renaming `pd/bopos.osc.pd` to `pd/bopos.pd` and exposing
it as `[bopos]`. **Recorded as superseded** by the engine-boundary
ratification's PD consolidation — not a bug introduced by boundary-5, and per
house rules this agent does not touch `.pd` files or that verify script.

### 2. `.loom/tied/seam-2-master-term/verify_master_term.py`

```
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/seam-2-master-term/verify_master_term.py
```

**FAIL** — `StopIteration` (no devices ever appear in dashboard state).
Investigated: the sim fleet subprocess exits immediately with
`simfleet.py: error: unrecognized arguments: --meter-interval 0`. Confirmed
via `git log -p -- tools/simfleet.py` that `--meter-interval` was removed by
the same commit `614882e`, which retired the legacy meter-broadcast path
per the ratification (line 101: "streaming (`meter_loop`, `METERS`, and
`METER_INTERVAL`) ... legacy broadcast" removed). **Recorded as superseded**
— the tied verify's CLI invocation targets a flag that no longer exists;
not caused by boundary-5's changes and not touched.

### 3. `.loom/tied/audition-1a-relay-launcher/verify_audition.py`

```
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/audition-1a-relay-launcher/verify_audition.py
```

**FAIL** — `pd_command_test` asserts
`assert "BOPOS_ENGINE_PORT 16661" in sends[0] and "ID 1" in sends[0]`.
This is exactly the legacy PD startup token (`ID <n>`) that boundary-5
replaced with the `bopos-context` bus sends (`bopos-context seed/run-id/
patch/assets`); the new -send string legitimately no longer contains
`ID 1`. **Recorded as superseded** by this stitch's own change (item 4 in
the stitch brief: legacy `ID`/`RANDOM`/`STARTTIME`/`STARTDATE`/`ACTIVEPATCH`/
`ASSETS` sends are gone).

Confirmed no other bug: patched a scratch copy of the tied script (not the
shipped one) to drop only the `"ID 1"`/`"ID 2"` substring checks — the
remaining assertions in `pd_command_test`, plus `exclusive_bind_test`,
`partial_start_failure_test`, `no_engine_protocol_test`, and
`owned_process_test` all pass (`PASS: heartbeats, selector relay, /id
catch-up, and owned teardown`). The scratch copy was deleted; the tied file
was never modified.

## Hardware run (bop000, 2026-07-12, after the local verify)

Deployed commit `5dc686e` to the real DigiAMP+ node `bop000` (local bench
edits stashed as "bop000 bench edits pre-boundary-5"; the untracked
`systemd/` copy — byte-identical to the repo's — moved to
`systemd.local-copy/`). Bob authenticated the `bopos-helper` restart. Then:

- `bash/stop-engine.sh` + `bash/start-engine.sh` launched jackd + PD on the
  DigiAMP with the new context step: PD's live cmdline showed
  `-send "; bopos-context seed 367299; bopos-context run-id
  default-20260712-215054-367299; bopos-context patch default;
  bopos-context assets /home/pi/bopOS/assets"` — no legacy sends.
- Ratified port topology held: helper (one python PID) owned 6660 + 7770;
  `pd` owned 6661 + 6662 only.
- LAN round-trip from the dev Mac: `/all/os/ping` → `/os/pong 4242
  2c:cf:67:b3:0a:58`; `/all/os/identify` → helper journal logged
  `IDENTIFY: 2c:cf:67:b3:0a:58 id -1` with no errors/tracebacks (the node is
  currently unassigned, so id is -1; selector `all` matched).
- Pre-existing, unrelated: JACK/PD real-time scheduling warnings (rtprio
  limits on this image).

## Not tested

- `sclang` process launch — no SC binary invoked; the template changes are
  covered by text assertions only.
- Audible confirmation of the identify chirp / patch behavior on bop000 —
  nobody was listening at the speaker; the wire and journal evidence above is
  what was captured.
- The `bopos-context` bus's effect inside a running PD patch (receiving
  `-send bopos-context ...` values a patch consumes) — PD-side behavior;
  no shipped patch reads seed/run-id yet, and PD is Bob's domain.
