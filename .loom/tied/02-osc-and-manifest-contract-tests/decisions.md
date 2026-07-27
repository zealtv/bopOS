# Decisions — OSC and manifest contract promotion

## Promoted assertions

Promotion was assertion-by-assertion into four code-surface-owned fast modules:

| Living module | Durable property | Archived sources inspected |
|---|---|---|
| `tests/test_manifest.py` | canonical flat/nested identities; identity bounds and uniqueness; contained entrypoints; finite bounded numeric declarations; type/promotion/legacy normalization; cue/cap/slot schema; normalized atomic writes | `patch-manifest/test_patch_manifest.py`; `1-contract-model-relay/verify_param_contract_relay.py` |
| `tests/test_paramgen.py` | numeric parameter automation set/fade/loop/LFO/stop grammar and rejection boundary | `automation-1-engine-and-parity/verify_param_automation.py` |
| `tests/test_pointfield.py` | atomic/sparse/clear point wire forms, malformed-frame rejection, falloff registry, sorted zero-indexed decomposition | `seam-3-points-node-side/verify_points_node_side.py`; `spatial-0-engine/verify_spatial_engine.py` |
| `tests/test_protocol_primitives.py` | selector-stripped nested patch/master engine surface; canonical group context and empty sentinel; persisted group launch context; integer slewed sync offset state | `1-contract-model-relay/verify_param_contract_relay.py`; `seam-2-master-term/verify_master_term.py`; `engine-group-context/verify_engine_group_context.py`; `sync-0-wire-shape/verify_sync.py` |

The tests exercise production helpers directly. They do not pin error prose,
contract-version literals, complete additive verb lists, source-file contents,
test-double interfaces, or browser presentation.

## Covered elsewhere; no duplicate promotion

- Exact-UID admin envelope behavior is already owned by
  `tests/test_device_enabled.py`, `tests/test_audio_config.py`, and
  `tests/test_log_config.py`. The broad archived
  `08-unbound-admin-seam/verify_uid_admin.py` remains input to the identity
  child rather than being copied here.
- Manual typed OSC validation and PD float precision are already owned by
  `tests/test_monitor_send.py`.
- Engine context replay after readiness is already owned by
  `tests/test_engine_ready_replay.py`.
- Asset-slot run context is already owned by
  `tests/test_asset_slot_context.py`.
- Manifest visibility across desktop and facilitator surfaces remains a slower
  living journey in `tests/verify_manifest_param_visibility.py`.

## Not promoted from this archive slice

- `boundary-6-contract-v12-and-renames/verify_boundary6.py` primarily pins a
  superseded version literal, source text, filenames, and one-time rename
  completeness. Those are authoring evidence, not runtime contracts.
- Full-stack timing, UDP broadcast, browser, and late-join journeys remain
  integration evidence. Child `06` retains the explicit sync leader/helper
  triage; this stitch promoted only the deterministic node sync primitive.
- Static checks of launcher shell tokens and exact PD `-send` text were not
  adopted. Run-context values are exercised through `runcontext.generate()`;
  `.pd` files were not touched.

## Product and simulator impact

No product behavior or protocol changed. `tools/simfleet.py` therefore required
no modification. One initially failing point test was corrected: five `/pt`
arguments are deliberately the valid sparse form, so the malformed fixture was
changed to a genuinely truncated full frame. This was a test-authoring error,
not a product defect.
