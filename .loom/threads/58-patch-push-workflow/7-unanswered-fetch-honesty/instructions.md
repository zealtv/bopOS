# 7-unanswered-fetch-honesty

On 2026-10-27 Eden Pearl missed two broadcast `/1/os/fetch` commands for
`kc-test` (probably Wi-Fi power save, see thread `79-wifi-power-save`). The
node never acknowledged ("queued"), yet its badge said **switching** — and
would until `FETCH_TIMEOUT_SECONDS` (1800 s) expired. Nothing told Bob the
node hadn't answered or that a retry was worth trying. A unicast resend
fixed it at once.

`5-fetch-tombstone-lockout` already lets a retry through after
`FETCH_STALL_SECONDS` (120 s); the badge doesn't reflect that.

Done when a fetch still in phase `sent` past the stall window shows as
unanswered (wording per glean `dashboard-vocabulary`) with Update patch as the
remedy, while acknowledged slow transfers (queued/fetching) keep the long
timeout. Consider whether per-device commands like fetch should go unicast to
the node's observed IP rather than broadcast — a design call for Bob.
