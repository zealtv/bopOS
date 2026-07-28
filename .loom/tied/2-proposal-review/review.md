# Review — preset primitive proposal

Date: 2026-07-28. Subject:
`.loom/tied/1-preset-architecture-design/proposal.md` and `decisions.md`.

This is an adversarial implementation review, not a new design. F1–F4 and the
earlier entity rulings remain the constraints. The findings below identify
places where the proposal cannot yet be implemented as written, silently loses
one of those rulings, or costs materially more than §11 budgets.

## Findings — defects

### D1 — `morph` is not an unambiguous grammar form as written

**Claim.** `morph <dur> <destination-spec…> [c:<n>]` can wrap any existing
full-state form, with the trailing curve shaping the morph.

**Evidence.**

- The existing grammar has exactly one optional trailing `c:<n>` per message,
  and for an LFO that token shapes the LFO itself
  (`docs/OSC-CONTRACT.md:268-293`).
- Both parsers remove all trailing options *before* inspecting the leading
  keyword (`python/paramgen.py:58-84`,
  `dashboard/static/js/paramspec.js:31-59`).
- The proposal makes the destination any existing full-state form and also
  assigns trailing `c:<n>` to the outer morph
  (`.loom/tied/1-preset-architecture-design/proposal.md:249-260`).

`morph 2s lfo sine 0 1 10s c:1` therefore has two valid meanings: linear
morph into a curved LFO, or curved morph into a linear LFO. It cannot express
both curves, and the current option-peeling parser has no boundary at which to
decide ownership.

**What breaks.** The contract amendment would ratify an ambiguous wire form;
the Python and browser parsers could implement different interpretations, and a
preset cannot round-trip an LFO destination's existing curve while also
specifying a morph curve.

**Recommendation.** Keep the ratified `morph` mechanism, but add a short
grammar-closure gate before the contract stitch. Give the outer interpolation a
distinct token/position or delimit the destination spec explicitly. Ratify
examples for constant, LFO with all three existing options, fade segment list,
and loop before changing the contract.

### D2 — “argument-vector interpolation” has no defined vector for much of the
promised domain, and period interpolation is not continuous in the current
engine

**Claim.** Any full-state destination (constant, LFO, segment list/loop) can be
morphed from the current generator by one argument-vector lerp per tick.

**Evidence.**

- The current parser produces structurally different specs: constants have one
  value, fades/loops have a variable-length segment list, and LFOs have
  shape/min/max/period/phase/free/curve (`python/paramgen.py:87-147`).
- The engine stores those as different slot shapes; fade slots hold expanded
  timed segments while LFO slots hold a clock formula
  (`python/paramgen.py:188-215`, `python/paramgen.py:229-273`).
- The proposal defines constant↔LFO coercion and a discrete LFO shape swap, but
  not LFO↔loop, constant↔loop, loop↔loop with different segment counts,
  fade↔loop, segment duration interpolation, or option ownership
  (`.loom/tied/1-preset-architecture-design/proposal.md:261-288`).
- A synchronized LFO currently computes phase as
  `t_synced / period + phase` (`python/paramgen.py:284-305`). Naively lerping
  `period` every tick changes the denominator under a large absolute clock and
  can jump phase/output. That contradicts the proposal's continuous
  cross-kind claim even for LFO↔LFO.

**What breaks.** The implementation cannot construct a stable vector for every
accepted pair. A “generic lerp” either rejects valid preset entries late,
silently invents padding/truncation rules, or produces audible discontinuities.
Catch-up is also undefined because there is no canonical “current interpolated
spec” for those pairs.

**Recommendation.** Specify and test a support matrix before engine work. The
smallest honest v1 is to reject unsupported source/destination pairs at parse
time and surface that at preset apply, while fully defining constant↔constant,
constant↔LFO, and LFO↔LFO phase continuity. If loops and arbitrary segment
lists remain in v1, define their dimensional alignment, duration rule,
discrete fields, completion state, and catch-up serialization explicitly.

