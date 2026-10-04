# Projects — design proposal

**Status:** draft for Bob, 2026-10-04 · text first; mockups follow once the
shape is agreed
**Builds on:** `rulings.md` (Seats per project, iterations are patch folders,
fleet = boxes bound to Seats, one show per project).

The test for every answer: does it make the surface and the code simpler?

## 1. The model

A **project** is the one thing an operator opens. One is open at a time.

| part | what it is | owns |
|---|---|---|
| **Project** | the composition, e.g. *Kite Choir* | everything below, plus master level, event lead time and Remote device commands |
| **Seats + groups** | the composition's voices | Seat ids and names, group membership, the box bound to each Seat, per-Seat parameter values |
| **Fleet** | the boxes bound to the project's Seats | nothing of its own — derived from Seat bindings |
| **Iterations** | patch folders in `patches/` the project lists, e.g. `kite-v1`, `kite-v2` | which one is **live** (today's fleet patch) |
| **Sites** | venues, e.g. *workshop*, *Northern Broadwalk* | room size and origin, listener, a position for each Seat; one is the **current site** |
| **Show** | the project's one show | steps and messages targeting Seats and groups |

Stays outside projects, global to the dashboard host:

- **Device registry** — aliases, Device enabled. A box keeps its name across
  projects.
- **Patch and asset catalogs** — `patches/` and `assets/` stay where they are,
  so distribution, fingerprints and serving don't change. A project points at
  patch folders by name; the asset slots it needs come from the live patch's
  manifest, as today.
- **Wi-Fi list (33b)** — stays installation-level for now, as ratified; it can
  move into the project later without changing anything else.

**No wire change.** Opening a project or changing site re-sends the existing
`/all/os/assign` (with the site's positions) and group sync; making an
iteration live is today's fleet-patch push and switch.

## 2. On disk

```
dashboard/projects/<project>/
  project.json     seats, groups, next_group_id, iterations + live,
                   master, event_lead_ms, remote commands, current site
  show.json        the show (today's show format, unchanged)
  sites/<site>.json  room, listener, positions {seat id: [[x, y], …]}
```

`dashboard/projects/` is gitignored, like `installation.json` today. A
host-level `dashboard/current-project` (one line) remembers which is open.

What changes in the data: **Seat positions move out of the Seat and into the
site.** Everything else on a Seat stays.

## 3. What goes

| goes | the operator instead | code removed |
|---|---|---|
| **Per-device patch pins** ("Pin to device", "Follow fleet patch", 📌) | every box in the fleet runs the live iteration | `set_device_patch` / `clear_device_patch`, `device_operations`, `device_generations`, `converge_device_patch` (`server.py`); `desired_patch` in the registry (`state.py`, `device_aliases.py`); `patch_pinned`; per-device manifest lookup in `live_control_manifest`; pin UI in `dashboard.js`; `tests/test_device_patch_override.py`, `verify_device_patch_targeting.py`, the pin part of `verify_set_patch_handoff.py` |
| **Switching to any patch in the catalog** | choose among the project's iterations; add a folder to the project first | the free patch picker on the Patches tab |
| **`fleet_patch.previous` + Revert** | mark the earlier iteration live | `revert_fleet_patch`, `previous` bookkeeping |
| **`params_patch`** (separate schema pointer) | controls follow the live iteration | `params_patch` field and its fallbacks |
| **Venue snapshots** (`installations/`, Save as… / Load) | sites: pick the current site; add one by copying the current site | `save_venue` / `load_venue` / `read_venue`, venue bar |
| **Show list** (create / load / rename / delete shows, `current_show`) | the project has one show; to start fresh, clear it or make a new project | the show picker and its five actions |

**Live patch swapping, scoped.** Changing the live iteration stays — that's how
a new iteration reaches the fleet. What goes is mixing patches across boxes
and swapping to unrelated patches. Mid-show swapping isn't offered; nothing
here prevents it, it's just not a feature.

## 4. Today's data, mapped

| today | lands in |
|---|---|
| `installation.json` `name` | project name |
| `seats` (id, name, groups, bound, params) | `project.json` seats |
| `seats[].positions` | current site's `positions` |
| `groups`, `next_group_id` | `project.json` |
| `room`, `listener` | current site |
| `master`, `event_lead_ms`, `facilitator_commands` | `project.json` |
| `fleet_patch` (name, fingerprint, staged_at) | `project.json` live iteration; fingerprint/staged_at kept as push bookkeeping |
| `fleet_patch.previous` | dropped |
| `params_patch` | dropped (the live iteration) |
| `current_show` + `shows/<name>.json` | `show.json` |
| `device_registry` | stays host-global (its own file, `dashboard/devices.json`), minus `desired_patch` |
| `installations/<venue>.json` | a site (room, listener, positions) |
| `schema` | `project.json` schema |
| `simulation`, `notices`, points | runtime, not stored — unchanged |
| asset slots | unchanged — from the live iteration's manifest |

## 5. The operator surface

- **Global project bar** (the old `34` ask): the top bar shows
  **Project · Site · live iteration** on every tab, e.g.
  *Kite Choir · Northern Broadwalk · kite-v2*. Clicking it opens a small menu:
  open project, new project, rename; change site, new site (copies the
  current one).
- **Opening a project** re-sends assignments and groups to its fleet, and
  shows the usual patch badges if the boxes aren't on the live iteration —
  pushing stays an explicit action.
- **Tabs:**
  - **Control** — unchanged.
  - **Show** — the project's show; the show picker goes.
  - **Devices** — device admin, the Wi-Fi panel (33b); pin controls go.
  - **Seats** — Seats, groups, bindings; the room view edits the current
    site's room and positions; the venue bar goes. Remote device commands move
    here (project setting) unless you'd rather they were per site.
  - **Patches** — the project's iterations: list, **live** marker, *make
    live*, *add iteration* (duplicate the live folder under a new name, or add
    an existing folder), Patch edit on any iteration. The catalog of folders
    outside the project is a secondary "add existing" list.
  - **Assets** — unchanged.

## 6. Migration

One-off conversion, run once, then the old paths are deleted — no
compatibility layer:

- `installation.json` → `projects/<name>/project.json` + a site named
  after the room setup (e.g. *default*), positions moved out of Seats.
- `current_show` → `show.json`; any other show files become their own
  one-show projects only if you want them (today there's one: `test`).
- Each venue snapshot → a site in that project, when its Seat ids match the
  project's; otherwise reported and left for you (today there's one:
  `10x8-test`).
- `device_registry` → `dashboard/devices.json`.

## 7. Order — smallest first, each leaving the system working

1. **Remove per-device pins.** Independent of everything else; pure deletion
   (`69-complexity` relies on it).
2. **Drop `params_patch` and Revert.** Controls follow the fleet patch.
3. **Project storage** — move `installation.json` + device registry into the
   new layout with the one-off migration; still one project, no switching.
   Includes the global project bar (read-only).
4. **Sites** — positions out of Seats; site select/new replaces the venue bar.
5. **One show** — show moves into the project; show picker goes.
6. **Iterations** — project patch list, live marker, add iteration; Patches
   tab scoped.
7. **Open / new / rename projects** — the project menu.

## Open questions

1. **Boxes outside the open project.** A box bound in project A keeps its
   Seat id on-device when you open project B, so it would still answer
   `all` and its old Seat number. Recommended: opening a project unassigns
   online boxes that aren't bound in it (they go quiet, `id -1`). Or leave
   them be — with a dedicated fleet it's rare.
2. **Remote device commands** — project setting (recommended) or per site?
3. **New iteration** — duplicate the live folder by default (recommended), or
   always pick an existing folder?
4. **Mockups** — once the text shape is right, I'll mock the project bar and
   Patches tab from the running app. OK to do them after this review?
