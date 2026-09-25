# Handoff — 2026-07-23 loom intake & holistic re-order

This session was **planning only** — no implementation. Bob brought a list of
new work (a bug, several features, a cleanup, a seed) and asked to get it onto
the loom in a structured way, then to produce a **holistic ordering of the whole
loom** for the next sweep. That's done. Nothing was built; the next session
starts the actual work at the top of tier 1.

## What changed on the loom

**Seven new threads** (goal stitch + children, instructions written):

| # | thread | kind | first stitch |
|---|--------|------|--------------|
| 29 | `fleet-patch-sync-hang` | **BUG** | `1-reproduce-diagnose` (loose end) |
| 30 | `gdown-retirement` | cleanup | goal is the loose end |
| 31 | `install-oneliner` | feature | `1-install-script` (loose end) |
| 32 | `multi-asset-packs` | feature | `1-context-list-design` (Bob gate) |
| 33 | `device-audio-config` | feature | `1-audio-config-design` (Bob gate) |
| 34 | `fleet-patch-global-state` | feature | `1-menubar-fleet-patch-design` (Bob gate) |
| 35 | `node-logging` | **parked seed** | `1-logging-seed-design.waiting` |

The new-thread numbers were assigned so **ascending number = sweep priority** in
tier 1 — `./.loom/loom.sh next` serves 29 → 30 → 31 → 32 → 33 → 34 literally.
(The number permutation during creation is why 30 = gdown not assets, etc. —
don't be confused by any lingering muscle memory; the slug is the identity.)

**Deferred, parked `.waiting`:** `20-console-dock` and `25-message-pill-encoding`
(the prior in-flight Show polish). They were **not renumbered** — renaming them
would have corrupted references in `.lore/` and dated `.notes/` handoffs. Parking
their loose-end children keeps them out of `next` while their identity numbers
stay valid.

**Dropped:** `21-theme-cyan-tint` (Bob, this session). It was named in the
2026-07-21 fix-pass text but never actually became a stitch — it's off the
program. `27-tied-guard-rot`'s stale "after 20 and 21" dependency was corrected
to "after 20".

## The holistic order (authoritative copy in CLAUDE.md → "Next sweep")

**Tier 1 — active linear sweep (`loom.sh next`):**
29 bug → 30 gdown → 31 install → 32 assets → 33 audio → 34 fleet-menubar.

**Tier 2 — failing tests, then deferred polish:**
27 guard-rot (elevated above polish; still gated on Bob's fresh session) → 20
console-dock → 25 pills.

**Tier 3 — paused on other design:** `18-show-chrome-density` leftovers.
**Tier 4 — Bob-gated / co-design / seeds:** 35 logging, asset-fleet-distribution
(after 32), scene-sequencing, framework-version-management, zero-2,
dashboard-terminology-review.
**Tier 5 — hardware/rig-gated:** sync-4, spatial-3, zero-1.

## The guard-rot vs node-bug assessment (Bob asked which feeds which)

Bob's rule: *if guard-rot bugs feed the node issue, fix them first; else node bug
first, then guard-rot.* I assessed it from the recorded sweep in
`.loom/tied/23-waveform-marker-guard-regression/` (results + `sweep-failure-logs.tar.gz`).

The red guards **on the patch/fleet path** — `dist-2-node-side`,
`fp-2-fleet-state`, `patch-switch-lifecycle`, `fp-1-identity-module` — all fail
on the **known rot signatures**: a pinned `contract_version '1.3'` (now 1.7), the
retired legacy-samplepacks link, pinned exact refresh-message lists / UI copy,
and fake-`state` API drift (`SimpleNamespace has no attribute 'data'` at
`osc_bridge.py:105`). The **behavioral** patch-sync assertions still **pass** in
sim — fetch progress, "converges bytes then switches responsive nodes",
per-device fetch serialization.

**Conclusion: guard-rot does NOT feed the node bug.** The node bug is fresh-Pi
specific (cold asset cache / first real fetch / no prior patch / no-timeout
fetch) — simfleet doesn't model that, which is why the guards can't see it. So
**node bug (29) first, guard-rot (27) after.** As a hedge, `29/1`'s instructions
tell the diagnosing agent to skim those three patch-path guard failures (read
only — fixing them is `27`'s job) in case a real regression hides among the drift.

## Where the next session should start

`./.loom/loom.sh next` → **`29-fleet-patch-sync-hang/1-reproduce-diagnose`**.
Claim it, reproduce (simfleet fresh-node first; dev Pi `bop000` if needed — see
memory `bop000-dev-pi-access`, sudo needs Bob), pin the exact hang, then create a
`2-fix` sibling from the cause. If the fix needs a PD receiver change, that's
Bob's domain → record in `.notes/pd-edits-for-bob.md`.

## Decisions still owed by Bob (surfaced, not blocking tier 1)

1. **Pill colours (`25`)** — Bob ruled a flat 7-category set: cue, point, raw,
   param-value, param-fade, param-lfo, param-stop. Open: his list omits `loop`
   (the generator select has value/fade/**loop**/lfo/stop). Fold, drop, or add a
   `param-loop` 8th? — settle in `25/01`.
2. **Guard-rot sweep (`27`)** — the whole sweep question (script yes/no,
   blocking/advisory) is a **fresh briefed session**:
   `.notes/handoff-guard-rot-briefing.md`. Elevated in priority but still gated.
3. The four design-gate stitches (32/33/34 + the parked 20/25 designs) each end
   in a Bob-ratified proposal → `.waiting`; don't implement past them.

## Not committed as part of this work

`dashboard/shows/` was already untracked at session start and is unrelated —
left alone, not staged.
