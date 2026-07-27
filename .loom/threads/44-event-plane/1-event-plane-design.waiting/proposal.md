# Event plane and `kind` grammar — proposal

**Status:** written 2026-07-27, awaiting Bob's ratification. Wire-visible, so
this is an OSC-contract revision (**v1.14**), not an addition by convention.

Bob's six rulings from the 2026-07-27 session are inputs, not questions:
every event forward-syncs (one fire button, global lead `0` is sync-off); an
explicit `kind` field as a hard break; a cue is a zero-element event and
`/cue` is deleted with no shim; event elements are free-form labeled floats;
presets do not capture events; no event automation is designed.

Six choices below are marked **[BOB]** — they are genuine forks, not
re-openings of the above.

---

## 1. The `kind` grammar

### 1.1 What replaces what

Today a param declares `type: "i" | "f" | "s"`, and an enum is inferred from
the presence of `options` on an `"i"`. A toggle is not expressed at all — it
is an `"i"` that happens to have `min: 0, max: 1`, which every surface has to
re-derive. Replace both with one explicit field:

| `kind` | wire | fields | notes |
|---|---|---|---|
| `float` | float | `min`, `max`, `default` | today's `"f"` |
| `int` | int | `min`, `max`, `default` | today's `"i"` |
| `toggle` | int `0`/`1` | `default` | `min`/`max` **derived** `0`/`1`; authoring them is invalid |
| `enum` | int index | `options`, `default` | `min`/`max` derived `0`…`n-1` (unchanged from what shipped) |
| `text` | string | `default` (optional) | today's `"s"` |

`type` is **removed**, not retained beneath `kind` — carrying both is exactly
the redundancy that produced the "is this an enum?" derivation in the first
place. The wire encoding is a property of the kind, and the one place that
needs it (OSC arg tagging) can map from `kind` in a single table.

Nothing about the *wire* changes for any of these five. A toggle sends `0`/`1`
as it always did; an enum sends its index as it always did. This is a
declaration-grammar break, not a protocol break.

### 1.2 Events stay a separate top-level list — recommended

The tempting move is one `params` list with `kind: "event"` alongside the
other five. **Recommend against it**, for one concrete safety reason:

Params are replayed. `replay_live_params`, per-Seat replay on reconnect, and
durable offline/unbound values all iterate declared params and re-send their
last value. Events are momentary and must **never** be replayed — firing a
stored event at a device that just came back online is an output-safety
defect of the same family as the mute bug in thread 29. If events live in
`params`, every one of those loops needs a `kind != "event"` filter added, and
the failure mode of forgetting one is silent and physical.

Keeping `events` a separate list makes every existing param loop correct by
construction. It also gives the control panel's ruled parameters/events
sections for free, and makes `8-manifest-reorder`'s "no cross-section drags"
constraint structural rather than enforced.

So: `params` entries carry `kind` (one of the five above); `events` entries
are events by virtue of the list and carry no `kind` field. Identity
uniqueness is already enforced across both lists.

### 1.3 The sweep this forces

- `python/manifest.py` — `PARAM_TYPES` → a `PARAM_KINDS` table; the `options`
  block moves under `kind == "enum"`; `toggle` gains derived `min`/`max`
  mirroring the enum treatment; the `type` key becomes **invalid** (reject
  loudly, the way `role` is rejected — a silently-ignored old key is how
  manifests drift).
- `dashboard/show_model.py` — imports `PARAM_TYPES` verbatim (line 43) for
  message arg tags. Message args are *wire* types, not declaration kinds, so
  this should **stop** importing from `manifest.py` and own its own `i/f/s`
  arg-tag set. The comment at line 36 says the reuse exists to prevent drift;
  the coupling is now the drift risk, and the two sets have genuinely
  different jobs.
- `python/bopos.py` — `/os/params` serves the manifest verbatim, so no change
  beyond validation; the `/p/*` value path is kind-agnostic.
