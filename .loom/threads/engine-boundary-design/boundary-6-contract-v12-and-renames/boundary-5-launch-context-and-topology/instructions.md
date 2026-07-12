# boundary-5-launch-context-and-topology

Make run context bopOS-owned while retaining atomic launch-time delivery.

- Generate seed, run-id string, patch, and assets from a bopOS-owned step;
  deliver them through `start-engine.sh` (`-send` for PD, environment for
  other engines), not an OSC-at-boot race.
- Add retrying `/config` acquisition to the SuperCollider starter.
- Remove audition instances' fixed-port bind attempts; each engine uses its
  assigned `BOPOS_ENGINE_PORT` (default 6661 in production).
- Unify the production/audition relay library only where evidence shows this
  is practical; topology equivalence is required, library identity is not.
- Preserve the ratification's civil-time opening without designing it here.
- Verify per `docs/VERIFICATION.md`; never edit `.pd` files.
