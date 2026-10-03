# Verification — engine ID int32

2026-10-03. Bob's condition was checked **with real Pd before changing the
node's two send tags**, not by source inspection alone.

## Pd compatibility gate

Used the installed `/Applications/Pd-0.55-2.app/Contents/Resources/bin/pd`
(`Pd-0.55.2`, compiled 2024-11-17), headless with `-noaudio`. Opened the actual
unchanged `pd/bopos~.pd`, supplied a scratch loopback engine port through
`BOPOS_ENGINE_PORT`, and sent explicit float- and int-tagged `/id` datagrams
for **0, 7 and -1**. The patch's existing context print produced identical
`bopos-context: id <value>` output for both tags for every value. Pd stayed
running, emitted no errors, and the harness exited 0 (`pd-id.log`).

Reproduce with the supplied `verify_pd_id.py` and the installed Pd binary as
its argument. The harness writes no Pd patch; it uses the shipped receiver,
`oscparse` → `list trim` → `route id` → `id $1` → `s bopos-context` path.
This is real Pd OSC/context verification on the host, not audio or device
hardware verification.

## Change and parity

Only `apply_assign` and `apply_unassign` change their `/id` tag from `f` to
`i`. Assignment values, the -1 tombstone, address, argument count and delivery
order remain unchanged; `/config` and ready replay already use `i`.
The packet-level regression now requires int32 on all four paths.

Audition already serializes integer `device_id` through its explicit `i`
builder. A packet check of `send_id` decoded `['/id', ',i', value]` for 0, 7
and -1. Simfleet models integer identities without an engine OSC socket, so
there is no mismatching engine `/id` send to alter. No simulator change needed.

§4.2 and OSC-REFERENCE now specify `/id <n:int32>`, including unassignment,
config and ready replay. Extended **the existing 1.19 §15 row** with the
integer ruling and real-Pd verification; header and shared constant stay at
1.19 and no new version is introduced. The Git-route retirement text remains.

## Other requested follow-up

Added the template's retired `update-patch` message box and connection as an
unchecked item in `64-pd-edits-owed.waiting/instructions.md`, with exact target,
reason and verification steps. That thread remains waiting for Bob; agents
have not changed any `.pd` file.

## Checks

- `tests/test_engine_ready_replay.py`: **13 tests passed**.
- Real Pd harness: all six explicitly tagged packets passed; exit 0.
- `./tools/run-tests.sh all`: **388 fast tests and all 23 browser journeys
  passed**, exit 0 (`tests.log`).
- Pyflakes on changed Python code, regression and Pd harness: clean.
- `git diff --check`: passed; no `.pd` diff.
