# 39-remove-installed-pack-from-device

Let an operator remove an installed asset pack **from a device**, from the
Asset tab, without SSHing in (Bob, 2026-07-24). This is device-side uninstall,
**not** host-catalog deletion — Bob deletes host folders directly on the
filesystem; the gap is doing the same to a device remotely.

## Terminology (proposed — Bob's call)

Keep **"Remove"**, matching the existing device-side button on *extra* rows
(`assetExtraRow`, `dashboard/static/js/dashboard.js:1131`: "Remove <name> from
<device>"). "Remove" already reads as *uninstall from this device* (vs "Delete"
which would imply destroying the host source). "Slot"/"pack" stays a label for
the thing removed, not the verb.

The new capability is: extend Remove to **installed catalog packs** on the
device, not just the unknown/extra ones. Today only extra rows offer Remove;
catalog rows (`assetCatalogRow`, `dashboard.js:1120`) show state + a
fetch/update action but no way to uninstall an installed pack.

## Scope

- Server handler / OSC path to remove a named asset pack's files from a
  device's asset store (uses the OSC contract's device asset surface; check
  §4 device asset-inventory + whatever the existing extra-row Remove already
  calls, and reuse it).
- Asset-tab Remove control on installed catalog rows + confirm; refresh
  inventory after (the row should fall to `absent`/`extra` state).
- **Guard:** warn/block removing a pack the device's *current patch manifest*
  still declares as an active asset slot (`active_asset_slots`,
  `assetIsActive`, `dashboard.js:1135`) — decide warn vs block.
- Simulator (`tools/simfleet.py`) parity for the device-side removal + fetch
  inventory update; Playwright coverage.
