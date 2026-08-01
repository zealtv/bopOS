# fp-0-design-proposal

Produce the compact fleet-wide-patch model/proposal that
`.notes/handoff-2026-07-14-fleetwide-patch-next.md` specifies. Cover, per the
handoff:

1. How one fleet-level desired patch simplifies the technical dashboard and
   facilitator UI.
2. How it simplifies dashboard state, distribution, simulation, engine
   lifecycle, parameter schemas, and convergence.
3. How bopOS distinguishes wrong-name from right-name-but-stale-content —
   define the patch content identity (digest/revision portable across
   git-managed and host-mirrored patches).
4. How fleet desired state and per-device observed state appear in the sidebar
   without turning device cards back into patch-management interfaces.

Also resolve the handoff's open questions: persistence of `desired_patch` in
`installation.json`, all-at-once vs staged switching, rollback semantics on
partial convergence, and what actions a mismatch badge offers.

Prefer extending an existing framework-owned report (`/os/patches` /
`/os/report`) over growing the heartbeat. Additive to v1.3 only.

Deliverable: a written proposal kept via `./lore.sh keep` (follow the
`dist-0-proposal` / `dashboard-8-identity-sim-design` pattern). Then mark this
stitch `.waiting` for Bob's ratification and surface it. On ratification,
split implementation children under `fleet-patch` and tie this.
