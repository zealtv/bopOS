# d8-2-simulate-toggle

Authority:
`.loom/tied/dashboard-8-identity-sim-design/` (proposal + ratification).
Needs d8-1's seat model.

Simulation as a distinct mode (Bob's Q3 ruling: no half-sim fleets —
"when simulation is on, that is a separate state from performance
entirely; all seats are filled with sims; simpler").

- [x] **Simulate ON**: dashboard spawns `tools/audition.py` as a managed
      child process, one engine instance per seat — **every seat**,
      regardless of real bindings — and binds instance↔seat via ordinary
      `/os/assign`. Instance rows enter the roster `virtual: true`, never
      persisted.
- [x] **The mode IS the send target** (Bob, 2026-07-13, resolving the seat
      id collision): performance mode = bridge sends to LAN broadcast as
      today; **sim mode = bridge sends unicast to `127.0.0.1:6660`**, where
      the relay is the sole binder (contract v1.2 topology; matches the
      loopback-only `/audition/listener` seam). Real devices can never
      receive sim traffic, so no warning gate is needed — render a passive
      "N real devices online (not driven)" note instead. Pause the bridge's
      assign-replay to reconnecting real devices while in sim mode so
      nothing leaks to the LAN; resume + replay on return to performance
      mode. No dual-driving logic, per ratification.
- [x] **Simulate OFF**: stop the relay cleanly (child-process lifecycle:
      spawn, health, teardown on dashboard exit too), drop virtual rows and
      their bindings; real seats' stored bindings are restored untouched.
- [x] **Listener puck renders only while simulation is active** (it drives
      the loopback-only `/audition/listener` seam, meaningless otherwise) —
      this supersedes the unconditional render in `spatial.js`; ui-2's
      drag-dial applies whenever the puck shows.
- [x] **Occupancy display**: each seat renders live / sim / empty on map +
      sidebar; sidebar gains a Simulate section (toggle + relay status).
- [x] **Deferred by Bob**: a cap on sim instance count — note it, don't
      build it.
- [x] Audition relay flags to reuse: `--devices N --audio-backend
      coreaudio|jack|none --engine-port-base …` (survey has the full CLI);
      audible is the mode (Q2) but keep `none` reachable for tests.
- [x] verify_*.py: toggle on spawns relay + N virtual rows bound to all
      seats + puck appears; toggle off reaps process and rows + puck hides;
      restart dashboard mid-sim → no virtual rows persisted.
