# Show tab + Patch tab braindump — Bob, 2026-07-19 (verbatim)

on the show tab:

parameter values can't be set to 0

only one step in a column should be able to be played at a time.


The step list should be in a vertically  resizable scroll box at a sensible default height with empy space ready to be populated by steps and dividers.  the step and divider + button should remain in place while new steps and dividers are added.


Then actions should default to one row (non-deletable) defaulting to stop.


cut and copying of messages can be keyboard only.  rearranging should be able to be done by clicking and dragging. this should work between steps, as well as inside steps. Those buttons (cut, copy, move left/right/other) in the edit section do not need to be there. Deleting messages by keyboard is good.  you should be able to undo via keyboard 

you should be able to click and drag steps and dividers to reorder them.


The step should fill up like a progress meter as it plays.

When an step is to be triggered by a then action - it should show a subtle blink-pulse (ie ready to fire)


consoles should start at their default heights

the forward sync cue tick box can be removed.  all cues are forward synced by design. there should be a global cue lead time control somewhere to set lead time.


message inspector Target should be collapsable

The play/stop/pause buttons aren't functioning as expected when clicked. There is a period of unresponisveness - ie clicking play, then immediately clicking stop does not work.  When a step is playing, the third button (after stop and pause) should display as >> or >| as it is "next" not "play" (i just noticed, this is actually my mistake - the button is too small for the >| symbol so i mistook it as a play button.  

The title of the step should not move when clicking the steps play button.

Ther should be a global transport with a play/pause, stop, and next. button.  Clicking play plays the currently selected step, or the first step if none is selected.  the stop all button should have a stop symbol, not text.  


On the Patch tab - "facilitator" shoud be changed to "Dashboard"

nothing uses the legacy group parameter in our demo patches.  let's remove it and tidy the demo patch manifests as required.

the example path hint in the path field is confusing - it needs to be clearer that it is an example.
