# Decisions — fetch convergence promotion

## Promoted assertions

| Living surface | Durable properties | Archived sources inspected |
|---|---|---|
| `tests/test_fetcher.py` | safe relative paths; exact transfer-manifest schema; verified file convergence; matching-byte skips; stale-file pruning; no `.part` residue; staged valid patch replacement; invalid patch preserves current bytes; unsafe/git/symlink landing rejection | `fetch-landing/test_fetch_landing.py`; `dist-2-node-side/verify_dist2_node_side.py` |
| `tests/test_node_fetch_dispatch.py` | valid dispatch; invalid-slot terminal error; identical-generation coalescing; honest queued/fetching phase for late requesters; unrelated framework dispatch remains responsive; active-patch stop → byte convergence → restart → terminal-success ordering | `fetch-landing/test_fetch_landing.py`; `dist-2-node-side/verify_dist2_node_side.py` |
| `tests/test_simfleet_fetch.py` | per-device serialization, independence across devices, queued/fetching/terminal parity, and identical in-flight requester coalescing | `dist-2-node-side/verify_dist2_node_side.py` |

The tests use production `fetcher.py` and `bopos.py` helpers and simfleet's real
queue methods. They assert phases and ordering by property, not complete
refresh-message lists or UI copy.

## Existing living coverage retained

- `tests/verify_device_patch_targeting.py` already proves that a device pin
  converges only the target, fleet deploy leaves pins intact, follow-fleet
  reconverges, and the registry survives reload.
- `tests/test_device_patch_override.py` owns desired patch/fingerprint
  persistence.
- `tests/test_node_fetch_dispatch.py` already owned the incoming asset-slot
  dispatch seam.

Those tests were not duplicated. Desired/reported fingerprint classification
remains in child `05`.

## Not promoted from this archive slice

- HTTP Range-resume mechanics were useful delivery evidence but are an
  implementation strategy beneath the durable verified-byte outcome. The
  living test uses deterministic local-file convergence.
- Exact dashboard refresh request lists, old contract-version literals,
  retired samplepack paths, removed verbs, UI sentences, and fake state API
  shapes are authoring evidence.
- Full patch-switch UI, real broadcast, and late-node journeys remain covered
  at integration level where still living; archived versions were not copied.
- A simulator can prove queue ordering and state transitions, not Raspberry Pi
  filesystem, SD-card, Wi-Fi, process scheduling, or first-transfer timeout
  behavior.

## Product and simulator impact

No product behavior changed. Simfleet already modeled the durable per-device
serialization contract, so the stitch promoted tests against it rather than
altering it.
