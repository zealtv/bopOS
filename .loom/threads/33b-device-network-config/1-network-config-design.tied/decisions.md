# Network config design — proposal for Bob

**Status:** ratified by Bob, 2026-10-04 (see Ruling at the end)
**Builds on:** `../0-lan-trust-review/ruling.md` (workshop provisioning,
network isolation, priority + disable, network manager decided in `2`).

Low friction and simple: one Wi-Fi list for the whole fleet, edited on the
dashboard, pushed in the workshop.

## 1. The model

One **fleet Wi-Fi list**, plus the **Wi-Fi country** (needed for the device to
use the right channels and to probe for hidden networks).

Each network has:

| field | meaning |
|---|---|
| `ssid` | the network name; also its identity — no duplicates in the list |
| `hidden` | the device probes for it instead of waiting to see it |
| `enabled` | off = stays saved on the device (secret kept) but never joined |
| secret | WPA2/WPA3-Personal passphrase, 8–63 characters; shown only as "secret set" |

**Priority is list order**: top of the list is preferred. A typical list:

1. show SSID1 — hidden
2. show fallback SSID2 — hidden
3. testing — visible, easy passphrase; disabled before bump-in

Out of the first slice: open (no-passphrase) networks, enterprise Wi-Fi,
Ethernet settings, static IP, per-device exceptions. Open networks are left
out on purpose — they're the venue networks the ruling keeps devices off.

**Edit semantics:** a blank passphrase on edit means *keep the secret*.
Renaming an SSID is remove + add, so it needs its passphrase again.

## 2. Where the list lives

- **Dashboard:** the list (SSIDs, hidden, enabled, order, country) sits in
  installation state next to the fleet. When `66-projects` lands it moves into
  the project's fleet; nothing else in this design depends on where.
- **Passphrases on the host — question for Bob (Q1).** Recommended: the
  dashboard keeps them in a host-local file, `state/wifi-secrets.json`, mode
  0600. `state/` is gitignored, and the file is never sent to the browser,
  never logged, and kept out of installation and venue files. Then a device
  added later gets the full list without you retyping passphrases. The
  alternative is no host copy: you retype a passphrase whenever a device
  doesn't have it yet.
- **On the device:** passphrases live only in the network manager's own
  root-only store. Not `bopos.config`, not the persistence store. bopos.py never
  reads a passphrase back; it learns only *secret set yes/no*.

## 3. The wire (proposed v1.20, additive)

Follows the exact-device `audio-config` / `log-config` pattern (§6):

```
/all/os/to <uid> wifi-config <json>
    → /os/wifi-config <uid> <ok|err> <phase> <json>
```

Request JSON (complete list, full state — the device ends up with exactly this):

```json
{"country": "GB",
 "networks": [
   {"ssid": "show-1",   "hidden": true,  "enabled": true,  "psk": null},
   {"ssid": "show-2",   "hidden": true,  "enabled": true,  "psk": "…"},
   {"ssid": "workshop", "hidden": false, "enabled": false, "psk": null}]}
```

- `psk: null` keeps the device's existing secret for that SSID. A network
  with no secret on the device and `psk: null` rejects the whole request
  (`invalid`), so the dashboard only sends passphrases a device is missing or
  that you changed.
- **Rejected whole (`invalid`):** missing/extra/wrongly typed fields, duplicate
  SSIDs, SSID not 1–32 bytes, passphrase not 8–63 printable ASCII, unknown
  country code, **no enabled network** (it would strand the device).
- **Receipt and `/os/report`** carry the same redacted `wifi` object — never a
  passphrase:

  ```json
  {"managed": true, "country": "GB", "active": "workshop",
   "networks": [{"ssid": "show-1", "hidden": true, "enabled": true, "secret": true}, …],
   "unmanaged": ["imager-net"]}
  ```

  `active` is the SSID joined right now (or null). `unmanaged` lists SSIDs the
  device has saved that bopOS didn't create, e.g. the network set in Raspberry
  Pi Imager — SSID only. `managed: false` means no Wi-Fi or no helper; the
  other fields are then absent.
- **Phases:** `applied`, `invalid`, `unavailable` (no Wi-Fi, or helper not
  installed/authorized), `failed` (the helper or network manager refused).
- **Ack timing:** the node validates, the helper writes the profiles, the node
  sends `applied`, *then* the network manager re-evaluates. If that moves the
  device to another network, it drops briefly; its heartbeat coming back is
  the confirmation. No rollback — recovery is physical (the ruling).
- **Adopting an unmanaged network:** listing an SSID that the device has as an
  unmanaged profile replaces that profile with a bopOS one. That's how the
  Imager-provisioned network comes under dashboard control (and can then be
  disabled). bopOS never deletes an unmanaged profile it wasn't given.

**About broadcast.** Exact-device messages go out as LAN broadcasts today
(`send_physical`), so a passphrase in a `wifi-config` request reaches every
host on the network, not just the target device. Under the ruling that's
acceptable: it only happens in the workshop, and every device gets the same
list anyway. The amendment says so explicitly rather than claiming
otherwise. Unicasting to the device's last-seen IP would narrow it; not needed
for the first slice.

## 4. Device side

