# 27-test-port-isolation

Browser journeys and some fast tests start a real dashboard on the default
UDP stream port 5551 and outside-input port 5552. With Bob's own dashboard
running (2026-10-27), those tests exit with "dashboard exited before serving
HTTP" (`could not bind to local_addr ('0.0.0.0', 5551)`) — the browser tier
goes red while the operator works.

As of `537749b`, 37 test files launch `dashboard/server.py` without
`--input-port`; most also omit `--stream-port`. `tests/verify_device_roster_sort.py`
shows the fix: allocate both with `free_port(socket.SOCK_DGRAM)`.

Done when every test that starts a dashboard uses private ports for every
listener it opens, and `./tools/run-tests.sh all` passes with a dashboard
running on the defaults. Prefer one shared launch helper over 37 edits if the
tests can adopt it without churn.
