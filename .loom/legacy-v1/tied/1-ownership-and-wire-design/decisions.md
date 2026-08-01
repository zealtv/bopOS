# Physical-device control routing — ratified design

Ratified by Bob in the 2026-07-23 working session. This design replaces the
single mutable OSC destination as an ownership model.

## 1. Ownership is explicit

Every outbound operation chooses one of three owners. The WebSocket handler
name or the tab from which a command originated is not itself a routing rule.

| Owner | Destination | Operations |
|---|---|---|
| execution | the active Live, Simulation, or Patch Edit target | master, MUTE ALL, patch parameters and generators, cues, points, and editor/audition-private controls |
| physical | the configured installation LAN target on UDP 6660 | exact-UID administration, physical assignment/membership, report/inventory requests, and physical patch and asset distribution/switching |
| host | no OSC destination | aliases, registry Forget, catalog refresh, saved Dashboard documents, and other host-only state |

There is no new port. `bopos.py` remains the sole physical-node LAN listener on
6660 and replies on 5550. The Dashboard may use one UDP socket, but its API must
make the execution or physical destination explicit for every send.

The current `fleet_mutations` set conflates locking, ownership, and execution
mode. Replace it with narrow policy:

- execution operations follow the active execution route;
- physical operations always use the physical route, including while
  Simulation or Patch Edit is active;
- host-only operations never acquire an OSC destination;
- workflow-specific guards remain local to the operation (for example,
  confirmation before replacing a Seat binding or an active asset slot).

## 2. Devices-tab inventory

Everything presented as an operation on a Devices-tab physical-device detail
belongs to the physical object, regardless of execution mode:

- Device enabled/disabled;
- set hostname;
- Identify, report, reboot, shutdown, restart engine, and Update bopOS;
- assign, replace, or unassign its Seat;
- request installed patches and retry/switch/pull its physical patch;
- inspect, send, update, or remove its physical asset slots;
- bulk physical-device actions exposed alongside the roster.

Alias rename/reset and Forget are host-owned registry operations for that
physical UID and emit no OSC. Navigation such as Open Seat/Open Assets is also
host/UI-only. A linked Assets workspace retains the selected physical UID and
therefore retains physical ownership.

The same operation keeps the same owner when reached elsewhere. For example,
Seat-tab assignment to a physical UID is physical; an assignment generated for
an audition virtual UID is execution-private.

Clock sync follows the execution route because it establishes the timebase for
execution-owned cues. Heartbeats and replies are inbound observations rather
than Dashboard routing choices.

Requests whose target may be physical or virtual (`params`, `patches`, and
similar inspection) resolve ownership from the target object. They must not
infer it from the supervisor mode.

## 3. Device enabled wire and state

The old exact-device `mute` vocabulary is retired rather than kept as a
compatibility alias. Finn Jet is the only deployed node and will migrate with
the host.

Dashboard → physical fleet, UDP 6660:

```text
/all/os/to <uid:string> enabled <0|1:int>
```

Only the exact UID applies it. `1` means that physical device's audio output is
enabled; `0` means disabled.

Physical node → Dashboard, UDP 5550, after persistence and mixer enforcement:

```text
/os/enabled <uid:string> <device-enabled:0|1> <output-enabled:0|1>
```

The node owns three distinct values:

```text
device_enabled       persistent exact-device state
mute_all              session execution state received as /all/os/mute
output_enabled        device_enabled AND NOT mute_all
```

Hardware enforcement remains below patch logic:

```text
hardware_mute = NOT output_enabled
```

MUTE ALL keeps its existing execution wire spelling `/all/os/mute <0|1>` and
follows the same active destination as master. It is not renamed to Device
disabled and does not mutate `device_enabled`.

`/os/report` replaces the ambiguous `device_muted` and effective `muted` fields
with:

```json
{
  "device_enabled": true,
  "mute_all": false,
  "output_enabled": true
}
```

Simulation and audition implement the same state grammar for parity, but the
Devices tab never exposes Device enabled/disabled for virtual nodes.

## 4. Persistence, boot, and convergence

The node persistence key is `device_enabled`, defaulting to `true`. On the
first updated Finn Jet boot:

1. Prefer an existing `device_enabled` value.
2. Otherwise, if legacy `device_muted` exists, store its inverse as
   `device_enabled`.
3. Ignore the legacy key thereafter.
4. Enforce `NOT (device_enabled AND NOT mute_all)` before or while launching
   the engine, as today.

The host device registry likewise stores `device_enabled`, defaulting to true.
On load, a legacy `device_muted` boolean is inverted once and the canonical
saved form drops the old field.

The Dashboard's per-UID desired state remains authoritative:

- an operator switch persists desired state before sending;
- an online acknowledgement clears pending only when it matches;
- an offline switch may stage desired state and remains unconfirmed;
- first appearance/reappearance sends desired state once;
- a report with missing or mismatched state triggers one repair send;
- ordinary matching heartbeats do not spam the command;
- old/unacknowledged state remains honestly unconfirmed.

## 5. Execution transitions

Entering or leaving Simulation/Patch Edit never sends a physical Device
enabled/disabled command and never replays any other physical administration.

The execution restore operation may:

- change only the execution destination;
- replay master and MUTE ALL to the newly active execution target;
- replay other explicitly execution-owned state where its existing contract
  requires it.

It must not replay physical assignment, membership, Device enabled/disabled,
hostname, inventory, patch, asset, or administration merely because the
execution target changed. Those states converge from their own physical events.

MUTE ALL and master must work in all three modes. The present Patch Edit guard
that rejects MUTE ALL is therefore removed. Their shared Dashboard values may
be replayed when the active execution target changes, just as master is today.

## 6. Implementation boundary

Expected implementation surfaces:

- `dashboard/osc_bridge.py`: explicit physical and execution sends;
- `dashboard/server.py`: ownership-aware handlers and narrow mode locking;
- `dashboard/state.py`, `dashboard/device_aliases.py`, and Dashboard JS/CSS:
  positive Device enabled state and migration;
- `python/bopos.py`: positive node state, wire receipt/report, and migration;
- `tools/simfleet.py` and `tools/audition.py`: grammar and state parity;
- `docs/OSC-CONTRACT.md`, `docs/OSC-REFERENCE.md`, and relevant port/architecture
  prose: terminology and route clarification;
- living `tests/` coverage organized by Dashboard routing and node protocol.

No `.pd` edit and no new network port are required.

## 7. Acceptance matrix

The implementation is not complete until focused checks prove:

1. In Live, Simulation, and Patch Edit, every physical Devices-tab OSC action
   reaches the physical receiver and never the audition receiver.
2. In those modes, master and MUTE ALL reach the active execution receiver and
   never the inactive one.
3. MUTE ALL works during Patch Edit.
4. Changing modes by itself emits no `/all/os/to … enabled …` frame.
5. Device enabled survives node and Dashboard restart, stages while offline,
   converges on appearance/mismatch, and clears pending only on `/os/enabled`.
6. MUTE ALL never changes persisted Device enabled state; effective output is
   their stated conjunction.
7. Host-only alias/Forget operations emit no OSC.
8. Finn Jet accepts the new spelling and reports the positive fields after its
   software is updated.
