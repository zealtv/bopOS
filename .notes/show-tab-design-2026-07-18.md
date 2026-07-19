# Show tab — design and schema (2026-07-18)

Design note for `.loom/threads/14-show-tab`, stitch 1. Naming/semantics from
`instructions.md` + `braindump-2026-07-18.md` are fixed, not reopened here;
this note completes them: show-file schema, storage location, internal WS
API, playback semantics. Reference for every later stitch in the thread.

## 1. Braindump ↔ brainstorm comparison

The braindump authorizes the first real slice of the tab the brainstorm
(`.notes/sequencer-brainstorm-2026-07-15/`) calls "Sequencer." It lands close
to the brainstorm's recommendation but simpler and more concrete.

**Adopted:** follow actions as generative flow (§02 — "a state machine in the
backend, zero wire cost"; this slice extends the set with `goto` and
section-level actions per Bob). Shows as files, tab + separable backend
module (§02 "Where it lives", §08 Q1), narrowed to one JSON file per show
(§2) rather than a directory of clip text files — rows hold concrete
messages, not scripts, so there's no per-clip text to keep separate.
Backend interpreter, asyncio, emitting through the existing relay path (§02
"Scheduling architecture") — "lookahead" here is only as deep as the
existing `/cue` forward-scheduling; no new horizon invented. Full-state /
last-writer-wins wire law (§02, §08 Q10) — inherited for free since the show
engine sends through the same `osc_bridge` methods every tab uses; the
brainstorm's "one playing clip per track" rule doesn't apply because steps
aren't track-scoped (see below). Rung 1 before language design (§05, §08 Q3)
— this slice is exactly that ordering exercised.

**Simplified:** one column, not tracks × clips — braindump's "more columns
later to be more Ableton like" defers that explicitly; no track concept
means no "one playing clip per track" conflict rule, so any number of steps
may be `playing` at once (a real gap the future multi-column work must
reconcile — flagged for stitch 3). Rows hold concrete OSC messages, not
scripted clips — sidesteps "polymorphic clip types round-tripping to text"
(§08 Q2) entirely; a step's messages are structured data built through
pickers (stitch 5), never a script, avoiding scene-language syntax
questions. "Collection"→"section", "row"→"step": terminology only.

**Deferred, untouched by this slice:** musical time/tempo (§02, §08 Q9) —
plain seconds only, no quantization; polymorphic clip types, ramp/point/
field/video clips (rungs 2–6) — the message inspector is a picker over
existing provided terms (`/p`, `/cue`, static `/pt`), not a new clip-type
system; decomposed curves and point-motion authoring (braindump names these
as future inspector residents); `/field`, scatter, cue args, scheduled
param writes (§08 Q4/Q6/Q7/Q8) — no contract revision needed here;
scene-language/pattern/script clips (§08 Q2/Q13/Q14) — `scene-sequencing`
stays paused, no syntax invented anywhere in this thread.

**§08 decisions this slice answers de facto** (evidence, not binding on the
co-design): **Q1** — tab + separable module, shows as files, file shape
narrowed to single-file JSON. **Q3** — Rung 1 before language work,
confirmed by construction. **Q11** — short horizon, no cancellation term:
forward-sync reuses `OSCBridge.fire_cue`'s fixed lead (default 500 ms).
**Q12** — a concrete follow-action vocabulary (stop, play again, next/
previous step, any/other-in-section, goto, next/previous section, multi-then
uniform random).

**Remain open:** Q2 (clip types vs one language), Q4 (`/field`), Q5 (ramp
decomposition), Q6 (scatter), Q7 (cue args), Q8 (scheduled param writes), Q9
(tempo model — shipping none is a data point, not an answer), Q10's
per-track rule (moot until columns exist), Q13/Q14 (language seeds,
agent-writability test).

## 2. Show file schema

### Storage location

Existing dashboard persistence has two conventions (`dashboard/state.py`):
(1) **embedded in the single durable state file** (`installation.json`, via
`InstallationState.durable()`/`.save()`, lines 344-360, 860-867) — presets,
groups, `device_registry`, `fleet_patch`: small installation-scoped facts
with exactly one live value, atomic `.tmp`+`os.replace`, `indent=2,
sort_keys=True`; (2) **one JSON file per named record in a sibling
directory**, same atomic pattern — venues in `installations/<name>.json`
(`venues_dir`/`save_venue`/`read_venue`, lines 881-928). Patches use a
heavier directory-per-patch convention (`server.py:145-151`,
`python/manifest.py`) not relevant here since messages are structured data,
not files.

