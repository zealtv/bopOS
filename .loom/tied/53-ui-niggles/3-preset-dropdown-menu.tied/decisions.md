# Decisions

- Recall and authoring are one disclosure-based `PresetMenu` component. A
  native select cannot represent commands with icons or a dependable divider,
  and briefly selecting a command would misrepresent it as applied state.
- The three authoring commands lead the menu, use visible glyphs plus words,
  and are separated from recall choices by a semantic `role="separator"`.
  This advances D8's chrome demotion into a merge; it does not revert D8.
- Dirty and schema-drift marks lead the closed label so ellipsis removes the
  name's tail, never its state. `deviated`, `missing`, and `foreign-patch` are
  distinct: `*`, `⚠`, and `↗`, each with explanatory menu text. Foreign-patch
  actions are disabled because neither capture nor recall can truthfully act on
  that target's running content.
- No card/column border was added. State stays on the preset control in the
  existing amber warning vocabulary, following both UX consults and preserving
  the ratified ground/card model. This is the treatment consumed by the
  following cards design rather than a second card-level treatment.
- The component owns its face in the seventh shared component stylesheet,
  `preset-menu.css`, and is registered with the component-ownership guard.
- The Patch editor now passes through the dirty-reason token. Its prior boolean
  coercion would have collapsed the three new treatments back into one there.
