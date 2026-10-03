# Shared reported contract version

`python/osc_contract.py` owns `VERSION = "1.17"`. The real helper, simfleet,
and audition import that module and use its version in `/os/report` JSON.
This corrects stale reported metadata to the existing ratified version; it
does not amend the contract or change message grammar.

The durable version regression reads the `**Version x.y**` contract heading,
compares it to the shared constant, and decodes the OSC datagrams produced by
the actual simfleet and audition report methods. It checks the report address,
single string argument, unicast target and reported version. The existing
real-helper report test now expects the shared constant instead of pinning
the stale literal. Together the tests catch a forgotten constant update or
a reporter diverging from it, without reading Markdown at runtime on nodes.

## Verification

- Before implementation, `tests/test_contract_version.py` failed: both
  serialized virtual reports said `1.16` instead of the heading's `1.17`, and
  the shared module was absent. See `before.log` (two failures, one error).
- After implementation, the same command passed all three checks; see
  `version.log`.
- `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python
  tests/test_device_enabled.py`: seven passed, including the actual helper's
  serialized `/os/report`; see `node-report.log`.
- `./tools/run-tests.sh fast`: all 380 tests passed; see `fast.log`.
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m
  py_compile python/osc_contract.py python/bopos.py tools/simfleet.py
  tools/audition.py tests/test_contract_version.py tests/test_device_enabled.py`:
  passed.
- Stitch `verify.py` runs both focused files and locates the repository by
  marker, so it remains usable after tying.
- `git diff --check`: passed.

No browser surface changed, so the browser tier was not repeated. The known
preset failure is still tracked by `5-browser-tier-red` pending preset removal.
Datagrams were decoded from recording sockets; the real helper's OSC clients
were faked by its existing test fixture. No physical Pi, audible engine,
installation LAN, or iPad verification is claimed. User changes to
`dashboard/shows/test.json`, `.codex/`, and `.obsidian/` were left alone.
