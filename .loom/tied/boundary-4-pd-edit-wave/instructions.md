# boundary-4-pd-edit-wave

Bob-owned Pure Data migration gate after the Python seam and death drill pass.

Agent work is specification and verification support only:

- Write exact edits to `.notes/pd-edits-for-bob.md`: remove the 6660 listener,
  admin forward, echo/report chain, internal selector/identity routing, and
  legacy feedback; introduce `[bopos]`, the ratified `bopos-*` buses, and a
  configurable ingress defaulting to 6661; rename `bopos.osc.pd` to `bopos.pd`.
- Provide a post-edit headless verification recipe/harness.
- Bob edits all `.pd` files. Agents must never edit them.
- Bench a production-style macOS N=1 PD engine before tying this stitch.
- If sole-binder recovery or the 6661 relay is not proven, wait rather than
  removing PD's direct path.
