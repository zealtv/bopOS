# Dashboard names and UI rules

When writing dashboard UI or prose, use the shipped names and the ratified design rules.

- The **Control** tab (formerly Dashboard; `#dashboard` still resolves) holds target cards: each card targets exactly one thing — all, a group, or a Seat — laid out in a grid, ordered all → groups → Seats. **Remote** is the standalone facilitator/iPad view and is the same surface.
- Monitor dock holds master fader, MUTE ALL and event lead time (Globals).
- Colour: `cyan` means modulation ("something is driving this"); `--amber` + `⚠` is warn. Marks lead a label so ellipsis never hides them.
- Design-language §12: `--bg` is ground, visible only between cards; a bordered region with a transparent background is the mistake.
- Component CSS belongs to the component, not to the surface it's mounted in — `tests/test_css_component_ownership.py` enforces it.
- Glyphs like `⌫ ⟳ ↥` render as tofu in headless Chromium; stick to the set the app already draws (`✕ ⧉ ✛ ╱ ▸ ▾`) and basic arrows.

## Triggers

- Control tab
- Remote
- facilitator
- target card
- design-language

## Associations

- [[ws-snapshot-handlers]]
- [[playwright-gotchas]]
