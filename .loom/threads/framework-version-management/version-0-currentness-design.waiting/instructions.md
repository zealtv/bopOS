# version-0-currentness-design

**Status:** waiting on Bob · design gate
**Goal:** define framework currentness and how Devices shows it.

## Decide

- **What "desired" means** — is the dashboard host's checkout enough? How is
  branch/release intent represented?
- **Classification** — current / stale / unknown / diverged. Can equality alone
  tell stale from diverged, or is ancestry/release metadata needed?
- **Where it shows** — compact per-device and fleet summaries.
- **Actions** — target only appropriate persistent nodes; explain ephemeral
  nodes without implying they can keep an update.

Reuse the shipped confirm / receipt / reboot / reappearance flow (see parent).
Keep framework revision separate from patch fingerprint and contract version.

## Deliver

A short proposal + implementation split, kept in lore. Then back to waiting for
Bob's ratification.
