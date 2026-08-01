# Design addendum — preset primitive

Revises `.loom/tied/1-preset-architecture-design/proposal.md` in response to
`.loom/tied/2-proposal-review/review.md`. The ratified rulings (F1–F4 and the
earlier entity rulings) are unchanged; this document repairs the places where
the proposal could not be implemented as written.

Written 2026-07-28. Four questions for Bob are in §9; everything else is a
closure I am confident in, biased — per Bob — toward the simplest thing that
is actually correct.

> **Superseded in part, 2026-07-29:** `.loom/tied/3-addendum-review/review-2.md` F1 —
> Bob ruled **morph is dropped from v1** and deferred to
> `feature-backlog/48-morph-interpolation`. §1 (A1) and §2 (A2) describe the
> deferred mechanism; timed apply now uses the existing fade grammar for
> float/int entries and sets everything else at t=0. §10.4 disappears; the
> live stitch layout is review-2.md §Layout.

Findings confirmed by independent reading before writing this: D1, D2, D5, D6,
D7 (see §8 for the two that are pre-existing bugs unrelated to presets).

---

## 1. A1 — `morph` grammar closure (closes D1)

**The defect.** `_options` (`python/paramgen.py:58`) peels trailing string
options off the end of a message *before* anything inspects the leading
keyword. With the destination allowed to be any full-state form, a trailing
`c:` in `morph 2s lfo sine 0 1 10s c:1` belongs to both the morph and the LFO,
and there is no boundary to decide.

**The closure: a wrapper's own arguments precede the message it wraps.**

```
/<sel>/p/<identity> morph <dur> [c:<n>] <destination-message…>
```

Parsing is: consume `morph`, consume the duration, consume **at most one
leading** `c:` token, then hand **the entire remainder, verbatim, to the
existing parser**. The inner message peels its own trailing options exactly as
it does today. No new option spellings, no delimiters, no change to
`_options`, and the inner grammar is untouched.

This bends §3.3's "keywords lead, options trail" only in the way a wrapper
must: the outer form's arguments cannot trail, because everything after them
is a complete inner message. The contract states that as a rule rather than an
exception.

Ratified examples to carry into the contract stitch: constant destination; LFO
destination carrying all three of its own options; LFO destination with an
outer morph curve *and* an inner LFO curve (the case that was previously
inexpressible); segment-list destination; loop destination.

*Alternative if simpler is preferred:* drop the outer curve entirely and make
morph interpolation always linear. Static→static keeps its curve through the
existing fade form, which is where curves are actually missed. → **Q1.**

## 2. A2 — what interpolates (closes D2)

**The defect.** Two parts. There is no defined argument vector for pairs like
loop↔LFO or loops of different segment counts. And — the sharper half — a
synced LFO computes phase as `t_synced / period + phase`
(`python/paramgen.py:284-305`), so lerping `period` changes the denominator
under a large absolute clock and jumps the output. The proposal's claim that
LFO↔LFO is continuous was simply false.

**The closure: magnitudes interpolate; anything that defines time or shape
takes the destination at t=0.**

| Argument | Behaviour during morph |
|---|---|
| LFO `min`, `max` | interpolate |
| LFO `phase` offset | interpolate (additive in the formula — stays continuous) |
| curve `c:` | interpolate |
| segment *values* in an aligned pair | interpolate |
| LFO `period` | destination at t=0 |
| segment *durations* | destination at t=0 |
| LFO `shape` | destination at t=0 |
| `f` (free) | destination at t=0 |

This dissolves the phase problem instead of solving it. With `period` fixed
from t=0, the running generator **is a valid clock-anchored LFO at every
instant of the morph** — just one with lerped magnitudes. So:

- The sync law survives intact. No phase accumulator, no device-local phase
  state, no fleet phase divergence, no re-anchoring discontinuity at
  completion.
- Catch-up becomes exactly what the proposal claimed and could not deliver:
  **send the current interpolated spec**, a real, idempotent, full-state
  generator message. A late joiner lands in phase.
- The engine cost is a lerp over a handful of floats, with no new evaluation
  path.

The alternative — a phase accumulator integrating `dt/period(t)` — is
continuous for any period trajectory, but it makes phase device-local for the
duration of the morph and cannot re-anchor to the fleet clock at completion
without either a per-device `p:` (destroying fleet phase alignment) or a jump.
In a system whose whole automation model is built on clock-anchored
idempotence, snapping the period is the cheaper honesty. An operator who wants
an audible rate sweep authors it as two steps.

**Unalignable pairs snap and are reported.** Rather than a support matrix the
operator has to learn, and rather than a rejection path:

- Pairs whose magnitudes align (constant↔constant, constant↔LFO via the
  zero-depth coercion, LFO↔LFO, loop↔loop with equal segment count)
  interpolate per the table.
- Every other pair **sets the destination at t=0** and is counted in the apply
  report (§4) as snapped, alongside the clamped and dropped counts.

One rule, no matrix, never an error, and the operator is told what happened.

## 3. A3 — the fingerprint split (closes D3, partly by disagreeing)

