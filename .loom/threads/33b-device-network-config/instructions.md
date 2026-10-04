# 33b-device-network-config

**Goal:** manage the fleet's saved Wi-Fi networks from the dashboard — add,
edit, remove, enable and disable SSIDs and passphrases — on a network model
that's been deliberately secured.

**Status:** revived by Bob 2026-10-03 (parked since 2026-07-23). `0` ruled
2026-10-04 (workshop provisioning + network isolation, `0-lan-trust-review/ruling.md`);
`1` ratified 2026-10-04 (`1-network-config-design/decisions.md`); `2` builds it.

## What Bob wants (2026-10-03)

> "a way to manage SSIDs and passwords via the bopOS dash. i want to have a
> development network for example, that is visible and has an easy to remember
> password, and then a performance network which will be hidden, and i want to
> be able to enable/disable networks from the dash."

So, at minimum:

- **Several saved networks per device**, e.g. a *development* network
  (visible SSID, memorable passphrase) and a *performance* network (hidden
  SSID).
- **Hidden networks** must work: the device has to probe for the SSID rather
  than wait to see it advertised.
- **Enable / disable** each network from the dashboard — e.g. turn the dev
  network off on the fleet before a show so devices only join the performance
  network.
- Fleet-wide as well as per device: the same profiles normally go to every
  device. (With `66-projects`, profiles may belong to the project's fleet or
  site — keep the seam.)

Out of scope unless Bob says otherwise: configuring the router/AP itself.
bopOS manages which networks the *devices* will join.

## Why it's gated

User-facing, writes privileged system config, handles secrets, and can
disconnect the very device being changed. And passphrases would cross a LAN
that today has no authentication at all — hence `0`.

## Constraints (from the 2026-07-23 brief, still binding)

- **Passphrases never leave the device once sent** — not in OSC status,
  WebSocket state, logs, browser storage, simulator fixtures or repo files.
  The UI may show "secret set".
- Routine apply is non-interactive; root work goes through a narrow
  provisioned helper (the hostname and power helpers are the precedent).
- Staged validation, safe apply, reconnect, rollback/recovery — disabling or
  deleting the network a device is on can cut the control path.
- Don't assume an interface name or that Wi-Fi exists.
- Keep secrets out of `bopos.config` unless the design proves it safe.

## Stitches

0. `0-lan-trust-review` — what anyone on the installation network can do
   today, and what should change. Feeds `1`.
1. `1-network-config-design` — the proposal for Bob.
2. `2-network-config-implementation` — builds the ratified design.