- The patch editor's declaration UI — a kind `<select>` replacing the type
  select plus the inferred-enum handling.
- Every fixture manifest under `tests/`, and `patches/*/bopos.patch.json`.
  Note the CLAUDE.md gotcha (7): the validator only allows numeric
  `min`/`max`/`default`, so `text` params must still omit `default` or the
  whole manifest silently fails to load — worth fixing to a loud error in the
  same pass.

**[BOB-1]** `text` vs `string` for the fifth kind. Recommend `text` — it reads
as "a kind of control" beside toggle/enum rather than as a wire type.

---

## 2. The plane

### 2.1 Address and the §3 planes table

Events take a normal three-part selector address, unlike the old `/cue`:

```
/<selector>/e/<identity>
```

`<identity>` is the same nested segment grammar as `/p/*` — `[A-Za-z0-9_-]+`
segments, at most eight, 255 ASCII bytes, so `/all/e/section/snap` is legal.

New planes-table row:

| plane | owner | contents |
|---|---|---|
| `/e/*` | **patch** (identities) / framework (scheduling) | patch-declared momentary events, arity 0–3; the framework forward-schedules every fire and engines see only the bare relative fire |

This is the interesting entry: it is the first plane with a **split owner**.
`/p/*` is wholly patch-owned and passes through; `/cue` was wholly
framework-owned with a framework-invented id space. Events are patch-declared
addresses that the framework intercepts and schedules. The planes table should
say so explicitly rather than leaving a reader to infer it — the framework
plane set stays closed, and `/e/*` joins it as a *shared* plane.

**The selector is the win.** Bob's requirement that cue triggering be
targetable at all / a group / a seat falls straight out: `/all/e/snap`,
`/g3/e/snap`, `/2/e/snap`. The old `/cue` was structurally incapable of this
— it was one of the two framework addresses that omit the selector, always
fleet-wide.

### 2.2 Undeclared identities

Follow the `/p/*` precedent and the old `/cue` behaviour together: the
framework **schedules any well-formed `/e/*` fire without consulting the
manifest** (as it never filtered undeclared cue IDs), and the dashboard
**badges** an undeclared identity rather than guessing. Declarations remain
documentation and UI surface.

---

## 3. Wire shape, arity 0–3

**Leader → fleet** (broadcast/unicast on 6660, as `/p/*`):

```
/<selector>/e/<identity>  <sharedTimeNs:string> [<e0:float> [<e1:float> [<e2:float>]]]
```

The fixed field comes first precisely because the element list is
variable-length. `sharedTimeNs` is the decimal string of an integer nanosecond
count, per §12 and exactly as `/cue` carried it — never a 32-bit float.

**Node → engine** (localhost 6661), after the local deadline:

```
/e/<identity>  [<e0> [<e1> [<e2>]]]
```

Selector-free and **time-free**, identical in discipline to `/p/*`: the engine
never sees absolute time (§12), and PD never touches a >6-significant-figure
float. A zero-element event is the bare `/e/snap` with no arguments — which is
today's `/cue snap` with the id promoted from argument to address.

### 3.1 The identity-grammar narrowing (measured: near-zero cost)

Today a `cueId` is `[^\x00\r\n]{1,64}` — spaces and punctuation allowed. As an
address segment it must be `[A-Za-z0-9_-]+`, so ids with spaces or punctuation
would need renaming.

**Measured, not assumed:** there are no declared `cues` in any
`bopos.patch.json` in the repo (`patches/`, `tests/`), and
`dashboard/shows/test.json` — the only show document — contains zero `/cue`
messages. The cue machinery is fully built and completely unused, which is
consistent with Bob's basis for the hard break. The narrowing therefore costs
nothing in-repo; the only exposure is cue ids inside Bob's own patches outside
it, which §7 covers as part of the PD edit.

**[BOB-2]** Accept the rename cost for the nested-address grammar and `/p/*`
symmetry (recommended), or keep the identity as a first *argument*
(`/all/e <identity> <time> …`) so arbitrary id strings survive. The argument
form is uglier, loses nesting, and makes the address plane non-uniform;
recommend the address form.

