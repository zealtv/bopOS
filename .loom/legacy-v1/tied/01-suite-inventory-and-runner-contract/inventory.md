# Living test-suite inventory

Date: 2026-07-27

## Baseline

`tests/` contains 27 Python files in two invocation styles:

- 15 `unittest` modules named `test_*.py`;
- 12 standalone Playwright journeys named `verify_*.py`.

The fast modules are already discoverable as one suite. All 15 use
`unittest.main()` when invoked directly, and discovery currently runs 99 tests.
The browser journeys each own a `main()` harness, start the real dashboard and
simfleet or a wire-compatible fake peer on non-default ports, drive Chromium,
and report their own checks.

There is no checked-in CI workflow, project test configuration, or aggregate
test runner. The only shared invocation is raw `unittest` discovery.

The tied archive now contains 189 Python files matching
`(verify|test)*.py`. The briefing's 168 total and 71 browser-free / 39-red
sample are historical measurements, not the current inventory and not a
backlog to make green.

## Fast browser-free tier

Stable invocation today:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python \
  -m unittest discover -s tests -p 'test_*.py'
```

| Living file | Owning surface | Main dependency shape |
|---|---|---|
| `test_asset_slot_context.py` | asset-slot discovery and launch/run context | production helpers, temp files, simfleet |
| `test_audio_config.py` | node audio configuration and receipts | production helpers, mocks, simfleet/audition parity |
| `test_audition_output_gate.py` | audition mute/output safety | audition helper with fake engines |
| `test_device_control_routing.py` | physical-device versus execution routing | dashboard/OSC bridge, async fakes |
| `test_device_enabled.py` | exact-UID enablement, persistence, receipts, mute independence | node/state/store, fake OSC |
| `test_device_install.py` | install/provision composition | shell syntax and source inspection |
| `test_device_patch_override.py` | per-device desired patch and fingerprint persistence | installation state and temp registry |
| `test_engine_ready_replay.py` | engine context and static-param replay | node helper and socket fakes |
| `test_log_config.py` | log destination config and protocol parity | node/store/simfleet with mocks |
| `test_monitor_probe.py` | assigned-target probe routing and typed reply | OSC bridge with async mocks |
| `test_monitor_send.py` | typed manual-send validation and PD float safety | dashboard validation helper |
| `test_node_fetch_dispatch.py` | node fetch dispatch seam and hostname independence | node helper with mocks |
| `test_nodelog.py` | append-only node-log facility | filesystem/temp files and simfleet parity |
| `test_osc_transport.py` | dashboard transport selection, recovery, shutdown | production bridge/server/state with socket mocks |
| `test_usb_automount.py` | USB mount/install source contract | shell syntax and source inspection |

This tier is browser-free and hardware-free. Some modules import installed
`pyOSC3` or `pythonosc`, and some invoke safe local shell syntax checks, but no
test requires a live node, audio device, LAN, Pure Data, or Chromium.

## Browser/integration tier

Current invocation is one process per file:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python tests/verify_<surface>.py
```

| Living file | Owning surface |
|---|---|
| `verify_control_surface_component.py` | shared Control/Device renderer and send seam |
| `verify_control_tab.py` | Control tab, target filter, cues/presets, compatibility alias |
| `verify_device_control_modes.py` | physical/execution route separation through the real UI |
| `verify_device_control_panel.py` | Device control panel, offline state, pinned patch params |
| `verify_device_patch_targeting.py` | per-device patch pin/follow-fleet convergence |
| `verify_generator_drawer.py` | generator drawer and parameter-automation wire grammar |
| `verify_live_param_checkbox.py` | live checkbox/slider commit under heartbeat rerenders |
| `verify_log_destination.py` | Device logging UI and exact-UID receipt round trip |
| `verify_manifest_param_visibility.py` | full desktop versus promoted facilitator parameters |
| `verify_osc_transport_monitor.py` | visible bounded transport-error reporting |
| `verify_precision_param_input.py` | exact typed parameter entry and editor parity |
| `verify_set_patch_handoff.py` | Device-to-Patches hand-off and target scoping |

This tier requires Playwright/Chromium in addition to the dashboard
dependencies. Individual journeys may also require `pythonosc`. They are
software integration checks, not hardware adoption: simulated peers cannot
prove cold-cache Pi transfers, JACK/PD behavior, audible mute, real LAN
broadcast, peripherals, or touch behavior on an iPad.

## Durable-contract inclusion test

Promote an assertion only when every answer below is yes:

1. **Authority:** Is the property ratified in a durable contract, architecture
   decision, or deliberately supported public workflow?
2. **Longevity:** Should it remain true across refactors and ordinary wording,
   styling, fixture, and internal API changes?
3. **Ownership:** Can the test live under the code surface whose change should
   update it?
4. **Observation:** Can it assert public state, wire shape, persisted data, or
   behavior instead of an incidental implementation mechanism?
5. **Repeatability:** Can it run deterministically in the declared software
   tier, with hardware limitations stated rather than simulated away?
6. **Actionability:** Would a failure name a property that maintainers either
   restore or intentionally revise in the same change?

An assertion that fails any item remains authoring evidence. Typical retirement
material includes exact UI prose, pixel/layout snapshots without a standing UX
contract, exact complete command lists where additions are legal, private fake
interfaces, obsolete version literals, superseded rulings, one-off delivery
proof, and hardware acceptance disguised as simulation.

Promotion is assertion-by-assertion. No tied guard is moved or adopted whole.
