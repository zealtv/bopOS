# 25-show-playback-consistency

**Status:** ready
**Goal:** `playback` lists only steps that exist and are timing.

Evidence: `lore:2026-10-05-bopos-review-show-model` F4, F5, F6, F9.

- **F4.** A send exception leaves a step "playing" with no timer; Clear Show
  and show management are then refused until Stop all.
- **F5.** Undo that removes a playing step leaves a ghost entry.
- **F9.** `remove_item` stops the step even when the removal is refused.
- **F6.** `duration_s: 1e-9` with infinite repeats sends ~30k OSC/s. An
  internal re-arm floor is fine; if it shows in the UI, ask Bob first.

Done when: the reproduction cases leave `show_playing()` truthful, Clear Show
works after each, a refused remove leaves playback alone; show tests, fast and
the Show journeys green.