---

## 4. Forward synchronization

No second clock path. `sync_node.CueScheduler` is generalized from
`schedule(shared_ns, cue_id)` → `schedule(shared_ns, identity, elements)` and
fires the assembled message; `SyncState`, the offset slew, the pong reply, and
the ±500 ms ping cadence are all untouched. `osc_bridge.fire_cue(cue_id,
lead_ms)` becomes `fire_event(selector, identity, elements, lead_ms)`, still
computing `shared_time_ns = now + lead`.

### 4.1 Lead `0` must bypass scheduling, not lean on the grace window

Bob ruled that a global lead time of `0` **is** sync-off. That has to be exact,
and today's machinery would only make it approximately true:
`CUE_LATE_GRACE_NS` is 50 ms (`python/sync_node.py:22`), so a 0-lead fire
arrives already "late" by one network hop and fires only because the hop is
under 50 ms. On a congested WiFi rig it would be dropped as stale — a fire
button that silently does nothing.

Recommend a sentinel instead: **`sharedTimeNs` of `"0"` means fire on
arrival**, bypassing the scheduler entirely. A real `time.monotonic_ns()`
instant is never 0, so the sentinel is unambiguous, costs no extra argument,
and makes "lead 0 = sync off" true by construction rather than by luck. The
late-grace policy then applies only to genuinely scheduled fires.

`osc_bridge.fire_cue_now` (which today means "earliest deadline") is deleted
in favour of the sentinel.

### 4.2 The lead-time setting

`state.cue_lead_ms` is the installation-wide lead (`dashboard/state.py:111`,
`890`, `1022`). Recommend renaming to `event_lead_ms` with a load-time
fallback read of the old key. That is settings loading, not a wire shim, so it
does not conflict with the no-shim ruling — and leaving "cue" in a key name
after deleting cues is precisely the naming rot this repo has been paying
down. Coordinate with `desktop-ui-overhaul/03-global-controls-monitor`, which
relocates the control itself; whichever lands second adopts the new name.

---

## 5. The `/cue` deletion sweep

263 references across 15 files. Per surface:

| surface | what goes |
|---|---|
| `docs/OSC-CONTRACT.md` | `/cue` planes row and §3.1 table row; §8 `cues` key; §4.2 term; the "two framework addresses that omit the selector" grammar note becomes one (`/sync/ping`) |
| `python/sync_node.py` (23) | `CueScheduler` generalized; `CUE_LATE_GRACE_NS` retained for scheduled fires |
| `python/bopos.py` (15) | `parts == ["cue"]` dispatch → `/e/*` route; `fire_cue_to_engine` → `fire_event_to_engine` |
| `python/manifest.py` (18) | the `cues` block and `CUE_ID` deleted outright; cue declarations become zero-arity `events` entries |
| `dashboard/osc_bridge.py` (6) | `fire_cue`/`fire_cue_now` → `fire_event` |
| `dashboard/show_engine.py` (6) | the `/cue` address branch → `/e/*` |
| `dashboard/state.py` (9) | `cue_lead_ms` → `event_lead_ms` (§4.2) |
| `dashboard/server.py` (34) | cue command surface, roster/manifest plumbing |
| `dashboard/static/js/show.js` (34) | cue step builder, pill category (§6) |
| `dashboard/static/js/dashboard.js` (38), `facilitator.js` (35) | cue trigger buttons → the control panel's events section |
| `tools/simfleet.py` (12), `tools/audition.py` (14) | `handle_cue`/`schedule_cue` parity |
| `pd/bopos~.pd`, `pd/bop/babs/babs.blineseq.pd` | **Bob's edits** — see §7 |

### 5.1 Show documents

`dashboard/shows/*.json` would persist a cue step as `{address: "/cue", args:
[{type:"s", value:"snap"}]}` — stored documents, not wire traffic, so the
no-shim ruling does not by itself decide them.

