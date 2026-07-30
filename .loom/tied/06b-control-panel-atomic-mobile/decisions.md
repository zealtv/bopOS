# Decisions — 06b-control-panel-atomic-mobile

Date: 2026-07-30.

## Cause

Bob's post-`06` screenshot was genuine reflow below the facilitator's 620px
media breakpoint. The component's three-column grid still won the cascade, but
the old host rule separately assigned:

```css
.live-param-range-wrap { grid-column:1/-1 }
.live-param-toggle .live-toggle,
.live-param-enum .live-enum { grid-column:1/-1 }
```

Grid item placement and grid template selection are independent. The shared
template therefore remained three columns while those children were forced
onto implicit full-width rows—the exact screenshot.

## Fix

Delete the obsolete host-owned `.live-param` placement rules from
`facilitator.css`'s narrow media query. Do not counter them with stronger
component declarations: Bob already ruled that Remote collapses onto the
shared component language, and leaving dead layout policy in the host would
invite the same cascade leak on another kind.

The media query retains only genuine host concerns: page/card padding, header
spacing, and the Send-all size.

## Regression shape

The living ControlSurface browser journey now switches the real facilitator
document to 480 CSS pixels—below the offending breakpoint—and measures the
value box, slider, and modulation button. Their vertical centres must agree
within one CSS pixel and their x positions must remain ordered left-to-right.
