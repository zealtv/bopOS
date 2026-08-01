# Review 2 — the design addendum, adversarially

Date: 2026-07-29. Subject: `41-preset-primitive/design-addendum.md` (authoritative
over the tied proposal), checked claim-by-claim against the code. Bob asked for
this review to also step back: is anything over-complicated, is there a simpler
shape, does the UX stay low-friction.

**Verdict: no addendum repair is broken.** Every closure survives adversarial
reading, with the qualifications below — mostly under-specifications to settle
in the grammar/store stitches, plus one overclaim ("provably equivalent"
coalescing) and one missed consumer in the ignore-policy sweep. Separately,
§F1 below raises one genuine simplification question for Bob that would remove
the riskiest third of the work; it is a scope question, not a defect.

Stitch layout is **deliberately not created yet** — Bob asked to discuss the
findings first. A recommended layout is sketched in §Layout at the end.

---

## Findings against the addendum's new claims

Ordered most serious first. None is a defect in one of Bob's four rulings.

### F1 — the morph wire form may not need to exist in v1 (scope question for Bob)

**→ RULED (Bob, 2026-07-29): morph is dropped from v1** and moved to
`feature-backlog/48-morph-interpolation`, which carries the settled design and
the review findings for revival. Timed preset apply ships as described below:
float/int entries fade via the existing grammar; generator/toggle/enum/text
entries set at t=0, counted in the apply report. The six-stitch layout in
§Layout applies.

Not a defect — the addendum's morph design is sound (F2–F4 below). But walking
the use cases showed the whole morph apparatus — new contract grammar, both
parsers, engine lerp machinery, simfleet parity, catch-up serialization, the
snap matrix — exists to interpolate **generator arguments**, while the
workhorse case, *morphing between scalar values*, is already fully expressible
with the existing fade form (`x <dur> c:<n>`), contract-unchanged.

A timed preset apply could ship as: **float/int entries fade via the existing
grammar; generator/toggle/enum/text entries set at t=0 and are counted in the
apply report.** That is the addendum's own snap-and-report philosophy, applied
one level earlier. It deletes stitch §10.4 entirely, halves the contract
amendment, and removes the only engine-side work in the thread. `morph` stays
additive later if fleet-wide LFO-depth sweeps are actually missed in practice
— nothing in this design forecloses it, because a preset entry is already the
full-state argument list morph would consume.

Why this is Bob's call, not mine: the thread vision names "morph the fleet's
state rather than snap it" explicitly, and F2 ratified argument-vector morph
over the mix function. But F2 chose *between two interpolation mechanisms*; a
scalars-fade-generators-snap v1 was never on the table, and it preserves the
ratified semantics as a strict subset. Per this stitch's gate ("a change large
enough that the §10 shape stops making sense" goes to Bob), surfacing it.

If morph stays in v1, findings F2–F4 apply to it.

### F2 — morph grammar: decidable as claimed, but three holes need contract text

Walked `morph <dur> [c:<n>] <spec…>` through both parsers
(`python/paramgen.py:58-147`, `dashboard/static/js/paramspec.js:31-100`).

**The decidability claim holds.** A valid inner message's head is a number,
`lfo`, `loop`, or `stop` — never an option token (a message that is only
options is rejected at `paramgen.py:115-116`). So greedily consuming one
leading `c:` after the duration can never steal the start of a valid inner
message, including a segment-list destination starting with a bare number.
`morph 2s c:1 c:2 0.5` fails cleanly (inner head `c:2` → "unknown keyword").
Trailing options on the destination (`morph 2s lfo sine 0 1 10s c:1 p:0.25`)
peel inside the inner parse, untouched. Int paths work (`parse_message(args,
"i")`). Confirmed unambiguous.

**Holes to close in the grammar stitch:**

1. **Destination kinds must be whitelisted.** The inner parser accepts `stop`,
   a bare fade (`morph 2s 0 1s`), and — once morph exists — a nested `morph`.
   All three are transitions, not full-state destinations; morphing into them
   is meaningless or unserviceable by catch-up. Contract rule: the destination
   must parse to `set`, `lfo`, or `loop`; `stop`, fade forms, and nested
   `morph` are grammar errors.
