# Bob's second-round rulings, 2026-07-19 (same day as the proposal)

These amend the draft proposal in
`.lore/items/2026-07-19-param-automation-generator-design/content/design-proposal.md`
and resolve most of its §9 open questions. Fold them into the ratified
record when this stitch ties.

1. **Option shorthand.** `curve:` / `phase:` / `free` get short forms
   `c:<n>` / `p:<0..1>` / `f`. Short forms are canonical on the wire (the
   dashboard emits them — bandwidth is the driver; OSC strings pad to
   4-byte boundaries so `c:2` is half of `curve:2`); long forms remain
   accepted aliases for hand-typed messages. No `ph:`/`fr` needed: options
   only appear trailing a keyword-led message, so one-letter prefixes are
   unambiguous there.
2. **Keyword/option ordering ratified**: keywords lead (`loop`, `lfo`,
   `stop`), options trail (`p:`, `f`, `c:`).
3. **LFO emission control-rate ratified**: 30–50 Hz "fine for now until it
   isn't".
4. **Int semantics ratified**: truncate (floor), emit exactly once at each
   integer crossing (the value's decimal point crossing zero), in either
   direction.
5. **Musical notation dropped** from the wire entirely (already in the
   proposal) — Bob confirms. **No per-segment curves** — Bob confirms he
   doesn't need them; drop from the deferred list if convenient.
6. **"Atom" is probably not the name** for the string/mixed-array kind —
   feels wrong for multi-part values. Candidates: attribute, property.
   Also open: whether it needs its own plane (`<selector>/a/*` for
   attribute) instead of sharing `<selector>/p/*`. Explicitly deferred —
   note it for the deferred stitch, do not decide now.

Still open for ratification: the grammar as a whole (Bob has not yet read
the full proposal text as a document).