**But there is nothing to migrate.** `dashboard/shows/test.json` is the only
show document and contains no `/cue` messages (§3.1). Recommend therefore
**writing no migration code at all** — a `SCHEMA` bump and load-time upgrade
path would be dead code on the day it shipped, which is the opposite of Bob's
"keep the code clean" instruction. A `/cue` message in a hand-authored
document simply fails validation loudly, like any other unknown address.

**[BOB-3]** No show migration (recommended, on the evidence above), or a
`SCHEMA` 1 → 2 load-time upgrade as insurance against show documents living
outside the repo that this scan cannot see.

---

## 6. Show and pill integration

`inferMessageMode` (`dashboard/static/js/show.js:275`) keys purely off the
address, so the change is one line: `/e/` → `event`. In the flat eight-category
set, the `cue` category is **renamed** to `event` (code `CUE` → `EV`) rather
than added alongside — a cue *is* an event, so a second category would be a
distinction without a difference. **The set stays eight**, which means the tied
`25-message-pill-encoding` taxonomy survives its ratification intact.

Arity is not encoded in the pill; the identity label carries it, and the
inspector shows the elements.

**[BOB-4]** Pill code `EV` for all events (recommended), or keep `CUE` for the
zero-element case so the operator's existing reading of the Show tab is
undisturbed.

---

## 7. Parity and PD

- **simfleet** — `handle_cue` → `handle_event`, honouring the `"0"` sentinel;
  needed in the same stitch per the house rule that protocol features land in
  the simulator together.
- **audition** — `schedule_cue`/`dispatch_due_cues` carry elements.
- **relay / engine context** — no change; events are not run context.
- **editor surface** — event rows become live (they render inert today).
- **PD — Bob's edits, written to `.notes/pd-edits-for-bob.md`, not made by an
  agent.** `pd/bopos~.pd` and `pd/bop/babs/babs.blineseq.pd` receive `/cue`
  today. The receiver moves to `/e/<identity>` and gains up to three float
  inlets' worth of payload. **[BOB-5]** — this is the one item that cannot be
  verified without you, and it determines whether the implementation stitch
  can be tied on software gates alone.

### 7.1 What verifies headlessly

Manifest/kind validation, the scheduler, the `"0"` sentinel, simfleet fire
receipt, show-document migration, and the pill taxonomy all verify in the
existing harness (`tools/run-tests.sh`, simfleet with `--sim-no-engine`).
Real PD reception and audible timing are a **hardware adoption check** on the
Finn Jet + Ciro Toast rig, and should be stated as such rather than claimed.

---

## 8. The future door, named once

Event-specific automation — repeat, pattern, ratchet — is expected eventually
and is **not designed here**; its shape is unknown. Nothing in this proposal
forecloses it: elements are positional floats and the plane carries a
variable-length list, so a later `§3.2`-style vocabulary can occupy the
argument positions after the elements exactly as the automation grammar does
on `/p/*`.

---

## 9. Implementation children, if ratified

1. `2-kind-grammar` — the declaration break: validator, editor, fixtures,
   `show_model` decoupling. No wire change; verifies headlessly.
2. `3-event-plane-wire` — `/e/*`, generalized scheduler, the `"0"` sentinel,
   bopos.py routing, simfleet + audition parity, contract v1.14.
3. `4-cue-retirement` — delete `/cue` everywhere, migrate manifests and show
   documents, pill rename, cue triggers onto the control panel's events
   section.
4. `5-pd-adoption` — Bob's receiver edits and the rig check.

Splitting 2 from 3 keeps the risky wire work off the critical path of the
`kind` break that `41-preset-primitive` and `8-manifest-reorder` are both
waiting on.

**[BOB-6]** Whether `41-preset-primitive` may start after child 2 (the kind
grammar is what it actually needs) rather than after the whole thread — which
would let the preset design proceed in parallel with the wire work.
