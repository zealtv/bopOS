# Receipt: 2026-11-05-ap-restart-soak-noor-dusk

Tended 2026-11-05.

- `lore:2026-11-05-ap-restart-soak-noor-dusk`: the request and both raw logs, kept whole.
- `glean:networkmanager-wifi` (new): NM manages wlan0; netplan profile names; priority applies
  only at (re)connect; AP-restart recovery with power save off; the lockout is unconfirmed.
- `loom:79-wifi-power-save` tied (soak in its `verification.md`; Bob asked to close it);
  `loom:79-wifi-power-save/3-link-recovery-design` dropped (NM's reconnect suffices).
- `loom:33b-device-network-config/2-network-config-implementation`: slice 0 platform facts and
  the 2026-11-05 hand switchover recorded; it stays waiting.
- `loom:33b-device-network-config/3-wrong-key-lockout` (new, waiting): the addendum's repro.
- `loom:76-bob-review`: hardware check 13 moved to Ruled; check 20 added for the lockout.
