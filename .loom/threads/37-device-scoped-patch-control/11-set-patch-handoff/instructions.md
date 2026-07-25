# 11-set-patch-handoff

A **Set patch…** button on the Device tab that hands off to the Patches-tab
target picker, pre-scoped to that device.

**Authority:** `.loom/tied/4-set-patch-handoff-design/decisions.md` (Bob,
2026-07-25).

## Ratified

1. **The hand-off target is the Patch tab**, not the Control tab — the proposal
   said Control and was corrected on ratification. There is exactly **one**
   deployment picker (the shipped bite-2 one); this stitch adds a shortcut to
   it, never a second picker.
2. **Tab switch**, with the device pre-scoped. No in-place mini-picker.
3. **An ordinary seat.** A standalone device gets a normal seat binding, exactly
   like a fleet node — not a hidden or utility seat. For an **unbound** device
   the flow first offers a one-click **"Give this device a seat"**, so the
   operator never has to learn that OSC v1.5 targets content by seat.
4. **Terminology:** "pinned" keeps its shipped meaning only — *this device holds
   its own patch, independent of the fleet* (`patch_pinned`, the 📌 marker,
   "Sync to pinned patch"). A seat-bound standalone device gets **no new name**.
   Do not introduce a second sense of the word.

## Where it goes

The button belongs in the Device-tab patch-diagnostics panel
(`patchDiagnostics()`, `dashboard.js:919`, bound in `bindPatchDiagnostics()`
:936) — beside the existing "Sync to …" / "Follow fleet patch" actions.

The picker it hands to is `fleetPatchTarget` / the deployable `<option>` list at
`dashboard.js:491`. Pre-scoping means switching tabs, setting
`fleetPatchTarget` to the uid, and rendering — reusing the existing state, not a
parallel path.

Give the operator a way back (a crumb or equivalent); losing the device context
on tab switch was the argument for the rejected mini-picker, so answer it.

## Verification

`tests/` (thread-27 policy). Cover: the button appears on a seat-bound device
and lands on the Patches tab with the target pre-selected; an unbound device is
offered a seat first and can complete the flow; the fleet target is unchanged
for anyone who did not use the shortcut.

**Trap (CLAUDE.md gotcha 12):** scope roster clicks to `#device-roster` — seat
rows carry `data-uid` too.
