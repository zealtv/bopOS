# Ruling — LAN trust for network config (Bob, 2026-10-04)

Bob ruled the trust model in conversation rather than through a full
`proposal.md`; this file stands in for it.

## The model: workshop provisioning, network isolation

- **Wi-Fi profiles are set up in the workshop**, on Bob's own network. Secrets
  only cross a network the operator controls, so no per-device encryption,
  fleet key or dashboard login is needed for this feature.
- **At the venue, nodes join only the show networks.** Hidden SSID, strong
  WPA2 passphrase. They never join shared venue Wi-Fi, which takes the
  shared-network threat off the table.
- This is the cheapest option in the brief — rely on network isolation and
  document it. The docs owe a short note saying so (lands with `2`).

## Networks

- **Testing network**: visible, easy passphrase for usability.
- **Show networks**: hidden, e.g. *show SSID1* and a *show fallback SSID2*.
- **Priority decides which network a device joins** — show networks rank above
  testing. Bob: *"i like the prioritising idea"*.
- **Disable is still needed** — Bob: *"i still would like to be able to
  disable networks as the current working one has a easy password"*. Before
  bump-in the testing network is normally disabled, so the easy passphrase
  isn't a way in at the venue. Leaving it enabled at low priority, as a
  fallback when the workshop router is brought along, is the operator's
  choice per show.

## Accepted

- Hidden is not secret: devices probing for a hidden SSID broadcast its name.
  The passphrase is the protection; hiding just keeps the public off it.
- Anyone who has a show passphrase has the same unauthenticated control of the
  fleet as anyone on the network does today. Accepted for now.
- Recovery when something goes wrong is physical (workshop, or bring a known
  network to the venue), not automatic rollback machinery.

## Deferred

- **Which network manager** the Pi OS images use — Bob: *"can be determined at
  implementation time when i have a device up"*. Moves to `2`.
