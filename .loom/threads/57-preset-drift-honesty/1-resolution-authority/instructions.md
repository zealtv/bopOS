# 1-resolution-authority

The Show tab's drift verdict comes from a hash. Make it come from the per-entry
resolution §8.1 names as the authority, and demote the provenance fact to a
notice.

**This stitch ships alone and resolves the reported symptom.** Read the goal
instructions first — particularly "the correction that shapes every stitch",
which is why resolution is *not* gated on the hash.

## Measured starting state

`dashboard/show_model.py:315-357`:

```python
def show_reference_warnings(show, patch_fingerprints, schema_fingerprints):
    ...
            elif current_patch != authored_patch:
                message_warnings.append({
                    "code": "patch_drift",
                    "message": f'Patch "{patch}" has changed since this preset message was authored.',
                })
```

One warning object **per message** × up to two codes. `dashboard/server.py:1428`
`show_warnings()` feeds it `identity.fingerprint(patches/<name>)` and
`preset_store.schema_fingerprint(manifest)` and nothing else — the preset
bodies are never read. `dashboard/static/js/show.js:542-547` maps the array
straight to `<p>` with no dedupe, and **discards** the `step_uid` /
`message_uid` the server already ships.

`dashboard/shows/test.json` holds the same `/preset/bonks-pd/medium-bonks` in
two steps, which is the two-line pair Bob saw twice.

## The change

### Model — `dashboard/show_model.py`

```python
def show_reference_warnings(show, patch_state):
    """Derived preset-reference warnings and provenance notices.

    `patch_state` maps patch name -> {
        "fingerprint": "<64hex>" | None,     # current patch content fingerprint
        "schema": "sha256:<hex>" | None,     # current manifest schema fingerprint
        "presets": {slug: {"verdicts": {identity: {"status": …, "reason"?: …}},
                           "error": str | None}},
    }
    """
```

Data-only: no `preset_store` import, no IO. The module stays as testable with
hand-written dicts as it is today, which is why this shape is preferred over
injecting a resolver callable.

Emission rules, walking steps then messages exactly as now:

*Collected per patch, emitted once:*

| condition | code | severity |
|---|---|---|
| `fingerprint is None` | `missing_patch` | `warn` |
| `schema is None` | `missing_schema` | `warn` |

*Collected per (patch, slug), emitted once, carrying the identity list:*

| condition | code | severity |
|---|---|---|
| any verdict `status == "dropped"` | `preset_dropped` | `warn` |
| any verdict `status == "clamped"` | `preset_clamped` | `warn` |

*Emitted per message, scalars kept:*

| condition | code | severity |
|---|---|---|
| `fingerprint != reference["content"]["fingerprint"]` | `patch_drift` | `notice` |
| `schema != reference["schema"]` | `schema_drift` | `notice` |

Emit the collected warnings in **first-encounter document order**, then the
notices, so the panel is deterministic.

`show_target_warnings` (`:298`) is unchanged except that it stamps
`"severity": "warn"` on each warning, so the client's filter never has to
infer.

**Put a comment on the function saying why resolution is not gated on the
schema hash.** The next reader will try to add the gate back as an
optimisation; the goal instructions explain what that costs.

### Server — `dashboard/server.py:1428`

Split the existing body:

```python
def show_reference_state(self):
    """Current fingerprints plus per-preset resolution for every referenced patch.

    Resolution is unconditional: it answers whether stored entries still land,
    which the schema hash cannot, and which re-stamping a reference must not
    be able to suppress (contract v1.17 §8.1 — the fingerprint is the fast
    check, the per-entry resolution is the authority).
    """
```

Walk `self.show` once collecting `(patch, slug)` from
`show_model.preset_message_parts`. Per patch: `identity.fingerprint(root)` and
`preset_store.schema_fingerprint(self.live_control_manifest(patch))`, exactly
the guarded code that is there today. Per slug: `self.preset_store.read(patch,
slug)` → `preset_store.resolve_entries(record["document"], manifest)`, catching
`PresetStoreError` into `{"verdicts": {}, "error": str(error)}`.

`show_warnings()` then collapses to:

```python
return (show_model.show_target_warnings(self.show, self.state.data.get("groups", {}))
        + show_model.show_reference_warnings(self.show, self.show_reference_state()))
```

