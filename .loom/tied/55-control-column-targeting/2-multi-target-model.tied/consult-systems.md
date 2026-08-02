# Consult — systems altitude: columns, steps, state, patch load

Read against `dashboard/server.py`, `preset_application.py`, `preset_store.py`,
`show_model.py`, `show_engine.py`, `static/js/control-{column,host,surface}.js`
and `docs/OSC-CONTRACT.md` v1.17, 2026-08-02.

---

## 0. The measurement everything below rests on

`apply_preset` (`server.py:2126-2137`) **coalesces a preset fan-out to a single
datagram per parameter** — but only when the resolved selector is exactly one
`all` or one `gN` *and* nothing was filtered out by patch mismatch. Otherwise it
addresses every seat individually. `apply_show_preset:2050-2054` sets that
selector only when `len(resolved) == 1`. Show `osc` messages fan one datagram
per selector (`show_engine.py:187-188`).

So the traffic rule for the whole thread is one sentence: **one portable
selector per message is the difference between P messages and P × N.**

| step shape (per target) | datagrams at playback |
|---|---|
| reference, target `all` or one group | **P_preset** |
| reference, target = list of k seats | P_preset × k |
| reference, target = two groups | P_preset × N (coalescing lost) |
| flattened literal values, one selector | P_declared (≥ P_preset) |
| reference + deviations (naive) | P_preset + D |
| **reference with `omit` + deviations** | **P_preset** (each param exactly once) |

The brief says deviation sparsity "is the one that buys traffic". Half right: it
buys *document* sparsity, but layered on top of a full preset apply it makes a
step **more** expensive than flattening, not less, and it sends D parameters
twice.

---

## 1. Recommendation — Q1: a column has exactly one target

**Adopt (d). The Control target picker becomes single-select — `all`, one group,
or one seat. Card-per-entry and aggregate-over-a-union both go away.** The
picker already has this mode (`multiple:false`, used by Assets and ruled for the
patches deploy row in `09`), so this is a parameterisation, not new machinery.

Not an aesthetic call. Three system reasons:

1. **It is the only shape that keeps every write coalesced.** A column over
   `{group A, group B}` cannot apply a preset in one call — `apply_preset` takes
   one `(scope, id)`. Serving it means either N per-seat applies (P × N) or
   widening the apply verb to take a selector *list*, which is exactly the
   vocabulary widening `4-n-columns/2-venue-wide-capture` removed from capture.
   Two columns cost two applies of P; one mixed column costs P × N.
2. **It makes provenance a total function.** `card_preset_projection` already
   collapses N seats to agree-or-mixed. Over a union of groups at different
   presets that answer is `mixed` with no way back — Q3's taxonomy becomes a
   lattice of mixtures. Over one target, "what preset is this column on" always
   has an answer, and Q3 becomes designable.
3. **N columns already are the multi-target case**, at strictly lower traffic
   and strictly higher legibility. Nothing is lost that a second column does not
   restore in one click.

The honest framing for Bob: **multi-select was a way to spell a group that does
not exist yet.** If two groups are always driven together, that is a group —
make it, and the venue gains a name, a portable show target, and a coalesced
selector. The picker should stop offering the ad-hoc alternative.

## 2. Recommendation — Q2: a step is a *reference with an omit list*, plus deviations

**A step message is a preset reference that names the parameters it must NOT
send, followed by ordinary `/p/*` messages carrying the deviating values.**

```json
{"kind":"reference","address":"/preset/bonks/dusk","args":[],
 "target":["group:choir"],"omit":["fx/mix","gain"],
 "reference":{"content":{"name":"bonks","fingerprint":"…"},"schema":"sha256:…"}}
{"kind":"osc","address":"/p/fx/mix","args":[{"type":"f","value":0.31}],
 "target":["group:choir"]}
```

Why this shape and not the three alternatives:

* **Against flattened values (early binding).** Late binding is worth keeping.
  A show references `dusk`; retuning `dusk` in the patch retunes every show that
  uses it, which is how presets earn their existence. Flattening freezes 40
  numbers per step into a document that no longer says *what* the state was, and
  it costs more datagrams (P_declared ≥ P_preset). Flatten already exists as an
  explicit per-message escape (`flatten_show_preset`) — keep it as the escape,
  not the default.
* **Against auto-generated presets.** Bob's own objections hold and one more is
  decisive: `presets/` travels with the **patch**, and §9 explicitly excludes it
  from the distribution fingerprint. A show that mints presets makes the show
  non-portable *and* silently couples show authoring to patch content that is
  version-controlled separately. Capture must never write to `presets/`.
