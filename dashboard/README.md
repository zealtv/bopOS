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
~/.venvs/bopos/bin/pip install -r dashboard/requirements.txt
./tools/install-hooks.sh
```

`./install-dashboard.sh` performs both setup steps. The installed commit hook
runs fast tests before each commit; test dependencies and the automatic browser
cadence are documented in [Verification](../docs/VERIFICATION.md).

Run the server (terminal 1, from the repo root):

```sh
~/.venvs/bopos/bin/python dashboard/server.py
```

Run a simulated fleet to play against (terminal 2):

```sh
~/.venvs/bopos/bin/python tools/simfleet.py --devices 5
```

Then open:

- **<http://localhost:8080/>** — Show, Dashboard, Seats, Devices, Patches,
  and Assets tabs. The landed controls cover device inspection, spatial
  authoring, patch editing, host-to-node distribution, discovery/assignment,
  synced events, sites, single-device asset delivery, and
  show authoring/playback (see "The Show tab" below).
- **<http://localhost:8080/facilitator>** — standalone Dashboard view: device cards
  with the patch's promoted (`dashboard: true`) params as labelled controls,
  master, and Silence All. On an iPad, "Add to Home
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

The header's **Execution target** toggle (Live / Simulation / Patch
edit) manages this audition rig directly: switching to **Simulation** runs
one selected patch across the whole simulated fleet, and every valid folder
under `patches/` is already available. **Set Live** on another of the
project's patches (Patches tab) restarts the managed engines into it. Send/Sync is
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

Steps have a duration (h/m/s), play-n-times or loop-forever, and one or more
**then-actions** resolved when playback exhausts:
stop, play again, next/previous step, any/other in section (other has
Ableton shuffle-bag semantics), goto a step by uid, next/previous section.
Multiple then-actions choose randomly. A goto whose target step was deleted
falls back to stop and flags the row. Playback is exclusive: starting or
resuming one step stops any other active step. Rows show elapsed progress and
an armed pulse for the focused next step. Per-row transport remains available;
the global transport plays/pauses the focused step (or the first step), stops
the active step, and triggers its next action.

Every Show `/cue` message is forward-scheduled on the shared clock. The lead
time is one persisted installation setting (default 500 ms) in the global
transport; parameters, points, and raw messages still send immediately because
their wire planes have no scheduled variant.

Messages are built in the context-sensitive inspector: parameter, cue,
point, or raw payloads, and a target picker that composes any mix of seats
and groups as chips (`3+7+g1`); cue/point payloads are selector-free so
their target is greyed. Message pills drag within or between steps, while
explicit handles drag steps and dividers. Copy, cut, paste, and delete are
keyboard operations on the focused pill or row (paste mints a fresh uid).
Ctrl/Cmd+Z is a global, server-authoritative undo shared by every connected
client; redo is deferred.

A project has one or more shows, each persisted as JSON in
`dashboard/projects/<project>/shows/<name>.json` (the file name is the show's
name), and one of them is open: `current_show` in `project.json`. The schema
and playback semantics live in
`.lore/items/2026-09-25-design-references-2026-07/content/show-tab-design-2026-07-18.md`.
The Show tab always edits the open show; it persists across dashboard restarts
and is shared by every connected client. The project menu's SHOW section
opens, adds (empty or a copy), renames and deletes shows in every mode, but
not while a show is playing; undo history belongs to the open show and is
cleared when another opens. A new project starts with one empty show, `Show`. Two collapsible OSC consoles sit
under the table: outgoing (everything the dashboard sends) and incoming
(everything the LAN surface receives, heartbeats included). Filter with
space-separated terms that AND together, `*` wildcards, and `!` negation —
e.g. `/p/* !/sync` — plus pause/clear and sticky auto-scroll. The ordered step
list has its own resizable scroll box (about 480 px by default), bounded touch
resize handle, and pinned add bar; height and scroll position survive live
transport redraws.

## Real fleet

On the installation LAN the defaults already match the OSC contract (listen
5550, send 6660, broadcast target). Run the server on any machine on that
network; real nodes appear as they heartbeat:

```sh
~/.venvs/bopos/bin/python dashboard/server.py --host 0.0.0.0
```

From the repo root, `./run.sh` is a shortcut for exactly that (run `./install-dashboard.sh`
once first to build the venv). Extra flags pass straight through, e.g.
`./run.sh --port 9000`.

`--host 0.0.0.0` is what the server *binds* to; it is not an address to browse
to. Open the LAN address `./run.sh` prints — the address you browse to is the
one nodes are told to fetch patches from.

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
`--data-dir` host root containing projects, device registry and current-project · `--assets-dir` host asset folders served
at `/assets` · `--patches-dir` host patch folders served at `/patches` ·
`--public-url` URL nodes should fetch from. Nodes are told to fetch patches and
assets from **whichever address you opened the dashboard at**, so open its LAN
address (`./run.sh` prints it). When the dashboard is opened through `localhost`,
`127.0.0.1`, or an unspecified address (`0.0.0.0` / `::` — the address `--host`
binds to, which on a node means the node itself), the server instead derives the
LAN source address from each real device's route. The explicit flag remains
useful on multi-interface or proxied installations.

The defaults are the repository's `assets/` and `patches/` directories. The
Patches tab lists the project's patches (`patches` in `project.json`); the one
the fleet runs is the Patch, tagged **Live**. **Add Existing…** lists another
valid catalog folder in the project, and **New Version** copies the Patch's
folder under a new name (the trailing number bumped, else `-v2`) without
changing what the fleet runs. **Set Live** — **Push** for the live patch after
editing it in place — is one confirmed operation: it converges the selected
bytes across online assigned devices, then switches their audio engines. Row badges show
fleet convergence; selecting a row opens its observed inventory, fingerprints,
fetch phase, manifest and framework revision facts, and Retry or Re-switch remediation.

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
new identities, and prunes removed ones. Parameter keys are the canonical slash-joined manifest `path + name`;
reconnect catch-up sends only identities declared by the active manifest.

In Patch edit, `path` is authored as slash-separated text and saved as a JSON
array while `name` remains the leaf. Nested declarations render as a tree and
send their complete `/p/<path>/<name>` address. Flat declarations stay in the
default parameters section, and path/name moves are shown as explicit
remove-plus-add identity changes. Old presentation-only `group` fields are
ignored when loaded and stripped on the next save; the editor no longer shows
them.

Project state lives in `dashboard/projects/<project>/project.json` (Seats,
groups, fleet patch, current site, master and Remote commands). Geometry lives
in `projects/<project>/sites/<site>.json`: room, listener and a positions map
keyed by Seat id. Seats have no stored positions.
The host device registry lives in `dashboard/devices.json`, and
`dashboard/current-project` names the open project. The Seats and Devices tabs let
you type each element's x/y relative to that origin; the dashboard converts it
through the same assignment path used by map dragging. The Site menu switches
geometry and replays assignments and groups to bound devices.
All runtime data paths are gitignored.

The header shows Project · Site · Patch · Show and opens the project menu. Project is the selected
directory name; Site and Show are the selected site and show filenames without
their extension.
Switching sites preserves project identity, Seats, groups and parameter values.
New Site starts with an empty room or copies an existing site's room, listener
and Seat positions. New Project starts with no Seats or patches and one empty show.
Opening a project stops Show playback, loads its site/show/patches, replays its
assignments and groups, and unassigns online physical devices outside its fleet.
Patch delivery remains explicit. Project switching is unavailable during
Simulation and Patch Edit. Rename moves the project folder and updates
`current-project`; the device registry stays host-global.

Project and site names are preserved as typed, including internal spaces. Names
start with a letter or digit and contain only letters, digits, spaces, `.`, `_`
or `-`, with no leading/trailing spaces or `..`. The directory or filename is
the sole name; there is no separately stored display label.

Before starting an existing installation with this layout, run
`python tools/migrate_project.py dashboard/installation.json` once. It creates
the first project and host registry, leaves the source untouched, and refuses
to overwrite existing destination data. For a project already converted by
the earlier project-storage migration, run
`python tools/migrate_sites.py dashboard/projects/<project>/project.json`.
Both migrations create a default site from the old geometry and convert legacy
venue snapshots whose Seat ids match. They report unmatched snapshots and
preserve all sources; the site migration keeps `project.json.pre-sites`.
The installation's `name` becomes the project directory name unchanged; use
`--project` to supply a valid name when the legacy name is invalid. Valid venue
filenames also keep their names unchanged; invalid names are reported and left.
An empty data root starts a default
project. A missing selection opens `default`; an existing unreadable or invalid
selection blocks saves. Its `current_show` comes along as the project's
current show. For a project already migrated,
`python tools/migrate_project.py --show dashboard/shows/<name>.json` copies
that show file into the open project's shows as its current show, byte for
byte, refusing an invalid show or an existing show of that name.
A project from before multiple shows keeps its one show in `show.json`; the
dashboard opens it read-only until
`python tools/migrate_shows.py dashboard/projects/<project>/project.json`
copies it, byte for byte, to `shows/<its name>.json` as the current show,
leaving `show.json` in place and keeping `project.json.pre-shows`.

If the dashboard cannot fully load its project, current site or registry files, the Show tab displays
a notice and saves are blocked for that session. The original file stays in
place, including malformed JSON or dangling group references; repair the file
named in the notice and restart the dashboard. Invalid sites are rejected
without replacing the current geometry.

The desktop Control tab and Device control panel show every parameter declared
by the active patch. The standalone facilitator/iPad view is curated:
parameters appear there only when their manifest declaration has
`"dashboard": true`. Framework commands default to none; use the Patches
tab's **Remote device commands** project-setting card to opt in supported
commands. The card writes the project state, whose durable form is:

```json
{"facilitator_commands": ["restart-engine"]}
```

Command controls are confirmation-gated, and destructive commands require a
hold. Each enabled command appears on every Remote target card and uses that
card's selector: All, one group, or one Seat. The allowlist belongs to the
project, never the patch manifest.