Cost is fine: `PresetStore._read_path` is stat-signature cached
(`preset_store.py:305-334`), the files are small, the number of distinct
`(patch, slug)` pairs in a show is small, and `identity.fingerprint()` over the
whole patch directory already runs here per call and is by far the more
expensive of the two. **No new broadcast and no new call sites** — the six
existing triggers (`server.py:299`, `1004`, `1011`, `1023`, `1272`, `1417`,
`1485`, `1502`) are untouched.

### Client — `dashboard/static/js/show.js:542`

```js
const warnings = [...notices, ...showWarnings.filter(w => w.severity !== "notice")];
```

Missing `severity` means warn, which keeps the installation `notices` (plain
strings wrapped as `{message}`) working unchanged. The panel keeps
`role="status"`, keeps target warnings, keeps notices. Nothing else in this
file reads warning fields today, so there is no other consumer to migrate.
`3-drift-marks` is what consumes the filtered-out notices.

## Payload shapes

```json
{"code": "preset_dropped", "severity": "warn",
 "patch": "bonks-pd", "slug": "opening",
 "identities": ["reverb/mix", "delay/time"],
 "message": "Preset \"opening\" on patch \"bonks-pd\": 2 stored parameters are no longer declared and will not be applied — reverb/mix, delay/time.",
 "refs": [{"step_uid": "a0000001", "message_uid": "b0000001"},
          {"step_uid": "a0000004", "message_uid": "b0000009"}]}

{"code": "patch_drift", "severity": "notice", "patch": "bonks-pd",
 "step_uid": "a0000001", "message_uid": "b0000001",
 "message": "Authored against an earlier version of patch \"bonks-pd\"."}
```

Heterogeneous **deliberately**, and the split is principled rather than
incidental. A panel paragraph needs *per-cause* granularity, so it takes `refs`
and drops the scalars — keeping a scalar alongside a list would silently anchor
every client to the first ref and be a lie by omission. An anchored mark needs
*per-message* granularity, so it keeps the scalars; it never reaches the panel,
so it produces no wall. `show_target_warnings` keeps its scalars for the same
reason: each of its warnings is genuinely about one message's target.

## What Bob should see afterwards

* edited `.pd`, manifest untouched → schema identical, all entries applied →
  one `patch_drift` **notice** → **panel empty**
* added a param → schema differs, all entries still applied → one
  `schema_drift` notice → **panel empty**
* removed a param or narrowed a range → **one** panel line naming the
  identities

## Verify

`tests/test_show_model.py` — the existing test at `:317-336` pins
`["patch_drift", "schema_drift"]` from one message and asserts both carry
`message_uid == "b0000001"`. Both assertions **survive verbatim**; only the
call site's argument changes, plus a new `severity == "notice"` assertion. That
it re-points rather than needing a rewrite is a good sign the shape is right.

Add:

* **the anti-fan-out pin** — two steps, three messages, all referencing the
  same drifted patch with one entry dropped: exactly one `preset_dropped` with
  `len(refs) == 3`, and exactly three `patch_drift` notices.
* **the stop-lying pin** — schema differs, every verdict `applied` → zero
  entries with `severity == "warn"`. This is Bob's added-a-param case as an
  executable claim, and it is the assertion this whole stitch exists to make
  true.

`tests/test_preset_application.py:203`
(`test_show_load_warnings_compare_both_reference_fingerprints`) drives the real
`Dashboard.show_warnings()` against a real saved preset (`{"gain": [0.5]}`) and
pins `["patch_drift", "schema_drift"]`. Update to the notice severities, and
add a sibling that narrows or removes `gain` in the fixture manifest and
asserts a `preset_clamped` / `preset_dropped` naming `gain`. **This is the
highest-value new test in the thread** — the only one exercising store,
manifest and resolution together.

`tests/test_preset_store.py` — no change expected, but confirm
`resolve_entries` already covers "a new declaration appears, every stored entry
still resolves `applied`". Add it if not; this stitch's correctness rests on it.

`tools/run-tests.sh fast` green. `tests/verify_show_reference_foundation.py:219`
asserts on `.show-warning-list` via the target-warning path, which does not
move — confirm it still passes rather than assuming it.
