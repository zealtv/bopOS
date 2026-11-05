# 1-pd-feature-inventory

**Status:** ready · agent work (no `.pd` edits)
**Goal:** one complete, exact list of everything bopOS offers a Pd patch, so
Bob can build the live reference (`2-live-pd-reference`) from it, plus a fast
test that goes red when the reference falls behind.

Bob, 2026-11-05: *"I want to make sure that all of the bopOS features are
documented, including logging to the USB, keystrokes, events, parameters.
All of that."* He builds patches using the template as a reference, and the
template has gone stale.

## Do

1. **Inventory** (`inventory.md` here). For every feature a patch can use,
   give the bus or message, exact spellings, argument shapes, and a minimal
   Pd idiom that has been checked in headless Pd 0.55 (see
   `80-osc-input/5-pd-event-fields.waiting/headless-test/` for the harness
   pattern). Read `pd/bopos~.pd`, `pd/bopos.point.pd`, the contract and
   `docs/COMPOSING.md`; don't work from the template, which is the stale
   copy. As of 2026-11-05, `bopos~.pd` exposes:
   - in: `bopos-param`, `bopos-event`, `bopos-point`, `bopos-context`,
     `bopos-master`, `bopos-notify`, `bopos-io`, `bopos-audition-matrix`;
   - out: `to-bopos-admin`, `to-bopos-io`, `to-bopos-log`, `to-bopos-report`;
   - audio: `throw~ bopos-0` / `bopos-1`.
   Cover at least: params (including nested routes and automation being
   framework-side), events (typed fields, zero-field fires, the `[list]`
   trap until `64`'s edit lands, the §3.2 nested-identity note), points,
   context (id, groups, run-id, seed, patch, assets root, version), master,
   notify, I2C io (create/poll/stream/write), keys and mouse (spellings in
   `2-live-pd-reference/keys-and-mouse.md`), logging (`to-bopos-log`,
   including where it lands: USB stick versus SD, Performance mode), report,
   store/load, admin verbs (current ones only; `update-patch` is retired),
   manifest declarations each feature needs.
   Mark anything you couldn't check headless as unchecked.
2. **Staleness test** (fast tier, `tests/`). Once Bob's reference exists,
   assert that every `s`/`r` bus `pd/bopos~.pd` exposes, and every admin/log
   verb the node accepts, appears in the reference patch. Write it with the
   bus list derived from `bopos~.pd`, so a new bus fails the test until the
   reference shows it. Land it skipped (with the reason) until
   `2-live-pd-reference` lands.
3. **Docs.** Point `docs/COMPOSING.md`'s Quick reference at the live
   reference, and widen its `bopos-io` line (about line 116, "sensor data, if
   you use I2C peripherals") to cover keys and mouse. Moved here from
   `84-key-input/4-pd-reference-patches` (dropped 2026-11-05, folded in).

## Done when

`inventory.md` is complete with spellings checked, the staleness test exists
(skipped until the reference lands), and COMPOSING points at the reference.
Bob reads the inventory before he patches `2`.
