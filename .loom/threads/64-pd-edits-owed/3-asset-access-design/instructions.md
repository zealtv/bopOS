# 3-asset-access-design

**Status:** ready · agent work, proposal first (no `.pd` edits)
**Goal:** design a framework Pd utility that makes asset access easy: find a
slot, list or pick its files and folders, and hand a full path to a loader
(`readsf~`, `soundfiler`, `bop.stream~`, `bop.sampler~`). Bob builds it in
`4-asset-access-abstraction`.

Bob, 2026-11-05: *"In [Kite Choir], I'm finding I'm needing to do a lot of
manual searching of folders. For example, listing a bunch of folders and then
seeing if they match the folder name that I'm looking for, and then building a
path … some sort of utility abstraction that would make it really easy to
access assets, get their paths, use those paths to send to, for example,
bop.stream or bop.sampler, or pull out specific assets or folders."*

## What Kite Choir does today (`patches/kc-test/main.pd`, read 2026-11-05)

- `[r bopos-context] → [route assets id]` gets the asset-slot folder list
  (COMPOSING: "select its absolute folder path from the asset-slot list").
  The patch then runs each entry through `[file split]` and `[select kc-test]`
  to find its own slot, and publishes it as `asset-path`. A hard-coded
  message of `/Users/bob/repos/bopOS/assets/...` paths stands in for that
  list while editing.
- Three near-identical subpatches, `get-tilt-file`, `get-trigger-file` and
  `get-point-file`: take a name, `[file split]` → `[list append]` →
  `[file join]` → `/*` → `[file glob]` → accumulate (`babs.accum`) → pick
  one with `babs.nth`, by device `id` modulo the count. `get-point-file`
  builds `<name>.wav` with `makefilename` instead.
- The results feed `readsf~` via `open <path>`.

## Other patches (read 2026-11-05; Bob suggested fire-button)

- **fire-button** (`patches/fire-button/main.pd`): `[loadbang]` → a
  hard-coded `pack ../../../assets/fire-button` message into
  `bop.stream2~`'s `pack` attribute (saved in the object, `#A saved pack …`).
  That relative path assumes the dashboard checkout's layout. Its manifest
  declares `"slots": []`, so the slot it plays from isn't declared. It routes
  `[route patch assets]` from context but doesn't use the result for the path.
- **bop.stream2~** (`pd/bop`): `makefilename %s/*.wav` → `file glob`, a
  "custom path" inlet, and the same stale `%s/samplepacks/$1/*/` template as
  `bop.stream~` / `bop.sampler~`. So the loaders already glob a folder; the
  question is who supplies the folder.
- **bonks-pd**: `[r bopos-assets-path]` under an "assets" header. Nothing in
  `pd/` or `patches/` sends `bopos-assets-path`, so it looks like a leftover
  from a retired mechanism. Its manifest also declares `"slots": []`.

So the emerging needs are: resolve *my slot* by name; list a folder (files,
subfolders, or a glob pattern); pick by name, index, or device id mod count;
join a full path; and refire when context arrives or the slot changes.

## Decide (proposal.md)

- **Shape:** one abstraction with methods (e.g. `[bopos.asset <slot>]`
  taking `list`, `get <name>`, `pick <n>`, `glob <pattern>`), or a small
  family (`bopos.slot`, `bopos.ls`, `bopos.pick`)? Bob prefers simple: say
  which is easier to remember and to patch with.
- **Where:** `pd/`, beside `bopos~.pd`, with its own `-help.pd` (pattern from
  `2-live-pd-reference`). Vanilla only (Pd 0.55 `[file]` family); check what
  `babs.*` already offers and whether to reuse it.
- **Timing:** context arrives at launch; what happens to a request that comes
  before it, and after a slot is re-sent? Never block or poll the disk in the
  audio thread; say when `[file glob]` runs.
- **Edit vs device:** the same patch must work in Patch Edit on the laptop
  and on a Pi. No hard-coded host paths.
- **Loaders:** how it feeds `bop.stream~` / `bop.sampler~`, which still build
  `%s/samplepacks/$1/*/` paths (the `samplepacks` item, folded in from `64`'s
  checklist; see `4`). Should the loaders take a full folder path from the
  utility instead of building their own?
- **Edge cases:** missing slot, empty folder, dotfiles and `.part` files
  mid-fetch, sort order (glob order isn't guaranteed; picks by index must be
  stable across devices), names with spaces.

Prototype each idiom in headless Pd 0.55 with a scratch harness (pattern in
`80-osc-input/5-pd-event-fields.waiting/headless-test/`) and a fake asset
tree, so the proposal's spellings are verified. Include worked replacements
for fire-button's hard-coded `pack` path as well as KC's subpatches, and say
whether patches that read assets must declare their slots.

## Done when

`proposal.md` gives the API, a worked replacement for KC's
`get-*-file` subpatches, the loader decision and the verified idioms. Then
stop for Bob (glean `decision-gates`).
