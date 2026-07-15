# framework-version-management

Make bopOS framework currentness visible and safely actionable across the fleet,
so an operator can identify out-of-date devices and converge them deliberately.

The wire already reports a node version and exposes `/os/updatebopos`; this
thread must define the desired-version source and honest comparison/update UX
rather than adding a redundant indicator.
