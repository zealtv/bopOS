# Decisions — 05-store-and-foundations

Date: 2026-07-29.

## Store boundary

- `dashboard/preset_store.py` owns the complete durable file boundary. Its
  public records keep the persisted document unchanged under `document` and
  carry `slug` plus `revision` beside it, so transport metadata never leaks
  into authored JSON.
- Revisions are `sha256:<hex>` over the exact file bytes. They are stable
  across process restarts, change on every material external edit, and make
  compare-and-swap independent of filesystem timestamp resolution.
- The validation cache is keyed by absolute preset path and the stat signature
  `(device, inode, mtime_ns, ctime_ns, size)`. Reads return deep copies.
  Save/delete invalidate the entry; an external change misses by signature.
- Invalid JSON remains visible in `list()` with its error and content revision.
  It is refused by `read()` (therefore by apply), but can still be explicitly
  deleted using that revision. Invalid data is never converted to an empty
  sparse preset.

## Slugs and conflicts

The existing transform is retained exactly: strip the display name, replace
`[^\w-]` with `-`, then truncate to 48 characters. The display name remains
authored in the document. Creating a name whose slug is already owned by a
different display name raises `PresetConflictError`; overwriting the same
display name requires the last-read content revision. A revision supplied for
a now-missing file is also a conflict.

## Entry validation and drift

The store accepts only non-empty argument lists containing one finite scalar,
one text string, or a form that the existing `paramgen.parse_message` parses
specifically as `lfo` or `loop`. Fade forms, `stop`, `morph`, malformed
generators, booleans and non-finite numbers are refused.

The pure resolver returns resolved params, a verdict per identity, and
applied/clamped/dropped counts. It drops absent identities and incompatible
text/generator category changes, and clamps scalar, LFO-envelope, and loop
destination values to the current effective range.

The ratified file shape stores argument lists but no per-entry source kind.
Consequently a scalar alone cannot reveal whether it was captured from
`float`, `int`, `toggle`, or `enum`; exact changes within that numeric family
are not inferable from a later file. The resolver treats numeric scalars as
numeric-compatible and uses the current declaration/range, while still
dropping every kind change the serialized representation can prove. This is
the only behavior that preserves both the ratified file shape and the
non-blocking range-narrowing rule; the limitation is explicit in the helper's
docstring rather than hidden in application code.

## Host-only policy

`python.identity.HOST_ONLY_DIRS` plus `is_host_only(relative_path)` is the one
named policy. Callers supply paths relative to a patch root:

- the identity walk removes `presets/` before descent;
- hash-cache load/save/seed refuse or purge host-only entries;
- fetch prune preserves a destination's host-authored presets;
- `file://` source enumeration never transfers them;
- the `/patches` static mount strips its patch-name segment and returns 404
  before lookup.

`_patch_fetch` still copies an existing patch wholesale into staging, and
`_reject_symlinks` still examines `presets/`. Tests cover both intended facts.
