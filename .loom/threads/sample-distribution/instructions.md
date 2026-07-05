# sample-distribution

**Goal:** a flexible, low-pain way to mass-update the audio (sample packs) running on
all Pis, using the **local network** rather than per-Pi cloud fetches. Review §10.

Today: `getsamples.sh` pulls a patch's `SAMPLEPACKSURL` (gdrive) per device, triggered
per device — slow, internet-dependent, and painful for a fleet during install week.

Direction:
- [ ] Dashboard/laptop as the sample source of truth: a samples directory per
      installation/patch, synced to Pis over the LAN (candidates: HTTP download from the
      dashboard backend with a manifest+hash so Pis fetch only what changed; or
      rsync-over-ssh driven by the backend; prefer whichever survives flaky WiFi and
      partial fleets best — resumable, verifiable)
- [ ] Fleet operation in the dashboard: "sync samples" per device / group / all, with
      per-device progress + version/hash display so a half-synced fleet is visible
- [ ] Keep the cloud path (`getsamples`) as the way the *laptop* acquires packs;
      the LAN path is laptop → Pis
- [ ] Contract: an `/os/samples/...` namespace (sync, report hash/version) — register in
      `osc-schema-contract`
- [ ] Where samples land on the Pi: keep the current per-patch convention
      (`patches/<patch>/…`), documented

Done when: a changed sample pack reaches every Pi in one dashboard action, verifiably,
without touching the internet.
