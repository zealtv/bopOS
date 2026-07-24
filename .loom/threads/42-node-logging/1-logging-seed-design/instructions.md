# 1-logging-seed-design

Grow the logging seed into a scoped design. Un-waited 2026-07-24 —
Bob wants it done, medium priority. When claimed: produce a
written proposal, **Bob ratifies**, tie with `decisions.md`.

## Cover

- **The facility:** an append-only, timestamped log other bopOS subsystems call.
  API shape (a `log(...)` in `python/`?), format (text vs jsonl), rotation.
- **Destination config** from the Device tab: model, persistence, absent-target
  fallback, and the OSC/admin surface to set it (contract §4.2). Device-tab UI is
  a Bob gate.
- **USB auto-mount:** the mechanism (udev rule / systemd automount), where it's
  installed, stable mount naming, and how logging targets the mount.
  **Note (2026-07-24): `31-install-oneliner` is already tied**, so the automount
  install step is *net-new* install work — spawn it as an implementation child
  of this thread that edits the install script, don't assume 31 carries it.
- **Enumerate the callers Bob has in mind** — this seed exists because several
  features will want it; list the concrete first users so the API fits them.

## Deliverable

`decisions.md` + child implementation stitches created from the ratified scope.
Coordinate the USB-automount install step with `31-install-oneliner` rather than
duplicating it.
