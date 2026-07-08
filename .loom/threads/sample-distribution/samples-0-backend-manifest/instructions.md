# samples-0-backend-manifest

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
