# zero-1-tuning-matrix

**Status:** waiting — needs a reachable Zero 2 W (claim in any session that
confirms one)
**Goal:** commit Zero-safe JACK defaults, backed by measurement.

Most of the matrix is already measured on Finn Jet (see parent and
`../measurements-2026-08-13-finn-jet.md`). Don't re-run what's there.

## Do

- **Bob (2026-09-25): don't make 32 kHz the default yet.** The repo default
  stays 44100; 32 kHz remains a per-node setting (Finn Jet).
- [ ] Measure 32 kHz under load (events firing). If tight: period 2048, then
      22.05 kHz.
- [ ] Try 512 frames at 22.05 kHz or 32 kHz to claw back latency — untried.
- [ ] Nice-level / `-rt` checks on target.
- [ ] Record results here; commit defaults.

## Access

Finn Jet or `bop000` (see memory `bop000-dev-pi-access`). Confirm the host
in-session. Never flash, reimage or `apt upgrade` without asking; sudo needs
Bob.
