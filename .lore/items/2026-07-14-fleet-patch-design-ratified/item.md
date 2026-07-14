# Fleet-wide patch design — ratified (fp-0)

Ratified design record for the single fleet-wide patch model
(`.notes/handoff-2026-07-14-fleetwide-patch-next.md` brief). Desired state is
one durable `fleet_patch` record (name + host content fingerprint +
`previous`); the per-seat `patch` field is deleted; the sim's patch becomes a
read-through. The one wire addition is additive: each `/os/patches` entry
gains a `"fingerprint"` — the node computes the same canonical
directory-manifest fingerprint the host already computes (`directory_info`),
via a shared `python/identity.py`, uniform across git-managed and mirrored
patches and sensitive to local drift. Observed-state badges derive per
device (`unknown/last seen` → `switching` → `missing` → `mismatch` →
`stale` → `current`), with operator-triggered retry only. **Set fleet
patch** is one confirmation-gated converge-then-switch operation,
all-at-once; Revert re-stages `previous`; no automatic rollback. The
fingerprint amendment folds into contract v1.4 alongside the pe-1 cues
amendment (one bump).

Bob's verbatim Q1–Q4 rulings are quoted in the proposal's final section.
Implementation split: fp-1-identity-module → fp-2-fleet-state →
fp-3-fleet-ui → fp-4-bop000-gate (hardware gated).

## Source

Written for `fleet-patch/fp-0-design-proposal`, 2026-07-14, single-pass
(council judged unwarranted — the ground truth largely determined the
design). Ground-truth file:line trail is §0 of the proposal, verified at
`e532733`. Ratified in-session the same day.

## Related

- `.notes/handoff-2026-07-14-fleetwide-patch-next.md`
- `.lore/items/2026-07-13-patch-asset-sync-proposal`
- `.lore/items/2026-07-14-patch-editor-design-ratified`
- `docs/OSC-CONTRACT.md` §7, §9
- `dashboard/server.py` (directory_info), `dashboard/osc_bridge.py`
  (/os/fetched, /os/rev), `python/bopos.py` (installed_patches),
  `python/fetcher.py`

## Tags

- proposal
- decision-record
- fleet-patch
- distribution
- dashboard
