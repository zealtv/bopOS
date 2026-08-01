# fetch-landing

**Do after the crux stitches; coordinates with the `sample-distribution` thread —
absorb, don't duplicate.** Contract: `docs/OSC-CONTRACT.md` §9.

- `/<id>/os/fetch <source-uri> <slot>` → unicast `/os/fetched <slot> <ok|err>`.
  Scheme dispatch: `gdrive:` wraps today's `bash/getsamples.sh` path; `http:` is the
  fleet-scale path (dashboard serves LAN HTTP + a manifest of files+hashes; nodes
  pull by diff, HTTP Range resume; works air-gapped); `file:`.
- Landing convention: framework-owned engine-neutral root `~/bopOS/assets/<slot>/`,
  handed to the engine at launch as an env var and an `ASSETS` startup message
  (alongside the existing `ACTIVEPATCH`/`RANDOM` sends in `bash/start.sh:104`).
- Symlink legacy `patches/<active>/bop/samplepacks` → assets root for one release so
  deployed patches keep working.

Verify: simfleet node fetches an asset-set from a dashboard-served HTTP manifest with
a simulated connection drop mid-transfer (resume, hash-verify), lands it in the slot,
and a fake engine finds it via `ASSETS`.
