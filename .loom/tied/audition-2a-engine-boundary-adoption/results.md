# Listener-puck boundary adoption

Stage 0 and engine-boundary v1.2 are tied. The listener-puck parent now records
the accepted ownership model: N real virtual devices, element-preserving audio
stems, and listener mixing outside the patch and engine-control surface.

The adoption review found one unresolved prerequisite rather than an
implementation defect: the proven Mac/CoreAudio Stage 0 output is already
mixed at the hardware device, so it cannot supply isolated stems to an
external listener matrix. The former JACK-only instruction was Linux-shaped
and cannot silently become the Mac composition workflow.

The parent now contains a Bob decision gate among JACK, macOS virtual/aggregate
device routing, and engine-native buses with a mandatory PD-capable fallback.
No wire, meter plane, patch parameter, or `.pd` edit was introduced.

Verification was documentation/architecture review against:

- `docs/OSC-CONTRACT.md` v1.2 §§4, 4.2, and 11;
- tied `engine-boundary-ratification` (production/audition topology and meter
  deletion);
- tied patch-seam resolution (one engine clones N elements); and
- tied Stage 0 Mac/CoreAudio acceptance (`808a152`).