### D3 — the preset file omits the ratified patch content fingerprint

**Claim.** The preset's `schema` hash, and the show message carrying that hash,
participate in the ratified `{name, fingerprint}` content-drift mechanism.

**Evidence.**

- The earlier ratified model requires cross-layer content references to carry
  patch `{name, fingerprint}`; shows and presets both record the patch they
  were authored against
  (`.loom/tied/2-workflows-and-simplification/decisions.md:6-15`,
  `.loom/tied/2-workflows-and-simplification/proposal.md:121-123`).
- The proposed preset file has only a parameter `schema` fingerprint
  (`.loom/tied/1-preset-architecture-design/proposal.md:60-81`).
- That hash deliberately ignores `main.pd`, samples, and every non-control file
  (`.loom/tied/1-preset-architecture-design/proposal.md:144-150`).
- The show section says the message participates in `{name, fingerprint}` but
  then says it carries the schema fingerprint
  (`.loom/tied/1-preset-architecture-design/proposal.md:329-333`).

**What breaks.** A patch can change sound, code, or assets while preserving the
same control schema. The preset and every show reference remain “fresh” even
though the already-ratified content reference has drifted. This is not merely a
warning-policy choice; it drops R2.

**Recommendation.** Store both facts: the patch `{name, fingerprint}` required
by R2, and the separate schema fingerprint used as the fast applicability
check. F1 makes this stable: because `presets/` is excluded, saving the preset
does not change the patch fingerprint. Decide whether the show owns authored
patch references once at document level (as the entity proposal sketched) or
on each preset message, but do not substitute the schema hash for the patch
content hash.

### D4 — selector reuse can apply a patch preset to devices running a different
patch

**Claim.** Apply can reuse the existing scope selector and resolve entries
against the card's staged schema.

**Evidence.**

- `live_scope_patch` selects a pinned patch only for `scope == "device"`;
  All/Group/Seat cards use the fleet schema
  (`dashboard/server.py:1543-1555`).
- `OSCBridge._selector_seats` resolves only membership, not effective patch
  (`dashboard/osc_bridge.py:473-485`).
- An `all` or `gN` `/p/*` datagram reaches pinned devices too. Node dispatch
  looks up the active patch but still forwards non-numeric/undeclared `/p/*`
  traffic through the ordinary relay path
  (`python/bopos.py:1419-1438`).
- Show playback likewise treats stored targets as literal selectors
  (`dashboard/show_engine.py:141-161`).

**What breaks.** Applying patch A's preset to All or a group can write
same-spelled identities into a pinned device running patch B. At best those
writes are ignored; at worst patch B consumes them with a different meaning.
Per-entry kind/range resolution against patch A does not protect patch B.

**Recommendation.** Resolve an apply to concrete seats first, derive each
seat's effective patch, skip/report mismatches, then fan out only compatible
seats. A heterogeneous target cannot safely reuse one `all`/group datagram;
coalesce compatible groups only when that is provably equivalent. Applying a
preset whose `{patch, name}` does not match a target's effective patch should
be a derived non-blocking skip/warning, not identity-name coincidence.

### D5 — host-only exclusion does not currently imply prune exclusion

**Claim.** Excluding `presets/` in `identity._walk_files` automatically removes
it from the transfer manifest, fingerprint, and prune-to-manifest convergence.

**Evidence.**

- `_walk_files` owns manifest/fingerprint enumeration
  (`python/identity.py:31-42`, `python/identity.py:167-189`).
- Fetch pruning is a separate, generic walk that deletes every file absent
  from `wanted`; it does not call `_walk_files` or know ignored directories
  (`python/fetcher.py:86-101`).
- Patch fetch copies the existing destination into staging, converges the host
  manifest, then invokes that generic prune
  (`python/fetcher.py:229-260`).
- A direct focused reproduction against current `_prune` deleted
  `presets/dawn.json` when only `main.bin` was wanted.
