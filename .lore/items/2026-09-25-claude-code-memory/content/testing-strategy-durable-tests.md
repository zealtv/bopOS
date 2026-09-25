---
name: testing-strategy-durable-tests
description: "Bob's ruling on test strategy — durable tests by code surface, not per-tied-stitch guards"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7fd4fb49-b2ce-415b-b7af-404f0fb1800d
  modified: 2026-07-23T07:15:26.633Z
---

**Bob's ruling (2026-07-23):** "We want durable, maintainable tests for
appropriate surfaces. Running tests of tied stitches was the wrong pattern."

**Why:** bopOS accumulated 168 tied guards in `.loom/tied/*/verify_*.py`, filed by
*stitch*. Nothing re-runs them, so they rot as code moves on — 39/71 browser-free
ones are red on clean `main`, and 6 diagnoses (threads 23/28 + the `hb-identity`
repair in 29/2-fix) found **zero real defects, every red a stale guard**. As a
persisted regression net they catch nothing; their value was captured at *authoring
time*. The tied-per-stitch layout is the root cause: guards are organized by the
wrong axis (stitch-adjacency, not code-surface), so they can't move with the code
and "re-run neighbouring stitches' guards" is the wrong instrument.

**How to apply:**
- A **living test** for a durable contract goes in `tests/`, next to the code,
  organized by **code surface** (`test_osc_contract.py`, `test_fetcher.py`,
  `test_mute.py`), and is refactored in the *same commit* that changes the code —
  so it can't rot. New checks for genuinely shared surfaces (OSC contract/wire,
  manifest schema, identity/fingerprint, mute safety, fetch convergence) go there,
  **not** into a new tied guard.
- Tied guards are **authoring artifacts / proof-of-work**, not a forever contract.
  Don't run the tied archive as a regression suite; don't invest in maintaining it.
- Thread [[implementation-queue-status]] `27-tied-guard-rot` is the reframed
  cleanup: a **two-tier split** — promote durable-contract assertions into the
  living suite; retire the rest (recorded, never silent-deleted). Still gated on
  Bob's fresh session; framing lives at the top of that thread's `instructions.md`
  and `.notes/handoff-guard-rot-briefing.md`.
- **Interim** rule still stands (CLAUDE.md): a tied guard you break during other
  work whose assertion Bob has superseded is repaired **in place** with a comment
  naming the superseding stitch (worked example: `hb-identity` ← `29/2-fix`) — but
  that's a stopgap, not the destination.
- Honest limit: sim/unit tests can't catch everything — the `29` node bug was
  fresh-hardware-specific and invisible to any guard.