Shows are venue-shaped: substantial, author-named, potentially numerous,
operator-picked — not a single fleet-scoped fact. Chosen location:

```
dashboard/shows/<name>.json
```

— lazily created (`os.makedirs(..., exist_ok=True)`) exactly like
`venues_dir()`, same `.tmp`+`os.replace` write. Unlike venues' id-keyed
dicts, the top-level `items` array is **order-significant** and must not be
key-sorted away. `installation.json` gains `"current_show": "<name>" |
null`, parallel to `fleet_patch`/`params_patch` — which show the playback
engine has loaded. Stitch 2 owns the exact `InstallationState` plumbing.

### Schema

```jsonc
{
  "schema": 1,
  "name": "opening-set",
  "items": [
    { "kind": "step", "uid": "a1b2c3d4", "alias": "intro drone",
      "messages": [
        { "uid": "m001", "alias": "gain up",
          "address": "/p/gain", "args": [{"type": "f", "value": 0.6}],
          "target": "all" }
      ],
      "duration_s": 45.0, "play_count": 1,
      "then_actions": [ {"type": "next_step"} ],
      "forward_sync": false },

    { "kind": "step", "uid": "e5f6a7b8", "alias": null,
      "messages": [
        { "uid": "m002", "alias": null,
          "address": "/cue", "args": [{"type": "s", "value": "snap"}],
          "target": "all" }
      ],
      "duration_s": 8.0, "play_count": 3,
      "then_actions": [
        {"type": "any_in_section"},
        {"type": "goto", "target_uid": "a1b2c3d4"}
      ],
      "forward_sync": true },

    { "kind": "divider", "uid": "d0001" },

    { "kind": "step", "uid": "c3d4e5f6", "alias": "seat 3 sparkle",
      "messages": [
        { "uid": "m003", "alias": null,
          "address": "/p/fx/sparkle", "args": [{"type": "f", "value": 1.0}],
          "target": "3" },
        { "uid": "m004", "alias": "reset point",
          "address": "/pt", "args": [
            {"type": "i", "value": 0}, {"type": "f", "value": 5.0},
            {"type": "f", "value": 4.0}, {"type": "f", "value": 1.5},
            {"type": "i", "value": 0}],
          "target": "all" }
      ],
      "duration_s": 20.0, "play_count": null,
      "then_actions": [],
      "forward_sync": false }
  ]
}
```

`items` is one flat ordered array mixing `"step"` and `"divider"` entries —
single-column-agnostic on purpose: a step carries no column/lane field yet,
but nothing precludes adding one later (on the step object, or a
lane-partition layered on top — not decided).