- The distribution static-file guard also permits a direct
  `/patches/<name>/presets/...` request because it filters dot/part/symlink
  paths only (`dashboard/server.py:60-71`).

**What breaks.** A mirrored node that already has a `presets/` directory loses
it on the next fetch, contrary to F1's explicit “invisible to
prune-to-manifest convergence” wording. Changing only `identity.py`, as the
proposal says, does not implement the ruling.

**Recommendation.** Make ignore policy a shared named primitive used by both
identity enumeration and fetch pruning, and add three tests: fingerprint
ignores preset edits, mirrored convergence preserves a pre-existing
`presets/`, and ordinary stale files still prune. Decide explicitly whether
direct HTTP serving of a known host-only path is allowed; if “host-only” means
not fetchable even by a hand-built URL, deny it in `DistributionStaticFiles`.
Clean ignored legacy entries from the persistent hash cache as hygiene
(`python/identity.py:89-110` currently only filters dot paths).

### D6 — capture is not honest after `stop`, and generator preset state does not
replay to an offline/rejoining target

**Claim.** Capture can read every durable state from seat params plus the
automation table, and applying the existing full-state argument list covers
offline targets through the normal catch-up path.

**Evidence.**

- Dashboard `set_param` records fade/loop/LFO automation, but `stop` and plain
  values clear the automation entry without updating the durable seat value
  (`dashboard/osc_bridge.py:426-469`).
- Node `stop` freezes the generator at its *current output*
  (`python/paramgen.py:201-207`). That output is not sent back to the
  dashboard.
- Fade is the one special case whose destination is written durably
  (`dashboard/osc_bridge.py:460-461`, `dashboard/osc_bridge.py:487-499`).
- Rejoin replay sends only `seat["params"]`; it never prefers an automation
  entry (`dashboard/server.py:1512-1518`). The node also explicitly forgets
  generators across engine restarts (`python/bopos.py:718-735`).

**What breaks.**

1. Start an LFO/loop, press Stop, then save: capture sees no automation and
   stores the stale pre-generator seat value, not the held node value.
2. Apply a preset containing an LFO/loop/morph to an offline seat: the
   dashboard can record the automation entry, but on rejoin it replays the
   stale scalar. The target never reaches the applied preset.
3. A node/engine restart during a generator preset similarly loses the
   dashboard's claimed state unless catch-up is extended.

**Recommendation.** Add generator-aware replay as part of the application core,
not the UI stitch: for each seat/identity, replay the active full-state
automation args when present, otherwise the durable scalar. Define `stop`
capture honestly before shipping save: either calculate and store a canonical
held value at stop time, or state that stopped output cannot be captured and
exclude/warn it. Morph catch-up must cover both “node received the morph and
engine restarted” and “seat was offline for the original morph”.

### D7 — the proposed schema hash silently misses enum meaning, and current
toggle normalization does not round-trip

**Claim.** `{identity, kind, min, max, options count}` is a stable sufficient
control-schema fingerprint and round-trips through `manifest.py`.

**Evidence.**

- Enum indices derive their meaning from ordered labels, not just count
  (`python/manifest.py:164-186`, `docs/OSC-CONTRACT.md:806-813`).
- Reordering `["dry", "wet"]` to `["wet", "dry"]` preserves kind, range, and
  option count while reversing the meaning of every saved index.
- Toggle validation adds normalized `min=0,max=1`, but a second validation
  rejects those same keys as authored bounds
  (`python/manifest.py:187-193`).
- A direct focused reproduction confirmed that validating a toggle, then
  validating the normalized output, fails with
  `min/max is derived for kind toggle`.

**What breaks.** Enum drift can silently apply the wrong named value while
reporting the schema unchanged. Any schema helper based on normalized manifests
also encounters a current load/save round-trip defect for toggles.

**Recommendation.** Hash the full canonical ordered enum labels, not their
count. Keep the overall declaration list sorted by qualified identity so
manifest drag reorder is intentionally irrelevant. Fix and guard toggle
load→save→load before building preset schema hashes; fingerprint a deliberate
canonical projection rather than serialized normalized editor output.

