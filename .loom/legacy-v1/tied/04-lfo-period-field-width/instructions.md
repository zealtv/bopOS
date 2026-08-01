# 04-lfo-period-field-width

**Defect (Bob, 2026-07-21):** "In the message inspector, when the parameter is
set to an LFO, the number box defining the duration of the period is obscured by
the increment and decrement buttons. Space could be made for that by shrinking
the unit box."

The generator builder GUI shipped with `16-param-automation/automation-2`; the
unit box and spinner are part of the generator arg fields in the Show inspector.

## Outcome

- The LFO period value is fully legible with its spinner buttons present, at the
  inspector's normal (and collapsed-sidebar) widths.
- Bob's suggested remedy is shrinking the unit box — take it unless something
  better falls out; if you deviate, say why in the stitch.
- Check the *other* generator kinds' numeric args at the same time (ramp, random,
  etc.) — the same field geometry is likely shared, and a fix that only helps LFO
  is half a fix.

## Verify

Playwright, per `CLAUDE.md` gotcha 10: use **one fixture message per generator
kind** rather than switching the generator `<select>` in-test. Assert the period
input's rendered content width against its value's text width, or simply that
the input's box does not overlap the spinner's.
