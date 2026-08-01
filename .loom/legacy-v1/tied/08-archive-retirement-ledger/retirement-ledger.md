# Tied guard retirement ledger

Closed 2026-07-27 by thread `27-tied-guard-rot`.

## Governing disposition

The maintained regression suite is the code-surface-organized suite under
`tests/`, invoked through:

```sh
tools/run-tests.sh fast
tools/run-tests.sh browser
tools/run-tests.sh all
```

The 189 Python guard scripts in 174 `.loom/tied/` families are preserved
historical evidence. They are not a second regression suite, are not expected
to be green, and are not a maintenance backlog. No archived file was deleted
or repaired during this thread, and no archive sweep was added.

The classifications below apply to assertions, not necessarily to every line
in a script. “Promoted” means the durable property has a named living owner;
the source script itself remains retired historical evidence. Every archived
guard not named below is classified **retired authoring/integration evidence**
by default. This default closes the long tail of presentation checks, exact
source and copy checks, test-double shapes, screenshots, and one-time delivery
proofs without silently deleting them.

## Promoted durable properties

| Archived guard family or family group | Living owner | Durable property retained |
|---|---|---|
| `patch-manifest`, `1-contract-model-relay` | `tests/test_manifest.py` | Manifest normalization, validation, bounded declarations, identities, and atomic persistence |
| `1-contract-model-relay`, `seam-2-master-term`, `engine-group-context`, `sync-0-wire-shape` | `tests/test_protocol_primitives.py` | Engine selectors, master/group context, empty sentinel, and integer offset state |
| `automation-1-engine-and-parity` | `tests/test_paramgen.py` | Numeric parameter automation grammar and rejection boundary |
| `seam-3-points-node-side`, `spatial-0-engine` | `tests/test_pointfield.py` | Point wire forms, validation, falloff math, and engine decomposition |
| `2-engine-admin-requests`, `08-unbound-admin-seam` | `tests/test_device_enabled.py`, `tests/test_audio_config.py`, `tests/test_log_config.py` | Exact-UID administration and attributable outcome envelopes |
| `03-osc-send-tab` | `tests/test_monitor_send.py` | Typed OSC validation and float precision |
| archived engine-ready/context guards | `tests/test_engine_ready_replay.py`, `tests/test_asset_slot_context.py` | Readiness replay and canonical asset run context |
| `fetch-landing`, `dist-2-node-side` | `tests/test_fetcher.py`, `tests/test_node_fetch_dispatch.py`, `tests/test_simfleet_fetch.py` | Verified-byte convergence, safe landing, dispatch, ordering, coalescing, and per-device serialization |
| `dist-3-dashboard-send`, `distribution-workflow`, `patch-switch-lifecycle` | `tests/verify_device_patch_targeting.py`, `tests/test_device_patch_override.py` | Intended-target dispatch, desired-patch persistence, and convergence before switch |
| `18-decoupled-device-mute`, `05-global-execution-target`, `12-dashboard-live-controls`, `3-device-enable-ui-state`, `28-fleet-mute-semantics`, `2-fix` | `tests/test_mute_safety.py`, `tests/test_device_enabled.py`, `tests/test_device_control_routing.py`, `tests/test_audio_config.py`, `tests/test_audition_output_gate.py` | Independent requested intent, fleet safety, effective output, persistence, restart, and route behavior |
| `hb-identity`, `assign-persistence`, `d8-1-seat-model`, `03-seat-identity-leaks`, `01-registry-and-generator`, `dashboard-3-discovery-assign` | `tests/test_identity_fingerprint.py`, `tests/test_node_fetch_dispatch.py` | Physical UID precedence, assignment/tombstones, and the Device/Seat boundary |
| `fp-1-identity-module`, `fp-2-fleet-state`, `patch-fingerprint-warm`, `11a-device-asset-inventory` | `tests/test_identity_fingerprint.py`, `tests/test_device_patch_override.py`, `tests/test_asset_slot_context.py`, `tests/verify_device_patch_targeting.py` | Canonical content identity, warm/unknown inventory state, drift derivation, and durable pins |
| `2-model-and-persistence` | `tests/test_show_model.py` | Show schema, normalization, finite-loop safety, tolerant loading, and atomic persistence |
| `1-protocol-node` | `tests/test_group_membership.py` | Validated exact-UID full-state membership and attributable receipts |
| `sync-1-leader`, `sync-2-helper-cue` | `tests/test_sync_protocol.py` | Robust offset estimation and scheduled cue policy |
| `rev-outcome-receipts`, `updatebopos-unattended` | `tests/test_admin_outcomes.py` | Attributable terminal outcomes, reboot ordering, and failure handling |

