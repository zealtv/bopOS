# Handoff — documentation review launch (2026-07-16)

This supersedes `.notes/handoff-2026-07-16-dashboard-sweep-complete.md`.

## Launch state

- The Dashboard implementation runway is complete. `tabs-3-next-sweep` and the
  `ui-tabs` goal are tied; there is no claimed stitch and no implementation
  loose end.
- The next session starts by claiming
  `patch-workflow-friction/friction-0-docs.waiting`. Its former distribution
  prerequisites are complete; the `.waiting` state now marks only Bob's chosen
  session boundary.
- `friction-1-starter-kit` remains waiting behind the documentation review so
  its examples and copy can follow the final information architecture.
- The current code head before this housekeeping commit is `6549b5f`. It makes
  the Dashboard wordmark version use Git's seven-character shorthand. Focused
  verification passed 3/3 and the existing Dashboard browser regression passed
  17/17.

## Documentation brief

Treat `friction-0-docs` as a complete documentation review, not a single new
composer page:

1. Make `README.md` the friendly overview for an intelligent audio-aware reader
   who may know Pure Data but is not assumed to be a developer.
2. Establish clear routes to a getting-started guide, a composer guide, and
   coherent technical documentation.
3. Keep the main composer workflow git-free: copy a demo under `patches/`, edit,
   audition, and use the Dashboard Send flow. Put Git in a separate advanced
   section.
4. Audit `README.md`, `docs/`, `dashboard/README.md`, `patches/README.md`, and
   their links for duplication, stale workflow, unexplained jargon, and broken
   hierarchy.
5. Walk Dashboard labels and the patch Send path against the real Dashboard and
   simfleet while writing. Label hardware-only claims honestly.

The complete ratified scope and the no-build zip-upload decision gate are in
the stitch's `instructions.md`. Read that file before editing documentation.

## Standing boundaries

- Never edit `.pd` files. Record any required Pure Data work in
  `.notes/pd-edits-for-bob.md`.
- Existing Pis need one manual `sudo bash/provision.sh` after updating to install
  the alias-derived hostname helper and sudoers policy. Routine **Update bopOS**
  cannot install this root-owned boundary.
- Real iPad/Safari, screen reader, installation LAN, audible engine, and real Pi
  behavior remain outside the completed software verification unless explicitly
  exercised in a future stitch.
