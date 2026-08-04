# Decisions

- Replaced fixed grid tracks with a wrapping flex row. This is the direct model
  for Bob's requested behavior: each card grows between two bounds, while a
  sparse final row remains packed against the left edge.
- The target-card component owns `flex-basis: 340px` and `max-width: 560px` in
  `card-identity.css`. Both Control's outer card shells and Remote's derived
  live cards already carry `.target-card`, so the dimensions travel with the
  component rather than being restyled by either host.
- Both host containers own only placement: wrapping, left justification,
  alignment, and gap. Below 340px, `min(340px, 100%)` and
  `min(560px, 100%)` preserve viewport fitting.
