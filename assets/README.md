# Assets

This directory is the host catalog for project media and data deployed by
bopOS. Each top-level folder is one independently managed **asset slot**:

```text
assets/
  belief-system-000/
    voices/
    textures/
  belief-system-001/
    voices/
```

Everything below a slot is opaque to bopOS. Slots may contain audio, text,
images, models, or any other files a patch or engine needs. Choose boundaries
operationally: content that should be sent, updated, rolled back, and removed
together belongs in one slot.

## Using a slot

1. Copy or create the slot folder under `assets/` on the dashboard host.
2. Open **Assets** in the dashboard and refresh the host catalog.
3. Select one online physical device that is assigned to a Seat.
4. Use **Send** for an absent slot or **Update** when its content is stale.
5. Use a new side-by-side slot name for substantial revisions when rollback
   matters—for example, send `belief-system-001`, switch the patch to it, then
   remove `belief-system-000` after a confidence period.

Updating an existing slot changes files in place while the engine keeps
running. If the active patch declares that slot, it may observe a partial
update. The dashboard warns before continuing; it does not stop or restart the
engine automatically.

Slot names must be a single visible folder name: do not start with `.`, and do
not use `/`, `\`, or a NUL character. Dot-prefixed entries, symlinks, and
in-progress `.part` files are excluded from catalogs and fingerprints.

## Repository boundary

Asset content is intentionally ignored by Git because it may be large or
installation-specific. This README is the only tracked file in `assets/`.
Distribute slot content through the dashboard workflow or the installation's
separate media storage—not by committing it to the bopOS repository.
