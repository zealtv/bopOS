# Decisions

- Corrected the selector rather than changing layout strategy again. The live
  server proved the intended CSS was current; reading the constructor call
  proved `#control-column-host` and `.control-column-derived` are the same
  element on Remote.
- The same-element host is now an unpainted, uncapped structural block. Its
  direct `.control-column-cards` child owns Remote placement and is an explicit
  wrapping flex container. Individual `.target-card` elements still own the
  shared 340–560px bounds.
- The browser-free guard now rejects the incorrect child-selector shape that
  passed stitch 6.
