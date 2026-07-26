# Imani Silver fresh-device incident diagnosis

Date: 2026-07-26
Host: macOS laptop, active LAN interface `en0`
Host address: `192.168.0.100/24`
Device: Imani Silver, `192.168.0.103`

## User-visible symptoms

1. Imani Silver appeared in the Devices roster but clicking her did not open
   Device detail.
2. Ctrl-C of `./run.sh` logged an application-shutdown failure:

```text
dashboard.stop()
  -> stop_supervisor()
  -> restore_live_state()
  -> osc.send_master()
  -> sender.sendto(...)
OSError: [Errno 49] Can't assign requested address
```

## Live browser reproduction

A fresh headless browser connected to Bob's already-running dashboard and
opened Devices. The sole roster row was:

```text
uid: b8:27:eb:b4:64:79
label: Imani Silver
version: dbb1bf3
rssi: -41 dBm
assignment: unbound
```

Clicking the row changed its class from:

```text
device-row patch-exception
```

to:

```text
device-row selected patch-exception
```

The detail panel nevertheless retained “Select a physical device.” The browser
reported:

```text
pageerror: Cannot read properties of undefined (reading 'params')
```

The relevant live device state was:

```text
uid=b8:27:eb:b4:64:79
id=-1
virtual=false
online=true
ip=192.168.0.103
version=dbb1bf3
engine_alive=1
rssi=-41
report=null
declared=null
patches=null
assets=null
alias="Imani Silver"
device_enabled=true
enabled_status="unconfirmed"
patch_badge="unknown"
desired_patch="bonks-pd"
```

The click is therefore not disabled and there is no intentional selection
eligibility rule. `renderDeviceDetail()` begins, but the Device control section
crashes before replacing the placeholder.

### UI cause

`dashboard/static/js/dashboard.js:1199-1211` finds no bound Seat, correctly
marks Device control disabled, but still renders the fleet declarations through:

```js
deviceSurface.tree("device", d.uid, [], declarations, true)
```

The shared component's device/seat branch calls
`valueForSeat(members[0], declaration)`. In
`dashboard/static/js/control-surface.js:33-35`, `members[0]` is undefined and
`seat.params` throws. This was introduced by commit `213092d` (“Give the Device
tab its own live controls”); the existing verifier covered bound devices but
not a fresh unbound device with a non-empty fleet control schema.

## OSC routing reproduction

The dashboard defaults to `--osc-target 255.255.255.255`. Its sender enables
`SO_BROADCAST` but does not bind a source interface/address.

Harmless five-byte UDP probes from an equivalently configured Python socket
produced:

| Sender/destination | Result |
|---|---|
| unbound → `255.255.255.255:6660` | errno 49, “Can't assign requested address” |
| unbound → `192.168.0.255:6660` | send succeeded |
| unbound → `192.168.0.103:6660` | send succeeded |
| bound to `192.168.0.100` → `255.255.255.255:6660` | send succeeded |

`en0` was active with:

```text
inet 192.168.0.100
netmask 0xffffff00
broadcast 192.168.0.255
```

This repository already records macOS errno 49 for PD's legacy limited
broadcast report path in
`.notes/handoff-2026-07-11-engine-boundary-design.md`; this incident proves the
Dashboard's unbound Python sender can hit the same routing failure.

### Operational effect

The transport fault is not confined to Ctrl-C. On first physical appearance,
heartbeat handling updates the in-memory device, then sends persistent Device
enabled state and requests assets/report/params. `_send_to()` does not catch
`OSError`. The enclosing datagram handler catches the exception as a generic
invalid datagram, so the incoming heartbeat can leave a partially initialized
record and the first-seen requests are skipped. That matches Imani's live
`report=null`, `patches=null`, `assets=null`, and unconfirmed enabled state.

On Ctrl-C, `Dashboard.stop()` first calls `stop_supervisor()`. Its already-off
branch calls `restore_live_state()`, which sends master and mute to the same
unroutable target. The escaping exception prevents the remainder of
`Dashboard.stop()`—task cancellation, `osc.close()`, and `state.close()`—from
running, hence Uvicorn's “Application shutdown failed.”

## Relationship and immediate workaround

The shutdown exception and Imani's missing reports/commands share the same OSC
transport fault. That fault does not directly cause the roster-click exception:
the unbound Device-control render is a second defect. Together they make a new
device appear visible but inaccessible.

The incident-session workaround was:

```sh
./run.sh --osc-target 192.168.0.255
```

Then assign Imani from an empty Seat in the Seats tab before returning to
Devices. Directed subnet broadcast makes the assignment command routable, and
binding supplies the Seat object the current Device-control renderer assumes.
This is a workaround only: an unbound Device must remain independently
selectable, and the launch path must not require a hard-coded venue subnet.

## Prior successful onboardings (Bob, 2026-07-26)

This is **not** the first fresh-device onboarding from this Mac: Finn Jet and
Ciro Toast were brought in successfully at least three times (both reflashed,
Ciro twice, Ciro set up through bopOS fresh). Bob ruled out environment drift
on 2026-07-26: same machine, same local network, no known OS/VPN changes, and
he doesn't believe he has ever passed flags to `./run.sh` himself.

That ruling, plus code archaeology, points away from "something recently broke
the transport" and toward **the transport fault being latent on this Mac all
along, with the earlier successes riding on paths that never needed the
unroutable destination**:

- errno 49 for unbound limited broadcast was already recorded for this Mac on
  2026-07-11 (`.notes/handoff-2026-07-11-engine-boundary-design.md`) — the
  host likely *never* routed it.
- Before `5eda7b4` (2026-07-23), `uid_command` sent via `self.send()` to the
  mutable execution `destination` (loopback during simulation); after it,
  device-enabled and UID admin always go via `send_physical()` to the raw
  `--osc-target`. So earlier sessions' first-seen sends may have taken a
  routable destination that the current code no longer uses for them.
- The Finn/Ciro reflash verifications were largely driven by loom sessions
  whose harnesses launch `dashboard/server.py` with explicit ports/targets —
  "Bob never passed flags" does not mean the *onboarding sessions* ran on the
  default target.
- The Imani incident's visible half — click-to-detail failing — is defect 1,
  introduced 2026-07-25 by `213092d`. Earlier onboardings predate it, and the
  incident workaround (assign from the Seats tab) is plausibly just what the
  earlier flow did naturally.

Stitch `2-macos-osc-routing-shutdown` starts with a bounded pass to confirm or
refute this latent-fault reading, because it decides what the regression test
should pin (a code path vs. a masked long-standing hazard).

## Working-tree note

No product files were changed during diagnosis. At intake, the pre-existing
working tree already contained:

```text
M .notes/handoff-2026-07-24-control-surface-presets.md
M dashboard/shows/test.json
```

Those changes belong to Bob and are unrelated to this thread.
