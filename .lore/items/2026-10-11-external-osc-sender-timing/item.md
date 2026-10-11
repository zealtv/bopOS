# Forward-sync timing from external OSC senders, and how Belief System really synced

Session investigation, 2026-10-11: why only the dashboard can stamp synced `/e/*` events, why a node-side relative lead loses sync, what Belief System's large `/objectStart` integer actually did (sender-clock "least late" estimation, not the Happy Brackets synchronizer), and Bob's conclusion that external senders should route through the dashboard.

## Source

Claude session with Bob, 2026-10-11, bopOS `main` at `b12f582`–`4390fc3`.
Primary evidence read in-session: `python/bopos.py`, `python/sync_node.py`,
`dashboard/osc_bridge.py`, `docs/OSC-CONTRACT.md` v1.21;
`~/repos/belief-control` (Max patches and git history);
`Belief System tech bible 2.0.pdf` (22 Nov 2023, Bob's SYNC archive);
`https://github.com/orsjb/BeliefSystem` at `0de624b` (2024-05-20),
`BeliefSystemIntelliJ/src/BeliefSystemRenderer.java`.

Corrects the Belief System reading in
`2026-09-25-architecture-review-2026-07-05` §5. Guidance carried forward in
glean finding `external-osc-timing`.

## Tags

- clock-sync
- events
- external-senders
- belief-system
- happy-brackets
- prior-art
