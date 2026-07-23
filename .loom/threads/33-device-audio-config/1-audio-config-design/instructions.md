# 1-audio-config-design

Design device audio configuration from the Device tab. Written proposal, **Bob
ratifies**, then tie with `decisions.md`.

## Decide

- **Property set.** Exactly which knobs: sound card selection, JACK sample rate,
  buffer/period size, nperiods, anything else Bob's "these sorts of things"
  implies. Valid ranges / enumerations per property.
- **Card enumeration.** Does the node report available cards (and their
  capabilities) up to the Dashboard so the tab offers a real picklist? Define
  that report if so.
- **Storage + apply model.** Where the chosen config persists on the node, and
  what applying it costs — engine restart, JACK restart, or reboot. Where in the
  start path it's consumed (`bash/start-engine.sh` / jackd / `.asoundrc`).
  **Coordinate with `bopos.config`** — `31-install-oneliner` now lands that file
  with sensible defaults at install (Bob, 2026-07-23), and the mute fix in
  `29-fleet-patch-sync-hang/2-fix` reads the **sound card identity** from it.
  The Device-tab sound-card selection here should write the **same** file/keys
  that install seeds and that the mute path reads — one source of truth for
  "which ALSA card is the DAC."
- **Privilege boundary.** Runtime vs provisioning. Keep the routine convergence
  path unprivileged; route anything needing root through `bash/provision.sh`.
- **Wire surface.** The OSC/admin terms to read current config and push new
  config (contract §4.2 `/admin`), plus contract amendment text.
- **Device-tab UI.** Where in the Device tab, what controls, what feedback
  (current vs desired, "restart required"), simulator/audition parity.

## Deliverable

`decisions.md` here; contract-amendment text; any Bob PD edit noted in
`.notes/pd-edits-for-bob.md`; update parent + un-`.waiting`
`2-audio-config-implementation`.
