# 77-performance-mode

**Status:** ready · ratified 2026-10-04 in the IO design (`59-i2c-inventory/0a-io-design-review.tied/proposal.md` §2, §8)
**Goal:** one prominent **Performance** toggle that locks development-only
behaviour across the fleet, enforced on the devices.

Bob, 2026-10-04: a global switch for things wanted in development and not in
performance; logging is *"to protect the sd card in the case of a hard
shutdown"*; Wi-Fi and patch modification locked too; **no prompt when a show
starts, but a prominent toggle**.

- **Separate from Live / Simulation / Patch Edit.** An explicit, prominent
  header toggle (show Bob a screenshot). It's never inferred from show
  playback.
- **Locked in Performance:** sensor streaming and stream-to-editor; **logging
  to the SD card** (logs go to RAM and the dashboard only); probes and Monitor
  sends; operator module writes; Wi-Fi changes; patch changes (pushes, Set
  Live, New Version, manifest saves, entering Patch Edit, including just
  viewing).
- **Remembered, never locked** (Bob rejected a fail-safe timeout as a lockout
  risk):
  - Each device persists its mode (written only on change). It survives
    reboots and starts in development on first install.
  - `/all/os/performance <0|1>` is never refused.
  - The dashboard persists its mode on the host and re-sends it to any device
    whose `/os/report` disagrees, as assignments converge.
  - The header warns while devices disagree.
- Devices enforce the lock list (`bopos.py` refuses); the dashboard disables
  the matching UI too.
- Contract: the `/all/os/performance` section and `/os/report.performance`
  from proposal §8, plus §15.
- Tests: persistence across restart, convergence, each lock refused on the
  device and disabled in the UI, the toggle never refused, RAM-only logging.

**Bob, 2026-10-04 (after merge):** the two-row header at 1440px with the Performance toggle is fine; keep it.
