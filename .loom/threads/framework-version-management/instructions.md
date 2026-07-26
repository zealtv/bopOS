# framework-version-management

Make bopOS framework currentness visible and safely actionable across the fleet,
so an operator can identify out-of-date devices and converge them deliberately.

This goal is still current, but much of its original update-flow scope has
shipped. The host checkout shorthand is visible; nodes report heartbeat
`version`, report `git_rev`, `contract_version`, and `update_model`; Devices
already exposes per-device and fleet **Update bopOS** actions; and unattended
convergence now reports phases, reboots only after success, and has passed a
real-node gate.

The remaining gap is desired-state comparison: define the authoritative
host/release fact and honestly classify each node as current, stale, unknown,
or diverged. Build any eventual UX on the shipped update action and receipt
model rather than redesigning them.
