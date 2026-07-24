# feature-backlog

Umbrella for concrete features Bob wants to revisit later without leaving them
in the active Loom queue.

- Each deferred feature remains a child thread with its own design,
  implementation, decisions, and history.
- Its current loose leaf is marked `.waiting`, with the deferral recorded in
  that feature's instructions.
- Moving a feature here changes priority only; it does not drop, narrow, or
  silently ratify the work.
- When Bob resumes a feature, move its thread back to the top-level active
  program (or another explicitly chosen owner), then claim its waiting leaf.

Current backlog:

- `33b-device-network-config` — saved Wi-Fi profiles and write-only
  credentials from the Device tab.
- `34-fleet-patch-global-state` — fleet-patch global state and a persistent
  menu-bar convergence indicator. Bob moved it here on 2026-07-23.
- `38-generator-editing-on-surface` — per-parameter generator editing on the
  shared control surface. Bob parked it here 2026-07-24 while thread 37 takes
  its first bite.
