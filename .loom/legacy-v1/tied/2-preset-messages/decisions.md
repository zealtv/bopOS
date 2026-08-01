# Decisions — 2-preset-messages

Date: 2026-07-29.

## Reference and playback boundary

`/preset/<patch>/<slug>` is a strict Show-only reference. Its optional numeric
duration is milliseconds and an optional trailing `c:<finite>` token requires
that duration. The reference carries the current patch content fingerprint and
the preset file's authored schema fingerprint. Drift in either is derived and
non-blocking.

`ShowEngine` recognizes this one reference family and calls an injected
dashboard callback. It still reads no patch, preset, group, or Seat state.
Dashboard callbacks serialize through the supervisor lock, resolve portable
targets to concrete Seats, and enter `Dashboard.apply_preset`; expanded
`/p/*` sends therefore retain the ordinary Monitor tap and application report.

## Authoring and expansion

The Show inspector lists presets for the message's patch from catalog metadata
and writes both fingerprints when authoring. `PRE` is the ninth flat pill
category; a duration adds the established cyan “driven” treatment.

Flatten resolves the referenced preset against the current manifest, applies
the same canonical and timed-kind rules as recall, and replaces the reference
with literal `/p/*` messages in one model mutation. It is deliberately current
resolution rather than a stale authored snapshot: flatten is the explicit
moment the operator chooses concrete editable values.

## Capture-as-step

Capture uses the Control iframe's current All / Groups / Seat filter. Preview
states applied, total, and omitted Seat counts before a confirmation can send
the mutation. Applied provenance is grouped by `(patch, preset name)` regardless
of derived dirtiness. Exact target sets project to `all`, then the lowest-id
equal group stored by name, then sorted Seat ids. The entire new step is one
`apply_show_mutation` call and one undo entry.
