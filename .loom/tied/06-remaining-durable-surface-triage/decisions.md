# Decisions — remaining durable-surface triage

This closes the candidate list from child `01` after accounting for promotions
made in children `02`–`05`. It is the promote/reject handoff for child `08`;
no blind archive sweep was performed.

## Promoted candidates

| Living owner | Durable properties | Archived sources inspected |
|---|---|---|
| `tests/test_show_model.py` | Show schema cleaning; typed messages and target normalization; identity uniqueness; finite-loop safety; section derivation; copy-on-write identity minting; atomic ordered persistence; tolerant missing/corrupt/invalid load; no-clobber creation | `2-model-and-persistence/verify_show_model.py` |
| `tests/test_group_membership.py` | exact-UID, validated, sorted full-state membership replacement; empty clear; persistence before exposure; attributable receipt; no state or receipt on invalid input/failure | `1-protocol-node/verify_group_protocol_node.py` |
| `tests/test_sync_protocol.py` | low-RTT robust leader estimate; assigned-only offset push after a minimum sample set; integer offset continuity; scheduled cue fire, grace, and stale-drop policy | `sync-1-leader/verify_sync_leader.py`; `sync-2-helper-cue/verify_sync_helper.py` |
| `tests/test_admin_outcomes.py` | post-action attributable revision receipt with open-ended status phase; callback-exception terminal receipt; receipt-before-reboot ordering; explicit reboot failure; dashboard records errors without success refresh side effects | `rev-outcome-receipts/verify_rev_outcome_receipts.py`; `updatebopos-unattended/verify_updatebopos_unattended.py` |

All additions exercise current production owners. No product behavior,
simulator behavior, wire grammar, or UI changed.

## Already covered; no duplicate promotion

| Candidate | Living owner |
|---|---|
| canonical group selectors, persisted engine context, and empty sentinel | `tests/test_protocol_primitives.py` |
| deterministic node offset slew primitive | `tests/test_protocol_primitives.py` |
| spatial point parsing, sparse/full/clear wire forms, falloff math, and engine decomposition | `tests/test_pointfield.py` |
| manual typed OSC validation and float precision safety | `tests/test_monitor_send.py` |
| audio configuration, installation composition, logging, USB automount, transport recovery, Control/Device routing, and precision parameter entry | their existing focused living modules and browser journeys |

The matrix's manual-send candidate was explicitly rerun with the focused set;
its four living tests remain sufficient.

## Rejected or retained only as integration evidence

- Exact Show UI copy, websocket event bursts, element geometry, drag layout,
  CSS mechanism, screenshots, and one-time restart delivery proofs are not
  model contracts. Current browser journeys own supported Show workflows.
- Complete admin phase enumerations and complete verb maps would prevent
  additive evolution. Living tests require attributable terminal outcomes and
  accept future phase names.
- Exact Git argv sequences, shell source tokens, simulated authorization, and
  historical unattended-update delivery proofs are implementation evidence.
  Shell and real persistent-node adoption remain with their owning update and
  hardware work.
- Sync meter traffic, loopback millisecond thresholds, random simulated skew
  tolerances, and "server did not wedge" delivery checks are integration
  evidence. The living suite owns the estimator and scheduler policies; real
  timing accuracy remains a hardware measurement.
- Exhaustive copies of group behavior across node, simfleet, and audition were
  not promoted. All three consume the shared `groups.py` parser; the node test
  owns persistence/receipt semantics and existing execution-route tests own
  simulator/audition selection.
- Browser screenshots, exact labels, CSS class lists, pixel dimensions, and
  one-time rollout proofs found in adjacent guards fail the longevity or
  observation criteria and should be retired by child `08`.

## Child `08` disposition

Child `08` can classify the inspected Show, group, sync, and update guards as
**durable assertions promoted selectively; archive scripts retained only as
historical integration evidence**. UI geometry/copy/screenshots and exact
implementation checks should be listed as retired authoring evidence, not
future regression backlog.
