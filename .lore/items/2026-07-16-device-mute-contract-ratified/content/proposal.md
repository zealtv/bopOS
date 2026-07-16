# Exact physical-device mute contract

**Status:** ratified by Bob on 2026-07-16.

## Why a contract addition is required

OSC v1.6 cannot address mute to a physical box independently of its Seat.
Numeric and Group selectors follow Seat identity, while `/all/os/to <uid> ...`
currently permits only the exact report and identify operations. Implementing
the requested control with a numeric selector would silently make mute follow
the Seat when the box is reassigned.

## Wire and state

Add one exact-UID full-state operation:

```text
/all/os/to <uid> mute <0|1>
```

The matching node applies it below patch logic and acknowledges only after the
hardware mixer or engine-stop fallback has enforced it:

```text
/os/mute <uid> <device-muted 0|1> <effective-muted 0|1>
```

The node keeps two independent layers:

- `device_muted`: persistent physical-box intent set only by the UID operation;
- fleet safety mute: the existing session overlay set by `/all/os/mute`.

Effective hardware mute is their logical OR. `/os/report` exposes both
`device_muted` and effective `muted`. On boot the node applies persistent
`device_muted` before or while starting the engine. A temporary fleet safety
press therefore does not become permanent, while a deliberately muted box
cannot sound during dashboard reconnection.

The host mirrors desired per-UID mute in the global `device_registry`, outside
venues and presets. It reasserts the value on heartbeat/report, tracks
pending/current/unconfirmed honestly, and deletes it on genuine Forget. Old
nodes without the receipt remain unconfirmed.

Releasing fleet safety mute must restore each box's desired UID state; it must
not blindly unmute boxes whose persistent `device_muted` remains true.

## UI boundary

The control appears in the selected physical Device detail as a compact
Mute/Unmute action with terse state. Each row in the Devices roster also has a
clear compact mute indication. It reflects effective mute and its accessible
label distinguishes persistent device mute from the fleet safety overlay; it
does not expose a second toggle in the list.

Mute remains a Device control, not a Seat or Group control. While fleet safety
mute is active, individual toggles are disabled. No explanatory interface copy
is added.

Seat/Group mute and solo remain deferred to a separate design.

## Ratification

Bob ratified the UID envelope, acknowledgement/report fields, two-layer OR
semantics, node-plus-host persistence, selected-detail control, and Devices
roster indication on 2026-07-16.
