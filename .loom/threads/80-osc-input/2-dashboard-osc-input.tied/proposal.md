# Proposal: the dashboard OSC input (contract v1.22)

**For Bob to ratify.** Drafted 2026-10-26 by Claude from the Kite Choir
workshop of the same day. Nothing implemented. Depends on part 1 only for
typed fields; everything else stands alone.

## In one paragraph

The dashboard opens one UDP port that any machine on the network can send to.
It accepts the running patch's declared events and parameters, bopOS point
frames, and a small `/bop/*` set of bopOS commands. It translates each message
to the device wire — target names to selectors, a missing `/e` or `/p` filled
from the manifest, missing fields filled from defaults, events stamped with
`now + lead` — and sends it to the active target. A reference tab lists
everything the port accepts, and shows what it rejected.

## Rulings this builds on (Bob, 2026-10-26)

Recorded in kite-choir-brains `docs/bopos-show-spec.md`:

- One interface; the inbound schema may differ from the device wire. No
  sentinel from senders; bopOS stamps time.
- `/e` and `/p` optional on input; anything ambiguous needs the explicit form.
- **Declared messages only.** Undeclared ones get rejected.
- Rejections show in the reference tab; no error replies.
- Any machine may send, for now.
- Commands follow the active target — Live, Simulation or Patch Edit.
- Outside point frames win over the dashboard's own.
- Master takes an optional fade.
- Defaults get filled at the input.

## 1. The port

**UDP 5552 on the dashboard**, LAN, any source. It joins 5550 and 5551 as a
dashboard listener. The number is a suggestion; many OSC apps default to 8000
or 9000, and Bob may prefer one of those. One fixed number, not a setting,
unless Bob wants it configurable.

§4's port table gains a row; so does `docs/PORTS.md`. The split-elements
amendment may rework the engine rows of the same table; the rows don't
overlap.

## 2. What it accepts

```
/<target>[/e]/<identity> [fields…]          patch event      → /<sel>/e/<identity> <timeNs> fields…
/<target>[/p]/<identity> <args…>            patch parameter  → /<sel>/p/<identity> args…
/pt …   /point …   /pt/clear <id>           point frames     → unchanged
/bop/master <0..1> [<dur>]                  master, optional fade
/bop/mute <0|1>                             MUTE ALL
/bop/lead <ms>                              event lead
```

Anything else is rejected.

### Targets

| Inbound target | Device selector |
|---|---|
| `all` | `all` |
| a seat number, `12` | `12` |
| `g<id>` | `g<id>` |
| a group name, `spot1` | `g<id>` of that group |

**Group names become addressable by rule** (Bob, 2026-10-26: force
compatible names upfront). As of 2026-10-26 they're free text up to 48
characters (`dashboard/state.py` `clean_group`). The new rule:

- lowercase letters, digits, `_` and `-`, 1–32 characters — the identity
  segment grammar, lowercased;
- not `all` or `bop`, not all digits, not `g` followed by digits, and not a
  plane name that follows a selector (`os`, `io`, `sync`, `e`, `p`).

The dashboard's group editor enforces it. Existing names that break it get
converted on load (lowercased, spaces and other characters to `_`, suffixed
if they clash), through the same adoption-and-notice path the dashboard
already uses for group-name clashes (`adopt_group_names`,
`group_name_adoption_notice`). That way every group is reachable by name and
the reference tab needs no "unreachable" marking. This changes operator-visible
naming, so it's part of what Bob ratifies here.

### Identities

The input looks the identity up in the **active target's patch manifest** (the
fleet patch in Live and Simulation; the edited patch in Patch Edit).

- **Explicit form** (`/spot1/e/trig/play`): the identity must be declared in
  that plane.
- **Short form** (`/spot1/trig/play`): the identity must be declared in exactly
  one plane, and its first segment must not be `os`, `io`, `sync`, `e` or `p`.
  Otherwise it's ambiguous and rejected; the reference tab flags such
  identities and shows their explicit form.
- **Undeclared** identities get rejected in either form. This is stricter than
  the device wire, where nodes still deliver undeclared events (§3.2).

### Events

1. Check each supplied field against its declared kind and range. Numbers coerce
   between `f` and `i`, because OSC apps differ on which they send (Max
   and TouchOSC often send floats for everything); `int`, `toggle` and `enum`
   accept a float only if it's a whole number. `text` requires a string.
   **Out-of-range values get clamped** to the declared range (Bob,
   2026-10-26): `min`/`max` for `float` and `int`, 0…n-1 for `enum`, 0/1 for
   `toggle`. The reference tab notes each clamp beside its rejections.
