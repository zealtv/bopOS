# 2-reference-schema-meaning

`reference.schema` is stamped with one meaning and compared with another. Rule
which one it is, and make both sides agree.

Small, independent of `1`, and a **hard prerequisite for `4-accept-restamp`** —
without it the Accept button is unstable in a way no amount of UI care fixes.

## Measured starting state

**The stamp** — `dashboard/static/js/show.js:691-697`:

```js
function presetReference(patch, entry) {
  const content = patchCatalogItem(patch);
  if (!content?.fingerprint || !entry?.schema) return null;
  return {
    content: {name: patch, fingerprint: content.fingerprint},
    schema: entry.schema,
  };
}
```

`entry` comes from `preset_catalog`, and `preset_store.list` sets
`"schema": document["schema"]` (`dashboard/preset_store.py:364`) — **the schema
the preset file was saved against.**

**The comparison** — `dashboard/show_model.py:347`:

```python
elif current_schema != authored_schema:
```

where `current_schema` is `preset_store.schema_fingerprint(manifest)`
(`server.py:1449`) — **the patch's current schema.**

Two different facts, one field.

## What this costs today

Pick a preset that is itself drifted — the dropdown already shows it with `*`
via the `drift` flag computed at `server.py:1881-1886` — and the **brand-new**
show message warns `schema_drift` the instant it is authored. There is nothing
the operator can do in the Show tab to clear it. That is a live defect
independent of everything else in this thread.

## What it would cost `4`

Accept stamps the *patch's current* schema, which is a value
`presetReference()` would never produce. So the next time anyone touches the
preset dropdown for that message, it gets stamped back to the preset file's
saved schema and the warning returns — an acknowledgement silently undone by an
unrelated interaction.

## The ruling

**`reference.schema` means "the schema this message was authored against"** —
the reading the warning already assumes. Make the stamp agree.

Minimal change: `preset_catalog()` (`server.py:1863-1888`) also carries the
patch's **current** schema fingerprint, and `presetReference()` stamps that.

Keep `entry.schema` and the existing `drift` flag exactly as they are. That is
a **different fact** — preset file versus current manifest — and the inspector
line it drives (`show.js:715`, "preset schema differs from the current patch")
is correct and stays. Do not collapse the two; naming them apart in
`decisions.md` is part of this stitch's job, because the next reader will see
two schema fingerprints in one payload and assume one is redundant.

Where to put the current fingerprint is your call — a sibling key on the
per-patch catalog value, or repeated on each entry. Prefer whichever leaves
`preset_store.list`'s per-entry shape untouched, since that shape is also read
by the Control surface.

## Verify

* `tests/test_preset_application.py` or the nearest module that already builds
  a real `Dashboard` with a real preset: author a reference against a preset
  whose saved schema differs from the current manifest, and assert
  `show_warnings()` returns **no** `schema_drift` for it. That is the defect,
  stated as a test, and it should fail before the change.
* Confirm the Control-surface `drift` flag and the inspector's "preset schema
  differs from the current patch" line are unaffected — one assertion each is
  enough, but make them explicit so a later reader sees the two facts were
  kept apart on purpose.
* `tools/run-tests.sh fast` green, plus
  `tests/verify_preset_control_surface.py` since `preset_catalog`'s payload
  shape is what it reads.