The current living suite also owns audio configuration, device installation,
logging, USB automount, OSC transport recovery, Control/Device routing,
precision parameter input, and manifest visibility. Archived guards in those
areas remain historical; they need no duplicate promotion.

## Superseded assertions

These assertions record a ruling that no longer governs the product:

| Archived source | Superseding ruling |
|---|---|
| `28-fleet-mute-semantics` and older `device_muted` checks | Device intent and fleet execution mute are independent; safety is composed at effective output. Owned by `tests/test_mute_safety.py`. |
| `hb-identity` engine-lifecycle mute fallback | Missing mixer control fails closed without using engine stop/start as the mute mechanism. Superseded by thread `29-fleet-patch-sync-hang`, child `2-fix`. |
| `assign-persistence` hostname-renaming checks | Assignment changes Seat routing, not physical Device identity or hostname. Owned by `tests/test_identity_fingerprint.py`. |
| `boundary-6-contract-v12-and-renames` version/source assertions and other pinned historical contract literals | The current parsers, schemas, and protocol primitives are authoritative; historical version and rename-completeness checks are not. |
| archived legacy-samplepack paths, removed verbs, exact additive command lists, and fake-state interfaces | Current asset slots, open-ended protocol additions, and production interfaces supersede them. |
| obsolete immediate-clear expectations in patch-switch delivery guards | Fetch state remains reconciling until the node reports the observed terminal state. Living fetch and targeting tests own the current behavior. |

The archived files remain unchanged so the historical decision trail is intact.

## Environment and hardware evidence

The following cannot be promoted as deterministic local regression claims:

| Archived area | Disposition or named follow-up |
|---|---|
| `sync-3-jitter-harness` and real clock accuracy | Environment-only evidence; `fleet-testing/clock-sync/sync-4-hw-measurement.waiting` owns real-rig acceptance. |
| spatial engine/room rollout and audible placement guards | Deterministic math is promoted to `tests/test_pointfield.py`; real-rig acceptance belongs to `fleet-testing/spatial-audio/spatial-3-rig-sweep.waiting`. |
| asset distribution on persistent nodes | Local convergence is promoted; fleet staging/adoption belongs to `fleet-testing/asset-fleet-distribution/fleet-0-bulk-distribution-design.waiting` and `fleet-1-node-staged-slot-swap.waiting`. |
| `audition-1b-pd-mac-gate`, JACK/ALSA/mixer, Raspberry Pi filesystem/SD/Wi-Fi timing, and Pure Data/audio-output checks | Hardware/environment-only evidence. Existing focused software tests own what can be established locally; adoption is checked with the relevant hardware work, not by maintaining the archive. |
| unattended update shell/Git delivery | Outcome semantics are promoted to `tests/test_admin_outcomes.py`; real persistent-node adoption remains operational evidence. Desired-version classification belongs to `framework-version-management/version-0-currentness-design.waiting`. |

There is no unnamed follow-up for archive repair or migration. The waiting work
above owns product or hardware acceptance, not maintenance of its tied guards.

## Retired authoring and integration evidence

The following are deliberately preserved but retired:

- exact UI copy, labels, DOM structure, CSS classes/mechanisms, geometry,
  screenshots, and pixel dimensions;
- complete additive verb/message/phase lists, historical version literals,
  filename/rename completeness, exact source tokens, and private dictionaries;
- exact `amixer`, Git, shell, broadcast, refresh, or websocket command lists
  where a durable observable outcome is already owned;
- fake interfaces and full-stack replicas that do not exercise the production
  owner;
- one-time rollout, restart, browser delivery, latency, responsiveness, and
  simulator-parity proofs;
- historical HTTP Range, cache, legacy-path, and samplepack implementation
  strategies beneath the current verified-byte outcome;
- all other guards in the 174-family census not explicitly classified above.

This catch-all is intentional: preservation does not imply continuing
authority or a promise to make a historical script pass.

## Encountered supersession rule

During unrelated work, do not sweep or proactively repair `.loom/tied/`.
If that work explicitly encounters and relies on an archived guard whose
assertion conflicts with a later ruling, classify it as superseded. The narrow
interim rule remains: update only the encountered assertion, add an inline
comment naming the superseding stitch, and record the ruling in the current
stitch’s `decisions.md`. Do not expand that exception into neighbour maintenance
or treat the rest of the archive as a suite.

## Sources

This ledger collates:

- `01-suite-inventory-and-runner-contract/{inventory,migration-matrix,runner-contract}.md`;
- decisions from children `02-osc-and-manifest-contract-tests` through
  `06-remaining-durable-surface-triage`;
- the runner and pre-tie workflow from
  `07-suite-runner-and-pre-tie-wiring/decisions.md`.