**Step:** `uid` (8 lowercase-hex chars, `secrets.token_hex(4)`, server-minted,
regenerated only on a detected collision) · `alias` (string or `null`,
free-text operator label, no auto-generation — unlike `device_aliases`'
generated word-pairs, a step's alias is authored, not identity) · `messages`
(ordered array; order is authoring convenience, all fire together) ·
`duration_s` (number ≥ 0, canonical seconds; stitch-5 edits h/m/s fields,
converts on save/load) · `play_count` (integer ≥ 1, or `null` = loop
indefinitely — §4) · `then_actions` (tagged-action array; empty = implicit
`stop`) · `forward_sync` (bool; §4).

**Divider:** `{"kind": "divider", "uid": "..."}` only — needs a uid too since
stitch 6's move/delete address items by uid regardless of kind.

**Message:** `uid` (same 8-hex scheme, own namespace) · `alias` (string or
`null`, falls back to a short-form of `address` in the UI) · `address`
(full OSC address as sent from the dashboard — still selector-shaped except
for `/cue`/`/pt`, which are inherently selector-free per contract §3.1/§4.1;
the send path, `OSCBridge.set_param`/`.fire_cue`/point helpers, does
selector insertion/stripping exactly as every other tab, so a message never
hand-builds a `/<selector>/...` string) · `args` (array of `{"type": "i"|
"f"|"s", "value": ...}`, reusing `python/manifest.py`'s `PARAM_TYPES = ("i",
"f", "s")` rather than inventing a new type tag set) · `target` (`"all"`, a
decimal Seat id string, or `"g<group-id>"` — the literal selector already
passed into `OSCBridge.set_param(selector, ...)`, `osc_bridge.py:226-227`,
pre-formatted so the playback engine never re-derives it). `/cue` and `/pt`
messages still carry `target` for schema uniformity, but the send path
ignores it for those two addresses (the stitch-5 inspector should grey the
target picker for cue/point payloads).

**Then-action serialization** — tagged list:

```jsonc
{"type": "stop"} | {"type": "play_again"} | {"type": "next_step"} |
{"type": "previous_step"} | {"type": "any_in_section"} |
{"type": "other_in_section"} | {"type": "goto", "target_uid": "a1b2c3d4"} |
{"type": "next_section"} | {"type": "previous_section"}
```

`goto` is the only variant carrying data, and carries the **target step's
uid**, never its alias (aliases aren't unique). The goto picker resolves
uid → alias/uid for display and writes the uid back.

## 3. Internal API sketch

WS envelope is fixed by `dashboard/static/js/ws.js:9,13` — `{"type", "data"}`
both directions. Naming patterns after three existing pairs in
`server.py`/`osc_bridge.py`: `save_preset`/`load_preset` → broadcast
`presets` (lines 597-633: mutating verb, then a renamed-noun catalog
broadcast); `save_venue`/`load_venue`/`list_venues` → broadcast `venues`
(lines 225-227, 952-997: `{names, current}` shape for a file-backed
named-record store — matches the show catalog exactly); `fire_cue` →
broadcast `cue_scheduled` (lines 572-586, `osc_bridge.py:251-256`: a
transport verb whose scheduling detail, `shared_time_ns` as a **string**
never a float per §12, returns on a distinctly-named broadcast).

**Show catalog** (client→server): `list_shows {}` (server replies `shows`,
also sent on connect like `venues`) · `create_show {name}` · `load_show
{name}` (stops all playback first) · `save_show_as {name}` (duplicate
current) · `delete_show {name}` (current becomes `null` if it was current).
Broadcasts: `shows {names, current}` (parallels `venues`); `show {data:
<full doc>}` — full-state, sent on connect and after every mutation, playing
`state`'s role for the installation.

**Step/divider/message edits** (client→server), paralleling `add_seat`/
`update_seat`/`remove_seat`/`reindex_seat` (`server.py:703-795`) and
`create_group` (`state.py:496-518`, which mints the canonical id
server-side): **uids are always server-minted**, never client-supplied.

| type | data |
|---|---|
| `add_step` / `add_divider` | `{after_uid: uid\|null}` |
| `update_step` | `{uid, alias?, duration_s?, play_count?, then_actions?, forward_sync?}` (partial patch) |
| `move_item` | `{uid, after_uid: uid\|null}` |
| `remove_item` | `{uid}` — stops the step first if playing/paused (§4) |
| `add_message` | `{step_uid, message}` — mints a fresh uid; also used for paste (stitch 6's clipboard is client-local; paste = `add_message` with the copied payload) |
| `update_message` | `{uid, ...partial fields}` |
| `move_message` | `{uid, to_step_uid, after_uid: uid\|null}` |
| `remove_message` | `{uid}` |

Every mutation persists and re-broadcasts `show` full-state — no incremental
patch broadcast for the document itself (unlike `device_update`, which
exists because devices are numerous/high-churn; shows are edited by one
operator at a time, so the `presets`/`venues` full-replace pattern fits).

**Transport** (client→server), paralleling `fire_cue`/`identify`/`action`
(lines 417-425, 572-586): `step_start {uid}` · `step_stop {uid}` (leaves
last-sent values in place — full-state world) · `step_pause {uid}` ·
`step_resume {uid}` · `step_trigger_next {uid}` (resolves `then_actions`
immediately) · `stop_all_steps {}`.

**Playback broadcast** (server→clients): `show_playback` — full snapshot,
sent on connect (alongside `state`/`distribution`/`venues`/`shows`/`show`)
and after every transport-driven change:

```jsonc
{"steps": {
   "a1b2c3d4": {"state": "playing", "iteration": 2, "remaining_s": 12.4,
                "section_bag": null},
   "e5f6a7b8": {"state": "paused", "iteration": 1, "remaining_s": 3.0,
                "section_bag": ["c3d4e5f6"]} }}
```

`section_bag` is only set for steps whose section has an active
`other_in_section` bag in progress. `remaining_s` is dashboard-only UI
countdown, never crosses to an engine (PD-float law doesn't apply, §4).

**OSC console taps** (server→clients, stitch 7): two always-on broadcasts,
no subscribe verb (matches "every client gets everything"). `osc_out
{ts, address, args, target}` — everything the dashboard sends, any tab.
`osc_in {ts, address, args, source}` — everything observed on the LAN
receive side, heartbeats included. Filtering (`*` wildcard, `!` negation,
space-separated AND) is client-side over a bounded ring buffer per the
stitch-7 instructions; the server does no filtering.

## 4. Playback semantics spec

**State machine** (per step): `stopped --step_start--> playing`,
`playing <--step_pause/step_resume--> paused`, `playing/paused
--step_stop--> stopped`, `playing --duration/play_count exhausted-->`
then-action resolution. `playing`/`paused` carry `iteration` (1-indexed
loop count in the current run) and an expiry timestamp (`paused` freezes it,
recording remaining time).

**Trigger/duration/play_count.** `step_start` (UI click, `goto`,
`next_step`, …): (1) `iteration = 1`; (2) emit all messages together (per
`forward_sync` below); (3) arm a `duration_s` timer (0 fires per the guard
below); (4) on expiry — if `play_count` is `null` or `iteration <
play_count`: `iteration += 1`, re-emit, re-arm (the "play n times" loop,
distinct from the `play_again` then-action which restarts the whole run
from `iteration = 1`); else (`iteration == play_count`, finite): resolve
`then_actions`. **Guard:** `duration_s == 0` is only valid with finite
`play_count` (validated at edit time, stitch 2) — `null` needs positive
duration or the step busy-loops; `duration_s == 0` with a finite count
resolves all iterations and the then-action synchronously in one tick.

**Then-action resolution.** Empty list → implicit `stop`. One action →
execute it. Multiple → uniform random pick via the show engine's own
`random.Random`, seeded from the installation's run-context seed (same seed
threaded through `bopos-context`/`BOPOS_SEED`) for reproducibility.
`stop`: → `stopped`. `play_again`: `iteration` resets to 1, behaves like a
fresh `step_start`. `next_step`/`previous_step`: next/previous **step**
item in `items`, skipping dividers; at either show boundary → `stop`.
`any_in_section`: uniform pick among the section's steps, **including
itself** (matches Ableton "Any"). `other_in_section`: shuffle-bag scoped to
the section — starts as "every step except the one just finishing," each
resolution removes its pick, empties reset to the full section minus the
step that just exhausted it (so the immediate next pick still can't repeat).
The bag is **per-section, per continuous play episode**: discarded when
every step in the section returns to `stopped`, not on individual stops that
leave other members running. `goto`: jumps to `target_uid`; if that uid no
longer exists, falls back to `stop` with a one-cycle `goto_missing: true`
flag on `show_playback` — the show file is never rewritten to drop stale
references, whether they went stale via stitch-6 editing or hand-editing the
JSON. `next_section`/`previous_section`: lands on the **first step of the
target section**; empty sections (see derivation) are skipped when walking;
no eligible section before the show boundary → `stop`, same as step-level.
Deliberately **non-wrapping** in v1 (a one-line change later if Bob wants
wraparound — flagged, not decided here).

**Section derivation.** Sections are maximal runs of consecutive **step**
items, split on **divider** items; a divider is never part of a section.
Leading/trailing/adjacent dividers produce zero-length gaps that are simply
not emitted as sections — `next_section`/`previous_section` walk only
real sections, so gaps are skipped by construction.

**Edge cases:** goto → deleted step: fall back to `stop` + one-cycle
`goto_missing` flag. next/previous-section → empty section: skip, walk
continues; no eligible section → `stop`. Step deleted while
playing/paused: `remove_item` stops it first, then removes it; other steps'
stale `goto` references are left as-is. next/previous-step or section walk
at a show boundary: `stop` (non-wrapping at both levels). A section that
becomes empty (its only step deleted): stops being enumerable by
section-walks — no special cleanup, falls out of the "skip empty section"
rule.

**Forward-sync.** `forward_sync: true` means: at `step_start` (and each
internal `play_count` repeat), each message's `address` is checked for
scheduled-delivery support. **Only `/cue` has it** — the contract's cue
plane (§3.1) is the only address with a wire-level shared-time argument.
The show engine reuses `OSCBridge.fire_cue(cue_id, lead_ms)`
(`osc_bridge.py:251-256`) verbatim — same default `lead_ms=500`, same
`shared_time_ns` computation/encoding — rather than re-deriving the math, so
behavior matches exactly and there's no second `/cue` sender to disagree.
Every other kind (`/p/*`, `/pt`, raw addresses) has no scheduled variant
(§08 Q8 open) and **falls back to immediate send**, per the parent
instructions. A forward-synced step mixing cue and non-cue messages
therefore sends cue messages pre-scheduled and others immediately in the
same trigger — a real skew bounded by `lead_ms` (~500 ms) that stitch 5's
inspector should surface explicitly rather than implying uniform
scheduling.

**PD float precision and 0-indexing.** `duration_s`, `remaining_s`,
`iteration` never cross the wire — dashboard-side scheduling/UI state only,
so the 32-bit-float law doesn't constrain them. The one wire-crossing time
value, `shared_time_ns` inside a forward-synced `/cue` send, is already
encoded as a decimal string by the reused `fire_cue` path
(`osc_bridge.py:254-255`), never a float, per §12. All indices — `items`
positions, Seat ids in `target`, the element index inside a `/pt` message's
args — are 0-indexed per the project-wide default.

## Notes for later stitches

- Stitch 2: validate `duration_s == 0` only with finite `play_count` at
  write time (§4 guard); mint uids via `secrets.token_hex(4)` with a
  collision-retry loop scoped to the show being written.
- Stitch 3: the shuffle-bag needs to track "is this section in a continuous
  play episode" (≥1 of its steps playing/paused) to know when to discard a
  bag — small engine-side bookkeeping beyond the per-step state machine
  alone; the parent instructions describe the reset condition in words, the
  engine needs an actual signal for "playback in that section stopped."
- Stitch 4/5: a message's `target` selector should reuse whatever
  all/group/seat picker component the live-controls work already built
  (`server.py`'s `live_param_target`/selector idioms) rather than a new one
  — flagged for stitch 5, not independently verified here (this stitch
  touches no UI code).
- No mismatches found against stitches 2–7's instructions as written; they
  already anticipate this note's storage-location and naming decisions
  (e.g. stitch 4 already says "internal key stays lowercase `show`," stitch
  7 already describes the console taps exactly as designed in §3). Nothing
  needs editing.

## Amendment — 2026-07-18, stitch 5c: target lists

Bob's screenshot review: a message must target "a seat, a number of specific
seats, or a group, groups, or a mix of all", and a dropdown is the wrong
interface. §2's `target` field is amended:

- `target` is a **non-empty list of selectors** — each entry `"all"`, a
  decimal Seat id string, or `"g<group-id>"`, the same literal selector
  strings as before. Examples: `["all"]`, `["3"]`, `["3", "7", "g1"]`.
- **Legacy load:** a single selector string (every show written before this
  amendment) is accepted anywhere a target is read and normalized to a
  one-item list; shows are persisted with lists from now on.
- **Normalization:** `clean_target` collapses exact duplicates (order
  preserved) and collapses any list containing `"all"` to `["all"]`.
- **Send semantics:** the playback engine fans a `/p/` message out as one
  `set_param(selector, ...)` call per listed selector. A seat covered both
  directly and via a listed group receives the write more than once; params
  are idempotent full-state writes, so this is harmless and no set-algebra
  is performed. `/cue` and `/pt` remain selector-free; they carry `target`
  for uniformity and the send path still ignores it.
- **UI:** the inspector's dropdown is replaced by a direct chip picker
  (All toggle, group swatches in GROUP_SLOTS colours, numbered seat chips in
  the bounded-roster idiom); the wire preview and pill titles render the
  terse form `3+7+g1`.

## Amendment — 2026-07-19, global cue policy

All Show `/cue` messages use forward-sync scheduling. The per-step
`forward_sync` flag is retired: legacy files may contain it, but loading and
saving drops it. The scheduling lead is now one persisted, installation-level
`cue_lead_ms` setting shared by all Show transports rather than a per-step
choice.
