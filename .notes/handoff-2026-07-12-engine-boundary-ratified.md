# Handoff — 2026-07-12 (engine boundary ratified)

Bob ratified the engine-boundary design with amendments. The authoritative
record is `.loom/tied/engine-boundary-ratification/ratification.md`; it wins
over the council judgment where they differ.

## Ratified direction

- Future `bopos.py` is the sole LAN 6660 binder; every engine, including PD,
  receives the same selector-stripped localhost 6661 API.
- The engine API, `[bopos]` façade, `bopos-*` bus glossary, retained 6662/8880
  IO boundary, launch-delivered run context, one-shot probe, and explicit
  contract v1.2 revision are accepted.
- Migration is a clean break: there are no deployed dashboards, so do not add
  the council's proposed `/helper/*` compatibility alias.
- Delete framework meter streaming and manifest `role: "meter"` entirely.
- The leased probe is unratified reference material only.
- Absolute timestamps must not cross as OSC floats or drive synchronized cue
  timing, but bopOS may eventually provide safely encoded civil time to a
  patch. A generic Python capability-provider/plugin boundary is an open note,
  not a v1.2 feature.

## Next stitch

```sh
./.loom/loom claim boundary-1-client-lock
```

The six implementation stages are nested as a real dependency chain, ending
with contract v1.2 and the behavior-free `helper.py` to `bopos.py` rename.
Read each stitch's `instructions.md` and the tied ratification before working.
Do not edit `.pd` files. The PD stage is Bob-owned and must wait for the prior
relay and helper-death gates.

No implementation stitch is claimed at this handoff.