2. **Phase wrap for catch-up.** The lerped `phase` offset must serialize into
   `p:<0..1>` (`paramgen.py:75-76` rejects outside that range). Lerping 0.9→0.2
   stays in range, but the contract should state whether phase lerps linearly
   or shortest-path-mod-1; if shortest-path, catch-up must wrap mod 1 before
   serializing. Recommend: plain linear lerp (simplest, always in range when
   endpoints are), stated explicitly.
3. **A doc note, not a rule:** `morph 2s 0.7 c:1` fails with "curve option
   requires a fade, loop, or lfo" (the inner set rejects a curve). The correct
   spelling is the leading form. The error text is technically true and
   completely misleading for this case; worth one sentence in the contract
   examples.

### F3 — "coalesce when nothing was skipped" is not provably equivalent

`selector_matches` (`python/groups.py:55-73`) returns true for `all` on
**every** device, including unassigned ones (`seat_id` −1/None). A coalesced
`/all/p/*` datagram therefore reaches unassigned devices running the fleet
patch; the per-seat fan-out it claims equivalence with does not. For `gN`
there is a second, smaller hole: the node matches against its own synced
membership list, so during a membership-sync window the coalesced datagram
and the dashboard-resolved per-seat set can differ.

Neither is dangerous — the unassigned-device behaviour actually *matches* how
every other all-scoped control (master, mute, live params) behaves today, and
the membership window is transient. But the addendum sells the rule as
"provably equivalent", and it is not. Two honest options:

- **Simplest: always send per-seat.** One path, no equivalence argument at
  all. Cost: N×M datagrams instead of M for a clean all-apply (~600 vs ~30 on
  a 20-seat, 30-param preset). The skipped-seat fallback bursts that anyway.
- **Keep coalescing, restate it as an optimization with a named delta:** an
  all-apply with no skips also reaches unassigned fleet-patch devices, by
  precedent with every other `all` control.

Recommend the second (the precedent argument is real — an unassigned device
that later gets a seat would otherwise sound different from its neighbours),
recorded as a stated semantic, not an equivalence proof.

### F4 — snap-and-report: coverage holds, but the report can mislead on "aligned" pairs

Enumerated what a preset entry can hold under the capture rules
(proposal §1 table): a scalar `[v]`, LFO args, loop args, or a text string.
Never `stop` (honest-stop writes a durable scalar instead), never a fade
(capture stores the destination), never a morph (capture stores the current
interpolated spec). Source states at apply: constant, fade-in-flight
(well-defined current value via `_current_locked`, `paramgen.py:332-340`),
lfo, loop, morph-in-flight (current interpolated spec). Every pair lands in
the table or in "every other pair snaps and is reported". **No pair falls
through.** Two qualifications:

1. **LFO→LFO with a different period counts as "aligned" and is not
   reported, yet the period — often the audible point of the change — snaps
   at t=0 with a phase jump** (`phase = t_synced/period`; changing the
   denominator under a large clock relocates phase instantly,
   `paramgen.py:297-305`). The addendum never claims t=0 output continuity,
   and the min/max envelope bounds the jump, so this is consistent — but an
   operator who morphs Dawn→Dusk expecting a rate sweep gets an instant rate
   change plus a magnitude glide, with the report saying everything
   interpolated. Fix is one line of honesty: the report (or the docs) states
   that time and shape always switch at onset; only depths glide.
