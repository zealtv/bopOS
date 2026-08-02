# 5-left-packed-flex-cards

Follow-up from Bob's review of `4-card-strokes-and-remote-bar`:

> cards should be left aligned - not leaving a big void in the middle. let's
> let the cards width flex between min 340 and max 560.

## Scope

- Apply the same wrapping, left-packed layout to Control and Remote.
- Let each rendered target card grow from 340px to 560px.
- Below 340px, preserve the existing responsive behavior and fit the available
  width rather than forcing horizontal page scroll.
- Replace the previous fixed-ceiling grid track and `space-between` rule; the
  unused space belongs at the right edge, never between sparse cards.

## Verify

- Update the browser-free layout contract for the 340–560px flex bounds and
  explicit left packing.
- Update the focused browser measurements for both hosts.
- Run `./tools/run-tests.sh fast`; attempt the focused browser journey and
  record any managed-sandbox boundary honestly.
