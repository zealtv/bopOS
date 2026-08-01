# pe-3b-simulator-param-catchup

Restore simulator parameter convergence after an audible live regression:
managed Pd processes report alive before their patch receive graph is ready,
so the dashboard's one initial `/os/params` catch-up can be lost. Replay the
dashboard-owned parameter declaration/catch-up a small bounded number of times
after each virtual audition node first appears. Keep the replay loopback-only,
cancel-safe, and scoped to the current simulate/edit supervisor generation.

Verify the delayed requests and catch-up frames in a focused browser-free test,
run PE-2/simulation regressions, then live-gate `bonks-pd` without manual OSC
gain injection. Never edit a `.pd` file.
