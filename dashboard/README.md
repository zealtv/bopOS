# bopOS dashboard

Web control surface for the fleet: the tabbed application at `/`, with
`/facilitator` retained as the standalone compatibility entry for the
touch-first Dashboard surface.

This is the operator reference (flags, modes, state files). For a guided
first run see [Getting started](../docs/GETTING-STARTED.md); for the
composer's deploy flow see [Composing](../docs/COMPOSING.md).

## Quickstart (laptop, no hardware)

One-time setup:

```sh
python3 -m venv ~/.venvs/bopos
~/.venvs/bopos/bin/pip install -r dashboard/requirements.txt python-osc
```

Run the server (terminal 1, from the repo root):

```sh
~/.venvs/bopos/bin/python dashboard/server.py
```

Run a simulated fleet to play against (terminal 2):

```sh
~/.venvs/bopos/bin/python tools/simfleet.py --devices 5
```

Then open:

- **<http://localhost:8080/>** — Dashboard, Seats, Devices, Patches, Assets,
  and Show tabs. The landed controls cover device inspection, spatial
  authoring, patch editing, host-to-node distribution, discovery/assignment,
  synced named cues, venues, presets, single-device asset delivery, and
  show authoring/playback (see "The Show tab" below).
- **<http://localhost:8080/facilitator>** — standalone Dashboard view: device cards
  with the patch's promoted (`facilitator: true`) params as labelled controls,
  master, Silence All, preset picker. On an iPad, "Add to Home
  Screen" launches it fullscreen.

Useful simfleet variations: `--unassigned 2` (exercise discovery/assign),
`--engine-dead 1` (a crashed engine), `--drop 0.05 --jitter-ms 30` (bad WiFi),
`--manifest path/to/bopos.patch.json` (serve a different param declaration).

When `tools/audition.py` runs on the dashboard machine, drag the white listener
puck to preview the installation from that position; edit its heading above the
map. The dashboard sends the complete listener state only to loopback port 6660,
where the audition relay derives and forwards fixed-stereo matrices. This
private preview state is never broadcast onto the installation LAN and is not
part of the fleet OSC contract.

The header's **Execution target** toggle (Live fleet / Simulation / Patch
edit) manages this audition rig directly: switching to **Simulation** runs
one selected patch across the whole simulated fleet, and every valid folder
under `patches/` is already available. Use the global Fleet patch selector
to restart the managed engines into another host patch. Send/Sync is
intentionally absent in this mode because there is no remote filesystem to
converge; live fleet devices are never driven while simulating.

`tools/simfleet.py` is different: it is the protocol-only remote-node harness.
It retains `/os/fetch` queue and receipt behaviour so distribution itself can be
tested without hardware.

## The Show tab

The Show tab (previously the reserved "Sequencer" placeholder) is the
primary performance-control surface. A **show** is an ordered list of
**steps** — compact one-line rows, Ableton-session-view density — separated
by **dividers**; the steps between two dividers form a **section**. Each
step carries a set of OSC **messages** (rendered as pills, colour-coded by
a stable hash of their alias) that all fire when the step starts.

Steps have a duration (h/m/s), play-n-times or loop-forever, optional
forward-sync for cue messages (schedules `/cue` ~500 ms ahead on the shared
clock), and one or more **then-actions** resolved when playback exhausts:
stop, play again, next/previous step, any/other in section (other has
Ableton shuffle-bag semantics), goto a step by uid, next/previous section.
Multiple then-actions choose randomly. A goto whose target step was deleted
falls back to stop and flags the row. Per-row icon transport
(play/stop/pause/trigger-next) plus a global Stop all.

Messages are built in the context-sensitive inspector: parameter, cue,
point, or raw payloads, and a target picker that composes any mix of seats
and groups as chips (`3+7+g1`); cue/point payloads are selector-free so
their target is greyed. Messages support copy/cut/paste/move/delete between
steps (paste mints a fresh uid), with keyboard equivalents on the focused
pill.

Show documents persist as JSON in `shows/` next to the installation state
file, one file per show; the schema and playback semantics live in
`.notes/show-tab-design-2026-07-18.md`. The transport strip carries the
show catalog: switch between saved shows (stops playback first), create,
rename, or delete them; the active show persists across dashboard restarts
and is shared by every connected client. Two collapsible OSC consoles sit
under the table: outgoing (everything the dashboard sends) and incoming
(everything the LAN surface receives, heartbeats included). Filter with
space-separated terms that AND together, `*` wildcards, and `!` negation —
e.g. `/p/* !/sync` — plus pause/clear and sticky auto-scroll.

