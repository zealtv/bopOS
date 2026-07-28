# 3-addendum-review

The **last gate before building**. Review the repaired preset design against
the code, then — unless something blocks — lay out the implementation stitches
and proceed. Bob placed this stitch knowing it flows straight into
implementation; there is no further design gate after it.

## Subject

- `.loom/threads/41-preset-primitive/design-addendum.md` — **authoritative**
  where it differs from the proposal.
- `.loom/tied/1-preset-architecture-design/` — proposal.md + decisions.md, the
  ratified base.
- `.loom/tied/2-proposal-review/review.md` — the first review, whose findings
  the addendum claims to close.
- Thread context: `41-preset-primitive/instructions.md`.

## Not up for re-litigation

F1–F4 from `decisions.md`, the earlier entity rulings, and Bob's four addendum
§9 rulings (morph keeps its curve via leading options; the preset file carries
the schema fingerprint only while the show message carries patch
`{name, fingerprint}`; venue group names become non-empty and unique; the
standalone facilitator gets no preset affordance at all).

As before, the one exception is evidence that a ruling is **unimplementable**
or carries an uncosted consequence. That is blocking — stop and surface it.

## Two jobs, in order

### Job 1 — attack the addendum's new claims

The first review hardened the proposal. The addendum's *repairs* have had no
adversarial pass at all, and they are where the risk now is. Each of these is
falsifiable; check it against the code rather than reasoning from the prose:

1. **The leading-option morph form parses unambiguously.** `morph <dur>
   [c:<n>] <spec…>`, remainder handed verbatim to the existing parser. Walk it
   through `python/paramgen.py` and `dashboard/static/js/paramspec.js` for
   every destination kind, including a destination whose own options trail and
   a destination that is itself a bare number. Does "at most one leading
   `c:`" stay decidable when the destination is a segment list starting with a
   number, or a `stop`? Is `morph` reachable on int/enum/toggle/text paths
   without a special case?
2. **"Magnitudes interpolate; time and shape snap" is actually continuous.**
   The claim is that with `period` fixed at t=0 the running generator is a
   valid clock-anchored LFO at every instant, so no phase accumulator is
   needed and catch-up can send the current interpolated spec. Verify against
   the real phase math (`python/paramgen.py:284-305`) — including the moment
   of the t=0 shape/period switch, the settle at completion, and an int/enum
   param quantizing through it. Does lerping `phase` alongside a fixed period
   really stay continuous?
3. **Snap-and-report covers every pair the store can produce.** Enumerate what
   a preset entry can actually hold given the capture rules, and confirm every
   source→destination pair either interpolates or snaps, with none falling
   through. Watch `stop` and text entries specifically.
4. **Per-seat provenance reproduces the arrangements people will make.** Try
   overlapping groups, a seat in two groups, a seat with no preset, and a
   preset applied then partly overwritten. Does the card projection ("all its
   seats agree, else mixed") match what `control-surface.js` already does for
   mixed values? Does capture's target derivation (all → `all`, exact group
   membership → group name, else seat list) hold when two groups have
   identical membership?
5. **Patch-aware targeting and the coalescing rule.** "Coalesce to the
   original selector only when nothing was skipped" — is that provably
   equivalent for `all` and for `gN`, given how `_selector_seats` and node
   dispatch actually behave? What does it do when a seat is unbound or its
   device is offline?
6. **The `stop`-value computation is right.** The addendum has the dashboard
   evaluate the generator at stop time and store the held value. Check that
   against how the node actually freezes (`python/paramgen.py:201-207`) —
   including a free LFO with device-local phase, where the dashboard cannot
   know the node's output.
7. **Generator-preferring replay is safe.** Replaying full-state automation
   args on rejoin instead of a scalar — verify against `set_param`'s automation
   bookkeeping and the fade special case, and confirm it cannot resend a
   completed fade as a live one.
8. **The shared ignore policy genuinely covers every consumer.** The first
   review found `fetcher._prune`. Sweep for any *other* walk that enumerates
   patch files — HTTP serving, inventory, run context, hash cache, the
   simulator.

Also confirm, don't assume: that the addendum's closures for the first
review's D1–D8, U1–U5 and C1–C4 actually land, and note any it answered
rhetorically rather than fixed.

### Job 2 — lay out the implementation stitches and begin

If nothing blocks: create the stitches from addendum §10 as real loom stitches
under `41-preset-primitive`, adjusted for whatever Job 1 found — merge, split
or reorder them where the evidence says so, and record why in the review
document. Then claim the first one and work it.

`3-` is taken by this stitch, so the implementation children number from `4-`.
Keep the dependency order visible in the names, per the loom's ordering rules.

**Stop and surface to Bob**, rather than building, if Job 1 finds: a defect
in one of his four rulings; an ambiguity in the wire grammar that a
contract amendment would ratify; or a change large enough that the §10 shape
stops making sense. Anything smaller is yours to fix in the layout.

## Deliverable

`review-2.md` in this stitch directory, before any implementation commit:

- **Findings** against the addendum's new claims, most serious first, each with
  evidence at `file:line`, what breaks, and the fix you applied or recommend.
- **Confirmed closures** — which of the first review's findings genuinely land,
  stated briefly, so the implementation can rely on them.
- **The stitch layout you created**, and any deviation from §10 with its
  reasoning.
- **Anything surfaced to Bob**, if the gate tripped.

Then implementation proceeds normally: claim, work, verify, tie, one stitch at
a time. `tools/run-tests.sh fast|browser|all` is the pre-tie check. Do not
amend the OSC contract until Job 1 has closed the grammar questions — that is
the first stitch's whole purpose.

## Carry into the work, not to rediscover

- **Two pre-existing bugs**, both independent of presets and both surfaced by
  the first review: toggle manifests do not round-trip (`python/manifest.py:187`
  rejects any present `min`/`max` on a toggle, then writes `min=0, max=1`
  itself — enum has exactly this round-trip treatment and toggle was missed),
  and `DistributionStaticFiles` (`dashboard/server.py:60`) would serve
  `/patches/<name>/presets/…` to a hand-built URL. The toggle fix belongs
  before anything hashes normalized manifests.
- **Q4's consequence:** `7-preset-slot` shipped the provisional preset row into
  *both* hosts of the shared `ControlSurface`. "No presets on the iPad" means
  removing it from the facilitator host, superseding that tied stitch's
  decision 1 — record the supersession by name, per CLAUDE.md's interim rule.
- **Q3's tail:** the non-empty/unique group-name invariant needs a one-time
  adoption path for existing venues with blank or duplicate names.
