# Decisions

- `preset_dirty` is now a nullable reason token: `deviated`, `missing`, or
  `foreign-patch`; `None` means the applied preset still matches. These names
  follow the three states identified by the UX consult and keep truthiness for
  existing clients until the dropdown-menu stitch adds distinct treatments.
- A manifest declaration disappearing from beneath a stored preset counts as
  `deviated`: the preset remains readable and applicable, but the live state
  can no longer equal its stored parameter set.
- The editor provenance mirror preserves the token instead of coercing it to a
  boolean. Visual interpretation remains explicitly deferred to
  `3-preset-dropdown-menu`.
- The focused test module now imports `unittest.mock` explicitly. Python 3.14
  no longer exposed it through the package attribute in this environment, so
  the existing fade-takeover cases could not run during the required focused
  verification.