- **Helper:** `/usr/local/sbin/bopos-set-wifi`, root via the existing sudoers
  file, **no arguments** — it reads the JSON on stdin (so passphrases never
  appear in a process listing), validates strictly, writes only bopOS-owned
  profiles (plus adopting by SSID as above), and prints the redacted state. A
  second mode, `bopos-set-wifi --status`, prints the redacted state for
  `/os/report`. Same install path as the hostname helper.
- **Backend:** NetworkManager or `wpa_supplicant`, chosen in `2` with a device
  up. The design needs only: per-network priority, hidden/probe, autoconnect
  off for disabled, root-only secret storage, list SSIDs without secrets.
- **No assumed interface name**; a device without Wi-Fi reports
  `managed: false` and replies `unavailable`.

## 5. Redaction — where a passphrase could leak

All covered by tests in `2`:

- Dashboard console tap: `osc_out` echoes every outgoing argument to every
  browser. `wifi-config` arguments must be redacted before the echo.
- Dashboard WebSocket state, installation/venue files, logs: list only, no
  passphrases.
- Node: no logging of `wifi-config` arguments; `/os/report` and receipts carry
  the redacted object only; nothing in `bopos.config` or the store.
- Simulator fixtures and virtual devices: accept the request, store
  `secret: true`, never the passphrase.

## 6. Dashboard UI

**Placement — question for Bob (Q2).** Recommended: a **Wi-Fi networks** panel
on the **Devices** tab, above the device list, since it's fleet-wide device
administration. It moves into the project surface when `66-projects` lands.

- Ordered list, top = preferred; ▲/▼ to reorder.
- Per row: SSID, *hidden* checkbox, *enabled* toggle, passphrase field
  (masked; shows "secret set"; blank = keep), ✕ remove.
- Country selector.
- **Send to all devices** button; per-device chip in the device list: *in sync*,
  *differs*, *needs passphrase*, *no Wi-Fi*, *sending…*, *error*.
- **Passphrase-on-the-network warning** (Bob, 2026-10-04): whenever a send
  will carry one or more passphrases, the dashboard says so before sending
  and asks to confirm — proposed wording: "⚠ This sends N passphrase(s) over
  the network. Anything on this network right now can read them. Send only
  on your own network." Sends that carry no passphrase (reorder, enable,
  disable) go straight through.
- **Warnings** (⚠, amber), not blocks:
  - disabling or removing a network that devices are on right now — "N
    devices are on *workshop* now; they'll move to the next enabled network
    they can see";
  - the only hard block is *no enabled network at all* (Send disabled).
- Unmanaged SSIDs a device reports are shown on that device's row, with
  "add to list" to adopt.

## 7. Verification gates for `2`

- Unit: validation (each rejection), redaction (console tap, WS, files, logs,
  receipts), keep-secret semantics, simulator parity.
- Browser journey: edit list, reorder, disable with warning, send, chips.
- **Real Pi (Bob's hands):** the workshop switchover rehearsal — both APs up,
  push the list, disable *testing*, every device reappears on the hidden show
  network; then disable show 1 and confirm the fallback takes over. Record the
  device and framework revision.

## 8. Proposed contract amendment (not written into the contract yet)

> **1.20 — Exact-device Wi-Fi configuration (§6, additive).**
> `/all/os/to <uid> wifi-config <json>` → `/os/wifi-config <uid> <ok|err>
> <phase> <json>`. The request is the complete ordered list of bopOS-managed
> WPA-Personal networks plus the Wi-Fi country; list order is priority.
> Each network carries `ssid`, `hidden`, `enabled` and `psk`, where `psk: null`
> keeps the device's existing secret. Invalid, partial or duplicate lists, and
> lists with no enabled network, reject whole. The node applies through a
> pre-provisioned argument-less privileged helper, replies, then lets the
> network manager re-evaluate; there is no rollback. Receipts and `/os/report`
> carry a redacted `wifi` object (`managed`, `country`, `active`, `networks`
> with `secret: true|false`, `unmanaged` SSIDs) and never a passphrase.
> **Trust:** the request travels as an installation-LAN broadcast like every
> exact-device verb, readable by any host on that network; it is intended for
> provisioning on an operator-controlled network only, and the dashboard
> warns before any send that carries a passphrase. Devices in the field
> join only hidden, passphrase-protected networks.

## Questions for Bob

1. **Passphrases on the host:** keep them in `state/wifi-secrets.json` (0600)
   so new devices get the list without retyping — recommended — or no host
   copy?
2. **UI placement:** Wi-Fi networks panel on the Devices tab — recommended —
   or somewhere else?
3. **First-slice scope:** WPA-Personal only (no open networks, no Ethernet or
   static IP) — OK?
4. Anything in the model or wire above you'd change before it's built?

## Ruling — Bob, 2026-10-04

1. **Host passphrases: yes** — `state/wifi-secrets.json`, 0600.
2. **Placement: yes** — Wi-Fi networks panel on the Devices tab, moving into
   the project surface when `66-projects` lands.
3. **First slice: yes** — WPA-Personal only; no open networks, Ethernet or
   static IP.
4. **Addition:** *"perhaps a warning when sending a passphrase over the
   network noting it will be visibile to anything currently on the network."*
   Added to §6 and the amendment. The wording above is a proposal; Bob sees
   it in the running app in `2` before it's final.
