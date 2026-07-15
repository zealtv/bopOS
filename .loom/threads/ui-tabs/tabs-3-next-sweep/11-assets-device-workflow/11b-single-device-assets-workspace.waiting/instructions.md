# 11b-single-device-assets-workspace

Blocked on `11a-device-asset-inventory`. Once inventory is ratified and tied,
replace the Assets placeholder with the first operational workflow:

- list host `assets/<slot>/` folders with operator-defined name, file count,
  bytes, modified time, and canonical fingerprint;
- select exactly one online assigned physical device and exactly one host or
  installed slot;
- **Send** an absent slot and **Update** a stale slot using the existing
  manifest-driven `/os/fetch` path;
- show honest device observation plus queued/fetching/succeeded/failed action
  feedback; after restart, derive state from inventory rather than a historical
  receipt;
- explicitly confirm and `/os/dropassets <slot>` for that one device, including
  installed slots no longer present in the host catalog;
- warn when updating or removing a slot declared by the selected device's
  active patch because the present asset fetch mutates the live directory;
- do not automatically stop/restart the engine in this stitch; sending a new
  side-by-side generation remains the safe migration path;
- remove asset selection/send/sync controls from Devices. Devices may retain a
  compact observed summary or link into Assets, but Assets owns these actions.

Do not add an All/Fleet target, durable fleet desired-assets record, Sync All,
rollout waves, packaging, archives, caches, byte ETA, or automatic engine
coordination. Those belong to `asset-fleet-distribution`.

Ship a focused real-dashboard + simfleet Playwright verifier covering send,
update, removal, target isolation, offline/unassigned guarding, warning copy,
reconnect observation, and the absence of fleet-wide action controls. Follow
`docs/VERIFICATION.md` and retain reviewed screenshots/results in the stitch.

Reference:
`.lore/items/2026-07-15-asset-management-direction/content/decision.md`.