### D8 — the proposed Show reference cannot carry its required metadata through
the current model, and group-by-name targets are not yet representable

**Claim.** `/preset/<patch>/<name>` plus its authored fingerprint can behave as
a normal Show message, using existing target chips with groups by name.

**Evidence.**

- `show_model.clean_message` returns exactly `uid`, `alias`, `address`, `args`,
  and `target`; any added fingerprint/reference member is discarded
  (`dashboard/show_model.py:98-122`).
- Server updates accept only `alias/address/args/target`
  (`dashboard/server.py:1307-1310`), and copy/paste preserves the same four
  fields (`dashboard/static/js/show.js:878-893`).
- Targets accept only `all`, decimal seat ids, and `g<integer>`
  (`dashboard/show_model.py:27-30`, `dashboard/show_model.py:59-75`).
- The target picker stores `g<id>`, not names
  (`dashboard/static/js/show.js:248-275`).
- Group names are currently allowed to be empty or duplicated; neither load,
  create, nor rename enforces uniqueness
  (`dashboard/state.py:491-514`, `dashboard/state.py:549-588`).
- Without a new branch, ShowEngine sends every non-`/p`/`/e` address verbatim,
  so `/preset/...` reaches the raw OSC path
  (`dashboard/show_engine.py:141-161`).

**What breaks.** The authored-against fingerprint disappears on load/add/edit;
a portable group name is rejected by the model; and duplicate/empty venue group
names make the earlier ratified name→id rule ambiguous. The pseudo-address
itself is accepted, but it is not enough to distinguish an expandable
composition reference from raw OSC.

**Recommendation.** Create a Show-reference foundation before the preset
message stitch: an explicit message kind/reference payload (or another
validated representation), authored patch references, portable named targets,
missing/ambiguous-name warnings, and round-trip/copy/undo guards. Resolve the
consequence of duplicate/empty group names with Bob: the cleanest path is
non-empty unique names as a venue invariant with an honest adoption path for
old venues. Inject a preset-expansion callback/service into `ShowEngine`;
do not teach the transport-only bridge to read patch files.

## Findings — under-specified behaviour

### U1 — “per-target applied preset” is not enough to reproduce overlapping
applications

All, groups, seats, and devices are overlapping views, not disjoint entities.
The current Control surface renders exactly those overlapping cards
(`dashboard/static/js/facilitator.js:122-140`). For example:

1. Apply Dawn to All.
2. Apply Dusk to Seat 2.
3. Capture as step.

Both provenance facts are true, and replay order is load-bearing. A dictionary
of unordered per-target markers can produce the wrong final state; clearing the
All marker loses real provenance and capture intent. The same problem occurs
with overlapping groups.

**Recommendation.** Define runtime provenance as an ordered application ledger
keyed by stable target references, with the card dropdown as a projection.
Capture preserves that order. If a different rule is intended—such as
non-overlapping leaf-seat provenance—Bob must choose it because it changes
portable capture semantics.

### U2 — malformed, empty, colliding, deleted, and concurrently saved presets
have no policy

The proposed one-file store needs explicit answers for:

- invalid JSON/version/shape, unsafe argument types, non-finite floats, and
  hand-edited out-of-range values;
- an empty sparse preset (a no-op that would still set provenance);
- display names whose existing slug transform collides (`A B` and `A-B`), case
  collisions, and Unicode `\w`;
- a `presets/` symlink or preset-file symlink escaping the patch root;
- two browsers saving the same slug after stale overwrite confirmation;
- deleting/renaming a preset still referenced by a Show or an
  `applied_preset` marker.

Current serialized WS mutations protect one server process
(`dashboard/server.py:287-321`) but do not make a stale client confirmation a
compare-and-swap. Current Show loading tolerates corruption by replacing it
with an empty show (`dashboard/show_model.py:613-628`); that would be dangerous
for a preset because “empty” is a valid sparse shape.

