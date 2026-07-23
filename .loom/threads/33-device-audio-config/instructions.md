# 33-device-audio-config

**FEATURE.** Set a Pi's audio configuration from bopOS — specifically the **sound
card** and the **JACK properties** (sample rate, buffer/period size, and the
like) — from the **Device tab** in the Dashboard.

Bob, 2026-07-23: "I'd like to be able to set some of the Raspberry Pi
configuration properties from bopOS, specifically the sound card and the JACK
properties like sample rate, buffer, these sorts of things. That should be in the
Device tab."

## Bob gate

Two gates here: it's **user-facing Device-tab UI** (facilitator/Dashboard view =
Bob ratifies), and it likely writes **privileged/persistent device config**
(sound card selection, JACK params consumed by `bash/start-engine.sh`). Design
first (`1-audio-config-design`), Bob ratifies, then build
(`2-audio-config-implementation`).

## What it touches

- `bash/start-engine.sh` launches PD with `-jack` / the SC engine — the JACK
  sample rate / period / card selection have to be applied where JACK (or PD's
  JACK client) is configured, and survive a restart. Find the current source of
  those values (env, `.asoundrc`, a jackd invocation, hardware defaults).
- The Device tab surface in the Dashboard + the OSC/admin path the Dashboard
  uses to push device settings (the `/admin` engine-sent request surface,
  contract §4.2).
- Provisioning: some of this may belong to first-time `bash/provision.sh` rather
  than runtime.

## Open questions for the design

- Which properties are settable (card, rate, buffer/period, nperiods, anything
  else) and what are the valid/enumerated values per Pi?
- Where does the setting live and when is it applied — runtime restart vs reboot
  vs reprovision? Applying audio config often forces an engine restart.
- Does the node need to enumerate available sound cards back to the Dashboard so
  the tab can offer a real list rather than free text?
- Privilege boundary: runtime convergence must not need root (see the
  provision/convergence split from the unattended-Update work); if a setting
  needs root, it goes through provisioning, not the routine path.
