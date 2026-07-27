# entity-architecture-review

Bob, 2026-07-27 (lore
`2026-07-27-control-panel-ui-and-architecture-braindump`): before the preset
primitive is implemented, take a holistic look at how the system's entities
relate — devices, seats, groups, pinning/controls, patches + manifests,
presets, shows — and find the simplest model that stays flexible and can be
held in one's mind. He smells complexity around devices/seats/pinning/
controls and expects presets to exacerbate it.

Known pressure points to examine:

- Shows will load patches mid-show (fleet-wide or per-device) and then
  sequence that patch's params and presets — so show ↔ patch/manifest and
  show ↔ seat-targeting couplings need to be deliberate, not accidental.
- Seat presets are site-specific and plausibly standalone; shows reference
  patches/presets and target seats; seat targeting may change show-to-show
  or seats may simply be repositioned. Avoid loopy dependencies among
  patches, patch presets, show files, and seat presets.

Hard constraint: **the system works today and must remain working.** The
output is understanding + small ordered changes that keep things clean —
not a rewrite.

Order: `1-system-map` (as-is documentation) then
`2-workflows-and-simplification` (workflow walkthroughs + proposal; ends in
a Bob review session). This thread **gates
`41-preset-primitive/1-preset-architecture-design`** — the preset design
proceeds on the reviewed model. It runs in parallel with or after
`desktop-ui-overhaul/01-control-panel`, which Bob put first.