**Recommendation.** Make the store strict and fail-visible: reject malformed
files from apply, list them with an error, reject empty saves, confine real
paths, and require an overwrite revision/token. Deletion leaves Show
references dangling with a warning; define whether applied provenance remains
as “missing” or is cleared.

### U3 — capture is dashboard-intended state, not observed node state

The architecture explicitly rejects runtime queries, so this is not a request
for an acknowledgement plane. It is an honesty requirement. Live writes commit
the dashboard mirror before sending (`dashboard/server.py:378-401`), fade
destinations are stored before `self.send`, and UDP `_send_to` can report only a
local socket error (`dashboard/osc_bridge.py:352-370`). A dropped packet,
offline node, or engine-start window therefore creates a real interval where
the preset captures desired dashboard state rather than node output.

**Recommendation.** Use “dashboard state”/“intended state” in UI and docs, keep
offline capture/apply legal, and rely on the repaired catch-up path from D6.
Do not describe capture as measuring what the engine currently sounds like.

### U4 — numeric canonicalization required by F4 does not exist at the durable
write boundary

The proposal says dirtiness compares at the six-significant-figure precision
the UI sends. Today `clean_editor_value` range-checks but does not canonicalize
(`dashboard/server.py:1761-1784`); the raw value is persisted before send
(`dashboard/server.py:378-401`), while OSC float formatting rounds later
(`dashboard/osc_bridge.py:390-397`). The dashboard can therefore store
`0.1234567` while the node received `0.123457`.

**Recommendation.** Add one shared canonicalization function used by live
writes, preset save/apply, schema resolution/clamp, and dirty comparison. Store
the exact value sent. Do not implement F4 as scattered client-side approximate
comparisons.

### U5 — surface authority is unclear

The provisional row is in shared `ControlSurface`, used by Control,
standalone facilitator, and Device (`dashboard/static/js/control-surface.js:252-277`).
The Patch editor is a separate `editorParamTree` implementation with no preset
row or generator drawer (`dashboard/static/js/dashboard.js:1035-1067`).
Standalone facilitator deliberately sees only `dashboard:true` params
(`dashboard/static/js/facilitator.js:59-80`) even though a default preset save
captures all params.

**Recommendation.**

- Budget a distinct Patch-editor authoring surface; activating only the
  provisional shared row does not implement the primary sculpt→save workflow.
- Decide whether standalone facilitator is apply-only or may
  new/save/delete. Recommendation: apply-only; include/exclude authoring for
  hidden params belongs on desktop Control/editor.
- Define whether Device-panel save captures the seat's values under the pinned
  patch and how it behaves while offline (the current panel is intentionally
  visible but disabled offline).

## Findings — unbudgeted cost

### C1 — “apply is free” is true only for the final datagram

`OSCBridge.set_param` does accept a complete argument list and `_datagram`
supports string atoms (`dashboard/osc_bridge.py:426-469`,
`dashboard/osc_bridge.py:390-397`). But it does not, by itself:

- validate entries against the correct effective patch;
- update scalar durable seat/device mirrors;
- replay automation to rejoining nodes;
- maintain ordered applied provenance;
- canonicalize/clamp values;
- report per-target adjusted/dropped/mismatched results; or
- persist and broadcast one atomic application.

The old `load_preset` performs a separate partial version of those state writes
(`dashboard/server.py:821-853`). Hiding the new logic in the panel or Show
stitch would create two application paths, contrary to R1.

**Recommendation.** Add a dedicated preset-application-core stitch/service
before any UI or Show integration. Every caller—Control, Device, editor recall,
Show expansion—uses it.

### C2 — Show integration contains two prerequisite architecture changes

ShowEngine is deliberately transport-only and is constructed with only the OSC
bridge, broadcast callback, and event-lead getter
(`dashboard/server.py:124-167`, `dashboard/show_engine.py:48-53`). Preset
expansion needs patch-store access, target-name resolution, effective-patch
filtering, drift reporting, and the application core. In addition, the
ratified group-name and authored-patch-reference changes have not landed
anywhere else.

