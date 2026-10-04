# Dashboard names and UI rules

When writing dashboard UI or prose, use the shipped names and the ratified design rules.

- The **Control** tab (formerly Dashboard; `#dashboard` still resolves) holds target cards: each card targets exactly one thing — all, a group, or a Seat — laid out in a grid, ordered all → groups → Seats. **Remote** is the standalone facilitator/iPad view and is the same surface.
- Installation notices render once in a persistent text status strip below the main tab bar on every tab, and below the standalone Remote header (Bob, 2026-10-03). No dismiss or repair action; Show keeps only its own target/drift warnings.
- Audio modes are **Live**, **Simulation** and **Patch Edit** (the editor's local audition engine) — the header's mode switch, right after the Project · Site · Patch bar. *Live Fleet* was renamed **Live** (66-projects, 2026-10-04); "Live fleet" in prose still means the real devices.
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
- Patch edit

## Associations

- [[ws-snapshot-handlers]]
- [[playwright-gotchas]]
