# hw-onboarding-doc

From Bob's seam-1 review (2026-07-11): document how to integrate a new piece
of hardware / audio interface into bopOS, and how mute interacts with the
board zoo. Agent-workable docs task (no hardware needed to write the
procedure; per-board verification rows get filled as boards are benched).

- [ ] A "new audio hardware" procedure doc — likely a README section or
      `docs/HARDWARE.md` linked from the README: what to configure
      (`audio_out` declared fact, ALSA/boot config), what to test on the
      bench, and **how to fold the results back into the repo** (add the
      board's mixer control to the `set_mute` candidate list, record the
      tested board in the doc's table).
- [ ] Mute interaction per board (contract §6 is the seed): which mixer
      control accepts a mute on each tested board (DigiAMP, Pimoroni Audio
      SHIM, class-compliant USB, …); where no mixer control exists, note the
      engine-stop fallback is degraded, not the design centre.
- [ ] Cross-link: `audio-input/input-1-hw-recipe` covers the input-capable
      HAT recipe — same doc family; coordinate the doc's structure so input
      boards land in the same table when that stitch opens.
- [ ] Untested boards must fail honest: the doc says how to check
      (`amixer scontrols`), never guesses.