Flatten-to-messages and capture-as-step also need atomic model operations so
one user action is one persistence/undo entry; existing `apply_show_mutation`
already supplies that boundary (`dashboard/server.py:1345-1372`), but the
operations do not exist.

**Recommendation.** Split Show-reference foundation from
Show-preset-message/capture. Inject an application callback into ShowEngine and
add atomic `flatten_preset_message` and `capture_preset_step` model operations.

### C3 — derived dirtiness is affordable only with a defined cache/data path

The feared heartbeat hot path is less severe than the proposal review brief
suggests: dashboard heartbeats update only the blip DOM
(`dashboard/static/js/dashboard.js:147-159`), and the server sends
`device_update` only when heartbeat-visible facts change
(`dashboard/osc_bridge.py:1198-1208`). Existing aggregate rendering already
walks member values/automation (`dashboard/static/js/control-surface.js:61-79`).

However, per-render comparison is cheap only if preset bodies and canonical
signatures are cached. Reading JSON from disk at render/broadcast time, or
shipping every preset body in every full-state message, would make the cost
material. Morph completion adds another derived-time rule: the stored
automation entry must compare as “in flight” before duration and as its
destination spec after duration without a sticky flag.

**Recommendation.** Cache validated preset documents by file stat/revision on
the server, publish only the selected preset/signature needed by each card (or
derive dirtiness server-side), and benchmark a realistic seat×param×preset
surface. Invalidate on atomic save/delete and external file changes.

### C4 — §11's six-stitch split is missing the load-bearing seams

The proposed split puts application semantics inside no named stitch, combines
all panel/editor surfaces, and asks the Show stitch to absorb the unimplemented
portable-target/content-reference foundation.

**Recommended dependency shape after Bob resolves the open questions:**

1. **Grammar/reference closure** — unambiguous `morph`, supported-pair matrix,
   patch-vs-schema fingerprints, named-group invariant, overlapping provenance.
2. **Manifest/distribution foundations** — toggle round-trip, schema helper,
   shared host-only ignore/prune policy and guards.
3. **Preset store** — strict atomic CRUD, cache, validation, slug/conflict
   semantics, drift resolution.
4. **Preset application core** — patch-aware concrete targeting, clamp/skip
   report, durable/automation state, offline/restart replay, provenance ledger.
5. **Morph wire + engine** — contract, Python/browser parsers, bopos engine,
   simfleet, catch-up, takeover, quantization.
6. **Control/Device/facilitator UI** — list/apply/save/delete according to
   surface authority, include/exclude, dirtiness and drift.
7. **Patch-editor save/recall UI** — its separate seat-0/plain-control path.
8. **Show reference foundation** — authored patch refs, group names, round-trip,
   target warnings.
9. **Show preset messages** — expansion, PRE pill, atomic flatten,
   capture-as-step.
10. **Venue preset retirement** — last, after every replacement path is live.

Some can be merged after measurement, but the dependency boundaries should
stay visible. In particular, do not amend the contract before D1/D2 are
closed, and do not retire venue presets before the application/UI replacement
is complete.

## Verified

These load-bearing pieces checked out, with the stated boundary:

1. **The final send path exists.** `OSCBridge.set_param` accepts list args and
   preserves nested identity strings in the address
   (`dashboard/osc_bridge.py:426-469`). Toggle/enum values send as integers;
   text strings are accepted by the OSC builder. Text fails numeric
   `parse_message` harmlessly, clears any numeric automation record, and still
   sends as `/p/*`. No second socket or preset wire plane is needed.
2. **Fade destination capture is already durable.** A fade records its final
   destination in seat/device mirrors before send
   (`dashboard/osc_bridge.py:452-461`, `dashboard/osc_bridge.py:487-499`).
   The caveats are UDP intent-vs-observation (U3) and generator replay (D6).
