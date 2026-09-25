# framework-version-management

**Goal:** the operator can see which devices run out-of-date bopOS and bring
them current deliberately.

**Status:** update mechanics are shipped. Missing: a definition of "current"
and honest per-device classification. Design gate waiting on Bob
(`version-0-currentness-design`).

## Already shipped — don't redesign

- Dashboard shows its own `host_version`.
- Nodes report heartbeat `version` plus `git_rev`, `contract_version`,
  `update_model`.
- Per-device and fleet **Update bopOS** actions.
- Unattended update: phases reported, reboot only after success, proven on a real
  node.

## Missing

What "desired framework version" means, and classifying each node as
**current / stale / unknown / diverged**.
