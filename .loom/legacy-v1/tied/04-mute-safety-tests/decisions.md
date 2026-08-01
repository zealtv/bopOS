# Decisions — mute safety promotion

## Promoted assertions

| Living surface | Durable properties | Archived context inspected |
|---|---|---|
| `tests/test_mute_safety.py` | effective output is `device_enabled and not mute_all`; device intent can be staged beneath fleet safety; only device intent persists across reconstruction; reports distinguish requested device state, fleet execution safety, and effective output | `28-fleet-mute-semantics`; `29-fleet-patch-sync-hang/2-fix` |
| `tests/test_mute_safety.py` | configured mixer targeting wins; automatic targeting excludes HDMI and remembers a working DAC control; missing mixer control fails closed without using engine lifecycle as a mute fallback | `29-fleet-patch-sync-hang/2-fix/verify_mute_targeting.py` |
| `tests/test_device_control_routing.py` | a physical device returning after being offline receives its persisted enabled intent | current dashboard heartbeat path |
| `tests/test_audio_config.py` | an audio-engine restart reapplies the current effective mute requirement without changing either requested state | current node audio-config path |

The new tests exercise production helpers and simfleet's protocol/report path.
They assert observable state and behavior rather than complete command lists,
UI copy, or private implementation shape.

## Existing living coverage retained

- `tests/test_audition_output_gate.py` already proves that fleet mute gates the
  effective master output while preserving the latest requested master value.
- `tests/test_device_enabled.py` already owns exact-UID persistence,
  enforcement-before-receipt, migration, report vocabulary, and failure
  behavior for device enabled intent.
- `tests/test_device_control_routing.py` already separates physical-device
  administration from live, simulated, and audition execution routes.

Those contracts were used as the base and were not duplicated wholesale.

## Superseded or deliberately omitted assertions

- Archived `device_muted` grammar and the rule that fleet mute blocks changing
  individual intent are superseded. Current controls are independent, with
  safety composed only at effective output.
- Exact `amixer` attempt lists, source-text checks, UI labels/icons, and
  browser presentation are implementation or presentation evidence, not the
  durable mute contract.
- Unrelated identity and heartbeat assertions found beside the archived mute
  guards remain out of scope for this stitch.

## Product and simulator impact

No product behavior changed. Production and simfleet already implement the
ratified positive-state model, so this stitch promotes that behavior into
living regression tests.
