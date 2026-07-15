# Nested patch parameter addresses — survey and design proposal

Status: **amended by Bob on 2026-07-15; remaining choices proposed for
ratification**. No implementation or OSC contract change has been made. Bob
explicitly requires the true nested OSC address to survive the engine boundary
for every engine; the earlier Pd-oriented dot-flattening proposal is rejected
and superseded here.

## Outcome of the survey

This is a **medium, bounded cross-cutting change**, not a one-file surgical edit.
The hierarchy itself is simple, but one flat string currently does five jobs:

1. manifest identity and validation;
2. fleet OSC address suffix;
3. engine OSC address suffix / PD route selector;
4. dashboard value and preset key;
5. display label and one-level `group` presentation.

Those jobs need to be separated deliberately. The expected implementation is
around ten production files plus focused regression updates and corresponding
routes in patches that adopt nested parameters. It does not require new ports,
a new message plane, a dashboard state schema bump, or a rewrite of the
framework `[bopos]` abstraction.

The smallest coherent approach is:

- keep `name` as the leaf name;
- add an optional structural `path` array to the manifest;
- use the slash-joined qualified name as the public identity and stored key;
- send that hierarchy literally on both the fleet wire and engine surface;
- let each engine's OSC parser expose the path as its native hierarchy.

Example:

```json
{
  "path": ["guitar", "reverb"],
  "name": "gain",
  "type": "f",
  "min": 0,
  "max": 1,
  "default": 0.75,
  "facilitator": true
}
```

This declaration has:

| Surface | Canonical form |
|---|---|
| Manifest components | `path: ["guitar", "reverb"]`, `name: "gain"` |
| Public parameter identity / stored key | `guitar/reverb/gain` |
| Fleet, one Seat | `/<id>/p/guitar/reverb/gain <value>` |
| Fleet, every Seat | `/all/p/guitar/reverb/gain <value>` |
| Engine surface | `/p/guitar/reverb/gain <value>` |
| Pure Data after `[oscparse]` | `p guitar reverb gain <value>` |
| Pure Data `bopos-param` message | `guitar reverb gain <value>` |
| Dashboard tree | `guitar` → `reverb` → `gain` |

An existing `{"name":"gain", ...}` declaration has an empty path and remains
exactly `gain`, `/<id>/p/gain`, `/p/gain`, and `gain <value>` in Pure Data.

## Why the path should be separate

Putting slashes inside `name` would overload a leaf label with structure and
would make validation, editor rename warnings, and engine delivery ambiguous.
It would also tempt consumers to repeatedly split and normalize an address-like
string.

A `path` array makes segment boundaries explicit in JSON, needs no escaping,
keeps existing flat manifests valid verbatim, and permits the same leaf name in
different branches:

```json
{"path":["instrument","marimba"], "name":"gain", ...}
{"path":["fx","reverb"],          "name":"gain", ...}
```

Uniqueness is checked on the full qualified identity, not on `name` alone.

## Fleet and engine address rules

### Fleet surface

The canonical controller-to-fleet grammar becomes:

```text
/<selector>/p/<segment>[/<segment>...] <values...>
```

`selector` remains `all` or one numeric Seat/device id. Selector matching is
unchanged. `/all` changes only the selection scope; it does not collapse or
reinterpret the parameter path.

### Engine surface

The relay strips only the fleet selector and preserves every patch parameter
segment:

```text
/<selector>/p/guitar/reverb/gain  ->  /p/guitar/reverb/gain
```

The framework still does not interpret or compose parameter values. This is
selector removal only and preserves the seam law. It also means external tools,
SuperCollider, Pure Data, and future engines all observe the same true OSC path
after the fleet selector.

### Engine-agnostic rule

The engine boundary has one OSC spelling, independent of engine type:

```text
/p/<segment>[/<segment>...] <values...>
```

`bopos.py` and the audition relay may remove only the bopOS fleet selector.
They must not flatten, encode, rename, or otherwise adapt the parameter path for
Pure Data, SuperCollider, openFrameworks, or any other engine. Each engine uses
its native OSC address matching/parsing to consume the identical message.

This is the same engine-agnostic boundary principle already used for `/id`,
`/os/master`, `/pt`, `/cue`, and `/notify`: topology may differ, but the engine
surface does not.

## Validation and escaping

- `name` and every `path` entry use the existing segment grammar
  `[A-Za-z0-9_-]+`.
- `path` is optional. When present it is an array of non-empty strings.
- Empty segments, `.`, `..`, slashes, dots, whitespace, OSC pattern characters,
  and percent-encoded substitutes are invalid.
