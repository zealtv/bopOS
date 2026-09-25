# 1-resolution-authority

**Status:** ready · first in queue
**Goal:** the Show warning panel reports only presets that will actually play
differently. Provenance becomes a notice the panel doesn't show.

Read the goal first — especially why resolution is never gated on the hash.

## Today

- `show_reference_warnings(show, patch_fingerprints, schema_fingerprints)` in
  `dashboard/show_model.py` emits one warning per message × up to two codes.
- `Dashboard.show_warnings()` (`dashboard/server.py`) feeds it only fingerprints;
  preset bodies are never read.
- `show.js` (the `.show-warning-list` render) maps the array straight to `<p>`
  and drops the `step_uid` / `message_uid` the server sends.
- `dashboard/shows/test.json` has the same preset in two steps — the repro.

## Change

**Model** (`show_model.py`) — new signature, still data-only (no IO, no
`preset_store` import):

```python
def show_reference_warnings(show, patch_state):
    # patch_state: {patch: {"fingerprint", "schema",
    #   "presets": {slug: {"verdicts": {identity: {"status", "reason"?}}, "error"}}}}
```

| emitted | condition | code | severity |
|---|---|---|---|
| once per patch | fingerprint is None | `missing_patch` | warn |
| once per patch | schema is None | `missing_schema` | warn |
| once per (patch, slug), with identity list + `refs` | any verdict `dropped` | `preset_dropped` | warn |
| once per (patch, slug), with identity list + `refs` | any verdict `clamped` | `preset_clamped` | warn |
| per message | fingerprint ≠ reference | `patch_drift` | notice |
| per message | schema ≠ reference | `schema_drift` | notice |

Order: warnings in first-encounter order, then notices. `show_target_warnings`
gains `"severity": "warn"` and is otherwise unchanged. Add a comment explaining
why resolution isn't gated on the hash.

**Server** — split out `show_reference_state()`: walk the show once for
`(patch, slug)` pairs (`show_model.preset_message_parts`); per patch, the
existing fingerprint + `schema_fingerprint(live_control_manifest(patch))`; per
slug, `preset_store.read` → `resolve_entries`, catching `PresetStoreError` into
`{"verdicts": {}, "error": str(e)}`. `show_warnings()` becomes target warnings +
reference warnings. Reads are stat-cached; no new broadcasts or call sites.

**Client** — filter out `severity === "notice"` before rendering the panel.
Missing severity = warn, so installation notices keep working. `3` consumes the
notices.

Payload shape: panel warnings carry `refs: [{step_uid, message_uid}, …]` and no
scalars; notices carry scalar `step_uid` / `message_uid`.

## Bob should then see

- `.pd` edited, manifest untouched → **panel empty**
- param added → **panel empty**
- param removed / range narrowed → **one line** naming the parameters

## Done when

- `tests/test_show_model.py`: existing drift test re-pointed (+ `severity ==
  "notice"`); new **anti-fan-out** test (3 messages, one dropped entry → one
  `preset_dropped` with 3 refs, three notices); new **added-a-param** test
  (schema differs, all applied → zero warns).
- `tests/test_preset_application.py`: update
  `test_show_load_warnings_compare_both_reference_fingerprints`; add a sibling
  that removes/narrows `gain` and expects `preset_dropped` / `preset_clamped`.
  This is the most valuable new test — store, manifest and resolution together.
- `tests/test_preset_store.py` covers "new declaration → all entries still
  `applied`" (add if missing).
- `tools/run-tests.sh fast` green; `tests/verify_show_reference_foundation.py`
  still passes.
