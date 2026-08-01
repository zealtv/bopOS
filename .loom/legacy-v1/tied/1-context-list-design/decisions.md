# Multi-asset-slot context design

**Status:** ratified by Bob on 2026-07-23, with the terminology ruling that
each top-level folder is consistently called an **asset slot**. There is no
separate "asset pack" concept.

## Recommendation

Keep the accepted asset-slot storage and distribution model, and make the
engine boundary describe those folders directly:

```text
assets/
  belief-system-000/
  belief-system-001/

bopos-context assets /home/pi/bopOS/assets/belief-system-000 \
                     /home/pi/bopOS/assets/belief-system-001
```

For a non-PD engine, `BOPOS_ASSETS` contains the same list and order as a JSON
array:

```json
["/home/pi/bopOS/assets/belief-system-000",
 "/home/pi/bopOS/assets/belief-system-001"]
```

The list is a launch-time snapshot. Adding or removing a slot while an engine
is running changes inventory immediately but changes engine context only on
the next engine start. Updating the contents of a path already in the snapshot
remains visible in place, with the existing partial-update warning.

## Asset-slot model

- An **asset slot** is one immediate, visible, non-symlink directory beneath
  the framework-owned `assets/` directory. "Pack" is not a second model or a
  user-facing synonym; the thread name is historical.
- Everything below a slot directory remains opaque to bopOS. There is no
  audio-only schema, slot manifest, registry, arbitrary external path, or
  semantic-version interpretation.
- Slots are added, converged, and removed through the existing Assets workflow
  and filesystem convention. The basename remains the unique slot name and the
  `/os/fetch` slot.
- Discovery excludes dot entries, symlinks, and non-directories exactly as
  `/os/assets` inventory does today. Absolute paths are formed only after that
  containment boundary, so engine context cannot name a path outside the
  framework assets directory.
- The canonical order is ascending slot name using Python's ordinary
  deterministic string ordering, matching `installed_assets()`. Order makes
  launch context reproducible but has **no search/override priority meaning**.
  Engines should select a slot by path/basename, not "first match wins".
- The slot list contains every installed slot, not only the active patch's
  manifest-declared `slots`. That preserves today's semantics: the old root
  exposed every installed child, while manifest slots remain documentation
  and dashboard safety information rather than an access-control list.

## Context forms

### Pure Data

The existing term becomes a variable-length list:

```text
bopos-context assets <absolute-slot-path-0> ... <absolute-slot-path-N>
```

Zero installed slots is `bopos-context assets` with no path atoms. One slot is
the same shape with one path atom; PD consumers must treat that as a
one-element list rather than a scalar special case. Paths are device-local
strings, never OSC floats.

`python/runcontext.py` should own discovery and produce a PD/FUDI-escaped atom
list for the launcher. `bash/start-engine.sh` must not interpolate raw
directory names into `pd -send`: spaces and FUDI separators must be escaped
without permitting another message to be injected.

### Other engines

`BOPOS_ASSETS` changes from one scalar root path to a UTF-8 JSON array of
absolute slot-path strings. JSON gives SC, openFrameworks, and future engines
an unambiguous empty/list representation and safely preserves spaces or
punctuation in a valid slot name. SuperCollider's standard `String:parseJSON`
can consume it without an added Quark.

The same ordered paths must appear in both PD and environment delivery.
`BOPOS_ASSETS=[]` is the empty form. This is an intentional v1.9 engine-facing
shape change; the shipped SC demo and composition docs move in lockstep.

Do not add a count (the list/JSON length already carries it), repeated indexed
terms, a delimiter-based environment string, or `BOPOS_ASSET_0...N`.

## Compatibility call

This is a clean semantic migration from "one root containing slots" to "a
list of slot folders", as Bob requested.

- The `assets` selector and `BOPOS_ASSETS` name remain stable.
- A PD one-atom `assets <path>` message is naturally a one-element list.
- There is no compatibility interpretation in which that one path is an
  assets root. Preserving both root and slot semantics under the same term
  would be ambiguous.
- The shipped PD template, SC demo, audition launcher, performance harness,
  and composition docs update in the implementation stitch. External patches
  need the v1.9 migration note.

## Pure Data impact

