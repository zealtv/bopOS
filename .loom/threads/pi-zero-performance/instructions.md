# pi-zero-performance

**Goal:** enough CPU headroom on the Pi Zero 2 W for real patches, with
Zero-safe defaults committed and a verdict on whether a non-Pd engine is
warranted.

**Status:** baseline measured on Finn Jet (2026-08-13). Defaults not yet
committed (`zero-1`, needs a Zero). Engine verdict is co-design with Bob
(`zero-2`).

Spool-specific tuning lives in kite-choir-brains (`bopos-uptodate/pi-zero-optimisation`);
generic defaults and the engine question live here.

## What we know (`measurements-2026-08-13-finn-jet.md`)

- **Pd is single-threaded** — one core maxed, three idle. `bonks-pd` hit 99% at
  44.1 kHz and stuttered.
- **Sample rate is the lever.** Period size alone made no audible difference.

  | patch | 22.05 kHz | 32 kHz | 44.1 kHz |
  |---|---|---|---|
  | `demo-pd` | 29% | 37% | 51% |
  | `bonks-pd` | 57% | 81% | 99% |

- **Finn Jet settled at 32000 / 1024 / 2.** 22.05 kHz aliased audibly on
  non-bandlimited oscillators (fixable patch-side). 32 kHz: 0 xruns in 120 s —
  but with no events firing; a busy show is unverified.
- **Io bridge costs 0.1%** (no peripherals attached).
- **Pd `-callback` is worse** (100% CPU, more xruns, sounds worse). Don't retry.
- The "51% floor on an empty patch" worry is retired — cost scales with rate.
- Repo default stays **44100** — Bob, 2026-09-25: not 32 kHz yet.

## Remaining

- [ ] Commit Zero-safe defaults (`zero-1`).
- [ ] Load-test 32 kHz with events firing.
- [ ] Nice levels / `-rt`: `bopos.py` and the io bridge must never steal from
      audio.
- [ ] Io poll rate vs patch needs, on a node with peripherals attached.
- [ ] Engine verdict (`zero-2`) — now part of the engine-agnosticism horizon
      (`lore:2026-09-25-horizon-architecture-refactor-2026-08-16`).
