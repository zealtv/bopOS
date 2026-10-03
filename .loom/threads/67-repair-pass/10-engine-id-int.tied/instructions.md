# 10-engine-id-int

**Status:** verified with real Pd · Bob ruled 2026-10-03 ("should be an integer
as long as pd is happy")
**Goal:** engines always receive `/id` as an int32.

Today `apply_assign` and `apply_unassign` (`python/bopos.py`) send `/id` with
an `f` tag; `config_callback` and `deliver_engine_context` send `i`. Proposal:
`.loom/threads/69-complexity/4-node-daemon-tidy.tied/id-type-proposal.md`.

## Do

- **Pd first — this is Bob's condition.** Confirm `pd/bopos~.pd` handles an
  int-tagged `/id` exactly like a float one: run real Pd if it's available
  (e.g. the audition rig in edit mode) and observe `bopos-context`; otherwise
  record source inspection only and say so. If Pd is *not* happy, stop and
  report — don't change the tag. Never edit `.pd` files (`64-pd-edits-owed`).
- Change the two `f` tags to `i`; keep values, `-1` sentinel, address,
  argument count and timing unchanged. simfleet/audition match.
- Contract: specify `/id <n:int32>` in §4.2 and make OSC-REFERENCE agree. Land
  it in the **same v1.19** as `68` (extend 68's §15 row), not a new version,
  unless 68's 1.19 has already been pushed — then 1.20.
- Update the packet-level regression that currently pins the mixed tags.

## Done when

- Pd check recorded (which kind). Fast + browser green.
