# 9-equal-card-tracks

Final card-layout review from Bob:

> I'd like all of the cards to be the same width, whatever that width happens
> to be. So, if there is a lone card at the bottom row, it shouldn't be wider
> than any of the other cards, it should be the same width as all of the other
> cards on the tab.

## Scope

- Use equal grid tracks on Control and Remote so every row shares one column
  width, including an incomplete final row.
- Preserve left alignment and the responsive 340–560px bounds.
- Cap each grid's width from its current card count so one or two cards stop at
  560px without stretching tracks across the whole viewport.
- Keep Remote's structural wrapper and sticky audio bar unchanged.

## Verify

- Browser-free guards cover the shared grid formula and both count-derived
  caps.
- At 1200px, both surfaces render four cards as three equal cards plus one
  final-row card of exactly the same width.
- Run fast and the real focused Playwright journey before tying.
