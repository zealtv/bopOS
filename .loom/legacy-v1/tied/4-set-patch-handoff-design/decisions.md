# Ratified (with correction) — Device-tab "Set patch…" hand-off (Bob, 2026-07-25)

Authority for implementation stitch `11-set-patch-handoff`.

## Correction — the hand-off target is the Patch tab

The proposal routed "Set patch…" to a picker on the **Control** tab. Bob's
ruling on stitch `6` reassigns that: **"patch deployment to the fleet or to a
pinned device happens on the patch tab."** The Control tab is the renamed
Dashboard (live control only) and hosts no picker.

So the ratified hand-off is:

**Device tab → "Set patch…" → Patch tab, with the bite-2 target picker
pre-scoped to this device.**

This resolves the proposal's open question 1 (tab switch vs in-place
mini-picker) in favour of the **tab switch**: there is exactly one deployment
picker, it lives on the Patch tab, and the Device tab holds a shortcut to it.
No second picker is built.

## Seat requirement — ordinary seat, no new concept

**Bob:** "standalone devices are no different spatially than fleet devices.
although a bit clunky, we can assign a seat and call it 'pinned' or similar."

Ratified as: a standalone device (Ciro Toast) gets an **ordinary seat binding**,
exactly like a fleet node. Pinning needs a seat because OSC v1.5 targets content
by seat; that constraint is accepted rather than engineered around.

**Terminology ruling (Bob, this session, in answer to a raised collision):**
**"pinned" keeps its existing shipped meaning only** — *this device holds its own
patch, independent of the fleet* (`patch_pinned`, the 📌 roster marker, "Sync to
pinned patch"). A seat-bound standalone device is **not** given a new name; it
just has a seat, and the Device tab says so the same way it does for any node.
No new concept, and no churn on the shipped `patch_pinned` vocabulary.

That settles open question 2 (auto-seat semantics): **allocate a real, ordinary
seat** — not a hidden or utility seat. For an unbound device the "Set patch…"
flow first offers a one-click **"Give this device a seat"**, so the operator
never has to learn the OSC reason for the requirement.

## Depends on

Stitch `6`'s rename (for the Control tab's own identity) and the bite-2 picker,
which is already shipped and unmoved.
