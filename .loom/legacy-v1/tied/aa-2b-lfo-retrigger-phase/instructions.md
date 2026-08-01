# aa-2b-lfo-retrigger-phase

Keep the Dashboard's non-free LFO visualization phase-aligned with the
node/audition generator when a looping show step resends identical automation.

1. Publish a monotonic-clock phase sample with the bridge's automation state.
2. Make the browser phase anchor consume that sample without changing free-LFO
   semantics.
3. Add focused backend and browser-side regression coverage proving an
   identical retrigger does not reset the displayed phase.
4. Do not edit Pure Data patches.
