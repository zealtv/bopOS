# Verification (2026-10-28, main at ce55ade + this change)

`tests/verify_identify_dot.py` used a real dashboard on private ports with
four physical-protocol peers. Seats 0 and 1 are bound; Seat 2 is unbound.
All 11 checks passed:

- **Devices tab:** clicking Cara Moss's roster dot sent `/all/os/to <cara>
  identify` (seen by the peer), and the selection stayed on Abel Fern. The
  dot pulses, and the pulse is finite (2 iterations).
- **Remote at 390 px:**
  - Seat 0's meta reads "Seat 0 · Dora Vale · online";
  - unbound Seat 2 has no button and reads "Seat 2 · unbound";
  - the dot's tap target is at least 28 × 28 px;
  - a tap on Seat 1 sent identify for Abel Fern;
  - there's no horizontal scroll.
- **Desktop dashboard:** no `.dot-identify` (the Control tab's cards are
  unchanged), and no page errors.

**Neighbouring journeys:** all 21 that touch the Control column, the Remote,
the Devices roster or the device panels pass:

| journey | | journey | |
|---|---|---|---|
| control_column_scroll | ✓ | live_param_kinds | ✓ |
| control_tab | ✓ | module_panels | ✓ |
| control_surface_component | ✓ | log_destination | ✓ |
| device_control_modes | ✓ | monitor_transport | ✓ |
| device_roster_sort | ✓ | manifest_param_visibility | ✓ |
| device_io_inventory | ✓ | remote_hold | ✓ |
| device_control_panel | ✓ | precision_param_input | ✓ |
| fleet_patch_deploy | ✓ | sites | ✓ |
| generator_drawer | ✓ | state_load_safety | ✓ |
| ground_and_card | ✓ | wifi_networks | ✓ |
| interaction_guard | ✓ | | |

The first attempt failed 19 of them because Bob's running dashboard held UDP
5551 and 5552 (stitch `67-repair-pass/27-test-port-isolation`). The rerun
with it stopped passed.

Not checked on hardware: whether a real node chirps or flashes on these
clicks. The Identify message is the same one the existing Identify buttons
send.

Screenshot: `remote-seat-card.png`.
