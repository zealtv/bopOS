# AP-restart soak on noor-dusk (2026-11-05): results for check 13, 79 and 33b

From the kite-choir-brains session on 2026-11-05 (Bob + Claude). Full write-up there:
`lore:2026-11-05-ap-restart-recovery-soak-noor-dusk`. Raw logs in `attachments/`.

**Please route:**

1. **`76-bob-review` hardware check 13 / `79-wifi-power-save`.** This is the soak with an AP restart.
   Rig: noor-dusk, Raspberry Pi 3 Model A Plus Rev 1.1, Debian 13 (trixie), kernel
   6.18.50+rpt-rpi-v8, NetworkManager 1.52.1, bopOS `74a9717`, `iw dev wlan0 get power_save` = `off`.
   AP: MikroTik mANTBox 2 12s, RouterOS 7.25.1, 2.4 GHz ch 6, bench signal −45 dBm. Stimulus: 60 s
   radio disable (`/interface wireless disable wlan1 ; :delay 60s ; …enable wlan1`), 11 times.
   **Result: 11/11 rejoined the same SSID unaided, 6–21 s after the AP returned** (bimodal, ~6 s or
   ~20 s). No hang, no power cycle, heartbeats back on the dashboard each time.
2. **`79/3-link-recovery-design`.** Evidence that, with power save off, NetworkManager's own
   reconnect survives an AP restart, which the stitch named as the condition for this being
   unnecessary. Limits: one node, strong signal, 60 s outages only.
3. **`33b/2` slice 0 (NetworkManager backend), two platform facts:**
   - The Imager-provisioned network appears as a **netplan-generated** NM profile named
     `netplan-wlan0-<ssid>` (here `netplan-wlan0-<workshop-ssid>`). Adoption-by-SSID must match on the SSID,
     not the profile name. `nmcli con modify` on such a profile **persists across reboot**: checked on noor-dusk after a
     16:38 reboot. `/etc/netplan/` holds `90-NM-<uuid>.yaml` files, consistent with NM writing back
     to netplan.
   - **NM falls back to any autoconnect profile in range and does not return to a higher-priority
     one** while connected. In bounce 1 the node moved from `<dev-ssid>` (priority 10) to `<workshop-ssid>`
     (priority 0) and stayed there more than 5 minutes after <dev-ssid> came back. So "list order is
     priority" governs only the choice made at (re)connect. A disabled-but-saved network must have
     autoconnect off, or it can capture devices. This is worth stating in the dashboard's warnings and
     docs. Kite Choir's guidance: field Pis carry only show-LAN profiles
     (brains `glean:field-pis-save-only-show-lan-networks`).

Bob declined an A/B test with power save on (2026-11-05): it was turned off intentionally.

**Addendum (later on 2026-11-05): a possible wrong-key lockout, for `33b` and `79/3`.** For a few
minutes, a spare AP broadcast `<dev-ssid>` with a placeholder passphrase. noor-dusk then stayed off Wi-Fi
for at least 4½ minutes after the AP had the correct key, while a phone joined in seconds. Only a power
cycle brought it back (within about a minute). This looks like NetworkManager blocking autoconnect after
auth failures (no secret agent on a headless node), but it wasn't confirmed, because the volatile journal
was lost. If it's real, a dashboard push that leaves an AP and the devices with mismatched passphrases
could strand devices until power-cycled. noor-dusk runs NM's default retry settings (`connection.autoconnect-retries -1`,
`connection.auth-retries -1`). A block for failed attempts normally lifts after ~5 min, but Noor was off far longer
(from the AP swap onwards, including ~5 min unbroken with the correct key on air before the power
cycle). That leans towards a block that doesn't self-clear (e.g. NM's no-secrets block with no agent). Options if a repro confirms it: provision
`autoconnect-retries 0` (retry forever), or a `79/3` nudge that re-activates the profile. Do any repro
outside performance mode: Bob accepts losing logs during shows, because performance mode avoids SD writes.

