# Proposal: typed event fields (contract v1.22)

**For Bob to ratify.** Drafted 2026-10-26 by Claude from the Kite Choir
workshop of the same day. Nothing implemented.

## In one paragraph

Today a `/e/*` event carries 0–3 floats (contract §3.2, v1.21). This proposal
replaces an event's `arity` and `defaults` with one **`fields` list**, where each
field is declared the way a parameter is — `name`, `kind` (`float`, `int`,
`toggle`, `enum`, `text`), range or options, default — and raises the limit to
**16 fields**. The wire carries each field with the OSC tag its kind already
uses for params; every engine instance receives them unchanged. This is a hard
break of event declarations (Bob, 2026-10-26: *"i don't care about the hard
break"*).

## Why

Kite Choir's layout (kite-choir-brains `docs/bopos-show-spec.md`, 2026-10-26)
needs:

```
/<target>/e/trig/play   <folder:s> [density:f] [gain:f] [fade:f] [play2end:i]
/all/e/point/<n>/start  <file:s>
/all/e/tilt/start       <folder:s>
/all/e/bg/start         <folder:s>
```

Strings and a five-field event. Nothing here names Kite Choir; any patch that
wants a sample path, a mode flag or a sixth number gets the same thing.

## This reopens two rulings

- Bob, 2026-07-27 (`.loom/tied/44-event-plane/instructions.md`): *"Event
  elements are free-form labeled floats. Arity 1/2/3."* Superseded: fields
  take any param kind, up to 16.
- Bob, 2026-07-28 (contract §15 v1.16): per-element `labels` retired; elements
  named only by position. Superseded by fields carrying a `name`, which follows
  from Bob's 2026-10-26 ask to declare events and params *"in the same or as
  similar way as possible"*. **Bob to confirm.**

The rest of the event plane (forward sync, the `"0"` sentinel, nodes
delivering without consulting the manifest) stays as ratified.

## 1. Manifest (§8)

An event declaration becomes:

```json
{"path": ["trig"], "name": "play", "dashboard": false,
 "fields": [
   {"name": "folder",   "kind": "text"},
   {"name": "density",  "kind": "float",  "min": 0, "max": 1, "default": 1,  "optional": true},
   {"name": "gain",     "kind": "float",  "min": 0, "max": 1, "default": 1,  "optional": true},
   {"name": "fade",     "kind": "float",  "min": 0, "max": 60000, "default": 50, "optional": true},
   {"name": "play2end", "kind": "toggle", "default": 0, "optional": true}
 ]}
```

- **A field is a param declaration without `path` and `dashboard`.** Same
  `name` grammar, same five kinds, same rules: `float`/`int` carry
  `min`/`max`/`default`; `toggle` a 0/1 default; `enum` its `options` and an
  index default; `text` an optional string default. The validator should share
  the code that checks params, so the two can't drift.
- **One addition to params: `optional`** (Bob, 2026-10-26), a boolean,
  default false — the same key and meaning as on `io_modules`, shown as an
  "optional" checkbox in the patch editor. Part 2 fills an omitted optional
  field from its `default` and rejects a message that omits a required one.
  Defaults follow the param rules for every field, so the dashboard's fire
  controls can prefill; an optional `text` field must carry one. Optional
  fields must all come after the required ones, since only trailing fields
  can be left off.
- **Names are unique within an event.**
- **`fields` may be empty or absent**: a zero-field event, today's momentary
  fire.
- **Up to 16 fields.**
- **`arity` and `defaults` are rejected loudly**, as the old `type` key is
  today. No shim (the `44/4-cue-retirement` precedent).

`enum` travels as its integer index, exactly as an enum param does; only the
dashboard and the reference tab read the labels.

## 2. Wire (§3.2)

```
/<selector>/e/<identity> <sharedTimeNs:s> [<e0> … <e15>]   leader → fleet
/e/<identity> [<e0> … <e15>]                               node → engine
```

Each field travels with the OSC tag its kind already uses for params (§8):
`float` → `f`; `int`, `toggle`, `enum` → `i`; `text` → `s`.

Limits, which the node enforces as it does today's identity and arity limits:

- **Text:** printable ASCII, no whitespace, 1–255 bytes. Whitespace is out
  because Pd turns an OSC string into a symbol, and symbols with spaces
  break when printed or saved. Kite Choir's naming rule already avoids them.
- **Int and toggle:** |value| ≤ 16 777 216 (2^24), the largest range a 32-bit
  float holds exactly — Pd stores every number as one (glean
  `pd-float-precision`). `toggle` only 0 or 1.
- **Float:** unchanged, rounded to six significant figures before sending.

**Nodes still don't consult the manifest.** A node accepts any well-formed mix
of `f`, `i` and `s` up to 16 fields and delivers it at the deadline. Checking
fields against declared kinds belongs to the sender: the dashboard's own fire
controls, and the input in part 2.

## 3. What breaks, and the mixed-fleet catch

**Manifests.** Every event declaration using `arity`/`defaults` becomes
invalid. In the local `patches/` copies as of 2026-10-26, three patches
declare events: `bonks-pd` (`bonk`, no fields), `demo-pd` (`snap`, no fields)
and `kc-test` (`target`, two fields). Deployed copies may differ, since
`patches/` is gitignored and devices get patches only by push (glean
`manifest-and-patch-distribution`). The node loads the manifest too
(`python/bopos.py`), so a node on new bopOS with an old-format patch would
see an invalid manifest — the `58/4-invalid-manifest-lockout` case. **Push the
migrated patches with the bopOS update**, and let the implementation stitch
convert the three local manifests.

**Wire.** Today's nodes **silently drop any event with a non-float field**
(`python/bopos.py:1617`, as of 2026-10-26). All-float events keep working on
old and new nodes; typed events reach only updated nodes. The update has to
reach every device before a patch relies on typed fields. **A release note
covers it; no dashboard warning** (Bob, 2026-10-26).

## 4. Engines

- **Pd:** `[oscparse]` turns `s` into a symbol and `i` into a float, so a
  patch receives `play m1s2/spot1/slice000 1 1 50 0` as a mixed list. Whether
  `pd/bopos~.pd`'s `/e/` path passes symbols through unchanged needs checking
  by Bob (glean `never-edit-pd`). If it needs an edit, it goes on
  `64-pd-edits-owed`.
- **SuperCollider and other engines** get standard OSC tags; nothing Pd-only.

## 5. What changes, by file

| Where | Change |
|---|---|
| `python/manifest.py` | `fields` validated by the param checks; `arity`/`defaults` rejected; limit 16 |
| `python/bopos.py` | accept `f`/`i`/`s` fields within the limits; `fire_event_to_engine` keeps each tag |
| `dashboard/osc_bridge.py` `fire_event` | send each field with its kind's tag |
| `tools/simfleet.py`, `tools/audition.py` | same parity as the node |
| Patch editor (`dashboard-patches.js`) | a field list edited like the param list: name, kind, range/options, default, an "optional" checkbox |
| Event fire controls (`show.js`, control surface) | the same control per kind that params use, labelled by field name |
| Patch manifests in `patches/`, tests | migrate `bonks-pd`, `demo-pd`, `kc-test` and fixtures to `fields` |
| `docs/OSC-CONTRACT.md` | §3.2, §8, §12 if needed, §15 entry |
| `docs/OSC-REFERENCE.md` | event examples with strings |

## 6. Verification

- **Headless** (`tools/run-tests.sh`): manifest validation, node parsing and
  limits, simfleet receipt of a typed fire, audition parity, editor journey.
- **Hardware, separate claim** (glean `hardware-claims`): Pd on the Finn Jet /
  Ciro Toast rig receives a symbol field from a scheduled event.

## 7. Decided, 2026-10-26 (Bob)

- One `fields` list; the hard break is fine.
- `enum` included; events and params declared as alike as possible.
- Up to 16 fields.
- Fields have names, like params — superseding the 2026-07-28 label
  retirement.
- An `optional` checkbox per field, as on `io_modules`.
- Mixed-version fleets: a release note only.

No questions left open. Ready for implementation stitches.
