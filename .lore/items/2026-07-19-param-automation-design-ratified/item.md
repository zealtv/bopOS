# Parameter automation design ratified

Bob's 2026-07-19 ratification of the generator-slot parameter-automation
design: one generator per numeric `/p/*` param (constant/fade/loop/LFO/stop,
last message wins), the extended arity grammar with string duration units,
`c:<n>` curve exponent, clock-anchored idempotent LFOs with `f` free-phase
opt-out, shorthand options canonical on the wire, int truncate-and-emit-per-
crossing, decomposition in bopos.py at 30–50 Hz, and the Show-tab builder /
animated-control / UX-gated waveform-viz plan. Strings/arrays deferred as an
unnamed non-param manifest kind.

## Source

Draft and braindump:
`.lore/items/2026-07-19-param-automation-generator-design/`. Second-round
rulings travel with stitch `automation-0-design-ratification`. Ratified by
Bob in-session, 2026-07-19.

## Status

**Ratified.** Authorizes thread `16-param-automation`, ordered after
`15-show-polish` with the dashboard-free stitches (contract §3 amendment,
bopos.py generator engine, simfleet parity) permitted to interleave. The
contract revision itself lands with the thread's first stitch.
