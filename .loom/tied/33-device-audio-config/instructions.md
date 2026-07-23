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

**Ratified 2026-07-23:** Bob accepted the five-setting, detected-cards-only,
transactional Save + engine restart design. The routine path is unprivileged,
uses node-level `bopos.config`, rolls back after a failed JACK start, and
reapplies Device enabled / MUTE ALL output safety. See the tied
`1-audio-config-design` decisions and v1.11 contract-amendment draft.

## What it touches

- `bash/start-engine.sh` launches PD with `-jack` / the SC engine — the JACK
  sample rate / period / card selection have to be applied where JACK (or PD's
  JACK client) is configured, and survive a restart. Find the current source of
  those values (env, `.asoundrc`, a jackd invocation, hardware defaults).
- The Device tab surface in the Dashboard + the exact-UID physical
  administration path. The ratified design explicitly excludes the
  engine-sent localhost `/admin` surface.
- Provisioning remains responsible for making hardware exist at the OS level.
  Routine selection among detected cards is unprivileged.

## Design questions — resolved in `1-audio-config-design`

- Which properties are settable (card, rate, buffer/period, nperiods, anything
  else) and what are the valid/enumerated values per Pi?
- Where does the setting live and when is it applied — runtime restart vs reboot
  vs reprovision? Applying audio config often forces an engine restart.
- Does the node need to enumerate available sound cards back to the Dashboard so
  the tab can offer a real list rather than free text?
- Privilege boundary: runtime convergence must not need root (see the
  provision/convergence split from the unattended-Update work); if a setting
  needs root, it goes through provisioning, not the routine path.
