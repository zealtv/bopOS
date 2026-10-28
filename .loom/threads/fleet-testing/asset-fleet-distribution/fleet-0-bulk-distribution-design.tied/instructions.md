# fleet-0-bulk-distribution-design

**Status:** un-parked by Bob on 2026-10-27. He wants the Assets tab to send to
all devices or to one chosen device, each with a progress bar.
**Goal:** a fleet asset-send design, ratified by Bob, then built. Size it to
the measured packs (see the parent), not the old 10–50 GB premise.

## Bob's rulings (2026-10-27)

- **One-off operation, not desired state.** Sending runs once over the
  targets chosen when it starts, then ends. Unlike the July core below, the
  dashboard keeps no record of which slots each device should have, and
  devices that come online later don't catch up by themselves. That can
  come later.
- **One device at a time.** The queue runs a single device; there's no
  concurrency setting for now. The July measurements explain why that's
  enough: all the Pis share one Wi-Fi channel, so downloading in parallel
  doesn't finish sooner overall (see
  `.lore/items/2026-07-15-asset-transfer-scale-reference/`).
- **Targets: All, or one device**, through the shared target picker. The
  Assets tab currently targets exactly one device (legacy stitch
  `11b-single-device-assets-workspace`, accepted 2026-07-15; that deliberate
  limit is now lifted).
- **A progress bar** for the whole operation and for each device.

## What the design should settle (my proposal from 2026-10-27; Bob hasn't ratified it yet)

- **Progress needs a contract amendment.** Today `/os/fetch-progress` sends
  only the `queued`/`fetching` phase, and §OSC-CONTRACT rules out invented
  percentages. Proposal: `/os/fetch-progress <slot> fetching <bytes_done>
  <bytes_total>`, sent about once a second. The total counts only the
  changed files, from the node's comparison with the host's file list.
  Older nodes keep sending phase only, and the UI shows an indeterminate bar
  for them. That needs a version bump and a Pi-side change (`bopos/` node
  code). Counting bytes on the dashboard side was rejected: it can't know
  each Pi's total.
- **Send each fetch to the Pi's own address, not as a broadcast.** On
  2026-10-27, Eden Pearl missed two broadcast patch fetches and sat at
  "switching". The same fetch sent straight to its address worked at once.
  Check what `OSCBridge.fetch` sends today and fix it for both assets and
  patches.
- **Operation panel:**
  - an overall bar showing devices done out of the total and bytes across
    the fleet;
  - one row per device: waiting in queue · fetching N% · done · failed
    (Retry);
  - Pause/Cancel. Cancel can't stop the transfer already running on a node
    unless the contract gains a cancel, so say what Cancel actually stops.
- **Offline or unassigned devices at the start** are listed as skipped. A
  device that drops mid-queue fails its row and the queue moves on.
- **Slots the active patch uses:** keep 11b's warning about overwriting a
  slot the running patch uses, but ask once for the whole operation, not
  once per device.
- **Dashboard restart mid-operation:** the operation may end. The rows then
  fall back to the observed inventory (current/stale), as 11b already does.
  Say so honestly.
- **A device that's already current** (fingerprints match) is skipped and
  marked done without fetching.
- Decide whether fleet patch pushes (`converge_fleet_patch`, which fans out
  to every device at once today) should share this queue later. Don't
  change them in this stitch.

## Deferred (July core, still valid later)

These stay deferred:
- durable desired fingerprints per device;
- automatic offline reconciliation;
- disk-space preflight;
- node-owned engine stop/activate/restart (builds on `fleet-1` if tied).

The following need measured evidence before anyone adopts them, and the
evidence must be recorded: immutable snapshots, canary/waves per access
point, ETA displays, wired caches, USB/SD orchestration, packfiles,
chunking, rsync/rclone, P2P, multicast.

## Process

Write `proposal.md` here: contract text, server queue, UI mockup screenshots
from the running app. Bob ratifies it, then the build splits into child
stitches (contract and node progress, dashboard queue, Assets UI and its
verification journey).
