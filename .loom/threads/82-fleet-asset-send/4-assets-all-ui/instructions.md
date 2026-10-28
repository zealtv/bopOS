# 4-assets-all-ui

The Assets-tab UI for fleet sends. The mockup is
`fleet-testing/asset-fleet-distribution/fleet-0-bulk-distribution-design.tied/mockup-all.png`.
Option B changes what it shows: "MB sent", with a percentage only for
absent slots.

## Do

- **Target:** the device picker (`assetPicker`, `target-picker.js`, device
  domain) gains an **All** chip. Ineligible devices stay visible but
  disabled, with their reason. It's single-select: All, or one device.
- **Catalog rows with All:** a fleet summary in place of the state chip
  ("3 current · 2 stale · 1 absent · 1 unknown"). The action reads
  **Send to N**, counting the devices not current; "No action needed" when
  N = 0. No Remove.
- **Catalog rows with one device:** as today.
- **Send panel** above the catalog while `asset_queue` has jobs:
  - an overall bar showing devices finished (done + skipped + failed) out
    of the total;
  - one row per job: device name, slot, state chip, and a bar. The bar
    shows an exact percentage when `bytes_total` is set; otherwise it's
    indeterminate with "212 MB sent". Waiting jobs show "waiting"; failed
    jobs show the reason and a **Retry** button;
  - **Cancel remaining** (its title says the running device finishes) and
    **Dismiss** once finished;
  - copy that says the queue doesn't survive a dashboard restart.
- The active-slot confirm appears once, listing the affected devices.
- Use the design language (glean `dashboard-vocabulary` and its doc). The
  component CSS belongs to the component. At 390 px, rows stack: name and
  state on one line, the bar below.

## Verify

A Playwright journey (glean `playwright-gotchas`) on private ports with
simfleet or physical-protocol peers. It checks:

- Send to All runs one device at a time (only one row is fetching);
- a current device is skipped;
- a failed device can be retried;
- Cancel remaining;
- the per-device bar moves;
- the 390 px layout;
- no page errors.

Then run the full browser tier, and send screenshots to Bob.
