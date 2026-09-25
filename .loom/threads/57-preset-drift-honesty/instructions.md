# 57-preset-drift-honesty

**Goal:** Show-tab preset warnings only fire when a show will actually play
differently, and the operator can acknowledge the rest.

**Status:** not started. `1` and `2` are ready; `3` and `4` are blocked on them;
`5` waits on Bob.

## The problem (Bob, 2026-08-03)

After editing a patch's `.pd` and deploying, a Show with preset references
shows a wall of identical warnings:

> Patch "bonks-pd" has changed since this preset message was authored.
> Patch "bonks-pd" parameter schema has changed since this preset message was authored.
> *(repeated per message)*

> "what would be a suitable way to dismiss this whilst making sure the show will
> likely still function? … in some cases i might have just added a parameter and
> so the show is not impacted."

Three defects:

1. **Fan-out.** `show_reference_warnings` (`dashboard/show_model.py`) emits one
   warning per preset message × two codes; `show.js` renders them with no
   dedupe.
2. **`patch_drift` hashes the whole patch directory**, so every `.pd` edit trips
   it. Contract §8.1 says applicability is about the manifest, not the files.
3. **`schema_drift` compares a whole-schema hash**, so adding a parameter looks
   the same as deleting one.

The right check already exists and isn't used here:
`preset_store.resolve_entries` gives per-parameter `applied` / `clamped` /
`dropped` verdicts.

## Bob's rulings (2026-08-03)

- **`patch_drift` becomes a quiet notice** — off the panel, onto the step pill.
- **Dismiss = re-stamp the reference.** Persisted, survives reload, one undo
  step. Not a transient `[x]`.
- **Placement:** pill mark + inspector action. The warning panel stays
  non-interactive.

## Design rule for every stitch

**Applicability is always computed from the preset body + current manifest,
never gated on the schema hash.** If it were gated, Accept would make the hash
match and silently hide a genuinely dropped parameter. Two separate questions:

| | provenance | applicability |
|---|---|---|
| asks | is the patch still what I authored against? | will every stored entry land? |
| from | stored vs current fingerprints | preset body vs current manifest |
| dismissible | yes — re-stamp | no — true until manifest or preset changes |

A second defect shapes the order: `reference.schema` is **stamped** with the
preset file's saved schema but **compared** against the patch's current schema.
So a new message pointing at an already-drifted preset warns immediately, and an
Accept button would be undone by the next touch of the preset picker. That's
`2`, and `4` hard-depends on it.

## Stitches

1. `1-resolution-authority` — panel reports real breakage only. Fixes Bob's
   symptom on its own. **Do first.**
2. `2-reference-schema-meaning` — make stamp and comparison mean the same thing.
3. `3-drift-marks` — ⚠ on the `PRE` pill + an inspector block. Needs `1`.
4. `4-accept-restamp` — the Accept action. Needs `2` and `3`.
5. `5-missing-preset-warning` — **waiting on Bob:** should a step pointing at a
   deleted preset warn?

## Out of scope (noted)

`show_target_warnings` fans out the same way (N messages to `group:Missing` →
N lines). Left alone because that path works and has a passing guard. A clean
later stitch if Bob wants it.

## Constraints

- Warnings stay derived, never stored, never blocking (R5). The re-stamp writes
  the same `reference` field the inspector's preset picker already writes.
- No new colour: `--amber` + `⚠` for warnings; cyan is reserved for modulation.
  Marks lead the label so ellipsis can't hide them (`53/3`'s rule).
- Pre-tie: `tools/run-tests.sh fast` + relevant `browser` journeys.
