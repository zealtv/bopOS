# Decisions

## Keep expired generations as ordered attribution barriers

An expired record no longer counts as an active fetch and therefore does not
block a retry. It remains at the head of the device/slot record sequence until
a terminal arrives.

The first terminal after a retry is ambiguous because OSC contract v1.3 has no
request ID. The bridge consumes the oldest expired record without changing the
device's observed distribution, then re-sends the still-active successor with
the same URI and fingerprint. After that send, every possible terminal names
the successor bytes, so the next terminal can certify them safely.

This was chosen over liveness-based retirement because an offline/online
transition does not prove that the node process restarted, and over age-based
retirement because any finite age weakens the no-misattribution invariant.
Multiple consecutive expired generations remain safe: each ambiguous terminal
retires one tombstone and re-sends the one active successor.

## Surface genuine suppression through the existing error event

`fetch_matches` now reports only live generations. If `fetch()` cannot start
and no identical live generation exists, convergence broadcasts the existing
WebSocket `error` shape with the device UID and slot. An identical live fetch
still coalesces normally and does not produce an error.

---

# Second pass (2026-08-13, after reopening)

See `reopened.md` for why. The decisions above stand; these extend them.

## Liveness is a legitimate basis for *starting* a generation

The first pass rejected liveness-based retirement on the grounds that an
offline/online transition does not prove the node process restarted. That is
correct — and it is an argument about **attribution**, which was then wrongly
applied to **admission**.

Attribution never depends on a liveness judgement, because a generation ruled
out is demoted to a tombstone rather than forgotten. Every guarantee the first
pass established still holds against a late receipt. What liveness decides is
only whether a *new* generation may start alongside it.

So the cost of judging wrongly is bounded and small: one extra `/os/fetch` for
a transfer already running, which the node coalesces — `queue_fetch` keys jobs
by `(uri, slot)` and appends the requester to the running job rather than
starting a second download. The cost of refusing to judge at all was a
30-minute silent lockout on every push to that device and slot.

## Two signals, because they cover different failures

`strand_device_fetches`, called from `offline_sweep`, retires a device's
generations the moment it drops off the network. This is the reported failure —
a reboot mid-transfer — and it recovers within the 30s offline sweep rather
than at 1800s.

`FETCH_STALL_SECONDS` (120s with no progress) covers the case with no offline
edge at all: the node stayed up and its terminal was lost to UDP. The bound is
derived from the node's own limit of 30s x 3 attempts per file, with margin.
`/os/fetch-progress` refreshes the clock, so a genuinely slow multi-file
transfer is not superseded while it is still reporting.

## `fetch_matches` had to move with `fetch`

Fixing admission alone would have changed nothing observable.
`converge_fleet_patch` falls back to `fetch_matches` when `fetch` returns
False, and a stranded record has a matching fingerprint, so it was reported as
in-flight — the device joined `waiting`, convergence timed out silently, and
the operator error the first pass added was never reached. Both predicates now
read liveness through one helper so they cannot drift apart again.
