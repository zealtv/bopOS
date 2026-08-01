# boundary-6-contract-v12-and-renames — results

Date: 2026-07-12. Authority: `.loom/tied/engine-boundary-ratification/ratification.md`.

## Contract v1.2 (`docs/OSC-CONTRACT.md`)

- Header records the 2026-07-12 engine-boundary revision and the explicit
  supersession of v1.1's PD-direct-6660 statement.
- §3: selector routing is bopos.py's; in-patch `route-by-id` retired.
- §4: sole-binder port table (bopos.py alone on LAN 6660/5550; engines on
  localhost only; audition `BOPOS_ENGINE_PORT` note).
- New §4.2: the full engine surface both directions (`/id`, `/os/master`,
  `/p/*`, `/pt`, `/cue`, `/notify` in; request-only `/config`, `/store`,
  `/load`, `/report` out), the `[bopos]`/`bopos-*` bus glossary, launch-time
  run context (bopos-context bus / BOPOS_* env, opaque run-id), and the
  ratified civil-time amendment (permitted in principle, API deferred).
- §4.1: bopos.py relays master//p/*//pt to every engine; "proposed" `/pt`
  flat-args wording resolved to ratified.
- §6: added the demand-driven one-shot `/os/probe`; recorded the deletion of
  meter streaming and the explicitly-unratified leased probe; helper-death
  recovery bound (≤2.2 s on bop000) noted as a standing gate.
- §11: the residual `role: "meter"` republish bullet replaced with the
  /report + probe demand-inspection model. No `role` wording reintroduced
  anywhere (§8's removal record retained as history).
- §9: landing handoff wording moved from legacy ASSETS/RANDOM sends to the
  run context.
- §12: civil-time constraint amended per ratification (the "absolute time
  never enters an engine" absolute was rejected as overly broad).
- §13: clean break recorded — no `/helper/*` alias, obsolete consumers not
  preserved.
- §14: rejected list gains the /helper alias, meter streaming/role keys, the
  leased probe wire shape, and engine-issued admin/LAN binding.
- Not implemented (per instructions): leased probe, report-presentation
  schema, capability-provider/plugin interface.

## Rename helper.py → bopos.py

Separate behavior-free commit. `git mv`, plus reference updates in:
`bash/start.sh` (launch + pidfile → `bopos.pid`), `bash/stop.sh`,
`bash/checkout.sh`, `systemd/bopos-helper.service` (ExecStart; unit name
kept), `python/{sync_node,manifest,pointfield,relay,requirements.txt}`
docstrings/comments, `tools/{simfleet,sync_measure}.py`,
`dashboard/README.md`, `docs/HARDWARE.md`, `README.md` (which also shed
superseded `bopos.osc.pd`//helper/*-forwarding descriptions), and the
evergreen `.notes` references. Dated records (`.lore/`, `.notes/handoff-*`,
architecture review) keep the old name as history.

Tied verify scripts are tools, not decision records: their `import helper` /
`python/helper.py` references were retargeted (`import bopos as helper`) so
the regression suites stay runnable.

## Verification (docs/contract level per docs/VERIFICATION.md)

- `verify_boundary6.py` (this directory): contract v1.2 consistency greps +
  rename completeness + compile checks — see script output.
- Tied regression sweep with `PYTHONPATH=python:python/io`, venv python:
  - PASS: patch-manifest (all), os-admin-verbs part 1 (all),
    boundary-3 framework-slimdown, sync-2 helper-cue, fetch-landing,
    assign-persistence, boundary-1 client-lock,
    boundary-5 launch-context (68/68).
  - boundary-3's manifest check needed one stale-string fix: it asserted the
    pre-dashboard-7 error text `role 'meter' was removed`; manifest.py's
    ratified message is `role was removed (2026-07-12)…`. Pre-existing
    (broken by `476154a`), fixed in the tied script only.
  - Pre-existing failures, identical at pre-boundary-5 commit `2dc98f5`
    (verified in a throwaway worktree, so NOT caused by this thread):
    hb-identity (3 config/identify checks, stale post-slimdown
    expectations), node-contract-fixes (pyOSC3.SENT monkeypatch), seam-3
    points-node-side (coroutine StopIteration). Left for a housekeeping
    stitch if the suites are wanted green.
  - boundary-2 pd-parallel-relay: expects `pd/bopos.osc.pd`; superseded by
    Bob's PD wave (the file is now `pd/bopos.pd`) — the parallel-relay
    migration state it verified no longer exists by design.

## Hardware

bop000 (DigiAMP+), 2026-07-12: pulled the rename, copied the updated
`bopos-helper.service` (ExecStart → `python/bopos.py`) into
`/etc/systemd/system/`, daemon-reloaded, restarted (Bob authenticated sudo).
`systemctl is-active` = active; `pgrep` shows
`/home/pi/venv/bin/python /home/pi/bopOS/python/bopos.py`; LAN
`/all/os/ping` → `/os/pong 4242 2c:cf:67:b3:0a:58` from the dev Mac. Without
the unit update the next restart/reboot would have failed (the installed
unit is a copy, not a symlink — worth remembering for future renames).
