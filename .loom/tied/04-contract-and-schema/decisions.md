# Decisions — 04-contract-and-schema

Date: 2026-07-29. Documentation-only stitch; `python/`, `dashboard/` and
`tools/` untouched, as instructed.

## What landed, and where

The amendment is **two edits to the contract**, plus a version header and a
revision-history row.

| Clause | Landed in | Why there |
|---|---|---|
| A preset is not a wire concept; storage layout; capture rule; schema fingerprint; timed apply | **new §8.1**, at the end of §8 | §8 already owns the manifest and everything derived from declarations. §8.1 follows the doc's existing habit of numbered subsections under a section that needs them (§3.1–§3.3). |
| `presets/` host-only exclusion | **§9**, as a bullet after the patch-landing convention | It is a distribution rule; it sits with the other convergence semantics and next to the dotfile/`.part`/symlink exclusions it extends. §8.1 cross-references it rather than restating it. |
| v1.17 row incl. the morph deferral | §15 | — |

§3.2 and §3.3 were **not touched**, per the instructions and because the
timed-apply clause deliberately consumes §3.3's existing fade form rather than
extending it. §8.1 says so explicitly and points at §3.3.

## Judgment calls

1. **§8.1 rather than a new top-level section.** A preset is host-side and
   non-wire, so putting it at §-level would overstate it; but the schema
   fingerprint and the capture rule genuinely need one normative home so the
   dashboard, editor, show model and patch tooling agree. A subsection under
   the manifest section says "derived from the manifest, not spoken on the
   wire", which is exactly the status. §8.1 opens by naming that status so no
   reader mistakes it for a plane.

2. **The canonical-JSON serialization is pinned harder than the stitch text
   required.** "Canonical JSON" alone does not make two implementations agree.
   Pinned: the five keys in the stated order, sort ascending by qualified
   identity in byte order, UTF-8, no insignificant whitespace, SHA-256,
   recorded as `sha256:<hex>`.

3. **`min`/`max`/`options` where the kind has none → JSON `null`.** The
   addendum's §A6 projection does not say what a `text` param contributes.
   Omitting keys per-kind would make the key order rule vacuous and invite two
   implementations to disagree; a fixed five-key shape with explicit `null` is
   unambiguous. Also stated: `min`/`max` are the **effective** values after
   §8's derivation (toggle `0`/`1`, enum `0`…`n-1`), not the authored ones —
   otherwise the hash would depend on whether the author wrote a redundant
   pair the loader derives anyway.

4. **The HTTP-surface denial is stated in the contract, not left to the
   store stitch.** The addendum §8 recommended "deny" so that *host-only*
   means one thing; stating it here is what makes it a contract term rather
   than an implementation choice 05 could quietly reverse. 05 still owns the
   guard itself.

5. **The morph deferral is written into the revision history, not the body.**
   §8.1's body says flatly that no `morph` and no preset wire form exist —
   the normative statement. The history row carries *why*, names
   `feature-backlog/48-morph-interpolation`, and records that a preset entry
   is already the argument list morph would consume, so a future reader knows
   it was considered and parked. Keeping the archaeology out of the body keeps
   the body normative.

6. **Capture wording adopts U3's "intended dashboard state".** Carried into
   §8.1 verbatim in spirit, with §14's rejection of a runtime query verb cited
   as the reason the distinction is structural rather than sloppy.

## Deliberately not done

**`contract_version` constants stay at `"1.16"`** in `python/bopos.py:1311`,
`tools/simfleet.py:488` and `tools/audition.py:269`. Two reasons: this stitch
is forbidden from touching those trees, and — the substantive one — that
constant is what a **node** reports about the wire vocabulary it speaks, and
v1.17 adds nothing a node speaks. The precedent is the 2026-07-27 "1.13 am."
clarification, which changed no wire shape and bumped no constant; the
constants moved only on 1.14/1.15/1.16, each of which changed the wire or the
manifest. If a later stitch decides the constant should track the document
number rather than the node's vocabulary, that is a deliberate choice to make
once, not a side effect here.

## Prose sweep

`grep -rn "1\.16" docs README.md CLAUDE.md python dashboard tools`, plus a
version-claim sweep of the same docs. Each hit judged:

- `docs/OSC-CONTRACT.md:3` header → **1.17**, date 2026-07-29.
- `CLAUDE.md` "Start here" item 2 (`now v1.15`) → **v1.17**, and the parenthetical
  now names v1.16 and v1.17 alongside v1.14/v1.15.
- `CLAUDE.md` thread-44 block, "The contract is now at **v1.15**" → reworded to
  "which is where the contract stood at the end of that step". It is a
  completion record for `4-cue-retirement`, not a current-state claim, and it
  had already gone stale at v1.16.
- `CLAUDE.md` queue item 8 (preset thread) → **rewritten**. It still described
  `morph` as the ratified interpolation mechanism (dropped by Bob 2026-07-29),
  claimed the implementation stitches were "deliberately not created yet"
  (they exist, `04-`…`10-`), and called v1.17 "proposed". It now points at both
  reviews, records the morph deferral and its backlog thread, and states that
  04 is tied and 05 is live. This is the orientation file; leaving it would
  have actively misdirected the next agent.
- `README.md:110` status blurb, "OSC contract v1.9" → **v1.17**. Seven
  revisions stale; a status paragraph that names a version should name the
  current one.
- `docs/OSC-REFERENCE.md` hits (`v1.6`, `v1.12`, `v1.13`) → **left alone**. Each
  annotates *when a specific term was introduced*; they are provenance
  markers, not currentness claims. v1.17 introduces no wire term, so
  OSC-REFERENCE gains nothing.
- `python`/`tools` `contract_version` constants → left; see above.

## Verification

- Re-read §8.1 and the §9 bullet against `design-addendum.md` (§A3, §A6, §8),
  `review-2.md` (§F1 ruling, §F4's whitelist/report notes, §F5's consumer
  table) and the tied proposal §1. No contradiction found. Checked
  specifically that §8.1's capture rule does not conflict with §8's existing
  "Presets do not capture events" sentence — it cites it rather than
  restating a second, divergent version.
- §3.2 and §3.3 confirmed byte-unchanged (`git diff` touches §0 header, §8
  tail, §9, §15 only).
- §14's rejected list re-read: nothing in v1.17 reintroduces a rejected
  design. §8.1 leans on §14's query-verb rejection rather than eroding it.
- `tools/run-tests.sh fast` → **196 tests, OK, exit 0.**

## Observation for a later stitch (not acted on)

`tools/run-tests.sh fast` is **green**, but CLAUDE.md's tier-2 item 11
describes thread `45-device-enabled-replay-red` as "the one red test in
`tools/run-tests.sh fast`". The named assertion,
`tests/test_device_control_routing.py:237`
(`test_reappearing_physical_device_replays_persistent_enabled_state`), now
passes on clean `main`. Either the defect was repaired as a side effect
elsewhere or the test was adjusted; thread 45's premise should be re-checked
before it is worked. Out of scope here — flagged, not touched.