2. **The store must enforce the entry whitelist**, because hand-edited files
   escape the capture rules: a `presets/*.json` entry containing `stop`, a
   fade form, or `morph` must be rejected by the strict store validation
   (extends U2's list). Same whitelist as F2's destination rule — define it
   once.

Also confirmed dashboard-side: toggle/enum/text entries must never be sent as
`morph` — the apply core snaps them at t=0. For enum this matters audibly: a
wire-level morph on an enum's integer would sweep through every intermediate
option (the int crossing path, `paramgen.py:348-354`, emits each index).
Kind-aware snapping lives in the apply core, where `kind` is known; the wire
stays kind-blind. State it in the application-core stitch.

### F5 — the ignore-policy sweep missed `_file_fetch`'s source walk

Job 1 item 8. Consumers found that enumerate patch files:

| Consumer | Covered by addendum? |
|---|---|
| `identity._walk_files` (`python/identity.py:31`) — manifest + fingerprint, host & node & simfleet & run context | yes (named) |
| `fetcher._prune` (`python/fetcher.py:86`) | yes (named) |
| **`fetcher._file_fetch` source walk (`python/fetcher.py:172`)** — builds its own manifest from the *source* directory with only a dot-filter, for `file://` fetches | **no — missed** |
| `DistributionStaticFiles` (`dashboard/server.py:60`) | yes (§8 guard) |
| hash-cache persistence (`python/identity.py:89-110`) — dot-filter only; stale `presets/` entries would linger | recommended by D5, not restated — carry as hygiene |
| `_patch_fetch` staging copytree (`python/fetcher.py:239`) | copies everything including `presets/`, which is *correct* — preserved presets ride into staging and must survive the (fixed) prune |
| catalog/inventory listings (`dashboard/server.py:115`, `python/bopos.py:955`) | directory names only — not affected |
| simfleet | uses `identity.*` — covered transitively |

A `file://` fetch (the local-dev and simfleet path) with an unfixed
`_file_fetch` would *transfer* `presets/` to the node and produce a
fingerprint mismatch against the host's excluding walk — the exact drift the
shared policy exists to prevent. The store/foundations stitch must route
`_file_fetch`'s enumeration and `_prune` through the same named policy as
`identity._walk_files`, and add the mirrored-convergence test D5 specified.

### F6 — "active" automation is not a stored property; replay needs a derived expiry

Job 1 item 7. Confirmed against `set_param`
(`dashboard/osc_bridge.py:426-469`): fade/loop/LFO entries are recorded with
`sent_at` and **nothing ever removes a completed fade** — the table holds it
until the next write. "Replay the active full-state automation args when
present" therefore needs *active* defined, or a seat rejoining an hour after a
30s fade gets the fade replayed live — a half-minute ramp from the node's
default to a destination it should simply hold (the exact failure the
instructions asked about).

Rule for the application core: an automation entry replays verbatim if it is a
loop or LFO (idempotent, unbounded), or a fade/morph whose
`sent_at + total duration` has not elapsed; otherwise replay the durable
scalar (which for fades is already the destination,
`osc_bridge.py:460-461, 487-499`). The browser already derives in-flight
status exactly this way; the server adopts the same derivation. Note also that
replaying through `set_param` re-records the entry with a fresh `sent_at` —
harmless for synced LFOs (node phase is clock-anchored; the browser marker
logic at `control-surface.js:100-125` already tolerates idempotent resends)
but the fresh timestamp must not resurrect a nearly-expired fade; replay
should preserve the original `sent_at`.

### F7 — honest `stop` is an estimate, and for free/sh/drift LFOs a poor one

Job 1 item 6. The node freezes at **its own** current output
(`paramgen.py:201-203`). The dashboard's evaluation differs by sync error +
latency for deterministic shapes (fine), but:

- a **free** LFO's phase is `random.random()` device-local
  (`paramgen.py:272`) — the dashboard cannot know it, and a group stop
  freezes *different* values per device while the dashboard stores one;
- **sh/drift** are seeded per cycle (`paramgen.py:291-295`); near a cycle
  boundary the dashboard's estimate lands in the wrong cycle and stores an
  arbitrary in-range value.

This does not sink the closure — U3's "capture records intended dashboard
state" framing covers it, and the stored estimate is strictly better than the
current stale pre-generator scalar. But the addendum's "makes stop honest" is
overstated; it makes stop *self-consistent*. Two acceptable shapes, pick in
the application-core stitch:

1. **Keep `stop` on the wire, store the estimate** (addendum's version), with
   the free/sh/drift caveat documented in the same breath as U3.
2. **Send the evaluated value as a plain set instead of `stop`.** Dashboard
   state becomes true by construction (the node holds exactly what was sent).
   Cost: free LFOs audibly jump to the estimate on stop instead of freezing
   in place.

Recommend 1 — a free LFO's whole point is per-device divergence, and stop
should not collapse it. Document that capturing a stopped free LFO stores the
dashboard's estimate.

### F8 — smaller items

- **Capture target derivation, identical group memberships:** Q3 makes names
  unique but two groups can still have identical seat sets; "equals a group's
  membership" then needs a deterministic tie-break. Recommend lowest group id.
  (`dashboard/osc_bridge.py:473-485` resolution confirmed otherwise sound;
  seats in overlapping groups are handled by per-seat provenance by
  construction.)
- **Card projection matches the existing idiom** — confirmed:
  `aggregateValue` (`control-surface.js:71-81`) already renders "all members
  agree, else mixed" for values and automation signatures; the preset dropdown
  projection is the same rule over the same members. No new idiom, as claimed.
- **Mixed⇒omitted on save needs visibility.** Saving from an aggregate card
  silently omits mixed params (sparse by design). The save affordance should
  show which rows are being omitted as mixed, or a later apply will
  mysteriously not restore them. UI-stitch note, not a design change.
- **Device-panel save while offline** (first review U5, third bullet) is still
  unstated. The panel is visible-but-disabled offline today; recommend save
  disabled offline (capture reads dashboard state, but saving a preset from a
  device you cannot hear invites garbage), settle in the UI stitch.
- **C3's caching path is the one first-review finding the addendum answered
  rhetorically** — nothing in the addendum says where preset bodies are
  cached or what is published per card. Assign explicitly: server-side cache
  keyed by file stat/revision in the store stitch; cards receive the selected
  preset + derived dirty flag, never the full preset list bodies.

## Confirmed closures

Checked, not assumed — the implementation can rely on these:

- **D1** closed by the leading-option wrapper; decidable (F2), with the
  whitelist/phase-wrap text to add.
- **D2** closed by magnitudes-interpolate/time-snaps; the phase math survives
  every instant including completion (lerped phase is additive in
  `t/period + phase`, so a fixed period keeps the sync law intact); catch-up's
  "current interpolated spec" is a real parseable message. Constant↔LFO
  zero-depth coercion is output-continuous at t=0. The only unstated part is
  F4's reporting nuance.
- **D3** closed per Bob's Q2 ruling; both halves land (schema hash in the
  file, patch `{name, fingerprint}` on the show message).
- **D4** closed by concrete-seat resolution + effective-patch filter
  (`live_scope_patch`'s device-only divergence confirmed at
  `dashboard/server.py:1543-1555`); the coalescing overclaim is F3.
- **D5** closed in principle by the shared policy; the consumer sweep gains
  `_file_fetch` (F5). The HTTP guard is adopted (deny).
- **D6** closed by generator-preferring replay + stored stop value, with
  "active" to be derived (F6) and stop's estimate framing tightened (F7).
- **D7** closed: ordered enum labels in the hash, sorted-by-identity
  projection, toggle round-trip fix carried (bug re-confirmed at
  `python/manifest.py:187-193`; enum's round-trip acceptance at
  `manifest.py:176-185` is the template).
- **D8** closed by Q3 + folding the show-reference foundation into §10.7.
  `clean_message`'s four-field whitelist still discards any added members —
  the model extension is real work inside that stitch, correctly named.
- **U1** genuinely dissolved by per-seat provenance — this is the addendum's
  best repair; order-independence holds by construction and the projection is
  the panel's existing mixed idiom (F8).
- **U2/U3/U4** carried intact in §8 (strict store, dashboard-state language,
  one canonicalization at the durable write boundary); U2 gains the entry
  whitelist (F4).
- **U5** closed by Q4 (facilitator row removed — supersedes `7-preset-slot`
  decision 1, to be recorded by name in the UI stitch) and the separate
  editor stitch §10.6; the offline-device-save sub-question remains (F8).
- **C1** closed by the application core; every caller routes through it.
- **C2** closed by the injected expansion callback; ShowEngine stays
  transport-only.
- **C3** is the rhetorical one — see F8, assign the cache explicitly.
- **C4** closed by the §10 shape, with the layout notes below.

## Layout (settled by the F1 ruling — morph dropped; stitches CREATED 2026-07-29)

The §10 seams are right; with morph deferred, §10.4 disappears and the layout
is **six stitches plus retirement**. Created zero-padded (`04-` … `10-`) so
the loom's lexical queue serves them in order:

1. `04-contract-and-schema` — the shrunken §10.1: ratify A3/A6 into the
   contract (v1.17) — `presets/` as a host-only patch subdirectory, the
   schema-fingerprint definition (ordered enum labels, sorted projection), the
   §8 capture sentence, and the one-line statement that a timed preset apply
   uses the existing fade grammar for float/int entries while
   generator/toggle/enum/text entries set at t=0. No new wire form.
2. `05-store-and-foundations` — §10.2 plus F5: strict atomic CRUD, cache
   (C3's explicit assignment), slug/conflict rules, entry-form whitelist
   (F4), schema projection and drift resolution, the shared ignore policy
   reaching `identity._walk_files`, `fetcher._prune`, **and
   `fetcher._file_fetch`**, hash-cache hygiene, the toggle round-trip fix,
   and the HTTP deny guard.
3. `06-application-core` — §10.3 plus F3/F6/F7/F8: patch-aware concrete
   targeting with the coalescing rule restated as a named-delta optimization,
   clamp/skip/snap report (period/shape-snap honesty), kind-aware timed
   apply (floats/ints fade, the rest snap), durable and automation state,
   generator replay with derived expiry (original `sent_at` preserved),
   estimate-documented `stop`, per-seat provenance with the lowest-group-id
   tie-break, one shared canonicalization.
4. `07-control-device-ui` — §10.5: list/apply/save/delete, include/exclude
   with mixed-omitted visibility (F8), derived dirtiness, drift inline,
   offline-device save disabled, and removal of the facilitator host's
   provisional row (recording the `7-preset-slot` decision-1 supersession by
   name).
5. `08-editor-save-recall` — §10.6 unchanged: the seat-0 sculpt→save path.
6. `09-show-integration` — §10.7; created as one stitch but split into two
   children at creation time per the first review's 8/9 boundary:
   `1-reference-foundation` (message-model extension, group-name invariant +
   adoption fix, portable named targets) and `2-preset-messages` (expansion
   via injected callback, `PRE` pill, atomic flatten, capture-as-step).
7. `10-venue-preset-retirement` — last, once every replacement path is live.

Dependencies: 4 gates everything; 5 then 6; 7 and 8 need 6; 9 needs 6 (no
morph-engine dependency remains); 10 is last.

## Higher-level assessment (Bob's ask)

The core is genuinely elegant and should not be touched: *a preset is the
argument lists it would send*, sparse, applied as ordinary fan-out, provenance
per seat with everything else derived. Every piece of that reuses an existing
idiom (mixed rendering, drift-derived-never-stored, one application path).

Complexity concentrates in exactly two places, and both are honest to
question:

1. **Morph** is ~a third of the implementation and all of its wire/engine
   risk, serving the generator-interpolation case; scalar morphing — the case
   operators will reach for — is the existing fade. F1 above.
2. **The five-outcome apply report** (applied/clamped/snapped/dropped/skipped)
   is the UX cost of "never error, always tell". It is the right policy; keep
   the report to one line with a disclosure, not a modal.

Use-case walkthrough (sculpt→save in editor; one-click apply per card;
tweak→save-as; capture-as-step; show morph step) found no friction the design
adds — the friction risks are presentation-level: the mixed-omitted save
(F8) and the misleading "everything interpolated" report (F4).

## Verification performed

Read: the addendum, tied proposal + decisions, first review, thread
instructions; `python/paramgen.py` (whole), `dashboard/static/js/paramspec.js`
(whole), `python/manifest.py:150-200`, `python/identity.py:31-130`,
`python/fetcher.py:80-275`, `python/groups.py:40-73`, `python/bopos.py`
dispatch region (~1385-1460) and inventory, `dashboard/osc_bridge.py:340-520`,
`dashboard/server.py:55-130, 810-860, 1500-1570`,
`dashboard/static/js/control-surface.js:40-300`, simfleet identity usage.
No implementation was changed; no tests were run (nothing to regress — this
stitch has produced only this document so far).
