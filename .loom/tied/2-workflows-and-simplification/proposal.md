# Workflows and the simplest model — proposal (2026-07-27)

Stitch `entity-architecture-review/2-workflows-and-simplification`. Builds on
`.notes/entity-map-2026-07.md` (the as-is map: a DAG, no cycles; the smell is
unversioned implicit couplings C1–C3 and dual expressions D1–D4) and Bob's
2026-07-27 interactive answers, which are quoted where they decide something.

---

## 1. Bob's workflow facts (input, this session)

1. **Shows travel.** "Ideally, the same show file runs" at a new venue, with
   different seat counts and arrangements. Compositional targeting is:
   spatial placement, groups, or random scatter across seats/groups with a
   density amount. Seat-order sequences "might be better handled spatially."
2. **Patch switching: between sections for now.** Per-device targeting
   possible later. Rainbow / HappyBrackets-style *simultaneous multiple
   patches* is a "consider later" door, wanted only if elegant.
3. **Presets are synth-style set sounds** made in patch-edit mode, then
   applied to groups/seats/all, ideally with interpolation. A step targeting
   different groups with different presets is a "meta preset".
4. **The smell**: params/values lifecycle + where-things-live; the
   pinning/fleet-patch workflow feels clunky (possibly just UI).

## 2. Workflow walkthroughs

### W1 — a show step loads a patch (fleet-wide, between sections), then sequences it

Today a show cannot switch patches: staging is a WS command path
(`stage_and_converge`), not a show-message kind. If it could, the existing
lifecycle already does the right thing (name change → full value reset to
defaults; `params_patch` repoints) — but the show document has no record of
which patch each section assumes, so the assumption is implicit in step
order. **Consequence:** the authored-against record needs to be a *list* of
`{name, fingerprint}` per show (one per patch the show touches), and a
"switch patch" step action references one by name. Convergence timing is
solved by the existing prefetch machinery: distribute early, switch at the
section boundary; the badge vocabulary (`switching`/`current`) already
describes it.

### W2 — different patches on different devices in one show

The seam law already makes heterogeneous fleets *safe*: a `/p/*` message a
patch doesn't declare is a legal no-op. The pin machinery (thread 37)
already expresses per-device desired patches. What's missing is not
mechanism but *visibility at authoring time*: nothing tells you which of a
step's targets will actually consume its messages. That is derivable — the
host has every manifest and every device's effective patch — so it should be
a derived warning, never stored state. The "multiple simultaneous patches"
door stays open and untouched: nothing in this model assumes
one-patch-per-device except the node's `active_patch.txt`, which is exactly
where a future amendment would land.

### W3 — re-siting: same show, different venue

What changes per venue: the seat set, positions, bindings, and group
*membership*. What must not change: the show, and the meaning of its
targets. Bob's targeting practice (groups / all / spatial / scatter) makes
**groups the portable compositional layer** — but today group *identity* is
venue-scoped: ids come from the venue's never-reused allocator, so a venue
rebuilt from scratch can allocate different ids for the same compositional
role, silently desynchronizing every show. Venues saved from a common
lineage keep ids stable, which is why this hasn't bitten yet.

Two further consequences: a show targeting seat 7 in a six-seat venue
silently no-ops (consistent, but invisible); and `reindex_seat` rewrites
preset keys but not show targets (map finding C3).

Scatter/density (random across seats or within groups, with density) is a
compositional primitive that exists nowhere yet; it belongs to the
`scene-sequencing` co-design, but the model below deliberately leaves it a
clean slot: it is *target-set resolution* (pick N of the selector's members
per event), which lives dashboard-side above the selector layer — no
contract change.

### W4 — sculpt → save preset → apply from Control → trigger from a show

With 41's ruled storage (presets in the patch folder, 1:1 with the
manifest), this flow is: editor writes `patches/<name>/presets/<preset>`;
Control lists the staged/pinned patch's presets and applies one to the
current target (fan-out of ordinary `/p/*` sets, hard takeover); a show step
message of a new preset kind `{target, preset, duration?, curve?}` does the
same with optional interpolation. **Bob's "meta preset" needs no new
entity:** a step already holds multiple messages with independent targets —
different groups getting different presets *is* a step. "Collections"
therefore have a natural first form: show steps (or a step saved as a
template), not a fourth store. If a standalone collection object is ever
wanted outside shows, that decision can wait until the step form proves
insufficient.

### W5 — the manifest changes under shows and presets