## Real fleet

On the installation LAN the defaults already match the OSC contract (listen
5550, send 6660, broadcast target). Run the server on any machine on that
network; real nodes appear as they heartbeat:

```sh
~/.venvs/bopos/bin/python dashboard/server.py --host 0.0.0.0
```

From the repo root, `./run.sh` is a shortcut for exactly that (run `./install.sh`
once first to build the venv). Extra flags pass straight through, e.g.
`./run.sh --port 9000`.

## Clock sync & cue timing

The dashboard is the clock leader: while it runs it broadcasts `/sync/ping`,
estimates each node's clock offset, and pushes `/<id>/sync/offset` so a broadcast
`/cue <cueId> <sharedTimeNs>` fires sample-tight(ish) across the fleet (contract
§3.1). Nothing to enable — it's on whenever the server is up.

To measure how tight cues actually land, `tools/sync_measure.py` fires a cue
burst and reports the cross-device spread:

```sh
# software floor (launches simfleet itself, writes a Markdown report):
~/.venvs/bopos/bin/python tools/sync_measure.py --devices 5 --sync-skew-ms 40

# real fleet (Pis running bopos.py already on the LAN; align an external
# GPIO/click recording to the printed fire schedule -- this is the sync-4 run):
~/.venvs/bopos/bin/python tools/sync_measure.py --mode hardware --cues 8
```

Sim spread is a single-machine floor; the honest number is the hardware run.

## Flags

`--port` HTTP port (8080) · `--listen-port` OSC in (5550) · `--send-port` OSC
out (6660) · `--osc-target` unicast/broadcast target (255.255.255.255) ·
`--state-file` installation.json path · `--assets-dir` host asset folders served
at `/assets` · `--patches-dir` host patch folders served at `/patches` ·
`--public-url` URL nodes should fetch from. When the dashboard is opened through
`localhost`, it derives the LAN source address from each real device's route;
the explicit flag remains useful on multi-interface or proxied installations.

The defaults are the repository's `assets/` and `patches/` directories. The
global Fleet patch selector lists valid host catalog patches. **Deploy as
fleet patch** is one confirmed operation: it converges the selected bytes
across online assigned devices, then switches their audio engines. Row badges show
fleet convergence; selecting a row opens its observed inventory, fingerprints,
fetch phase, manifest/git facts, and Retry or Re-switch remediation. **Revert**
stages the previous fleet patch through the same flow. A ◆ marker identifies an
active Git-managed patch, which retains its **Pull latest** action.

Asset distribution remains device-addressable: select a device, then Send one
asset folder or Sync all assets. A successful receipt marks that host manifest
in sync; after editing a host folder, Refresh catalog marks the prior receipt
stale. Ordinary device detail has no per-device patch selector, Switch, Send
Patch, or patch Sync controls; heterogeneous patches are not a supported fleet
mode.

Changing to a different fleet patch also changes the one active parameter
schema: every seat is reset to that manifest's declared defaults and keys from
the previous patch are removed. Setting the same patch again (including a stale
content retry) preserves values for unchanged qualified identities, defaults
new identities, and prunes removed ones. Revert changes patch names, so it
restores the previous patch with its manifest defaults rather than retaining a
hidden per-patch parameter history. Parameter and preset keys are the canonical
slash-joined manifest `path + name`; reconnect catch-up and preset load send
only identities declared by the active manifest.

In Patch edit, `path` is authored as slash-separated text and saved as a JSON
array while `name` remains the leaf. Nested declarations render as a tree and
send their complete `/p/<path>/<name>` address. The legacy `group` field stays
presentation-only: clear it before adding a path, and path/name moves are shown
as explicit remove-plus-add identity changes.

State lives in `dashboard/installation.json` (devices, positions, room,
visual coordinate origin, listener, master, presets). The Seats and Devices tabs let
you type each element's x/y relative to that origin; the dashboard converts it
through the same assignment path used by map dragging. Named snapshots live in
`dashboard/installations/<venue>.json`
via the Venue save/load buttons. Both are gitignored.

The Dashboard is fail-closed. Patch parameters appear there only when their
manifest declaration has `"facilitator": true`. Framework commands default to
none; a venue may opt in supported fleet-wide commands in its installation
state, for example:

```json
{"facilitator_commands": ["restart-engine"]}
```

Command controls are confirmation-gated, and destructive commands require a
hold. Each promoted command has a fleet action for fleet setup/operation and a
single-device action for onboarding/remediation. The allowlist belongs to the
installation, never the patch manifest.
