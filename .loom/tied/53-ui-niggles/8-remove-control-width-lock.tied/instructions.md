# 8-remove-control-width-lock

Correction from Bob's screenshot review of the Control tab:

> the control tab cards seem to be locked at their minimum width

## Cause

The retired horizontal-column layout left this high-specificity declaration in
the old compact block of `style.css`:

```css
#control-column-host>.control-column { flex:0 0 342px; }
```

The new component rule is `.target-card.target-card`, which cannot beat an ID
selector regardless of source order. Control cards therefore compute to
`flex-grow: 0` and remain at 342px. Remote does not use this direct-child shape.

## Scope and verification

- Reset the direct child's flex at the active Control layout boundary so the
  shared 340–560px component bounds can operate.
- Guard the computed-growth override in the browser-free layout contract.
- At a wide viewport, require four Control cards to grow materially beyond
  340px; retain the existing 1200px sparse-row left-alignment check.
- Run fast and attempt the focused browser journey before tying.
