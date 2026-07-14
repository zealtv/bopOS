# Patch editor design — ratified (pe-0)

Ratified design record for the dashboard's patch-editor tab: a composer-helper
mode built on the managed-audition machinery. One supervisor mode enum
(`off | simulate | edit`, mutually exclusive); `audition.py --edit` runs one
PD instance **with the GUI** as the live editing surface; a manifest-driven
param panel sends `/p/*` over loopback (the relay's no-validation pass-through
means declared-on-save params flow with zero restarts); a form-based manifest
editor covers params and the new `cues` field; New patch scaffolds a manifest
plus a stub `main.pd` copied verbatim from a Bob-provided template; points get
a session-only one-element mini spatial setup; master is the only global.
Contract v1.4 carries the cues amendment alone — the [bopos]+[bopos.out~]
single-object merge keeps its own later revision.

Bob's verbatim rulings on the four open questions (and the earlier
sim-XOR-edit and shared-infrastructure rulings) are quoted in the proposal's
final section. Implementation splits into pe-1..4 under the `patch-editor`
thread.

## Source

Written for `patch-editor/pe-0-design-proposal` during the 2026-07-14 staging
session with Bob (same session that created the `fleet-patch`, `ui-tabs`, and
`patch-editor` threads). Ratified in-session the same day.

## Related

- `docs/OSC-CONTRACT.md` §3.1, §4.2, §8
- `.lore/items/2026-07-13-composer-experience-brain-dump`
- `.loom/tied/preview-0-channel-model-spike` (bopos.out~ internals)
- `tools/audition.py`, `python/relay.py`, `dashboard/server.py`
  (start/stop_simulation)

## Tags

- proposal
- decision-record
- patch-editor
- dashboard
- manifest