- No escaping or normalization exists. A manifest contains the exact canonical
  segments and comparison is case-sensitive.
- The full qualified identity must be unique within a manifest. Duplicate leaf
  names in different paths are legal.
- A conservative implementation cap should keep the qualified address at no
  more than eight segments and 255 ASCII bytes. This is an authoring guard, not
  an OSC transport limitation, and can be adjusted at ratification.

Rejecting special syntax is preferable to defining an escaping dialect that all
manifest, Python, JavaScript, OSC, PD, SC, persistence, and future sequencer
consumers would need to implement identically.

## Dashboard model, persistence, and catch-up

Dashboard-owned values should be keyed by the canonical slash-joined identity:

```json
"params": {
  "instrument/marimba/gain": 0.7,
  "fx/reverb/gain": 0.35
}
```

JSON object keys already allow slashes, so Seat state, presets, and venue copies
need no enclosing schema change. The dashboard should centralize qualification
in one helper rather than continuing to use `declaration.name` throughout.

Catch-up remains declaration-driven:

1. a node returns its manifest through `/os/params`;
2. the dashboard qualifies every declaration;
3. it fills a missing canonical key from the declaration default;
4. it sends each stored value back on the full nested fleet address;
5. the node relay strips only the selector and delivers the same nested path.

Preset save/load uses the same canonical keys. `/all` authoring updates the key
for every targeted Seat before emitting one `/all/p/...` message, preserving the
current full-state/idempotent rule.

The node's generic engine `/store` filesystem-backed key API is unrelated to
dashboard patch-parameter snapshots and does not need to accept slashes.

## Grouping and tree rendering

`path` is the authoritative hierarchy. Each parent segment renders as a nested
section and `name` renders as the leaf control.

The existing `group` field is presentation-only and currently supplies one
flat heading in the patch editor. For compatibility:

- existing flat declarations with `group` retain their current presentation;
- new nested declarations use `path` and should not also set `group`;
- the editor should make `group` and `path` mutually exclusive and offer an
  explicit conversion rather than silently treating a group as a wire path.

This matters because automatically converting `group: "mix"` into `path:
["mix"]` would silently change `/p/gain` to `/p/mix/gain` and break current
patches and presets.

The Dashboard live surface and facilitator compatibility page should render the
same tree data. A compact card may collapse parent branches, but it must not
discard the qualified identity when binding a control.

## Editor CRUD and identity changes

The manifest editor gains an editable path control, presented to the author as
slash-separated text but serialized as an array. `name` remains the leaf field.
The live test panel sends the qualified public identity.

Changing either `path` or `name` changes parameter identity. It is treated as a
remove plus add:

- unchanged qualified identities keep their dashboard values;
- new identities begin at their declared default when one exists;
- removed identities are pruned from current Seat values when the revised
  manifest schema is staged;
- historical preset entries may remain inert until that preset is deliberately
  resaved, but preset load must send only identities declared by the active
  manifest;
- editor warnings show the old and new qualified addresses; these are also the
  exact engine addresses after `/p`.

There is no safe automatic move heuristic once duplicate leaf names are legal.
If preserving values across a move becomes important, that should be an explicit
editor migration action, not an inferred zip of removed and added rows.

## Pure Data boundary

The current `[bopos]` abstraction receives OSC, applies `[oscparse]`, then
`[route p]`, and publishes the remaining list on `bopos-param`. It already
preserves a nested address correctly. Sending `/p/track1/fx/distortion 0.5`
produces:

```text
[oscparse]       -> p track1 fx distortion 0.5
[route p]        -> track1 fx distortion 0.5
```

A consuming patch can route the hierarchy natively:

```text
[r bopos-param]
|
[route track1]
|
[route fx]
|
[route distortion]
```

Existing `[route gain]` objects keep working because an empty manifest path
produces the unchanged `/p/gain` engine address. Patches that declare nested
parameters intentionally add or change their downstream route objects. Under
the repository ownership rule, those `.pd` edits are Bob's work and are recorded
in `.notes/pd-edits-for-bob.md`.

No change appears necessary in `pd/bopos.pd` itself: it already performs the
required OSC parsing and only removes the reserved `p` plane. If a future helper
abstraction makes nested route trees more convenient, that is additive patch
authoring ergonomics rather than a protocol requirement.

Pure Data is one example of the engine-agnostic rule, not the reason for the
wire shape. SuperCollider and other engines receive the identical nested
`/p/...` address and bind it with their native OSC matchers.

