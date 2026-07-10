# seam-5-sc-starter-kit

**GATED: requires `seam-1-contract-amendment` tied; the wire details it needs
land in seam-2/seam-3 — prefer running after those tie.**

SuperCollider is a first-class engine (Bob's ruling R3) and the SC side is
**agent-buildable** (only `.pd` is Bob-gated). Build the SC starter kit in
`templates/` (Bob's 2026-07-08 ruling: starter-kit templates live in this
repo):

- An SC template patch (`bopos.patch.json` with `engine: "scsynth"` or
  `sclang` — decide against `bash/start-engine.sh`'s launch path and document)
  that: receives `/p/*` params, multiplies `/os/master` into a master bus mix
  stage (the `bopos.out~` twin), consumes point scalars per element (the
  `bopos.point` twin — clone N element voices, map to output channels), fires
  on `/cue`.
- README documenting the seam from the SC author's side: what arrives, on
  which port, what the minimal correct patch implements, how it degrades if
  ignored.
- Verify: launch the SC template against `simfleet`-style traffic if scsynth
  is available on the dev box; otherwise verify message plumbing with a stub
  and mark the audible run for the audition rig. Be honest in results.md
  about what was exercised.
- The PD twin stays in Bob's waiting room (`pd-edits-for-bob.waiting`) — link,
  don't build `.pd`.
