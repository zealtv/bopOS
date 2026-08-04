# Decisions

- Remote's derived `ControlColumn` is now an explicit unpainted full-width
  wrapper. Its `.control-column-cards` child is the wrapping, left-packed flex
  container, so the `.live-card` elements are direct flex items in a dependable
  formatting context.
- The shared `.target-card` component continues to own the 340px basis and
  560px ceiling. No Remote-only card sizing was introduced.
- The selector is host-specific only for placement and neutralizing the
  structural wrapper; the component ownership guard confirms it does not
  restyle `.live-card`.
