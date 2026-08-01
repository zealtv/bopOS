# 06b-control-panel-atomic-mobile

Fix the narrow Control/Remote regression Bob found immediately after
`06-control-panel-reflow-and-editor`.

At `max-width:620px`, `facilitator.css` still applies the retired host layout:

```css
.live-param-range-wrap { grid-column:1/-1 }
.live-param-toggle .live-toggle,
.live-param-enum .live-enum { grid-column:1/-1 }
```

Those placement declarations survive the shared component's stronger
three-column template and force controls onto separate implicit rows. Remove
the host-owned reflow rules rather than adding a component override; Bob has
ruled that Remote collapses onto shared components, and the parameter row is
atomic.

Add a real narrow-facilitator browser assertion that all three numeric-row
objects share one vertical centre below the 620px breakpoint. Run focused,
fast, and browser verification. Record the screenshot finding and tie.
