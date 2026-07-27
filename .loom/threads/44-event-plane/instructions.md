# 44-event-plane

The **event** parameter kind and its wire plane, from Bob's 2026-07-27 mockup
braindump (lore `2026-07-27-control-panel-ui-and-architecture-braindump`) and
the same-day widening (lore
`2026-07-27-events-cues-and-global-controls-braindump`).

## Scope narrowed 2026-07-27 (Bob, live session)

The original intake named four missing kinds — toggles, integers, enumerators,
events. Bob corrected that: **toggles and integers already exist** (a toggle is
just `type: "i"` with `min: 0, max: 1`), and **enums shipped** during the
control-panel work as `options` on an integer param
(`docs/OSC-CONTRACT.md` §8, `python/manifest.py`) — wire unchanged, the value
is the integer index, `min`/`max` derived from the option count, labels read
only by the control surface.

**Events are the only genuinely missing kind, and the only wire work here.**
They are already *declared but inert*: a top-level `events` list beside
`params` (`{"name", "path", "arity": 1|2|3, "labels", "defaults",
"dashboard"}`), accepted by the validator, rendered as a dead row in the
control panel so the design has a known surface. No plane carries them.

## Rulings in force (Bob, 2026-07-27 — do not re-litigate)

- **A cue is an event with zero elements**, and cues are **absorbed into the
  event plane as a hard break.** The `/cue` plane goes away in the same
  contract revision — no compatibility shim, no legacy path. No production
  shows rely on cues, so keep the code clean. Manifest-declared cues, Show-tab
  cue steps and pill taxonomy, Control-tab cue triggers, and
  engine/simfleet/audition/relay all migrate to zero-element events.
- **Every event forward-synchronizes.** There is no per-event and no per-fire
  sync choice, so **the mockup's per-row `sync` button is dropped** — an event
  row has one fire action. Lead time stays a single global control, and
  **global lead time `0` is exactly "forward sync off"**; that is the only
  off switch. (Consistent with the Show polish sweep, which already retired
  per-step forward-sync so that all cues forward-sync.)
- **Explicit `kind` field.** The manifest moves from `type` + `options` to an
  explicit kind grammar (toggle / integer / enum / event). Nothing is in
  production, so this is a **hard break** — migrate the validator, saves, the
  patch editor, and the control surface; do not carry the old spelling.
- **Event elements are free-form labeled floats.** Arity 1/2/3 with
  author-supplied labels; note / velocity / duration is the common case, not
  an enforced framework meaning.
- **Presets do not capture events** (for the moment). Events are momentary; a
  preset stores values for toggle/integer/enum params only. This is the answer
  `41-preset-primitive` needs — it does not have to ask again.
- **No automation design for events.** Do not spec generators or repeat/pattern
  behaviour. Bob: "we don't know what that shape is yet, but there will likely
  be some set of automations that are event-specific in the future." Name the
  door in one sentence; design nothing through it.

## What still has to be designed

The wire, and only the wire, plus the sweep it forces:

- the plane address (`<target>/e/*` is Bob's guess) and its row in the §3
  planes table — events are *patch-declared* like `/p/*` but
  *framework-synchronized* like the old `/cue`;
- the wire shape for arity 0–3, including how the zero-element (cue) case
  reads;
- how forward synchronization is expressed, **inheriting** §3.1's
  `cue_lead_ms` / shared-time machinery rather than opening a second clock
  path — engines must only ever see relative time (PD float discipline: no
  absolute epochs);
- the `kind` migration across manifest, validator, editor, and surfaces;
- Show-tab message kinds and how the ratified flat eight-category pill set
  (tied `25-message-pill-encoding`) absorbs the retired `cue` category;
- parity: engine (`bopos~`/template — **Bob owns `.pd` edits**, note them in
  `.notes/pd-edits-for-bob.md`), simfleet, audition, relay, editor.

Anything wire-visible is an **OSC-contract amendment** — the framework plane
set is closed, so a new plane is a ratified §3 revision, not an addition by
convention.

## Sequencing

Bob (2026-07-27): this "might be something that needs to be implemented before
the preset design", so the thread sits **ahead of `41-preset-primitive`** and
after the control-panel work. The preset question 41 was waiting on is now
answered above (events are not captured).

UI shape for the kinds is specced by
`desktop-ui-overhaul/01-control-panel/2-control-panel-design`: the control
panel has a **parameters section and an events section**, not intermingled,
with cues (as zero-element events) in the events section, targetable at all
seats / a group / an individual seat. That stitch describes the UI; this
thread ratifies the wire and implements engine/simfleet/relay parity.

Start with `1-event-plane-design` (Bob-gated proposal); implementation
stitches follow ratification.
