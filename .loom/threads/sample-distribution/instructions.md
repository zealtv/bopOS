# sample-distribution

**2026-07-13:** all three children are `.waiting` on the `patch-asset-sync`
thread — Bob's composer-experience brain dump reshapes this into a unified
patch+asset model; `dist-0-proposal` will absorb or supersede these stitches
explicitly. Don't work this thread until that lands.

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
- [ ] Contract (**settled 2026-07-07** — `docs/OSC-CONTRACT.md` §9, implemented by
      `osc-schema-contract/fetch-landing`; absorb, don't duplicate): the verb is
      `/os/fetch <source-uri> <slot>` → `/os/fetched <slot> <ok|err>`, scheme-dispatched
      (`http:` = dashboard-served LAN manifest+hash with resume; `gdrive:` legacy)
- [ ] Landing (**changed from per-patch**): framework-owned engine-neutral root
      `~/bopOS/assets/<slot>/`, handed to engines via `ASSETS` at launch; legacy
      `patches/<active>/bop/samplepacks` symlinked one release

Done when: a changed sample pack reaches every Pi in one dashboard action, verifiably,
without touching the internet.