The launch `-send` already lands arbitrary trailing atoms on
`[r bopos-context]`; the incompatible part is the singleton helper inside
`pd/bopos~.pd`, which currently turns `assets <root>` into one
`bopos-assets-path` symbol.

Bob's completed edit:

1. retired the singleton `build-assets-path` helper and singular
   `bopos-assets-path` bus from `pd/bopos~.pd`;
2. kept `bopos-context` as the one canonical context surface rather than
   introducing a second plural asset bus;
3. updated the shipped PD template to consume
   `[r bopos-context] -> [route patch assets]` directly, preserve/show the
   whole assets list, and display its length.

This is cleaner than the proposal's provisional `bopos-assets-paths` helper:
the contract already defines `bopos-context assets <path...>`, and a second bus
would duplicate that state without adding a distinct semantic boundary.

## Contract v1.9 amendment text

In `docs/OSC-CONTRACT.md` section 4.2, replace the scalar asset-root portions
of run context with:

> Run context carries the installed asset-slot set as a launch-time snapshot.
> PD receives `bopos-context assets <absolute-path...>`; zero paths is the
> empty set and one path is a one-element list. Other engines receive
> `BOPOS_ASSETS` as a UTF-8 JSON array of the same absolute device-local paths
> in the same order. Each path names one immediate, visible, non-symlink
> directory below the framework-owned assets directory. Paths are ordered by
> slot name for deterministic enumeration; order does not define search or
> override priority. The set includes every installed slot, not only
> manifest-declared slots, and changes only when the engine is next started.

In section 9, replace "the assets root is handed to every engine" with:

> Each top-level asset slot lives at `~/bopOS/assets/<slot>/`. At engine
> launch, bopOS hands every installed slot
> to the engine as its absolute folder path through the section 4.2 list.
> Distribution continues to address the slot by its `<slot>` basename; the
> `/os/fetch`, `/os/assets`, and `/os/dropassets` terms do not change.

Add a v1.9 history row identifying this as the multi-asset-slot run-context
revision and explicitly noting the intentional scalar-root-to-list migration.

## Implementation touch surface

- Add one shared Python slot-discovery helper used by `python/runcontext.py`
  and `python/bopos.py`; keep `installed_assets()` as the `/os/assets`
  inventory API while removing duplicated directory-selection rules.
- Have `runcontext.generate()` include `assets: [absolute paths...]`; its CLI
  emits shell-safe JSON plus a separately FUDI-escaped PD atom sequence.
- Update `bash/start-engine.sh`, `tools/audition.py`, and
  `tools/perf_matrix.sh` to use those generated forms.
- Update `patches/demo-sc/main.scd` to parse `BOPOS_ASSETS` into an Array, plus
  its README, `docs/COMPOSING.md`, `assets/README.md`, OSC reference material,
  and stale dashboard-development context.
- Mirror the same slot list in simulator/audition engine launch context. The
  existing `/os/assets` inventory and fetch/drop wire shapes stay unchanged.
- Keep **asset slot** in user-facing headings/counts and in distribution
  terminology. Explain
  that add/remove changes reach engine context on restart; do not invent an
  automatic restart or fleet rollout in this stitch.
- Add living tests under `tests/`, organized by the touched run-context/asset
  surfaces, rather than another tied-stitch-only guard.

## Explicit non-goals

- Fleet desired state, bulk rollout, staging, activation, and restart
  orchestration remain in `asset-fleet-distribution`.
- No arbitrary registered paths or external mount discovery.
- No slot precedence/search policy.
- No live mutation of launch context.
- No `.pd` edits by an agent.

## Ratification

Bob ratified the three load-bearing calls on 2026-07-23:

1. include every installed top-level asset slot, not only manifest-declared
   slots;
2. use deterministic slot-name order with no precedence semantics;
3. deliver JSON-array `BOPOS_ASSETS` plus PD `assets <path...>`, retiring the
   old scalar-root meaning.

Bob additionally ruled that the folders remain **asset slots** throughout.
There is no argument or need for distinguishing "asset packs" from slots.

## PD completion amendment

Bob completed the PD changes and confirmed in the local patch editor on
2026-07-23 that zero, one, and two asset slots produce lists of length 0, 1,
and 2 from the host-machine slot inventory. He chose direct
`bopos-context` consumption, as recorded above. The same edit also landed the
previously pending live `groups` context route and `clip~ -1 1` immediately
before both output channels.
