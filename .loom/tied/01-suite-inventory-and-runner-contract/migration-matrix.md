# Durable coverage and migration matrix

This is an inspection map for children `02`–`06`, not a promise that every
named guard contributes a living assertion. Each child must audit current
`tests/` coverage first and apply the inclusion test in `inventory.md`.

## 02 — OSC and manifest contracts

| Durable area | Living baseline | Tied guards worth inspecting |
|---|---|---|
| Manifest schema, nested parameter paths, canonical validation | `test_asset_slot_context.py`, `verify_manifest_param_visibility.py` cover consumers but not the whole schema | `patch-manifest/test_patch_manifest.py`; `1-contract-model-relay/verify_param_contract_relay.py` |
| Ratified OSC namespaces, target grammar, engine boundary, admin envelopes | pieces in `test_device_enabled.py`, `test_monitor_probe.py`, `test_monitor_send.py`, `test_engine_ready_replay.py` | `boundary-6-contract-v12-and-renames/verify_boundary6.py`; `seam-2-master-term/verify_master_term.py`; `2-engine-admin-requests/verify_admin_requests.py`; `08-unbound-admin-seam/verify_uid_admin.py` |
| Provided spatial/point terms and wire decomposition | no dedicated living module | `seam-3-points-node-side/verify_points_node_side.py`; `spatial-0-engine/verify_spatial_engine.py` |
| Parameter automation grammar and node/simulator parity | browser coverage in `verify_generator_drawer.py`; replay edge in `test_engine_ready_replay.py` | `automation-1-engine-and-parity/verify_param_automation.py` |
| Forward-sync wire shape | no dedicated living module | `sync-0-wire-shape/verify_sync.py`; inspect `sync-1-leader/verify_sync_leader.py` only for wire invariants |
| Engine group run context | `test_engine_ready_replay.py` covers redelivery, not the full context | `engine-group-context/verify_engine_group_context.py` |

Reject obsolete contract-version literals and source-text checks when the same
property can be exercised through production parsers or message builders.

## 03 — fetch convergence

| Durable area | Living baseline | Tied guards worth inspecting |
|---|---|---|
| Node fetch dispatch and per-device serialization | `test_node_fetch_dispatch.py` covers only queue dispatch | `dist-2-node-side/verify_dist2_node_side.py`; `fetch-landing/test_fetch_landing.py` |
| Dashboard staging and dispatch to the intended target | end-to-end per-device patch flow in `verify_device_patch_targeting.py` | `dist-3-dashboard-send/verify_dist3_dashboard_send.py`; `distribution-workflow/verify_distribution_workflow.py` |
| Desired/reported fingerprint convergence | persistence in `test_device_patch_override.py`; UI journey in `verify_device_patch_targeting.py` | `fp-2-fleet-state/verify_fp2_fleet_state.py`; `patch-fingerprint-warm/verify_patch_fingerprint_warm.py` |
| Bytes converge before switch; node stays responsive | no focused living unit | `patch-switch-lifecycle/verify_patch_switch_lifecycle.py`; `asset-cache-and-legacy-retirement/verify_asset_cache_repair.py` |

Do not promote legacy samplepack paths, exact refresh-message lists, UI copy, or
fresh-Pi claims that simfleet cannot establish.

## 04 — mute safety

| Durable area | Living baseline | Tied guards worth inspecting |
|---|---|---|
| Fleet execution mute versus physical device enabled | `test_audition_output_gate.py`, `test_device_control_routing.py`, `test_device_enabled.py` | `18-decoupled-device-mute/verify_decoupled_device_mute.py`; `05-global-execution-target/verify_execution_target.py` |
| Effective node output safety and acknowledgements | partial node coverage in `test_device_enabled.py` | `12-dashboard-live-controls/verify_device_mute_protocol.py`; `3-device-enable-ui-state/verify_device_enabled.py` |
| Heartbeat/restart convergence | audio-config restart edge in `test_audio_config.py` | `hb-identity/test_hb_identity.py`; `12-dashboard-live-controls/verify_live_controls_backend.py` |
| Exact target selection | route coverage in `test_device_control_routing.py` | `2-fix/verify_mute_targeting.py` |

The current ruling is authoritative: requested device mute and fleet execution
mute are independent inputs whose OR determines effective safety. Do not
resurrect the superseded fleet-blocks-device-mute assertion.

## 05 — identity and fingerprint

| Durable area | Living baseline | Tied guards worth inspecting |
|---|---|---|
| Canonical device identity and fingerprint helpers | asset context and desired-patch persistence have partial coverage | `fp-1-identity-module/verify_fp1_identity.py` |
| Assignment/unassignment persistence and exact-UID administration | host migration in `test_device_enabled.py` | `assign-persistence/test_assign_persistence.py`; `08-unbound-admin-seam/verify_uid_admin.py` |
| Seat identity does not leak or replace device identity | route tests cover behavior indirectly | `03-seat-identity-leaks/verify_seat_identity.py`; `d8-1-seat-model/verify_d8_seat_model.py` |
| Alias changes preserve physical identity and content pin | desired-patch rename case in `test_device_patch_override.py` | `01-registry-and-generator/verify_device_alias_registry.py`; `dashboard-3-discovery-assign/verify_assign.py` |
| Desired/reported patch fingerprint semantics | `test_device_patch_override.py`, `verify_device_patch_targeting.py` | `fp-2-fleet-state/verify_fp2_fleet_state.py`; `11a-device-asset-inventory/verify_device_asset_inventory.py` |

Prefer production state and identity helpers over incomplete `FakeOSC` or fake
state interfaces.

## 06 — remaining durable surfaces

These are candidates for the discriminating question, not presumed promotions:

| Candidate surface | Living baseline | Tied guards worth inspecting |
|---|---|---|
| Show document schema and tolerant persistence | none in `tests/` | `2-model-and-persistence/verify_show_model.py` |
| Group protocol and engine context | group context replay edge only | `1-protocol-node/verify_group_protocol_node.py`; `engine-group-context/verify_engine_group_context.py` |
| Sync leader/helper timing protocol | none dedicated | `sync-1-leader/verify_sync_leader.py`; `sync-2-helper-cue/verify_sync_helper.py` |
| Spatial math and point decomposition | none dedicated | `spatial-0-engine/verify_spatial_engine.py`; `seam-3-points-node-side/verify_points_node_side.py` |
| Update outcome receipts | none dedicated | `rev-outcome-receipts/verify_rev_outcome_receipts.py`; `updatebopos-unattended/verify_updatebopos_unattended.py` |
| Manual typed OSC send | `test_monitor_send.py` already strong | `03-osc-send-tab/verify_monitor_send.py` only to confirm no durable gap |

Newer living modules for audio configuration, installation, logging, USB
automount, transport recovery, Control/Device surfaces, and precision parameter
entry should be treated as the baseline. Inspect archived guards in those areas
only when a concrete uncovered forever-contract is identified.
