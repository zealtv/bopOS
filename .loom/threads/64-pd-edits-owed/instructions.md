# 64-pd-edits-owed

**Status:** queued (Bob, 2026-11-05) — Pd edits are his; agents never edit `.pd`.
The agent halves are `1-pd-feature-inventory` and `3-asset-access-design`.
**Goal:** the Pd side of bopOS: land the Pure Data edits the framework still
owes, and give patch authors a current reference and easy tools (Bob,
2026-11-05: *"this is kind of feeling like … a PD thread"*).

Checked against `pd/` and `patches/` on 2026-09-25. Full specs, exact
spellings and verification steps: `lore:2026-09-25-pd-edits-for-bob-2026-08`
(`content/pd-edits-for-bob.md`). Everything else in that record has landed.

## Children (2026-11-05)

- `1-pd-feature-inventory`: agent. Every feature a patch can use, with exact
  spellings, plus a staleness test and COMPOSING pointer.
- `2-live-pd-reference`: Bob's. A live reference patch, edited in one place,
  plus a thin template. Absorbs the template `update-patch` removal and the
  keys and mouse examples (from `84-key-input/4-pd-reference-patches`,
  dropped as folded in). Approach OK'd by Bob 2026-11-05: help patch; the
  template carries a comment pointing at it ("right-click bopos~ → Help for
  how to work with bopOS in Pd").
- `3-asset-access-design`: agent. Propose a Pd asset utility (find a slot,
  list and pick files, build paths for loaders) from Kite Choir's needs.
- `4-asset-access-abstraction`: Bob's, needs `3`. Build and adopt it. Absorbs
  the `samplepacks` path templates and the demo-pd asset example.

Order: the event `[list]` edit below first; `2` needs `1`; `4` needs `3`.

## Owed (single edits)

- [ ] **Nested parameter routes — on first use.** `pd/bopos~.pd` already
      preserves nested paths. The first patch that declares a nested param
      changes its consumer from `[route distortion]` to
      `[route track1] → [route fx] → [route distortion]`.

- [ ] **Event bus `[list]` hides events from `[route]`.** In `pd/bopos~.pd`,
      delete `#X obj 384 181 list;` (between `route p e pt notify`'s `e`
      outlet and `s bopos-event`) and connect the `e` outlet straight to
      `s bopos-event`, as the `p` outlet goes straight to `s bopos-param`.
      Today `[list]` turns `do 1 2` into `list do 1 2` (and a zero-field fire
      into `symbol do`), so a bare `[route do]` off `[r bopos-event]` matches
      nothing. The template's own example (`r bopos-event → route do →
      unpack f f f`, since `7ce74d1`) has never received an event. Found by
      headless test 2026-11-05: evidence in
      `80-osc-input/5-pd-event-fields.waiting/verification.md` and
      `headless-test/harness3.pd`. Verify in Pd:
      - `/e/do`, `/e/do 1 2` and `/e/do "play"` reach the template's
        `route do` as `bang`, `1 2` and `play`;
      - `patches/kc-test` (which puts `list trim` first) still responds to
        its `trig` events. `list trim` passes the un-listed form unchanged,
        so it should.
      Re-running `headless-test/harness3.pd` after the edit should show
      `EVENT-BARE-ROUTE` lines matching `NOLIST-BARE-ROUTE`.

## How agents add to this

When a change needs a Pd edit, add a checklist item here (or a child stitch
if it's large) with exact spellings and how to verify, then verify the
Python/dashboard/simfleet side on its own.
