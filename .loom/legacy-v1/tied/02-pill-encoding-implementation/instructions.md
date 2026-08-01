# 02-pill-encoding-implementation

`01-pill-encoding-design` was ratified by Bob on 2026-07-23.

Build the ratified pill encoding in `dashboard/static/js/show.js` +
`dashboard/static/css/style.css`.

## Outcome

- `pillColourClass()` (`show.js:130`) stops hashing and starts deriving the
  pill's appearance from payload mode and generator per the ratified design.
- The encoding degrades correctly for the three modes with no generator.
- Renders per the design in **both** themes, at the token layer — no new hex at
  call sites.
- Focus, drag, and drop-target rendering still read correctly on an encoded
  pill (`.focused`, `.show-drop-before`, `.show-drop-after`, `.show-pill-drag`).
- The now-unused `.show-pill-0..7` palette and `PILL_PALETTE_SIZE` are removed,
  not left orphaned — including the light-theme repeats.

## Verify

Playwright per `CLAUDE.md`, from the `~/.venvs/bopos` venv. Copy the newest tied
dashboard guard as the template.

Cases: one fixture step carrying a message of each payload mode and each
generator kind — mind gotcha (10), changing the generator `<select>` writes
through onto the focused message, so use **one fixture message per generator
kind** rather than switching kinds in-test. Assert the rendered distinction in
both themes. Screenshots of a dense step row into the stitch directory for Bob.

Re-run the tied Show-tab and theme guards, including the two `21-theme-cyan-tint`
repaired ones. If a guard asserts on the old hash palette, it is superseded —
repair it in place with an inline comment naming this stitch and record the
ruling in `decisions.md` (see `.loom/tied/03-divider-rule-styling/decisions.md`).
