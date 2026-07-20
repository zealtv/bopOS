# 03-collapsible-steps

Make step rows fold up to hide their message pills, per the row anatomy
ratified in `01-ux-review-step-rows-and-chrome` (`decisions.md` there is
binding — indicator placement, click/keyboard targets, persistence scope,
default state, collapse-all if ratified).

## Outcome

- A collapsed step shows the ratified single-row form (indicator, `⋮⋮` grab
  bar, play button, name, duration/cue info); expanded shows the pills as
  today. The `⋮⋮` grab-bar icon is retained unchanged (Bob).
- Collapse must not break: drag/reorder (row and pill), keyboard editing
  and navigation, selection/focus model, insertion anchoring from the edit
  bar, duplicate/delete, scroll-to-new-row, playback visualisation (a
  playing or armed collapsed step still shows progress/armed state), and
  second-client updates.
- Pills inside a collapsed step remain reachable by expanding; pill
  keyboard copy/paste continues to work on visible pills exactly as today.
- Collapse state storage (show document vs client-local) per the ratified
  decision; if it enters the document it is a small additive field.

## Verification

Focused Playwright: collapse/expand via pointer, touch, and keyboard;
anatomy/order assertions at 1280px and 768px; playback state visible on a
collapsed playing step; drag-reorder of collapsed and expanded rows;
persistence/second-client behavior per the ratified storage decision; the
edit-bar interactions against collapsed rows; no horizontal overflow.
Re-run the tied edit-bar suite unmodified. Retain screenshots.
