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