Today: seat values reconcile correctly; presets half-apply silently (the
`active_param_identities` filter); show messages no-op silently. The fix is
the system's own idiom — desired vs observed vs derived — applied to
authorship: store an **authored-against `{name, fingerprint}`** wherever
content is referenced, and *derive* a freshness badge against the live
catalog. Never block on drift (a half-applicable preset should still apply
its intersection, with a visible warning), because blocking would make a
patch edit a breaking event mid-production.

## 3. The model (recommendation)

Four layers, references only ever point from later layers to earlier ones —
the DAG the system already is, made explicit and versioned:

| layer | store | holds | identity |
|---|---|---|---|
| 1. Hardware | host registry | box facts: alias, enabled, pin | uid (MAC) |
| 2. Site | venue (`installation.json`, snapshots) | room, seats (positions, bindings, live values), group membership | venue name; seat ids site-local |
| 3. Content | patch folder | code, manifest, **presets (41)** | patch name + fingerprint |
| 4. Composition | `dashboard/shows/` | steps: messages, preset applies, patch switches | show name; records authored-against content fingerprints |

Rules that make it hold:

- **R1 — one application path.** Every way of making sound state change —
  Control edit, preset apply, show message, interpolation — collapses to the
  same per-param fan-out over selectors with hard takeover. No layers, no
  locks, no second ownership scheme. (Already ruled for 41; stated here as
  the global rule.)
- **R2 — cross-layer content references carry a fingerprint.** Shows and
  presets record the `{name, fingerprint}` they were authored against;
  freshness is derived, warned, never blocking. Site references (targets)
  resolve live instead — a group is *meant* to mean whatever the venue says
  it means today.
- **R3 — portable shows target groups and all.** Seat-id targets stay legal
  (they're needed for site-specific work and debugging) but the Show tab
  should treat them as site-bound and say so. Groups need one decision to
  become truly portable (fork F1 below).
- **R4 — sound identity lives in the patch; mix state lives in the site.**
  A patch preset is "what this sound is" (values + generator specs); the
  seat's live values are "where the room is right now". The venue-preset
  store retires once 41 lands (it is empty today — no migration needed).
- **R5 — derived, never stored, verdicts.** Drift badges, consumability
  warnings (W2), and convergence all stay recomputed-per-broadcast facts.

## 4. Small ordered changes (each keeps the system working)

1. **Record `{name, fingerprint}` on preset save** (today's venue presets,
   one added field) and show a drift note on load. Tiny; rehearses the exact
   mechanism 41 and shows need; harmless to the empty store.
2. **Record authored-against patches on show save** (additive `patches`
   field on the show document) + a derived freshness badge in the Show tab.
3. **Close C3**: seat reindex either rewrites show targets in
   `dashboard/shows/` or (cheaper) the Show tab flags targets that name
   nonexistent seats. The flag also covers W3's six-seat case.
4. **F1 decision, then implement**: group identity for portable shows (see
   forks).
5. **41 proceeds** on this model: patch presets + preset-apply message kind +
   interpolation; venue presets retire.
6. **Pin/fleet workflow clunk**: no semantic change proposed — the split
   (fleet default in venue, pin in registry) is right; the clunk is a UI
   sequencing problem and moves to `desktop-ui-overhaul` as an input.
7. **Show-triggered patch switch** (W1): a `patch` step-action referencing an
   authored-against entry; between-sections semantics; prefetch stays the
   operator's explicit act.

Deliberately not proposed: multi-simultaneous-patches (door noted at the
node's active-patch seam, wanted only if elegant — later); scatter/density
(scene-sequencing co-design; slot identified as dashboard-side target-set
resolution); any change to the value-mirror plumbing (D2 is internal and
working).

## 5. Forks for Bob

- **F1 — portable group identity.** Options: (a) *convention*: venues derive
  from a common lineage, ids stay stable, document it — zero code; (b)
  *resolve by name*: shows store group targets as names, resolved against
  the venue at load, warning on misses — small code, names become
  compositional API; (c) *stable role slots*: a fixed small set of role ids
  (g0–g3) with per-venue meaning — zero code, pure discipline.
  Recommendation: **(b)**, because it makes the show file self-describing
  and survives independent venue authoring; (a) until then.
- **F2 — venue-preset retirement timing.** Retire at 41-landing (clean), or
  keep both stores briefly. Store is empty today, so recommend: retire.
- **F3 — where the "authored-against" warning surfaces.** Show tab only, or
  also at show *load* (`current_show` pointer set). Recommend both; same
  derived check.
