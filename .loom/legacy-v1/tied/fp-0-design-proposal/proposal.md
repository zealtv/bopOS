# One fleet-wide patch — model and design proposal (fp-0)

Drafted and **ratified by Bob 2026-07-14** (verbatim rulings at the end).
Brief:
`.notes/handoff-2026-07-14-fleetwide-patch-next.md`. Grounded in the code as
of `e532733`; file:line references are the verification trail.

## 0. Ground truth (verified, with the receipts)

1. **The host already computes a content identity per patch.**
   `directory_info` (dashboard/server.py:83-98) fingerprints each patch
   directory: sha256 over the canonical JSON of its file manifest (per-file
   path/size/sha256; dotfiles, symlinks, `.part` excluded). It is served to
   nodes at `/patches/<name>/.manifest.json` and shown in the catalog.
2. **The dashboard already records what each node acknowledged.** On
   `/os/fetched ok`, `device["distribution"][slot] = fingerprint`
   (dashboard/osc_bridge.py:464), persisted. The state model itself documents
   the gap: "the node receipts success but does not report a hash"
   (dashboard/state.py:77-80).
3. **The node verifies content at fetch time** — per-file size + sha256
   against the fetched manifest (python/fetcher.py:75) — but retains no
   identity afterward and reports none.
4. **`/os/patches` reports no identity** — name/active/git/manifest only
   (python/bopos.py:650-675). `/os/report` carries the active patch *name*
   and the framework `git_rev`; `/os/rev` is the framework revision, not
   patch identity (python/bopos.py:634-647, 803-816).
5. **Switch convergence already loops through `/os/rev`:** admin verbs reply
   `/os/rev` post-action, which clears `patch_switch` and triggers a refresh
   of patches/params/report (python/bopos.py:678-687,
   dashboard/osc_bridge.py:470-484). Node-side switch rolls itself back on a
   failed launch (tied `patch-switch-lifecycle`).
6. **Per-device desired patch exists today in two places:** each seat carries
   a durable `"patch"` field defaulting to `demo-pd`
   (dashboard/state.py:108,158-162), and the sim holds one fleet-wide
   `simulation["patch"]` (dashboard/server.py:643-656) — the simulated fleet
   is *already* single-patch by construction.
7. **v1.3 fetch has no request id** — expired tombstones guard late receipts
   (dashboard/osc_bridge.py:506-517). Retry semantics must respect that.
8. **Git-managed device patches** are flagged by `.git` presence, refused by
   host-mirror fetch, updated via `pullpatch` (python/bopos.py:339-361).

## 1. The model: desired state is fleet-scoped; observed state is per device

**Desired:** one durable record in `installation.json`:

```json
"fleet_patch": {"name": "bonks-pd", "fingerprint": "<64hex>", "staged_at": ...}
```

`fingerprint` is the host catalog fingerprint captured when Bob stages the
patch (ground truth 1). Venue snapshots carry it like everything else in the
state file. The per-seat `"patch"` field retires (open question 1); the sim's
`simulation["patch"]` becomes a read-through to `fleet_patch.name` — the sim
already behaves this way, so simulation and deployment converge on one
model with no new sim machinery.

**Observed:** per device, derived — never stored as a verdict — from what the
node reports. Which requires the one wire addition:

## 2. The wire addition: nodes report patch content identity (additive, v1.5)

Each entry in the `/os/patches` listing gains a `"fingerprint"` key: the
node computes, per installed patch, **the same canonical directory-manifest
fingerprint the host computes**, with the identical walk rules. One shared
implementation — extract the walker/fingerprint from
`dashboard/server.py:49-98` into `python/identity.py`, imported by both the
dashboard and `bopos.py` (both live in this repo; nodes already pull it).
Cache per-file hashes by stat signature exactly as the host does
(dashboard/server.py:66-76) so a Zero re-hashes only changed files.

Why this shape and not alternatives considered:

- **Same bytes → same identity, everywhere.** It is portable across
  git-managed and host-mirrored patches (the walk already excludes `.git`
  along with all dotfiles), which git SHA alone is not (handoff's own
  observation), and it detects *local drift* — a hand-edited file on a node
  changes its reported fingerprint. A stored-receipt identity (writing the
  fetch-time fingerprint to a control file) cannot see drift and creates a
  second identity kind for git patches.
- **No heartbeat growth.** `/os/patches` is already requested exactly at the
  convergence moments — after `/os/rev`, after sends (ground truth 5,
  dashboard/osc_bridge.py:467-468) — matching the handoff's preference for
  extending an existing framework-owned response.
- **Strictly additive:** unknown keys in the listing are already tolerated
  shapes; the dashboard's cleaner (dashboard/osc_bridge.py:426-433) learns
  the new key; old nodes simply report no fingerprint and render as
  `unknown` identity, not as an error. Mirrored in `tools/simfleet.py` and
  `tools/audition.py` in the same stitch, per standing rule.

