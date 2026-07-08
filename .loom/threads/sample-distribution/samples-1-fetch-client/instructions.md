# samples-1-fetch-client

Device side: helper.py implements the `http:` scheme of `/os/fetch` against
samples-0's manifest server.

- [ ] On `/os/fetch http://... <slot>`: fetch manifest, diff against local
      `~/bopOS/assets/<slot>/` state by hash, download only changed files,
      resume partials (Range), verify hashes, then reply `/os/fetched <slot>
      ok|err` (unicast to requester, per contract transport discipline).
- [ ] Progress observable while running — heartbeat-adjacent or a `/os/report`
      field; pick the contract-cleanest option and record it (samples-2 needs
      it for per-device progress display). If it needs a new outbound message,
      shape it additively and note it in the contract.
- [ ] Local pack version/hash persisted so a re-fetch is a cheap no-op.
- [ ] simfleet grows `/os/fetch http:` in the same stitch (sim devices fetch
      into a temp assets dir — real client code path if practical).
- [ ] verify_*.py: full fleet fetch on sim (some devices pre-seeded, one
      interrupted mid-file), assert only-what-changed transfers + all `ok`.
