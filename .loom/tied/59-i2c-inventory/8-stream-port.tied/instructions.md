# 8-stream-port

**Status:** after `1` and `77-performance-mode`
**Goal:** development streaming of one device's modules to the dashboard.

Spec: `../0a-io-design-review.tied/proposal.md` (ratified 2026-10-04; Bob's words in `rulings.md`). Work in slices that each verify (`tools/run-tests.sh`, browser journeys where UI changes) and commit. Wire changes are ratified as written in proposal §8; write the matching contract text and §15 row as each piece ships.

- `io-stream <0|1>`: 1 opens or renews a **10 s lease**, 0 closes; one stream
  per device; **refused in Performance** (proposal §2, §8).
- While leased, the bridge copies its bundle to 7771; `bopos.py` forwards it to
  the requester on **5551** as `/io/stream <uid> …`. At most the poll rate.
- The dashboard listens on 5551, renews while anything consumes the stream,
  and stops renewing when nothing does.
- simfleet streams fake values. Tests: lease expiry, refusal in Performance,
  one-device rule, and that control and heartbeats are unaffected.
- Contract: §4 port rows, the §6 paragraph that allows IO value streams, §15.
