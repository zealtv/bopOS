# dashboard-light-cues-and-consoles

Fix the remaining light-theme contrast issues Bob identified on 2026-07-20:

- replace the facilitator/Dashboard cue lead progress and triggered flash's
  hardcoded dark-green fill/end state with paired theme tokens;
- retain the existing dark appearance, but use a pale readable green progress
  and flash treatment in light mode;
- give the Show outgoing/incoming OSC logs an explicit high-contrast terminal
  text token on their intentionally dark console background; and
- verify normal animation, triggered state, reduced-motion state, and console
  text contrast in a real browser.

Keep focused screenshots/results, preserve Bob's untracked `dashboard/shows/`,
and do not edit `.pd` files.
