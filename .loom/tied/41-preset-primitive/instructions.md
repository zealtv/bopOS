# 41-preset-primitive

Re-found presets as a manifest-scoped primitive. From Bob's 2026-07-24
patching-session braindump (lore `2026-07-24-patching-session-braindump`),
extended same-day in conversation with the Show-tab trigger + interpolation
idea.

The vision: a preset belongs to a patch and its manifest and applies to a
single device/seat. Collections of presets compose onto groups/seats/all.
Save a preset from the patch editor's control panel while sculpting the
patch; load it from the Control tab onto a seat, a group, or everything.
Trigger presets from the Show tab as sequenced actions — and, powerfully,
**interpolate into a preset over time**: an optional duration + curve, so a
show step can morph the fleet's state rather than snap it.

Today's dashboard presets are dashboard-side parameter snapshots; this
thread moves preset identity into the patch/manifest layer. Bob explicitly
asked for an architectural evaluation, not a straight port.

Child `1-preset-architecture-design` is the Bob-gated design stitch;
implementation stitches follow ratification.

**RATIFIED AND TIED 2026-07-28.** The design is
`.loom/tied/1-preset-architecture-design/proposal.md`, with Bob's four
rulings in `decisions.md`. Headline: a preset is not a wire concept — an
entry is the `/p/<identity>` argument list, stored sparsely in
`patches/<patch>/presets/<slug>.json` and applied as an ordinary fan-out.
`presets/` is excluded from the distribution fingerprint; interpolation is
the additive `morph <dur> <spec…>` grammar form; capture-as-step omits
un-preset targets; the applied marker is stored provenance with derived
dirtiness. Contract delta proposed as v1.17.

**Reviewed and revised 2026-07-28.** `2-proposal-review` is tied
(`.loom/tied/2-proposal-review/review.md`) and found real defects: the `morph`
form was grammatically ambiguous, its phase maths was wrong, `presets/`
exclusion did not reach `fetcher._prune`, generator state never replayed to a
rejoining seat, and an All-scoped apply could write into a pinned device
running a different patch.

**`design-addendum.md` in this directory revises the tied proposal** and is
authoritative where the two differ. It closes every finding, notably: a
wrapper's arguments precede the message it wraps (`morph <dur> [c:<n>]
<spec…>`); **magnitudes interpolate, anything defining time or shape takes the
destination at t=0** — which keeps the generator clock-anchored and idempotent
throughout a morph instead of needing a phase accumulator; unalignable pairs
snap and are reported; apply resolves to concrete seats and filters by
effective patch; provenance is stored per concrete seat so no ordered ledger
is needed.

**All four addendum questions are RULED (Bob, 2026-07-28, §9):** morph keeps
its curve via leading options; the preset file carries the schema fingerprint
only (the *show* message carries patch `{name, fingerprint}`); venue group
names become non-empty and unique; and the standalone facilitator gets **no
preset affordance at all** — which means the provisional row shipped by
`7-preset-slot` must be *removed* from the facilitator host, superseding that
stitch's decision 1.

**Reviewed 2026-07-29 — and MORPH IS DROPPED FROM V1 (Bob).**
`.loom/tied/3-addendum-review/review-2.md` attacked the addendum's repairs: none broken,
but its F1 surfaced that the whole morph apparatus serves only
generator-argument interpolation while scalar morphing is the existing fade
grammar. Bob ruled: defer morph to `feature-backlog/48-morph-interpolation`
(which carries the settled design for revival). **Timed preset apply ships
as: float/int entries fade via the existing `x <dur> c:<n>` form;
generator/toggle/enum/text entries set at t=0 and are counted in the apply
report.** The contract delta shrinks to the `presets/` exclusion + schema
fingerprint + capture sentence — no new wire form, no engine work. The
review's other findings (coalescing named-delta, `_file_fetch` in the ignore
policy, derived replay expiry, estimate-documented `stop`, entry whitelist)
fold into the six-stitch layout in review-2.md §Layout, which supersedes
addendum §10.

**`3-addendum-review`** — Bob placed one more review, and **that one
flows straight into implementation**: it attacks the addendum's own repairs
(which have had no adversarial pass), then lays out the stitches from addendum
§10 as real children numbered from `4-` and starts working them. There is no
further design gate. It stops for Bob only on a defect in one of his rulings,
a wire-grammar ambiguity a contract amendment would ratify, or a change big
enough to break the §10 shape.

**The implementation stitches are CREATED (2026-07-29)** and specced for an
independent implementing agent: `04-contract-and-schema` →
`05-store-and-foundations` → `06-application-core` → `07-control-device-ui`
∥ `08-editor-save-recall` → `09-show-integration` (children
`1-reference-foundation` then `2-preset-messages`) →
`10-venue-preset-retirement`. Work them in numeric order (07/08 are
parallel after 06); each stitch's `instructions.md` names its authority
docs, scope, file:line anchors, and verification. `3-addendum-review` is
tied.

**IMPLEMENTATION STATUS 2026-07-29:** `04` through `10` are tied. Patch
presets now span storage, application, desktop Control/Device/editor surfaces,
and Shows; the retired installation-scoped venue-preset store, websocket
verbs, desktop shelf, and standalone facilitator affordance are gone. The
later-added `11-browser-test-failures` is the only remaining child before this
thread can tie.

**Architecture gate CLEARED 2026-07-27**: `entity-architecture-review` is
tied. The preset design proceeds on the ratified four-layer model — see
`.notes/entity-map-2026-07.md` (as-is map) and the tied
`2-workflows-and-simplification` proposal.md/decisions.md. Bob ratified
in-session: venue presets **retire** when this thread lands (store is empty,
no migration — settles Q8); collections start as **show steps / step
templates**, not a new store (reshapes Q5); shows will reference groups **by
name** and content by `{name, fingerprint}` with derived non-blocking drift
warnings (the drift policy of Q1/W5); one application path with hard
takeover is the global rule. The mockup's provisional preset row (dropdown +
new/save/del at the control-panel top) is UI input for the design stitch.
**Re-sequenced same day (Bob, 2026-07-27): `44-event-plane` comes first**,
because a preset must know what it captures for each kind. The design stitch
here stays `.waiting` behind `desktop-ui-overhaul/01-control-panel` and
`44-event-plane/1-event-plane-design`.

**What 44 already settles for this thread (Bob, 2026-07-27 — don't re-ask):**
toggles, integers, and enums all exist today and are captured as ordinary
values (a toggle is `type: "i"` 0–1; an enum is an integer index with
`options` labels). **Presets do not capture events** — events are momentary,
and the question is closed for the moment. The one thing still coming out of
44 is the explicit `kind` grammar (a ratified hard break replacing
`type` + `options`), which this thread should express presets in terms of.

**Additional design input (Bob, 2026-07-27): capture-as-step.** From the
Control tab, once presets are set up targeting different groups/seats, one
click stores the current target→preset arrangement as a **show step** — the
authoring path for "meta presets", closing the ratified "collections start
as show steps" ruling. The design stitch's Q6 (show integration) must cover
this capture flow: what exactly is snapshotted (the target→preset mapping;
current values for targets without a preset applied?), and where the button
lives (coordinate with the control-panel design's preset row).
