# PD and engine boundary — design-session brief

This brief distils Bob's 2026-07-11 PD patching observations into questions for
a later higher-capability design session. It records tensions, not decisions.
The verbatim source is the lore item
`.lore/items/2026-07-11-pd-engine-boundary-brain-dump/`.

## Scope guard

Do not resolve these questions opportunistically during the current PD rewrite.
Finish and verify the ratified OSC seam first. Then use this brief to frame a
cross-engine design conversation covering PD, SuperCollider, openFrameworks,
and future engines.

## Questions to settle

### 1. What is the engine abstraction?

- Define the exact responsibilities of the patch-facing bopOS abstraction.
- Decide whether `bopos.osc.pd` should become the broader `[bopos]`/`bopos.pd`.
- Specify equivalent surfaces for SC, openFrameworks, and other engines.
- Separate transport plumbing from patch-provided terms and engine behavior.

### 2. Who owns command ingress?

- PD currently receives LAN commands, selector-routes them, then forwards
  lifecycle/provisioning verbs back to helper on 7770.
- Decide whether helper should own LAN administration directly, leaving the
  engine abstraction with only a selector-free local surface.
- Preserve a migration path for working installations rather than silently
  deleting the current bridge.

### 3. How should IO be separated?

- Retain the performance benefit of separate ports for potentially high-rate
  I2C/peripheral traffic.
- Keep `/io` control forwarding to `io/main.py:8880` for lights, actuators, and
  peripheral administration.
- Define a clear engine-neutral IO surface and direction names. Current PD
  names `to-bopos-io` and `from-bopos-io` are promising local vocabulary.
- Account for SC and other engines needing multiple local sockets without
  turning every starter patch into bespoke port plumbing.

### 4. What should local buses be called?

- `osc-in`/`osc-out` are vague and mix transport direction with ownership.
- Reserve the `bopos-` prefix for framework-owned patch-global sends and
  receives. The emerging `bopos-notify`, `bopos-cue`, and `bopos-points`
  names make the legacy `ID` and `osc-in` buses visibly inconsistent.
- Candidate vocabulary should distinguish patch-to-framework,
  framework-to-patch, IO, reports, notifications, and raw/parsed OSC.
- Names such as `from-bopos` and `to-bopos` are clearer but may overstate what
  is on each bus; settle semantics before renaming.

### 5. Who owns identity and run context?

- Identity, assignment, positions, active patch, random seed, and run timing
  appear across helper, shell startup messages, and PD globals.
- Decide what is framework state, what a patch may subscribe to, and how it is
  delivered consistently to every engine.
- Keep absolute time out of PD floats; use strings or an engine-neutral run id
  if time/date context is genuinely required.

### 6. What are meters?

- **Ruling (Bob, 2026-07-11): meters are not mission-critical — dropping them
  entirely is a valid solve.** See "Bob's rulings and taste" below.
- Decide whether a meter is measured audio telemetry, arbitrary patch-authored
  feedback, or both as explicitly different declaration types.
- Specify scope: whole device, output channel, or 0-based element.
- Specify subscription/lifecycle so meters are off by default or demand-driven
  where fleet scale would make continuous reporting expensive.
- Set rate limits, aggregation, silence behavior, and bandwidth budgets for
  large fleets with multiple elements.
- Preserve synthetic feedback as a useful patch-authored dashboard surface
  without mislabelling it as physical output level.
- The 2026-07-11 three-PD Mac run found that PD's legacy report connection to
  `255.255.255.255:5550` fails with macOS error 49 even though the local meter
  emits `level <value>` correctly. Separate meter semantics from the report
  transport fix; test directed-broadcast/unicast alternatives deliberately.

### 7. What debugging surface replaces cruft?

- **Known real use (Bob, 2026-07-11):** capacitive touch data forwarded from
  `io/main.py` through PD to the PD dashboard via `/rpt` — useful but messy;
  consider a report-on-request model. See "Bob's rulings and taste" below.
- Audit legacy echo/report behavior against OSC contract v1.1.
- Preserve useful inspection of sensor and OSC values through an intentional
  diagnostic facility rather than permanent broadcast chatter.
- Remove or gate development prints such as PX/PY once an equivalent debug
  workflow exists.

### 8. Naming and process boundaries

- Consider whether `helper.py` should become `bopos.py`, but only alongside a
  clarified role; a rename alone does not repair the boundary.
- Document ports as ownership boundaries and performance choices, not historical
  accidents.

## Bob's rulings and taste (2026-07-11, pre-council)

These are inputs from Bob, recorded before the council session. Treat them as
constraints and priors, not open questions.

- **Meters are not mission-critical.** If ditching meters entirely is a solve,
  that is a valid design outcome. Do not contort the boundary to preserve them.
- **The real echo use-case:** in the plant installations, the stream of
  capacitive touch data was forwarded from `io/main.py` through PD and back out
  to the PD dashboard for debugging. That worked but is messy as implemented —
  the `/rpt` address and the circuitous OSC path. Bob suspects this points at a
  broader **report-on-request model** rather than the current permanent
  forwarding chain; the council should evaluate that framing.
- **Taste criterion for the ruling:** simple, clean, understandable, and
  performant. Prefer the design that a patch author can hold in their head over
  one that preserves every existing capability.

## Evidence to bring to the design session

- OSC contract v1.1 and the patch-seam council record.
- The tied macOS port-sharing spike and audition relay results.
- Packet-rate estimates for device/element meters and I2C streams.
- The current PD rewrite and SC starter side by side.
- A list of which legacy echo/print paths are still used in real debugging.
  (Answered 2026-07-11: the capacitive-touch `/rpt` chain described in "Bob's
  rulings and taste" is the known real use; treat other echo/print paths as
  presumed-unused unless the repo shows otherwise.)
