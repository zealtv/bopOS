# 03-responsive-osc-terminals

Lay out the outgoing and incoming OSC terminals side by side wherever each can
remain operationally readable, and stack them vertically on narrow displays.

## Outcome

- Use equal-width columns at the wide layout; switch to outgoing-then-incoming
  stacking at a content-driven breakpoint (the UI review suggests roughly
  900px, to be ratified in `01-layout-review`).
- Give expanded terminals the same fixed overall height. Keep summary and
  filter/action rows fixed while each monospace log fills the remainder and
  scrolls internally; live traffic must never grow the panel or page.
- Collapsed terminals remain summary-height and continue to expand
  independently. Preserve filter, pause, clear, count, auto-scroll, and current
  default-open behavior.
- Long OSC frames scroll or wrap inside their own log without widening the grid
  or causing page-level horizontal overflow.

## Verification

Focused Playwright must prove equal top/height at wide desktop width, correct
source order and full width when stacked, stable panel height under sustained
traffic, independent internal scrolling and collapse, retained terminal
controls, light/dark contrast, and no horizontal page scroll. Exercise at least
1280px, a tablet width, and 768px; retain wide and narrow screenshots and run
the existing OSC-console and Show dense-layout regressions.
