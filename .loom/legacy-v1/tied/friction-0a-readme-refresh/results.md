# README refresh results

Rewrote the root `README.md` against the implemented July 2026 system rather
than the removed PD-dashboard workflow.

The new entry point covers:

- current delivery status and the outstanding Linux/hardware gates;
- Pi installation with the repository's present `pi`/`/home/pi` bootstrap
  assumptions stated explicitly;
- the web technical and facilitator dashboards;
- persisted dashboard assignment and `bopos.devices` as an optional seed;
- manifest-declared engines, entrypoints, parameters, and facilitator controls;
- the OSC v1.2 sole-LAN-listener engine boundary and all six ports;
- PD and SuperCollider patch adapters, provided terms, and run context;
- current I2C command spellings;
- simulated, audible, and MCP2221A laptop development paths;
- the actual repository layout and durable documentation links.

Bob's dashboard direction was also recorded: numeric element coordinates and
room origin/alignment are no longer a standalone stitch. The existing
`dashboard-5-position-precision` task waits for the broader UI review so those
features are judged with layout, legibility, and interaction design.

Verification:

- every relative Markdown link in `README.md` resolves;
- `dashboard/server.py --help` accepts the documented dashboard flags;
- `tools/audition.py --help` accepts the documented local audition flags;
- `python3 python/manifest.py patches/default` validates the documented current
  patch model as `ENGINE='pd'`, `ENTRYPOINT='main.pd'`;
- stale root references to `DASHBOARD.pd`, bare legacy patch commands, and
  `bopos.devices` as identity authority are absent;
- `git diff --check` passes.

No runtime, protocol, patch, or Pure Data file changed.