The review reads the omission of a patch content fingerprint from the preset
file as dropping R2. I disagree with that half and accept the other.

**Preset file: schema fingerprint only.** R2 governs *cross-layer* references —
composition reaching into content. A preset lives **inside** the patch it
describes; having it carry its own container's fingerprint is self-referential,
and it would warn on every `main.pd` edit that touched no control at all. A
warning that fires when nothing relevant changed is worse than no warning: it
trains operators to dismiss the channel. Within the content layer the schema
fingerprint is the whole of what "can this still be applied" means.

**Show preset message: patch `{name, fingerprint}` — the review is right.** A
show reaching a preset *is* the cross-layer reference R2 governs, and the
proposal had it carrying the schema hash instead. It carries both: the patch
reference R2 requires, and the schema fingerprint as the applicability check.

This is an interpretation of a ratified rule, so → **Q2.**

## 4. A4 — patch-aware application (closes D4, C1)

**The defect.** `/all/p/…` and `/gN/p/…` reach every matching node regardless
of which patch it runs, and `live_scope_patch` (`dashboard/server.py:1543`)
only diverges for `scope == "device"`. Applying patch A's preset to All can
write same-spelled identities into a pinned device running patch B, where they
may mean something else entirely.

**The closure.** Apply resolves to concrete seats *first*, then filters:

1. Resolve the scope to concrete seats (existing machinery).
2. For each seat, derive its **effective patch** (pin, else fleet).
3. Seats whose effective patch ≠ the preset's patch are **skipped and
   reported** — a derived, non-blocking mismatch, not an error.
4. Fan out to the surviving seats. **Coalesce to the original `all`/`gN`
   selector only when nothing was skipped**; otherwise send per-seat. One
   rule, provably equivalent, no heterogeneous-datagram reasoning.

**This lives in a preset application core, not in the UI.** The review is
right that "apply is free" was true only of the final datagram: validation,
durable mirror updates, clamping, provenance, the per-target report, and
atomic persist/broadcast all have to happen somewhere, and today's
`load_preset` (`dashboard/server.py:821`) does a partial version of exactly
that. Every caller — Control, Device, editor recall, Show expansion — goes
through one core, per R1's one-application-path rule.

The apply result is a per-target report: applied / clamped / snapped /
dropped (identity gone or kind changed) / skipped (patch mismatch).

## 5. A5 — generator replay and honest `stop` (closes D6)

**Two defects.** `replay_live_params_for_seat` (`dashboard/server.py:1512`)
replays only durable scalars, so a generator preset applied to an offline seat
never arrives when it rejoins — and a node/engine restart loses it the same
way. And `stop` clears the dashboard's automation entry without writing any
durable value, so a capture taken after Stop stores the stale pre-generator
scalar rather than the value the node is actually holding.

**Closures, both in the application core rather than the UI:**

- **Replay prefers the generator.** For each seat/identity, replay the active
  full-state automation args when present, else the durable scalar. This is a
  strict improvement to a path that is currently wrong for *all* automation,
  not just presets.
- **`stop` computes and stores its held value.** The dashboard knows the
  generator spec and the elapsed time, so it can evaluate the held output and
  write it durably at stop time. That repairs the underlying state rather than
  papering over the capture symptom, and it makes `stop` honest for replay and
  for the panel readout too.

Note for the docs, per U3: capture records **intended dashboard state**, not
observed node output — UDP, offline nodes and engine-start windows all make
those legitimately differ, and §14 rejects a query verb. UI and docs say
"dashboard state", never "what the engine is playing".

## 6. A6 — schema fingerprint contents (closes D7)

Hash a deliberate canonical projection, sorted by qualified identity so that
manifest drag-reorder is irrelevant by construction:

```
[{identity, kind, min, max, options: [ordered labels]}, …]
```

**Ordered enum labels, not the count** — the review is right that reordering
`["dry","wet"]` preserves kind, count and derived range while reversing the
meaning of every stored index.

## 7. A7 — provenance without a ledger (closes U1)

**The defect.** All/group/seat cards are overlapping views. Apply Dawn to All,
then Dusk to Seat 2, and a dictionary of per-card markers cannot say what the
arrangement is; the review proposes an ordered application ledger.

**The closure: store provenance per concrete seat, and derive everything
else.** Applying Dawn to All writes `Dawn` on every seat; applying Dusk to
Seat 2 overwrites that one seat. Then:

- A card's dropdown shows a preset when **all** its seats agree, and reads
  mixed otherwise — which is exactly how the panel already renders mixed
  parameter values. No new idiom.
- Capture-as-step emits one message per distinct preset, targeting the seats
  that carry it. Order-independent by construction: there is no replay order
  to get wrong, because the captured arrangement is the *state*, not the
  history that produced it.
- Portability is preserved where it exists: if a preset's seat set is every
  seat, emit `all`; if it equals a group's membership, emit that group by
  name; otherwise a seat list.

No ledger, no ordering rule, and no supersession problem — an append-only
ledger would grow without bound under repeated application and would need a
supersession rule of its own.

