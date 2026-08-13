# Reopened 2026-08-13

This stitch was tied earlier the same day (`completed-at` 2026-08-13T15:11:49,
commit `96bec64`). Bob reopened it within the hour, on the rig, because the
defect it names is still live on Finn Jet.

`decisions.md` and `verification.md` below are **kept as written**. They are
accurate about what the first pass did and tested; they are not accurate as a
claim that the lockout is fixed. This file records the gap.

## What the first pass covered

A fetch record whose timeout had fired (`phase == "expired"`). It stops being
counted as an active fetch, so a retry can start, and the first ambiguous
terminal retires the tombstone and re-sends the successor.

## What it missed

A record stranded in a **live** phase — `sent`, `queued`, or `fetching` —
because the device acknowledged the fetch and then rebooted, or its terminal
was lost. This is the strictly more common case: it is what a reboot, a WiFi
blip, or a fleet deploy catching a node mid-restart actually produces.

`fetch()` refuses a new generation on `phase != "expired"`, and `fetch_matches`
then reports the stranded record as in-flight. `converge_fleet_patch` takes its
`matched` branch, adds the device to `waiting`, and waits for a terminal that
will never arrive — **bypassing the operator error this stitch added**, which
is why the symptom is a button that visibly does nothing.

So the first pass narrowed the lockout from permanent to
`FETCH_TIMEOUT_SECONDS` (1800s), since `_expire_fetch` still converts the
record into a tombstone the new retry path can clear. Inside that 30-minute
window the operator experience is unchanged.

## Evidence from the rig

Finn Jet held `fetch: {"patch:bonks-pd": "fetching"}` with `distribution: {}`.
Re-triggering `set_device_patch` from the dashboard produced **no `/os/fetch`
on the wire and no `ws_error`** — the device journal recorded nothing at all
for the attempt. Reproduced away from hardware as
`test_live_generation_stranded_by_reboot_does_not_lock_out_retry` in
`tests/test_fetch_generations.py`.
