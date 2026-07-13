# samples-0-backend-manifest

**.waiting (2026-07-13):** Bob's composer-experience brain dump
(`.lore/items/2026-07-13-composer-experience-brain-dump`) reshapes sample
distribution into a unified patch+asset model (`patch-asset-sync` thread,
host↔Pi directory mirror, "Get/Send Assets"). Don't build against the brief
below until `patch-asset-sync/dist-0-proposal` is ratified — the proposal
will absorb or supersede this stitch explicitly.

Dashboard backend serves sample packs over the LAN with a manifest. Contract
is settled (§9, implemented by `fetch-landing` — absorb, don't duplicate):
`/os/fetch <source-uri> <slot>` → `/os/fetched <slot> <ok|err>`, `http:` scheme
= dashboard-served manifest+hash with resume.

- [ ] Read `.loom/tied/fetch-landing/` first — the landing (`~/bopOS/assets/
      <slot>/`, `ASSETS` env) and any stub of the http scheme may already
      exist; this stitch builds the serving side against it.
- [ ] Backend: a samples directory per installation/patch (laptop acquires
      packs via legacy `getsamples` cloud path — unchanged); HTTP endpoints:
      manifest (file list + per-file hash + pack version/hash) and file
      download with Range support (resume).
- [ ] Manifest format documented in this stitch + docs; version/hash is what
      the fleet UI (samples-2) will display.
- [ ] verify_*.py: serve a fixture pack, fetch manifest, verify hashes,
      simulate an interrupted download resuming via Range.

Design for flaky WiFi and partial fleets: resumable, verifiable, idempotent
re-fetch. Keep it boring — plain HTTP, no rsync daemon.
