# 17-usb-service-hardening

**Status:** ready · Pi adoption check goes to Bob's hardware list
**Goal:** the root USB unit runs only root-owned code, and a partition's stop
unmounts only what that partition mounted.

Evidence: `lore:2026-10-05-bopos-review-install-services` B1, B2 (`reproduce.py`: `privilege_source_audit`,
`usb_ownership`).

- **B1 (high).** `systemd/bopos-usb@.service` has no `User=` and runs
  `/home/pi/bopOS/bash/bopos-usb-mount`; provisioning chowns the checkout to
  `pi`. Install the helper root-owned outside the checkout (as the hostname
  and Wi-Fi helpers already are) and point the unit there.
- **B2.** sdb1's start succeeds via the already-mounted guard; its stop calls
  an argument-less `unmount` that unmounts sda1. Pass the instance; unmount
  only when it owns the mount; serialise add/remove (`flock`).

Done when: fixture tests fail before and pass after (A mounted, B ignored, B
removed → A stays; then A removed); installer tests green. Hardware claims
pending (`glean:hardware-claims`).