(Version note — ratified Q4 "fold in": **v1.4 carries both** the pe-1 cues
amendment and this fingerprint key. One contract bump; pe-1 and fp-1
coordinate on the same revision, whichever is claimed first writes the
header bump and the other adds its amendment text to it.)

## 3. Observed-state badges (derived dashboard-side)

Precedence order, first match wins:

| badge | condition |
|---|---|
| `unknown / last seen` | device offline, or `patches` never queried — never current, never mismatched |
| `switching` | `patch_switch` in flight (cleared by `/os/rev`) or a `patch:` fetch queued/fetching |
| `missing` | desired name absent from the node's listing |
| `mismatch` | active patch name ≠ desired name |
| `stale` | names match, node fingerprint ≠ desired fingerprint (or node reports none: old framework → `stale (unverified)`) |
| `current` | names match and fingerprints match |

Badge actions (handoff open question): **both** `inspect` (opens device
detail — diagnostics, fetch states, listing) and `retry` (re-send for
missing/stale, re-switch for mismatch). Retry respects the tombstone rule
(ground truth 7): it is a new fetch command, never a re-armed receipt.

## 4. What each part of the system sheds

- **Dashboard state:** seats lose `patch`; devices lose nothing; one new
  `fleet_patch` record. No per-device patch choice anywhere.
- **UI:** one fleet patch selector + convergence summary ("7 current · 1
  switching · 1 stale") in the global control area. Per-device patch
  dropdowns, Switch, and per-device Send Patch leave the ordinary interface;
  device rows carry the badge; device detail keeps diagnostics and
  remediation (retry, pull-latest for git patches) without implying
  heterogeneous composition is supported.
- **Distribution:** stage once (capture fingerprint), fan out `/os/fetch` to
  devices not `current`, observe receipts + refreshed listings, retry only
  `missing`/`stale`. Asset Send/Sync is untouched.
- **Switching:** one fleet operation. Sequence: converge content first
  (fetch to non-current nodes), then switch — the dashboard sends per-device
  `/id/os/patch` to every online node, progress per device via
  `patch_switch`/`/os/rev` exactly as today. All-at-once, not staged waves:
  per-device progress and badges already make partial convergence visible,
  and staging adds scheduler state with no user yet asking for it
  (heterogeneity stays a future bridge, not latent complexity).
- **Params/facilitator:** one manifest fleet-wide; the facilitator view and
  global param controls stop needing to reconcile per-device declarations.
  Node-reported declarations remain the source (they should agree with the
  host manifest when `current`; disagreement is what `stale` looks like).
- **Simulation/audition:** already single-patch; `fleet_patch` just becomes
  the one place the choice lives in both modes.

## 5. Rollback

No automatic rollback. `fleet_patch` keeps a `previous` field (name +
fingerprint); a one-click **Revert** re-stages the previous patch through
the same converge-then-switch flow. Rationale: node-side switch already
self-rolls-back on launch failure (ground truth 5), so a botched fleet
switch leaves honest badges, engines on their prior patch, and an operator
choice — automatic fleet rollback on partial convergence would fight the
retry path and mask WiFi flakiness as failure.

## 6. Implementation split (created on ratification)

- **fp-1-identity-module** — extract `python/identity.py` from the
  dashboard's walker; contract amendment text for the `/os/patches`
  fingerprint key; node-side reporting with stat-signature cache; simfleet +
  audition mirror; validator/unit verify (browser-free).
- **fp-2-fleet-state** — `fleet_patch` in installation state (+ venue
  snapshots, `previous`); seat `patch` retirement/migration; badge
  derivation; WS surface.
- **fp-3-fleet-ui** — global selector + convergence summary, badges on
  device rows, removal of per-device patch controls from the ordinary
  interface, device-detail remediation, Revert. Playwright verify against
  simfleet including an induced `stale` (edit a host file after send).
- **fp-4-bop000-gate** — live check on the dev Pi: stage → converge →
  switch → induce drift → observe `stale` → retry. Bob/hardware gated.

## Ratification record (Bob, 2026-07-14, verbatim)

The four open questions were put to Bob in-session; his answers, quoted:

> 1. delete. simplicity is a guiding principle. 2. one confirmed action. 3.
> operator triggered. 4. fold in

Applied as: (1) the per-seat `patch` field is deleted outright — no dormant
heterogeneity hooks; (2) **Set fleet patch** is one confirmation-gated
action that converges content and then switches; (3) `stale` remediation is
operator-triggered retry only in v1; (4) the fingerprint amendment folds
into contract v1.4 alongside pe-1's cues amendment — one bump.