3. **Current automation args are available for LFO/loop/fade capture.**
   `OSCBridge.automation` is runtime-only, keyed by seat and qualified identity,
   and holds the original argument list (`dashboard/osc_bridge.py:137-140`,
   `dashboard/osc_bridge.py:436-459`). Exact argument-list comparison matches
   F4. `stop` is the exception in D6.
4. **One shared identity walker does cover host, node, simulator, and run
   context.** Host catalog uses `identity.directory_manifest`
   (`dashboard/server.py:74-107`), node patch inventory uses
   `identity.fingerprint` (`python/bopos.py:950-987`), and run context uses the
   cached form (`python/runcontext.py:77-103`). A correctly shared exclusion can
   keep identities equal. Prune is the separate defect in D5.
5. **Manifest reorder need not affect the schema hash.** Parameter identity is
   canonical and validated (`python/manifest.py:47-73`), and manifests preserve
   authored order. Hashing the proposed projection after sorting by qualified
   identity makes drag reorder irrelevant. Include full ordered enum labels and
   fix toggle normalization as D7 requires.
6. **The pseudo-address can ride generic Show editing once its model is
   extended.** Current address validation accepts `/preset/...`; move,
   duplicate, persistence, and undo are address-agnostic
   (`dashboard/show_model.py:98-122`,
   `dashboard/show_model.py:450-487`,
   `dashboard/server.py:1345-1388`). An explicit playback branch is still
   mandatory; otherwise it is raw OSC.
7. **Monitor honesty comes for free after correct expansion.** Every expanded
   `set_param` reaches the existing outgoing tap in `_send_to`
   (`dashboard/osc_bridge.py:352-370`), so Monitor will show what was actually
   emitted rather than the pseudo-address.
8. **Pinned Device panels already receive their own patch schema.** The server
   projects pinned `live_controls` per device
   (`dashboard/server.py:1633-1655`) and the Device panel selects it
   (`dashboard/static/js/dashboard.js:1377-1405`). This is useful input to the
   patch-aware application core, but it does not make All/Group selectors safe
   (D4).
9. **Per-render dirtiness is not automatically a heartbeat-rate regression.**
   The dashboard has a blip-only heartbeat handler and existing rendering
   already aggregates param/automation state. With canonical cached signatures,
   the comparison itself is likely cheap; C3 names the measurement and data
   path still required.

## Open questions for Bob

1. **Which `morph` pairs are v1?** Recommendation: ratify an unambiguous outer
   curve token and ship only pairs with a fully specified coercion/phase rule;
   reject the rest visibly rather than inventing loop/segment padding during
   implementation.
2. **May venue groups be empty or duplicate once shows resolve by name?**
   Recommendation: no—make names non-empty and unique within a venue, with a
   one-time adoption warning/editor fix for existing venues. “First match”
   would make portable shows nondeterministic.
3. **How should overlapping applied targets be captured?** Recommendation:
   preserve an ordered runtime application ledger (All Dawn, then Seat 2 Dusk)
   and emit references in that order. This retains provenance and reproduces
   the actual arrangement without flattening to anonymous seat snapshots.
4. **What may the standalone facilitator do with presets?** Recommendation:
   apply only. Keep new/save/delete and per-param inclusion on desktop
   Control/Patch editor, where every manifest param is visible.

## Verification performed

- Read the proposal, decisions, thread context, current OSC contract, entity
  decisions, and all cited implementation paths.
- Traced full-list `/p/*` send, durable/automation capture, effective patch
  selection, identity/fetch/prune, manifest normalization, Show persistence,
  playback, copy/paste/undo, and Control/Device/editor/facilitator rendering.
- Focused temporary reproduction: normalized toggle validation fails its second
  pass with derived `min/max`.
- Focused temporary reproduction: generic fetch prune deletes a pre-existing
  `presets/dawn.json` absent from the wanted manifest.
- `git diff --check` — pass.
- `./tools/run-tests.sh fast` — pass, 196 tests.
- No implementation was changed. Hardware, browser, LAN, audio, and PD were not
  exercised because this is a proposal/code review.
