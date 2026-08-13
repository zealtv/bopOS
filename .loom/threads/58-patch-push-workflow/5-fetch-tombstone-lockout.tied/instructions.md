# 5-fetch-tombstone-lockout

A fetch that expires against an unreachable device leaves a permanent tombstone
in `OSCBridge.fetch_pending`, and from then on **that device can never be sent
those bytes again for the lifetime of the dashboard process.** Every deploy,
pin and sync silently does nothing. Only restarting `server.py` clears it.

This is a defect, not an affordance gap — it is why Bob could not sync Ciro
Toast on 2026-08-05 (see `incident-2026-08-05-ciro-toast.md`, "Second session"),
and it outranks the three UI stitches in this thread.

## Measured starting state

`dashboard/osc_bridge.py:749-763` refuses to send when a record already exists
for that uid and slot:

```python
records = self.fetch_pending.setdefault(slot, deque())
if any(record["uid"] == uid for record in records):
    return False  # one generation per device/slot; never mislabel coalesced bytes
```

`_expire_fetch` (`osc_bridge.py:1624-1635`) deliberately does **not** remove the
record when the timeout fires:

```python
# Keep an expired tombstone ahead of any retry: v1.3 has no request id,
# so allowing a new generation could make a late old receipt certify
# newer bytes falsely. A late terminal still consumes this record.
record["phase"] = "expired"
```

The reasoning is sound — the contract has no request id, so a late `/os/fetched`
must be attributable to the generation that asked for it. But the record is
removed in exactly one place, the `/os/fetched` handler
(`osc_bridge.py:1553-1566`). **If the device never replies, nothing ever removes
it.** Not the device going offline, not it coming back, not a new fleet
operation, not a new pin. `shutdown()` (`osc_bridge.py:174-176`) cancels the
timers but does not clear the deque, and the whole structure is in-memory, so a
process restart is the only cure.

The second half of the failure is what makes it invisible.
`converge_fleet_patch` (`dashboard/server.py:2680-2682`):

```python
if (self.osc.fetch(uid, uri, slot, fingerprint)
        or self.osc.fetch_matches(uid, slot, fingerprint)):
    waiting.add(uid)
```

`fetch()` returns `False` (tombstone), and `fetch_matches` returns **True** —
the tombstone carries the same fingerprint the caller wants — so the device is
added to `waiting` as though a transfer were in flight. The loop then waits out
`FETCH_TIMEOUT_SECONDS + 1`, observes nothing, and exits. No OSC is sent, no
error is raised, no `ws_error` reaches the operator, and the badge stays
`stale`. From the UI it is indistinguishable from a button that does nothing.

## How it was reached, which is not exotic

The device was crash-looping on an invalid manifest (`4-invalid-manifest-lockout`)
when a fetch was sent. It never received it, so it never replied. That is the
general shape: **any device that is unreachable when a fetch goes out poisons
that slot until the dashboard restarts** — a Pi rebooting, a flaky WiFi moment,
or a fleet deploy that catches one node mid-restart.

## The change

Distinguish "a reply may still arrive" from "this generation is dead" so a new
fetch can be issued without letting a stale receipt certify new bytes. The
tombstone's *purpose* must survive: a late `/os/fetched` from generation N must
never be credited to generation N+1.

Some directions, none of them ratified — whoever claims this should choose and
record why in `decisions.md`:

* **Retire the tombstone on evidence the old generation cannot reply**, e.g.
  when the device has been observed offline since the record was created, or
  when its reported uptime shows it restarted after the fetch was sent. A node
  that rebooted has no pending fetch to reply about.
* **Keep the tombstone but stop it blocking**: allow a new record alongside it,
  and have `_fetch_record` refuse to credit a terminal to a record whose
  generation has been superseded. This preserves the anti-mislabelling property
  in the place that actually enforces it — attribution — rather than by
  suppressing sends.
* **Age it out.** A tombstone older than some multiple of `FETCH_TIMEOUT_SECONDS`
  cannot plausibly be about a reply still in flight over UDP on a LAN.

Whatever lands, `fetch_matches` must not report a dead record as in-flight —
that is the part that converts a blocked send into a silent success. And a
suppressed fetch should be **visible**: today `fetch()` returning `False` is
discarded by its only caller.

## Verification

`tools/simfleet.py` speaks the real protocol, so this is reproducible without
hardware: deploy a patch to a sim node, kill or silence it before it replies,
let the fetch expire, bring it back, and deploy again. Assert an `/os/fetch`
goes out the second time. On today's tree it does not — write that assertion
first and watch it fail.

The natural home is `tests/verify_device_patch_targeting.py` or a new
`tests/test_fetch_generations.py` if the logic is better exercised without a
browser; the record bookkeeping is browser-free and belongs in `fast` if it can
be tested there.

Also worth an assertion: the operator sees *something* when a convergence
cannot start. Silence is what made this cost a session.

## What was and was not proven on 2026-08-05

**Proven:** with the tombstone present, `retry_fleet_patch` emitted no
`/os/fetch` and the device's journal recorded none, across repeated attempts
from the UI. After restarting `server.py` — which clears `fetch_pending` —
one `retry_fleet_patch` converged the device end to end (fetch ok, patch
switch, engine restart, badge `current`, `main.pd` hash matching the host).

**Not proven:** that the tombstone was the *only* reason, because the restart
also cleared every other piece of in-memory state at the same time. The code
path above is sufficient to produce exactly the observed behaviour and the
device's `fetch` record read `{"patch:fire-button": "timeout"}` throughout,
which is the tombstone's own signature — but the confirming experiment is the
simfleet reproduction above, not the restart.

**A methodology note that cost twenty minutes here:** the websocket protocol is
`{"type": …, "data": {"uid": …}}`. A probe that puts `uid` at the top level gets
`uid = None` (`server.py:314-315`), and `retry_fleet_patch` then returns
silently at its `distribution_targets` guard with no error to the client — so a
malformed probe looks exactly like the bug it is meant to be testing. Any
harness written against this path should first assert its own message reaches
the verb, by watching for the `/os/patches` request the handler always makes.
