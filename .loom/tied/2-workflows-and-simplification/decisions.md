# Decisions — 2026-07-27, Bob, live interactive session

Bob supplied the workflow facts (quoted in proposal.md §1) and ratified the
proposal's model and all three forks in-session:

- **The four-layer model stands**: hardware (registry) → site (venue) →
  content (patch folder) → composition (shows); rules R1–R5 (one
  application path with hard takeover; fingerprinted content references with
  derived, non-blocking drift; portable shows target groups/all; sound
  identity in the patch, mix state in the site; verdicts derived never
  stored).
- **F1 — groups resolve by name.** Shows store group targets as *names*,
  resolved against the venue at load, warning on misses. Group names become
  the compositional API for portable shows. (Wire selectors stay `g<id>`;
  the name→id resolution is dashboard-side at load/play time.)
- **F2 — venue presets retire when 41's patch presets land.** The store is
  empty today; no migration. One preset concept in the system; the mockup's
  provisional preset row becomes the patch-preset UI.
- **F3 — drift warnings surface in the Show tab AND on show load.** Same
  derived check, two surfaces.

Also settled by Bob's workflow answers (proposal §1–§2):

- Show-triggered patch switching starts **between sections**; per-device
  later; multi-simultaneous-patches is a noted door (node active-patch
  seam), only if elegant, not designed now.
- "Meta preset" = a step whose messages apply different presets to different
  targets — **collections start as steps/step templates, not a new store**.
- Scatter/density is scene-sequencing input; identified slot: dashboard-side
  target-set resolution above the selector layer.
- Pin/fleet-patch clunk is a UI problem, not a semantic one → input to
  `desktop-ui-overhaul`.

Consequence: `41-preset-primitive/1-preset-architecture-design` is un-gated
and designs on this model. The small ordered changes (proposal §4) are
implementation candidates to be laid out as stitches where not already
covered by 41.