2. Fill omitted trailing fields from their declared defaults. A missing
   required field (one declared without a default) is a rejection.
3. Stamp `now + event_lead_ms` and send to the active target. Lead 0 sends the
   `"0"` sentinel, as the dashboard's own controls do today.

More fields than the event declares is a rejection.

### Parameters

Pass through with the selector translated. bopOS's automation grammar (fades,
`loop`, `lfo`) works unchanged, because nodes decompose it (§3.3). The dashboard
records the value as it does for its own controls, so the UI and catch-up
reflect what qtable set.

### Point frames

Pass through unchanged. **Outside frames win:** while outside frames keep
arriving — say within the last 2 seconds — the dashboard holds back its own
point output: the ~25 Hz motion loop and the catch-up frame it sends a
reappearing device (`dashboard/osc_bridge.py` `send_points_frame` callers, as
of 2026-10-26). Bob noted on 2026-10-26 that the point editor only sends
while someone uses it, so this guard mostly matters for authored moving points
and catch-up. If Bob thinks it isn't worth it yet, drop it; the pass-through
stands on its own.

## 3. `/bop/*` commands

Each sets the same dashboard state the UI control sets, so the UI follows and
the value persists exactly as it does today.

| Command | Effect |
|---|---|
| `/bop/master <0..1> [<dur>]` | sets master; with `<dur>`, ramps there |
| `/bop/mute <0\|1>` | sets execution MUTE ALL |
| `/bop/lead <ms>` | sets installation `event_lead_ms`, 0–10 000; persists, and the dashboard's lead control mirrors it |

**Master fade.** The dashboard ramps master linearly and broadcasts
`/all/os/master` steps at ~25 Hz, the point-frame rate. A new master value,
from the UI or the input, cancels the ramp. The UI's master control follows
the ramp as it moves. The ramp's destination persists
at its start, so a dashboard restart mid-fade lands on the target.
`<dur>` takes §3.3's duration forms: a bare number in ms, or `250ms`, `10s`,
`1.5m`. No device or patch change.

The alternative is a node-side master generator, like `/p/*` fades: one
packet per fade and loss-proof, but a wire change on every node. Recommend the
dashboard ramp for now; it's what "if this is easy" asked for.

Later admin commands (patch switching, target switching) slot in under
`/bop/` the same way, each its own ruling.

## 4. Routing

All forwarded traffic goes through the dashboard's existing execution send,
which already follows the active target (`osc_bridge.py` `send`, "Send to the
active execution target"). In Simulation it reaches the simulated fleet; in
Patch Edit, the edited device. No new routing.

## 5. The reference tab

A dashboard tab listing everything the port accepts, generated from the
active manifest plus the `/bop/*` table:

- the dashboard's IP and the port, to copy into qtable;
- `/bop/*` commands with their arguments;
- each declared event: short and explicit address, fields with kinds and
  defaults, ambiguity flags;
- each declared parameter: address, kind, range;
- groups, by name and `g<id>`;
- **recent rejections**: time, sender IP, address, reason — an in-memory list
  of the last ~50, cleared on restart.

The tab's name and layout are operator-visible, so they come back as a mockup
from the running app before they're built (glean `decision-gates`). A working
name: **OSC**.

## 6. Contract placement

A new §4.3, "Outside-app input", plus the port row, a §15 entry, and
`docs/OSC-REFERENCE.md` rewritten around the input as the way in. The glean
finding `external-osc-timing` gets revised once this lands.

## 7. Verification

- **Headless:** unit tests for translation, ambiguity, defaults, coercion and
  rejection; a simfleet run where an OSC client sends to 5552 and simulated
  nodes receive stamped events; master ramp steps.
- **Hardware, separate claim:** qtable → dashboard → Finn Jet / Ciro Toast,
  events landing in sync.

## 8. Decided, 2026-10-26 (Bob)

- Group names forced compatible upfront (§2).
- The outside-points guard stays (§2).
- Port **5552**.
- Master fade by **dashboard ramp**.
- `/bop/lead` **persists** and the UI mirrors it.
- Reference tab named **OSC**; its layout still comes back as a mockup from
  the running app before it's built.
- Out-of-range event fields **clamped**, not rejected.

No questions left open. Ready for implementation stitches.
