# 1-system-map — work notes (2026-07-27)

Deliverable: `.notes/entity-map-2026-07.md` — the as-is entity map with a
summary overview, two mermaid diagrams (topology; reference graph), per-entity
tables (identity/storage/lifetime/references/wire), the coupling analysis
(C1–C3 implicit couplings, D1–D4 dual expressions), and the storage-ownership
table.

Ground truth read for this map: `dashboard/state.py` (whole),
`dashboard/server.py` (preset save/load, live_control_declarations,
public_device/public_state, preset_scope_seats, active_param_identities),
`dashboard/show_model.py`, `dashboard/device_aliases.py`,
`python/manifest.py`, `python/identity.py`, `python/runcontext.py`,
`python/store.py`, `python/groups.py`, `python/fetcher.py` (header),
`docs/OSC-CONTRACT.md` §3–§4, plus the live `dashboard/installation.json` and
`dashboard/shows/test.json` for real shapes.

Key findings carried forward to stitch 2:

- **No reference cycles** — the graph is a DAG. The complexity smell is
  implicit (unversioned) couplings and dual expressions, not loops.
- C1: seat param values keyed by a schema (`params_patch`) they don't record.
- C2: presets and shows embed manifest identities/addresses with no patch
  name or fingerprint — drift is silent (preset half-applies via the
  `active_param_identities` filter; show messages become legal no-ops).
- C3: `reindex_seat` rewrites preset seat keys but NOT show targets — shows
  keep stale numeric selectors after a renumber.
- D1–D4: venue presets vs coming patch presets; the three-way value mirror
  (seat/device/virtual); desired-patch split (fleet in venue, pin in
  registry — deliberate); the `dashboard:` flag serving two audiences until
  `01-control-panel/1` lands.

Descriptive only, per instructions — no proposals here.
