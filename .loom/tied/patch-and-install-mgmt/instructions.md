# patch-and-install-mgmt

**Split 2026-07-08 from dashboard-4-patch-mgmt.** The buildable phase-4 items —
they ride the `/os/*` provisioning verbs already landed in `os-admin-verbs`
(helper answers `/os/patch`, `/os/addpatch`, `/os/pullpatch`, `/os/getsamples`
on 6660 with `/os/rev` receipts; simfleet mirrors them). The sensor-data view
is blocked on Pi-side work and lives in the sibling stitch.

Checklist:
- [ ] Patch panel, per device + fleet-wide: current patch (from `/os/report`),
      switch (`/os/patch <name>`), add from GitHub (`/os/addpatch <user>
      <repo>`), pull (`/os/pullpatch`), get samples (`/os/getsamples`)
- [ ] Framework update visibility: `/os/update` per device and `/all`, with
      per-device version + the `/os/rev` convergence already surfaced so a
      half-updated fleet is visible at a glance (a version-drift indicator)
- [ ] Installation file management: save current `installation.json` as a named
      venue, list saved venues, load/switch between them (re-broadcast state)

Notes:
- Patch switch/addpatch/pullpatch reboot the node; the dashboard should show
  the transient offline→online and the post-reboot report (new patch).
- No dropdown of *available* patches exists on the wire yet — switch takes a
  patch-name input (like addpatch takes user/repo). A patch-listing verb would
  be a contract addition; note it as a proposal if it feels needed, don't add.
- Verify in simfleet + headless browser like the other dashboard stitches.
</content>
