# Decisions

Bob ratified all three proposal recommendations on 2026-08-03: “yes to all
three.”

1. **Placement and ownership:** the Patches tab carries a clearly labelled
   venue-setting card beside the manifest editor. It writes installation
   state, never `bopos.patch.json`.
2. **Remote placement:** framework verbs remain in Remote's existing
   `Fleet setup` and per-seat `Device setup` sections. They do not participate
   in manifest parameter/event ordering.
3. **Desktop scope:** the allowlist gates Remote only. Desktop Device Actions
   remain unconditional, and Control retains its Devices-tab handoff.

The four supported commands render in one canonical order: restart engine,
update bopOS, reboot, shutdown. This prevents hand-authored installation files
from shuffling a safety-relevant surface.
