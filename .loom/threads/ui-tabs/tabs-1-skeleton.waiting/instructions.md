# tabs-1-skeleton

Implement the ratified tabs-0 IA: move the existing panels into tabs without
redesigning them. Mechanical restructure — the polish pass is tabs-2.

- Preserve all existing behaviour; every dashboard verify still passes.
- Ship a `verify_*.py` (Playwright, per CLAUDE.md testing notes) exercising tab
  switching and confirming each relocated panel still functions in its tab.
- Fix the facilitator/technical switch placement per the ratified IA.
- Reserve the Patch editor tab (may be an empty stub pointing at the
  patch-editor thread if pe work hasn't landed).

Blocked until tabs-0 is ratified.
