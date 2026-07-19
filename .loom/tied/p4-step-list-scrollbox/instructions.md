# p4-step-list-scrollbox

Layout: the step list becomes a contained, user-resizable region.

1. **Vertically resizable scroll box** around the step rows: sensible
   default height (enough for a dozen-plus compact rows without dwarfing
   the inspector), CSS `resize: vertical`-style handle (or an equivalent
   touch-friendly drag handle if native resize is unusable on touch —
   check on the 768×1024 layout and log the choice), internal scroll,
   empty space visible below the last row ready to be populated.
2. **The + Step / + Divider add bar stays put** while steps and dividers
   are added: fixed beneath (outside) the scroll region, not drifting down
   with content. Adding a step scrolls it into view.
3. **Consoles start at their default heights** — Bob's note implies the
   collapsible consoles currently restore in a wrong/expanded state on
   load; make first paint match the intended default (collapsed or
   default-height per stitch-7's design) and persistent toggling still
   work.
4. Dense-layout budget from 5b still holds; the scroll box must not
   reintroduce page-level horizontal scroll and keeps working on the
   narrow (≤760 px) layout.

Verify: `verify_show_scrollbox.py` (house pattern): 30-step show scrolls
inside the box while the add bar and transport strip stay on-screen;
adding a step does not move the add bar's y-position; the new step is
scrolled into view; resize handle changes the box height; consoles render
at default height on first load. Amend tied 5b's viewport budget check if
its measurement crosses the new container (log it).
