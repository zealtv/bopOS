# 0-lan-trust-review

**Status:** ready · ends in a proposal Bob ratifies
**Goal:** a deliberate trust model for the installation network, before
bopOS starts sending Wi-Fi passphrases over it.

## Today (`lore:2026-10-03-bopos-code-review-2026-10`, § Also noted)

Nodes accept anything that arrives on 6660 from anyone on the network. Any
host on the Wi-Fi can reboot or shut down devices, update or check out bopOS,
switch patches, write `/os/store` keys, change audio/log config, or make a node
fetch content from an arbitrary URI. Patch push serves files over plain HTTP.
`68-remove-git-patch-route` removes one path (cloning arbitrary GitHub repos).

Fine on a private network the operator controls. Not fine on shared or public
Wi-Fi (e.g. a venue network at the Northern Broadwalk), and not fine for
carrying passphrases.

## Assess

1. **Inventory** every way in: OSC verbs on 6660 and 7770, HTTP endpoints on
   the dashboard, fetch URIs, the websocket (who can open the dashboard?), SSH
   defaults on the image.
2. **Threat model** for the realistic settings: private dev network; private
   hidden performance network; shared venue network. What matters in each —
   a prank reboot mid-show, reading secrets, taking over audio.
3. **Options**, cheapest first: rely on network isolation (hidden/WPA2
   performance network, nodes join nothing else) and document it; an
   allowlisted dashboard address; a shared fleet key that signs or MACs admin
   messages; encrypting secrets to a per-device key for `1`; dashboard login.
   Say what each costs on a Pi Zero and in operator friction.
4. **What `1` needs** specifically to send a passphrase to exactly one device
   without it being readable by others on the network.

## Deliver

`proposal.md`: inventory, threat model, recommended minimum (now) and what can
wait, with any contract amendment proposed (not written). Mark `.waiting` and
surface to Bob; `1` builds on his ruling.