## Concrete implementation seams

### Must change

- `python/manifest.py`: validate path segments and uniqueness; expose one
  canonical qualification helper.
- `python/relay.py`: accept a variable-length patch tail and preserve it after
  selector removal while keeping `/os/master` strictly three-part.
- `python/bopos.py`: stop rejecting nested patch messages at the current
  `len(parts) == 3` gate.
- `tools/audition.py`: accept nested patch addresses before using the shared
  relay shaper.
- `tools/simfleet.py`: compare and retain canonical qualified identities rather
  than one `member` segment.
- `dashboard/osc_bridge.py`: send, default, persist, and catch up by qualified
  identity.
- `dashboard/server.py` and `dashboard/state.py`: use qualified keys for live
  values, patch-schema reset, presets, editor state, and safe schema pruning.
- `dashboard/static/js/dashboard.js`: path CRUD, nested editor controls, and
  qualified WebSocket payloads.
- `dashboard/static/js/facilitator.js`: nested promoted controls and qualified
  payloads. This will overlap the waiting `12-dashboard-live-controls` work and
  should land first or be explicitly folded into it.
- `docs/OSC-CONTRACT.md`, `README.md`, dashboard/patch starter documentation,
  and focused verification artifacts.

### Does not need to change

- UDP ports, selectors, `/os/params`, heartbeat, sync, cue, point, distribution,
  or assignment wire shapes;
- `python/store.py` and the engine-owned `/store` API;
- installation/venue outer JSON schema;
- current flat patch manifests or their stored flat keys;
- `pd/bopos.pd` itself, unless audible verification exposes an unexpected parser
  issue.

The demo manifests can remain flat as compatibility fixtures. A new nested test
fixture should exercise duplicate leaves in separate branches. Any shipped Pd
fixture that adopts that nested declaration needs corresponding nested `[route]`
objects, performed by Bob rather than an agent.

## Verification shape

An implementation should prove at least:

1. manifest validation accepts duplicate leaves in different paths and rejects
   duplicate qualified identities or invalid segments;
2. both OSC libraries already in use round-trip
   `/all/p/guitar/reverb/gain` unchanged (surveyed successfully with
   `python-osc` and `pyOSC3`);
3. production and audition relays deliver the same
   `/p/guitar/reverb/gain` address and preserve all values;
4. simfleet applies and logs two distinct `gain` leaves;
5. dashboard edit, individual, `/all`, catch-up, preset save/load, same-patch
   schema revision, and reconnect paths use canonical slash keys;
6. flat `/p/gain` behavior and existing manifests remain byte-for-behavior
   compatible;
7. the Dashboard and facilitator views render the same nested declaration tree;
8. an audible Pd gate proves `/p/track1/fx/distortion 0.5` becomes
   `track1 fx distortion 0.5` on `bopos-param` and reaches a nested route tree.

## Recommended implementation split after ratification

1. **Contract/model/relay:** manifest qualification, validation, production and
   audition relay, simfleet, contract wording, browser-free wire verification.
2. **Dashboard state/editor:** canonical stored keys, catch-up, schema pruning,
   presets, editor CRUD/tree rendering, focused backend and browser verification.
3. **Live Dashboard integration:** promoted all-Seat and per-Seat nested controls,
   ideally coordinated with `ui-tabs/.../12-dashboard-live-controls` to avoid
   building that surface twice.

This keeps each stitch independently testable and isolates the only significant
migration risk—the dashboard's stored-key and preset behavior—from the simple
OSC relay change.

## Bob's engine-surface ruling

Bob, 2026-07-15:

> why dot separated to pd? i would much prefer make those changes to the pd
> files and maintain true osc. via osc i need to be able to send something like
> /all/p/track1/fx/distortion 0.5 - and pick that up in pd via osc parse as an
> actual osc message.

Bob added that Pd is not the only engine, so preserving standard OSC is the
governing engine-agnostic requirement.

Applied as a binding amendment: dot-flattening and all engine-specific address
adaptation are rejected. The nested path is preserved from
`/<selector>/p/...` to the one common engine `/p/...` surface. Pure Data receives
the real parsed hierarchy; every other engine receives the exact same OSC
address.

## Remaining ratification questions

1. Ratify `path` as a separate array plus leaf `name`, rather than allowing
   slash-separated names?
2. Ratify canonical slash-joined dashboard/preset keys and remove-plus-add
   semantics for later path moves?
3. Ratify `path` as authoritative and `group` as flat-only compatibility
   presentation, with no implicit group-to-path migration?
