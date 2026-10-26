# 80-osc-input

**Goal:** one OSC interface into bopOS that qtable, or any OSC app, can drive:
the running patch's events and parameters, plus bopOS's own master, mute and
lead. Generic in bopOS; Kite Choir is the first customer.

Bob, 2026-10-26: *"essentially like a single OSC interface that Qtable or any
other OSC application can tap into, and the OSC messages that are being sent to
Bop OS might differ … from those that are going out to the devices. So that's
where Bop OS is able to insert the event lead time, and we don't need that
sentinel."*

This turns glean `external-osc-timing`'s "future path, not started" into a
design. Bob's 2026-10-11 "no development" stood until this request.

## Sources

- Kite Choir layout, workshopped with Bob 2026-10-26: kite-choir-brains
  `docs/bopos-show-spec.md` (loom `bopos-show-osc-spec` there). That file holds
  the rulings this thread builds on.
- lore `2026-10-11-external-osc-sender-timing`.
- Event plane history: `.loom/tied/44-event-plane/`,
  `.loom/legacy-v1/tied/1-event-plane-design/`.

## Stitches

Ratified by Bob 2026-10-26 (both proposals tied, every question answered):

1. `1-typed-event-fields` — richer `/e/*` events: one `fields` list declared
   like params, five kinds, `optional`, up to 16.
2. `2-dashboard-osc-input` — the input on 5552, `/bop/*`, the OSC tab.

Implementation:

3. `3-event-fields-wire` — manifest, node, simfleet, audition, contract.
4. `4-event-fields-editor` — authoring and fire controls. Needs 3.
5. `5-pd-event-fields` — Bob's Pd check and rig confirmation. Needs 3.
6. `6-group-name-rule` — addressable group names. Independent.
7. `7-osc-input-port` — the input itself. Needs 3 and 6.
8. `8-osc-tab-mockup` — mockup from the running app, to Bob. Needs 7.
9. `9-osc-tab` — build the ratified tab. Needs 8.
10. `10-qtable-rig-check` — qtable through bopOS on the rig. Needs 5 and 7.

Queued first on 2026-10-26 (Bob): 3, 6, 4, 7, 8, 9. Bob's own items — 5, 10,
and the mockup from 8 — are parked `.waiting` and listed in `76-bob-review`
(Open 19–20, Hardware checks 11–12).

## Coordination

`62-split-elements/4-contract-amendment` is the other contract amendment in
the queue. Checked 2026-10-26: it hasn't started, holds no version number, and
overlaps only on the §4 port table and how groups work. Whichever lands first
takes v1.22. Keep wording multi-instance and engine-agnostic (glean
`horizon-refactor`): "every engine instance", not "the Pd".
