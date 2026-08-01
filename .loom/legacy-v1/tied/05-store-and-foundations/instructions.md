# 05-store-and-foundations

The preset store, the distribution exclusion, and two pre-existing bug fixes.
**Needs 04 tied** (the contract names what this stitch implements).

Authority: `.loom/tied/1-preset-architecture-design/proposal.md` §1,
`../design-addendum.md` §6/§8, `.loom/tied/3-addendum-review/review-2.md` F4/F5/F8.

## 1. Toggle round-trip fix (do first — schema hashing depends on it)

`python/manifest.py:187-193` rejects any present `min`/`max` on a toggle,
then writes `min=0, max=1` itself, so validate→save→validate fails. Enum got
exactly the right treatment at `manifest.py:176-185` (accept a matching
derived pair so a round-tripped manifest stays valid, reject a *different*
authored pair) — mirror it for toggle, with the same explanatory comment
style. Add a durable test: validate a toggle manifest, save, re-validate.

## 2. Shared host-only ignore policy

One named primitive in `python/identity.py` (e.g. a `HOST_ONLY_DIRS`
constant + `is_host_only(relative_path)` helper) declaring `presets/` as a
host-only top-level patch subdirectory. It must be consumed by **all three**
enumeration/prune sites — the third was missed by the addendum and found by
review-2 F5:

- `identity._walk_files` (`python/identity.py:31`) — manifest + fingerprint
  for host, node, simfleet, and run context (all transitively shared).
- `fetcher._prune` (`python/fetcher.py:86`) — the generic
  prune-to-manifest walk. A preserved `presets/` on a node/mirror must
  survive convergence.
- `fetcher._file_fetch`'s **source walk** (`python/fetcher.py:172`) — it
  builds its own manifest from the source directory with only a dot-filter,
  so an unfixed `file://` fetch (the local-dev/simfleet path) would transfer
  `presets/` and then fingerprint-mismatch against the host's excluding walk.

Hygiene: the hash-cache load/save (`python/identity.py:89-110` region)
filters dot paths only — also drop host-only paths so stale `presets/`
entries don't linger in `.hashcache` files.

Note: `_patch_fetch`'s staging `copytree` (`python/fetcher.py:239`) copies
everything including `presets/` — that is **correct** (preserved presets ride
into staging and back); do not filter it. `_reject_symlinks` continues to
cover `presets/` too (a symlink inside it should still refuse convergence).

**Tests (D5's three, plus the file:// case):** fingerprint unchanged by
preset add/edit/delete; `_patch_fetch` over a destination with a pre-existing
`presets/dawn.json` preserves it while still pruning an ordinary stale file;
`file://` fetch of a source containing `presets/` does not transfer it.

## 3. HTTP deny

`DistributionStaticFiles` (`dashboard/server.py:60`) filters dot/part/symlink
paths only; a hand-built `/patches/<name>/presets/…` URL would serve. Bob's
ruling: host-only means not fetchable at all — deny (404) any request whose
path enters a host-only subdirectory of a patch. Test with the running app
or a starlette test client.

## 4. The preset store

Server-side module (suggest `dashboard/preset_store.py`) owning
`patches/<patch>/presets/<slug>.json`. File shape per proposal §1:
`{bopos_preset: 1, name, saved, schema, params: {identity: [args…]}}`,
sparse. Behaviours:

- **CRUD**: list (with per-file validity), read, save, delete. Atomic writes
  (tmp + `os.replace`), same host-side pathing discipline as the manifest
  editor's writes.
- **Strict, fail-visible validation** (U2 — the show-model
  tolerate-by-emptying idiom is *unsafe* here because empty is a valid sparse
  shape): malformed JSON/version/shape is listed with an error and refused by
  apply, never treated as empty. Reject empty `params` on save. Reject
  non-finite numbers.
- **Entry whitelist** (review-2 F4): every entry's argument list must be a
  full-state form — a single scalar, a single string (text kinds), or a list
  parsing to `lfo`/`loop` via `paramgen.parse_message` semantics. Reject
  `stop`, bare fade forms, and anything else. Hand-edited files escape the
  capture rules; the store is the gate.
- **Slug/collision rules**: carry the existing 48-char `[^\w-]` slug
  transform from the old `save_preset`. Define and test the collision policy:
  saving a *new* preset whose slug matches an existing file with a different
  display name is a refused conflict, not a silent overwrite.
- **Overwrite revision token** (U2): save carries the revision (file mtime/ns
  or a content hash) the client last saw; a mismatch is a refused
  compare-and-swap failure so two browsers cannot silently clobber. The
  serialized WS mutation queue does not cover stale client confirmations.
- **Path confinement**: real path must stay inside the patch root; refuse
  symlinked `presets/` or preset files.
- **Cache** (C1/C3, assigned here explicitly): validated documents cached by
  file stat signature, invalidated on save/delete and on external change
  (stat mismatch). Nothing downstream reads JSON at render/broadcast time.

## 5. Schema projection + fingerprint

Implement the v1.17 canonical projection (04's definition): sorted
`{identity, kind, min, max, options: [ordered labels]}`, canonical JSON,
sha256. One function, used by save (stamps `schema`) and by drift detection.
Also implement the pure **per-entry drift resolution** (proposal §1 table:
present+kind-same+in-range → apply; range-narrowed → clamp; kind-changed or
absent → drop; sparse omissions untouched) as a pure function here — stitch
06 consumes it. Verdicts are derived, never stored, never blocking (R5).

## Verify and tie

Durable tests live under `tests/` organized by code surface (see
`.loom/tied/…/retirement-ledger.md` context in CLAUDE.md — do not write
stitch-local-only guards for durable behavior). `tools/run-tests.sh fast`
green. Record decisions (slug collision policy, revision-token choice, cache
key) in `decisions.md`. Test scripts locate the repo by marker, never by
`..` hops.