## 8. Pre-existing bugs the review surfaced (not preset work)

1. **Toggle manifests do not round-trip.** `python/manifest.py:187` rejects
   any present `min`/`max` on a toggle, then writes `min=0, max=1` itself, so
   validate→save→validate fails. Enum got exactly this round-trip treatment
   (with a comment explaining why); toggle was missed. Small and isolated —
   it should be fixed before anything hashes normalized manifests, but it is
   not a preset defect.
2. **`presets/` would be HTTP-reachable.** `DistributionStaticFiles`
   (`dashboard/server.py:60`) filters dot/part/symlink paths only, so a
   hand-built `/patches/<name>/presets/…` URL would serve. If "host-only"
   means not fetchable at all, deny it there. Recommendation: deny — it costs
   one guard and makes the term mean one thing.

Also carried, from U2: the store is strict and fail-visible — malformed files
are listed with an error rather than silently treated as empty (an empty
preset is a *valid* sparse shape, so the show-model's tolerate-by-emptying
idiom is unsafe here), empty saves rejected, real paths confined to the patch
root, and overwrite requires a revision token so two browsers cannot silently
clobber. From U4: one shared canonicalization function at the durable write
boundary, used by live writes, capture, apply, clamping and dirty comparison,
storing exactly the value that was sent.

## 9. Questions for Bob — ALL FOUR RULED 2026-07-28

**Q1 — morph curve → RULED: keep it, leading options.**
`morph <dur> [c:<n>] <spec…>` per §A1. A wrapper's arguments precede the
message it wraps; the inner message goes verbatim to the existing parser, so
an LFO destination keeps its own trailing `c:` and both curves are
expressible.

**Q2 — preset file drift → RULED: schema fingerprint only.** §A3 stands: R2
governs cross-layer references, and a preset lives inside the patch it
describes, so a self-reference would warn on every `main.pd` edit that touched
no control. The *show* preset message still carries patch `{name,
fingerprint}` per R2 — that half of the review's D3 is adopted.

**Q3 — group names → RULED: non-empty and unique, as a venue invariant.**
Nothing enforces either today (`dashboard/state.py:491`), and without it "first
match" makes a portable show nondeterministic. Existing venues with blank or
duplicate names get a one-time adoption fix; that work belongs to the Show
integration stitch (§10.7), which is where name resolution lands.

**Q4 — facilitator presets → RULED: none at all.** Bob took the simpler option
over the recommended apply-only. Presets are a desktop concept entirely; the
standalone facilitator/iPad surface has no preset affordance.

**Consequence to carry, not to rediscover:** `7-preset-slot` shipped the
provisional preset row into **both** hosts of the shared `ControlSurface` —
the embedded Control tab *and* the standalone facilitator
(`dashboard/static/js/control-surface.js:252-277`, rendered by
`facilitator.js`). Under this ruling the row must be **removed** from the
facilitator host, not merely left inert. That decision reverses the shipped
stitch's decision 1 ("the row is per panel, not per privileged card"), which
predates this ruling; record the supersession by name in the UI stitch, per
CLAUDE.md's interim rule. It also parallels `04-event-fire-affordance`: an
iPad fires, it does not configure.

## 10. Stitch shape

The review's ten-stitch split has the right seams but is heavier than needed.
Merging the three UI surfaces and folding the manifest foundations into the
store gives seven, with the same dependency boundaries visible:

1. **Grammar & reference closure** — ratify A1/A2/A3/A6 into the contract
   (v1.17) with worked examples; settle Q1–Q3. Nothing is amended before A1
   and A2 are closed.
2. **Store & foundations** — strict atomic CRUD, cache, slug/conflict rules,
   schema projection and drift resolution, shared host-only ignore policy used
   by *both* `identity` enumeration and `fetcher._prune`, plus the toggle
   round-trip fix and the HTTP guard.
3. **Application core** — patch-aware concrete targeting, clamp/skip/snap
   report, durable and automation state, generator replay, honest `stop`,
   per-seat provenance, one shared canonicalization. Every caller uses it.
4. **Morph wire & engine** — contract form, both parsers, `bopos.py`,
   simfleet, catch-up, take-over, int quantization.
5. **Control / Device UI** — list, apply, save, delete; include/exclude;
   derived dirtiness; drift inline. Per Q4 this also **removes** the
   provisional preset row from the standalone facilitator host.
6. **Patch-editor save & recall** — its separate seat-0 path, which the
   provisional shared row does not cover; this is the primary sculpt→save
   workflow and the proposal under-budgeted it.
7. **Show integration** — patch references and named-group targets on the
   message model, then the `/preset/*` family, expansion through an injected
   callback (never teaching the transport-only ShowEngine to read patch
   files), `PRE` pill, atomic flatten and capture-as-step.
8. **Venue preset retirement** — last, once every replacement path is live.

1 gates everything; 2 and 4 are parallel after it; 3 needs 2; 5 and 6 need 3;
7 needs 3 and 4; 8 is last.
