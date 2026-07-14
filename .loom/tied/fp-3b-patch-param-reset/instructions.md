# fp-3b-patch-param-reset

Fix the silent managed-simulation switch exposed after fp-3: `bonks-pd`
loads, but same-named/stale seat parameters from the prior schema override its
manifest defaults (most stored `gain` values were zero).

- On a **different fleet patch name**, replace every seat parameter map with
  exactly that validated manifest's declared defaults; mirror the reset into
  live runtime devices before convergence/restart.
- Remove parameters absent from the new manifest. A declaration without a
  default is absent until the operator supplies it.
- Same-name Set/restage and stale Retry preserve current values.
- Revert is a name change and therefore restores the previous manifest's
  defaults, not a hidden per-patch parameter history.
- Apply the rule to managed simulation and deployed-fleet paths. Do not edit
  `.pd` files.
- Verify browser-free with managed audition (`--no-engine`) plus state checks;
  run fp-3 UI and simulation regressions.
