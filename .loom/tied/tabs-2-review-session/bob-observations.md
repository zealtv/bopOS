# Bob's hands-on tabs-2 observations — 2026-07-15

## Mode model

- Simulate needs more prominence: above the seat list or in the global menu.
- Remove the redundant "Edit this patch" button beside Simulate; Patches owns
  entering edit mode.
- Validate the global model **Live / Simulate / Edit** with an expert reviewer.
- Stopping simulation left stale Dashboard cards until the browser refreshed.

## Fleet patch and device convergence

- Binding leaked a device hostname into the seat name.
- A patch switch became stuck in `switching`.
- Selecting the desired fleet patch feels more natural in Patches than Devices.
- Devices should make divergence obvious and offer one action to bring a device
  back to the desired fleet state.
- Installation-day workflow may need patch/asset convergence before or after
  seat binding; an unbound device must remain inspectable and administrable.

## Seats versus devices

- Seat edit/remove/bind/position controls currently render in Devices after a
  seat is selected in Seats. This makes both nouns and navigation ambiguous.
- Seat ID cannot be changed; after unbinding, the route back to the seat is
  unclear and the device appears in both active/recent and unbound lists.
- The correct home for binding devices to seats needs review. Map-first binding
  is attractive on installation day.
- Unbound devices still need Identify, reboot, update, patch convergence and
  useful device facts. They currently lose most controls/params.
- Devices needs **Shutdown All** and an obvious Identify action.

## Live Dashboard and identity

- Device cards currently fall back to MAC/uid. Because preset parameter state is
  seat-scoped, bound cards should be labelled by seat name (and perhaps ID).
- Longer term, devices need memorable, readable, stable identities distinct
  from seats. Hostnames are readable but not guaranteed unique. Bob suggested a
  deterministic human-name alias such as "Freda Sparks" mapped from uid, making
  "Freda Sparks sits in Seat 0" a useful metaphor. Defer this to its own stitch.

## Information density

- Full patch fingerprints/content identities are unnecessary by default. Show a
  short tail, with click-to-copy access to the complete value.

## Candidate composer workflow

In parallel, create the initial patch and draft seat positions. Then iterate:

1. Simulate to preview.
2. Adjust parameters and test points/cues.
3. Edit the patch.
4. Repeat those three steps.

## Candidate installation workflow

1. Turn on devices; check framework versions and update as needed.
2. Assign devices to seats, preferably from the map. Patches/assets may or may
   not already be present.
3. Install devices and Identify them while walking the room or looking from
   front of house; confirm each physical device matches its map seat.
4. Once seat assignments are confirmed, send/converge the fleet patch.
5. Send/converge assets across the fleet.
6. Test cues and parameters.
7. Tune for show.
8. Later maintenance independently converges changed framework, patch and asset
   state as required.

This is a candidate workflow, not a claim that every production follows the
same order. The UI should support variation without losing desired/observed
state clarity.
