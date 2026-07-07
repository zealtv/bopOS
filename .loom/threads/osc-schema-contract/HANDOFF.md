# Handoff — OSC contract implementation run

*Written 2026-07-07 at the close of the council session. You are (probably) a fresh
session inside `~/repos/bopOS`, about to execute with Codex delegation.*

## Where things stand

`docs/OSC-CONTRACT.md` v1.0 is **ratified** — it is the spec; don't re-litigate it.
The reasoning (five experts, judgment, Bob's ratification) is in the tied stitch
`.loom/tied/schema-design-draft/` and lore item `2026-07-07-osc-schema-council`.
Read the contract first; dip into `ratification.md` only if a decision seems odd.

## Run order (minimal intervention)

Work these in sequence; each is independently tie-able. Claim → implement → verify
in simfleet → tie. Delegate grunt work via `~/repos/ai-kit` skills
(`codex-implement` for bounded builds, `codex-review` for a second pass); keep
orchestration, contract fidelity, and review yourself.

1. **`dashboard/dashboard-0-sim-fleet`** — build the testbed first. Simulate
   today's deployed wire protocol; every later stitch lands its message changes in
   simfleet as part of its deliverable.
2. **`osc-schema-contract/node-contract-fixes`** — three independent, well-specified
   code deltas. Good Codex warm-up; no ordering hazards.
3. **`osc-schema-contract/hb-identity`** — heartbeat with identity from helper.py,
   ping/pong, identify, mute. Crux 1, half one.
4. **`osc-schema-contract/assign-persistence`** — `/os/assign` + node-side
   persistence + boot resolution. Crux 1, half two. Needs 3's heartbeat.
5. **`osc-schema-contract/patch-manifest`** — `bopos.patch.json`, `/os/params`,
   `/os/report`, launcher generalisation. Crux 2.
6. **`dashboard/dashboard-1-core`** — can start any time after 1; after 5 it can
   render declared params instead of hardcoded sliders.
7. **`osc-schema-contract/fetch-landing`** — coordinate with the
   `sample-distribution` thread (its instructions now point at contract §9).
8. Then `dashboard-2/3/4`, `clock-sync`, `spatial-audio`/`scene-sequencing` per
   CLAUDE.md.

## What needs Bob (park, don't block)

- **All `.pd` edits** — removing the PD-side `/hb`/`/aloha` emitters, `route p`,
  the `/helper`→`/os` and `/gain`→`/p/gain` aliases. As stitches hit these, write
  the exact spec into `pd-edits-for-bob.md` in this thread dir and carry on;
  Python-side work never waits on them (aliases mean both spellings work).
- **Hardware verification** — simfleet proof is the tie bar; note "not
  hardware-verified" in the stitch and move on.
- **Design gates** — anything user-facing in the facilitator view (dashboard-2).

## Standing rules that bite here

- PD floats are 32-bit: uids/versions/times cross the wire as strings.
- Full-state idempotent commands only — no increments, ever (mute spam is a feature).
- Every capability query has a legal empty answer; nodes never fall silent for
  lacking hardware.
- Deployed fleets (Kite Choir, The Plants) migrate on aliases — no port changes,
  no flag days (contract §13).
