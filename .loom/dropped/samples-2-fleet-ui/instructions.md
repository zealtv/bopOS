# samples-2-fleet-ui

**.waiting (2026-07-13):** gated on `patch-asset-sync/dist-0-proposal`
ratification — see the note in `samples-0-backend-manifest.waiting`. The UI
naming here ("sync samples") is explicitly under redesign (Get/Send Assets).

Dashboard fleet operation: "sync samples" per device / group / all.

- [ ] UI action fires `/os/fetch` at the selection with the backend's own URL;
      per-device progress + resulting pack version/hash on the device cards so
      a half-synced fleet is visible at a glance (parent's key pain).
- [ ] Mismatch surfacing: devices whose pack hash ≠ the served pack stand out.
- [ ] Tech-view only — do not add this to /facilitator without Bob (decision
      gate on user-facing facilitator changes).
- [ ] verify_*.py Playwright: sim fleet with mixed pack states, one click
      syncs all, progress renders, hashes converge.

Parent's done-when: a changed pack reaches every Pi in one dashboard action,
verifiably, no internet. Sim proves the flow; note real-Pi validation for
Bob's rig list when tying the parent (goal → `.waiting` on that, dashboard
pattern).
