# Ratified — per-parameter generator affordance (Bob, 2026-07-25)

Bob ratified `proposal.md` with all three open questions settled. This stitch is
a design gate; its ratified content is the authority for the implementation
stitch `8-generator-drawer`.

## Ratified design

Every numeric control carries a two-state **mode switch — `value ▸ gen`**. The
control keeps one param address in both modes; only the authoring mode changes.

### 1. Drawer, not popover — everywhere

**Bob:** "drawer".

Flipping to `gen` opens an **inline drawer** below the row, hosting the extracted
`automation-2` builder (waveform / rate / depth / center / phase + the ratified
`16-param-automation` waveform preview). This holds in *all* hosts — patch
editor, Device tab, and the dense All aggregate on the Control tab. The proposal
floated a popover variant for the dense aggregate; that variant is **dropped**.
One affordance, one implementation, no host-conditional behaviour.

### 2. Mixed aggregate — existing pattern, no new rule

**Bob:** "when members disagree use the existing pattern. adjusting the
parameter — either as a value or a generator, then sets all members. same
behaviour as before."

So the aggregate does **not** disable when members disagree, and generators are
**not** a special case:

- disagreement is *indicated* using whatever the promoted-control aggregate
  already does for mixed values (stage-7 behaviour — reuse it, do not invent a
  second indication);
- **any** adjustment — moving a value, or committing a generator — is a
  broadcast that sets every member of the current scope;
- after the adjustment the aggregate is, by definition, no longer mixed.

The implementation must reuse the existing mixed-aggregate code path rather than
branch on `mode === 'gen'`.

### 3. Stop lives inside the drawer

**Bob:** "a stop control inside the drawer".

The mode switch stays strictly two-state (`value` / `gen`). Stopping a running
generator is a **control inside the drawer**, not a third segment. Rejected
alternative: a `value ▸ gen ▸ stop` three-state segment — it conflated "which
authoring mode am I in" with "is the generator running", which are independent.

Stop emits the ratified `/p/*` stop grammar (contract §3.2); what the value
settles to on stop is already the grammar's business, not this design's.

## Seam to 41 (preset primitive)

Unchanged: what a generator means *inside a preset* — capture, reload,
interpolation — remains 41's design. This stitch settles live authoring only.
Bob's ordering stands: this affordance lands **ahead of** 41.
