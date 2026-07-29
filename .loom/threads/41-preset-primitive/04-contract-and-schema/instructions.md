# 04-contract-and-schema

**Gates every other stitch in this thread.** Amend `docs/OSC-CONTRACT.md` to
**v1.17** with the ratified preset foundations. This is a documentation
stitch: no parser, engine, or dashboard code changes, and **no new wire form**
— morph was dropped from v1 (Bob, 2026-07-29; deferred to
`feature-backlog/48-morph-interpolation`).

## Authority — read before writing, do not re-litigate

1. `.loom/tied/1-preset-architecture-design/proposal.md` + `decisions.md` —
   the ratified base (F1–F4).
2. `../design-addendum.md` — authoritative where it differs; note its
   supersession banner (morph §A1/§A2 are deferred, everything else stands).
3. `.loom/tied/3-addendum-review/review-2.md` — the final review; its §Layout is the
   live plan and its findings are folded into these stitches. Bob's four §9
   addendum rulings are settled.

Read the contract's §15 revision history first for the current version
(v1.16 as of 2026-07-28) and the house amendment style.

## The amendment (additive)

1. **`presets/` is a host-only patch subdirectory.** In the patch
   distribution sections (§8/§9): authored content that travels with the
   patch in git and host-to-host copies, but is excluded from the
   distribution manifest, the patch fingerprint, and prune-to-manifest
   convergence, and is not served over the distribution HTTP surface even to
   a hand-built URL. Rationale to state: saving a preset must not restage the
   fleet patch. Nodes have no preset concept — apply is dashboard-driven
   fan-out of ordinary `/p/*` messages.
2. **The parameter-schema fingerprint.** Define the canonical projection a
   preset's `schema` field hashes: the canonical JSON of
   `[{identity, kind, min, max, options: [ordered labels]}, …]`, sorted by
   qualified identity, sha256. Sorting makes manifest drag-reorder
   irrelevant; **ordered enum labels** (not a count) are deliberate —
   reordering labels reverses the meaning of stored indices and must change
   the hash. Note this is a dashboard/store concept referenced here so host
   tooling agrees on one definition; it is not wire traffic.
3. **One capture sentence** (§8): a preset captures declared params only;
   events are never captured (already ruled); master, mute, positions, and
   assignments are site-layer, not preset material.
4. **Timed apply uses the existing grammar.** One short paragraph: a preset
   applied with a duration emits the **existing** §3.2 fade form
   (`<dest> <dur>` with optional trailing `c:<n>`) for `float`/`int`
   entries; `toggle`, `enum`, `text`, and generator (lfo/loop) entries are
   set full-state at t=0. No new wire form exists for presets; the contract
   gains no `morph` and no preset plane.
5. **§15 revision history** entry: v1.17, 2026-07-XX (today's date),
   summarizing the above, and noting the morph deferral explicitly so a
   future reader knows it was considered and parked, not overlooked.

Also sweep prose that states the current contract version (`CLAUDE.md`'s
orientation block, `README.md` if it names a version, any code/doc constant —
`grep -rn "1\.16" docs README.md CLAUDE.md python dashboard tools` and judge
each hit) and update the ones that claim to be current.

## Out of scope

Everything executable. The schema-fingerprint *implementation* is stitch 05;
the apply behavior is stitch 06. Do not touch `python/`, `dashboard/`, or
`tools/`.

## Verify and tie

- Re-read the amended sections against the authority docs for contradictions,
  especially §3.2/§3.3 (which must remain untouched) and the distribution
  sections' existing exclusion language (dotfiles, `.part`).
- `tools/run-tests.sh fast` — must stay green (nothing should depend on
  contract prose, but some guards grep docs).
- Record in `decisions.md` in this stitch: the exact revision-history text
  and any judgment calls about where each clause landed.
- Commit (plain-prose subject per `git log` style), tie.