* **Against naive reference + deviation (the brief's recommendation).** It is
  broken today, in two independent ways.
  - **Ordering.** `queue_show_preset` spawns a task (`server.py:203`,
    `1692-1701`) while `_emit_messages` sends `/p/*` synchronously in the same
    loop turn. **Every deviation in a step lands before the preset it deviates
    from, and is overwritten.** The step does not reproduce the state it
    captured.
  - **Timed apply.** With a duration, the preset emits the §3.3 fade form. A
    deviation on the same identity is not merely reordered — it fights a fade
    that keeps writing for the whole duration. There is no ordering that fixes
    this; the fade must never be sent for that parameter at all.

  `omit` fixes both by construction: no parameter is addressed twice, so no
  ordering question exists and no fade contends. It also restores the traffic
  claim the brief wanted — exactly P_preset datagrams.

`omit` is a **host document field only.** `clean_message` builds its result key
by key, so this is one validated list in `show_model.py` plus one filter over
`canonical` in `apply_preset`. §8.1 already declares a preset non-wire and apply
"an ordinary dashboard-driven fan-out"; choosing which of that fan-out to send
is a host concern by definition. **The brief's claim that no OSC contract change
is needed is correct** — I checked §3, §8.1 and §9. The show *document* schema
does change, and with no shows in existence that is free.

Capture derives `omit` for nothing: `preset_dirty`
(`preset_application.py:264-292`) already walks parameter by parameter; return
the differing identities instead of `True` and you have both the omit list and
the deviation values in one pass.

**Sub-question — should capture let you pick which values are sent?**
No new affordance, and the reason is a correction to the brief: **the choice
already exists on save.** `save_patch_preset` takes an `include` allowlist
(`server.py:2000-2007`) and the drawer renders a checkbox per parameter
(`control-surface.js:336, 508, 538`). So the two do not diverge if capture stays
argument-free — capture's answer to "which values" is *the ones that deviate*,
which is derived, not chosen, and therefore cannot drift from anything. Keep D1:
capture takes no arguments. If an operator wants a curated state, they save a
preset (choosing) and capture (deriving) — one chooser, in one place.

## 3. Recommendation — Q3: the taxonomy, and one channel for it

Bob's four states are incomplete, and two of the missing ones are currently
*conflated with dirtiness*, which is a live legibility defect:
`refresh_preset_dirtiness` (`server.py:1966-1988`) sets `preset_dirty = True`
when the preset file cannot be read, and `preset_dirty` returns `True` when the
seat's effective patch differs from the marker's. Both render as "you tweaked
it".

| # | state | derived from | glance / inspect |
|---|---|---|---|
| 1 | inert — no manifest, lost target, empty group | D5 path | glance |
| 2 | **free** — no preset applied (or forgotten across restart) | `applied_preset` absent + `preset_provenance_seen` | glance |
| 3 | **clean** | marker, `dirty == false` | glance |
| 4 | **deviated** | marker, `dirty == true` | glance + per-row inspect |
| 5 | **mixed** — members disagree on which preset | `card_preset_projection` | glance (group/all only) |
| 6 | **unresolved** — preset deleted or renamed | store read fails | glance, distinct from 4 |
| 7 | **inapplicable** — target's patch ≠ preset's patch | `effective_patch_for_seat` | glance, distinct from 4 |
| 8 | schema drift | catalog `drift` | inspect |
| 9 | automation running | existing cyan | orthogonal, already channelled |

Split 6 and 7 out of `preset_dirty` into a three-valued provenance verdict.
They are different actions: 4 means *capture will record your tweaks*, 6 means
*capture will fail*, 7 means *this column is talking to the wrong patch*.

**Treatment: no new colour.** Cyan means "something is driving this" and adding
a second hue meaning "something changed this" would collide with it at exactly
the moment both are true. Use the grayscale scale and position:

* The column header **is** the closed target picker, so put the provenance chip
  there, left of the target, as one word plus one leading mark — `dusk` /
  `∗dusk` / `—` / `⚠dusk`. Leading, per `53/3`.
* **Deviated is the one state that gets a weight change, not just a mark:** the
  chip inverts (ink fill, panel text). It is the only state where what you hear
  and what the document would say disagree, and it is the state Bob is being
  bitten by.
* Per-row deviation ticks in the value box answer *which* values — inspection,
  and free from the same per-identity walk.
* Bob's border-round-the-column: I would not. A column is already a card in a
  horizontal track; a state border on the card competes with focus, with D5's
  disabled state, and with the armed-capture treatment. The header chip is
  where the operator is already looking when they open the picker.

## 4. What this forbids

* **No ad-hoc multi-target on Control.** You cannot drive "seats 3, 5 and 9" in
  one gesture without making them a group. Worth it: it keeps every write and
  every apply on one coalesced selector, keeps provenance total, and pushes
  recurring sets into named venue state that shows can target portably.
* **No aggregate panel over a union**, and therefore no "two groups at different
  values read as `mixed`" problem to design around.
* **Capture never writes to `presets/`.** No auto-generated presets, ever; a
  show cannot mutate patch content.
* **Capture takes no arguments — still.** No scope, no parameter picking, no
  "capture this column". D1 stands.
* **No parameter is addressed twice within a step.** `omit` is not optional
  bookkeeping; it is the invariant that makes timed applies safe.
* **A step cannot carry a bare `/p/*` message with no patch identity** — see §6.

## 5. The weak point

**Single-target columns make transient comparison expensive.** The real workflow
"let me hear seats 2 and 7 together, adjust, move on" now costs either two
columns (fine) or a throwaway group (venue pollution — groups are durable state
with names, and shows target them *by name*, so junk groups leak into the
portability layer). The aggregate model would have served that in one picker
interaction.

I still recommend single-target, because the traffic cliff and the provenance
lattice are permanent costs paid at every playback and on every screen, while
the comparison cost is paid by the operator once and mitigated by two columns.
But if Bob rejects anything here, this is the argument to reject it on — and the
mitigation to build then is *scratch groups* (unnamed, non-portable, excluded
from capture targets), not multi-select.

## 6. What it needs from `34-fleet-patch-global-state`

Three things, all small, and none of them requires the fleet patch to be
first-class. My model reads patch identity **per seat** through
`effective_patch_for_seat` and **per message** through `reference.content.name`.
Whether 34 makes the fleet patch a stored global or a projection of per-device
desired state, both readers keep working.

1. **A convergence signal, not a timer.** Loading a patch stops the engine,
   fetches, restarts (§9). A step that switches patches must be able to gate the
   next step on *converged*, not on a duration. 34 must expose per-device
   convergence as an awaitable fleet-level predicate. Without it a show will
   fire its first post-switch preset into a dead engine.
2. **Deviation messages must be able to carry a patch identity.** Today
   `clean_message` **rejects** a `reference` block on an `osc` message
   (`show_model.py:224`). A preset reference is patch-safe by construction —
   `apply_preset` splits `matching`/`skipped` on `effective_patch_for_seat` and
   silently declines to send to a seat on the wrong patch. A bare `/p/gain`
   deviation has no such protection: after a mid-show patch switch it goes out
   blind, to a parameter that may not exist or may mean something else. Relax
   that one line so an `osc` message may carry the same
   `{content:{name,fingerprint}, schema}` envelope, and have the engine apply the
   same match-or-skip. That is the single invariant my model depends on and it
   is currently unprotected.
3. **Nothing else.** Capture already records the patch per cluster; drift
   warnings already exist per reference; `preset_patches()` already enumerates
   fleet + pins + editor. A mid-show patch switch breaks **no** invariant in
   this design once (2) lands: references to the old patch go inert and are
   reported rather than misfiring, and the Control tab re-derives its manifest,
   preset catalogue and capture set from the seat's effective patch as it does
   today for a pinned device.

## 7. Where I think the brief is wrong

1. **"There is no way to choose which params a preset stores."** There is —
   `include` on the save verb and a checkbox per parameter in the save drawer.
   This changes the answer to Bob's sub-question.
2. **"Deviation sparsity is the one that buys traffic."** Layered on a full
   preset apply it *costs* D extra datagrams and sends deviating parameters
   twice. It buys traffic only with an omit list.
3. **Reference + deviation is not merely a shape to choose — it does not work
   today.** Preset applies are spawned as tasks while `/p/*` sends are
   synchronous, so deviations authored in a step land first and are overwritten;
   timed applies make the conflict unfixable by ordering.
4. **The state taxonomy is missing two states that already exist and are
   mislabelled**: preset-missing and patch-mismatch both currently render as
   dirty.
5. **"Nothing requires an OSC contract change" is correct** — but it hides that
   the *show document schema* changes twice (`omit`, and a `reference` envelope
   on `osc` messages). Free today, since no shows exist; not free later.
