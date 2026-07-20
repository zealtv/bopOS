# aa-2c-preserve-lfo-anchor

Repair the still-visible non-free LFO restart when a looping Show step resends
the identical generator command.

1. Preserve the browser's existing animation anchor for an identical non-free
   LFO command, matching the node generator's idempotent absolute-time phase.
2. Continue resetting for changed LFO arguments and for free LFOs.
3. Add a real facilitator browser regression whose step-to-LFO period ratio
   lands the retrigger half a cycle away, matching the saved `go` cue.
4. Do not edit Pure Data or Bob's saved show.
