# Parameter automation braindump and generator-slot design proposal

Bob's 2026-07-19 braindump on timed fades, units, curves, LFOs, and animated
dashboard controls, plus the same-session design conversation and the
resulting draft proposal: one generator slot per numeric `/p/*` param
(constant / fade / LFO / loop, last message wins), `curve:<n>` exponent,
authoring-layer musical units, clock-anchored idempotent LFO phase,
decomposition in bopos.py, strings/arrays deferred as a non-param "atom"
manifest kind, and a UX-gated waveform visualisation for automated controls.

## Source

Bob, 2026-07-19, verbatim in `content/braindump-2026-07-19.md` including his
rulings on the agent's six pushbacks. Worked design in
`content/design-proposal.md`.

## Status

**Draft — awaiting Bob's ratification.** Direction agreed in conversation;
the exact grammar and the implied contract revision (§3 shorthand registry;
later §8 atom kind) are not ratified. Explicitly separate from the
`15-show-polish` sweep — tracked as its own thread, `16-param-automation`,
whose design stitch is `.waiting` on this ratification. Open questions are
listed in the proposal's §9.
