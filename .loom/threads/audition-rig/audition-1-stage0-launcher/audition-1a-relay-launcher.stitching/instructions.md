# audition-1a-relay-launcher

Build the agent-owned, engine-neutral half of audible Stage 0. The Mac port
spike is tied: one process must own LAN command port 6660 and deliver each
virtual node's matched traffic to a distinct localhost engine port.

Deliverables:

- `tools/audition.py` with simfleet-compatible core flags: `--devices`,
  `--target`, `--report-port`, `--cmd-port`, `--manifest`; add explicit
  engine/local-port/process options as needed.
- N deterministic virtual identities and ids, each emitting contract `/hb`
  reports so the real dashboard distinguishes nodes sharing one host IP.
- One UDP LAN listener using the same selector rules as the ratified contract.
  For `/<id>/...` and `/all/...`, forward only to matching virtual nodes,
  strip the selector, and send to that node's distinct localhost engine port.
  Fleet-wide unselected messages may be copied only where Stage 0 semantics
  are explicit; do not pretend to implement helper clock sync or `/pt`
  decomposition.
- Deliver `/id <id>` locally after engine startup/catch-up.
- Launch real PD processes using the active manifest/entrypoint, existing
  startup values, `BOPOS_ENGINE_PORT`, and CoreAudio `-pa` by default on macOS.
  Preserve an explicit Linux JACK mode or command seam; do not require JACK on
  Mac. Never edit `.pd` files.
- Track only processes the launcher starts. Graceful stop followed by bounded
  escalation must not blanket-kill unrelated PD sessions or watchdogs.
- A dry-run/no-engine mode suitable for deterministic verification.

Verification:

- Add a stitch-local browser-free `verify_audition.py` using UDP engine stubs
  and non-default ports. Prove N heartbeats with distinct uid/id, `/all` fanout,
  exact-id isolation, selector stripping, `/id` catch-up, ignored unmatched
  selectors, and clean owned-process teardown/dry-run behavior.
- Exercise the real dashboard backend where practical; otherwise state the
  remaining dashboard integration boundary honestly.
- Compile every touched Python file and run `git diff --check`.
- Retain exact commands/results and unverified audio/PD/SC boundaries here.

Out of scope / gate:

- Current PD cannot select a local receive port. Bob's edit and the real
  three-instance Mac audio/dashboard run are tracked in sibling
  `audition-1b-pd-mac-gate.waiting`.
- SC port parameterization and multi-server audio are not required while SC is
  absent from this Mac, but the relay protocol must remain engine-neutral.
