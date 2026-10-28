# 82-fleet-asset-send

**Goal:** the Assets tab sends an asset slot to **All** devices or to **one**
device, one device at a time, with a progress bar. There's no wire change
and no Pi change.

Bob chose this on 2026-10-28, picking "option B" from four options in
`fleet-testing/asset-fleet-distribution/fleet-0-bulk-distribution-design`
(see its `proposal.md` and `decision.md`). It's a one-off operation (no
durable desired state) running one device at a time. Progress comes from
the dashboard counting the bytes it serves, not from a contract amendment.

## How it works

- The dashboard keeps a queue of *(device, slot)* jobs and runs one at a
  time over the existing `/os/fetch` → `/os/fetched` path. The Pi still
  pulls only the files it lacks from the dashboard's own HTTP server.
- Because only one device fetches at a time, the dashboard can attribute the
  bytes its server sends to that device's IP. That gives a live
  "MB sent" figure for each device, a stall signal (no bytes for 2 min →
  failed, move on), and an exact percentage when the slot is absent on the
  device (the total is then the slot's size).
- `/os/fetch` goes to the Pi's own address, not the broadcast address.

## Stitches

1. `1-unicast-fetch`: independent.
2. `2-served-bytes`: independent.
3. `3-asset-send-queue`: needs 1 and 2.
4. `4-assets-all-ui`: needs 3.

Hardware proof (a real pack to the KC Pis, timed) belongs in `fleet-testing`
once this is tied.
