# patch-admin-surface

**Goal:** a patch running on a Pi can request framework admin actions
(update the active patch, update bopOS, shut down, reboot) and receives the
bopOS version and active-patch fingerprint alongside the patch name it
already gets. All of it documented, including a complete OSC quick-reference
table covering every message any sender can construct.

**Ratification:** Bob requested this directly on 2026-07-17 (this session).
The v1.6 contract §4.2 says engine-sent traffic is "requests only —
administrative commands never cross from an engine to the framework"; Bob's
request supersedes that constraint for a bounded admin verb set. The
amendment stitch records his words — that is the ratification record; no
separate gremlin gate needed.

Children in order: 1-contract-amendment → 2-engine-admin-requests →
3-version-context → 4-osc-quickref.

House rules that bite here: never edit `.pd` files (any `[bopos]`
abstraction bus additions are Bob's follow-up — say so in the docs);
PD OSC floats are 32-bit (versions/fingerprints travel as strings).
