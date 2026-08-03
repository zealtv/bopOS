# 57-preset-drift-honesty

Bob edits a patch's `.pd`, deploys it, opens a Show that holds preset
reference messages, and gets this:

> Patch "bonks-pd" has changed since this preset message was authored.
>
> Patch "bonks-pd" parameter schema has changed since this preset message was authored.
>
> Patch "bonks-pd" has changed since this preset message was authored.
>
> Patch "bonks-pd" parameter schema has changed since this preset message was authored.

His words, 2026-08-03, so a later reader can check the stitches against the ask
rather than against my paraphrase:

> what would be a suitable way to dismiss this whilst making sure the show will
> likely still function? just a simple dismiss [x]? can we or should we
> highlight any parameters that have changed, in some cases i might have just
> added a parameter and so the show is not impacted.

## Three defects, not one

1. **The wall.** `show_reference_warnings` (`dashboard/show_model.py:315-357`)
   emits one warning object *per preset message* × up to two codes, and
   `show.js:542-547` maps them straight to `<p>` with no dedupe. N preset
   messages on one edited patch produce 2N byte-identical paragraphs pushing
   the step list down the page.

2. **The first line warns about the wrong thing.** `patch_drift` compares
   `identity.fingerprint(patches/<name>)` — a hash of the **whole patch
   directory**. Contract §8.1 (v1.17, ratified) says the applicability check
   hashes the manifest projection

   > **not** the patch directory, so editing `main.pd` or adding a sample does
   > not invalidate a preset; only changing what is controllable does.

   So this line fires on every `.pd` edit *by construction*. It is a provenance
   fact (R2/Q2), not an applicability one, and it has been wearing the wrong
   clothes.

3. **The second line cannot tell "added a param" from "deleted a param".**
   `schema_drift` compares a whole-projection hash, so **adding** a parameter
   trips it even though no stored preset entry is affected. That is exactly
   Bob's "in some cases I might have just added a parameter and so the show is
   not impacted" — and today the app has no way to say so.

The authority §8.1 names **already exists in the repo and this path does not
use it**: `preset_store.resolve_entries` / `resolve_drift`
(`dashboard/preset_store.py:209-246`) returns per-identity
`applied` / `clamped` / `dropped` verdicts against the current manifest.

## Bob's rulings, 2026-08-03

| | ruling |
|---|---|
| `patch_drift` | **Demote to a quiet notice.** Off the panel, onto the pill, with an Accept action. Keep storing the fingerprint — the R2 signal stays legible, it just stops shouting. |
| dismiss | **Re-stamp the reference.** A persisted acknowledgement that survives reload, one undo entry. Not a transient `[x]`, which would hide the signal without answering it. |
| placement | **Pill mark + inspector action.** The panel stays non-interactive `role="status"`. |

## The correction that shapes every stitch

**Applicability is computed unconditionally from the preset body and the
manifest. It is never gated on the schema hash.**

The tempting design — "the hash is the cheap screen, resolve only when it
trips" — is a silent data-loss bug once Accept exists: re-stamping makes the
hash match, the screen stops tripping, and a genuinely `dropped` entry becomes
permanently invisible. The acknowledgement would suppress the one signal that
says the show is broken.

Two independent facts, and only one of them is drift:

| | provenance | applicability |
|---|---|---|
| question | is the patch still the thing you authored against? | will every stored entry land as stored? |
| inputs | stored vs current fingerprints | preset body vs current manifest — **the reference plays no part** |
| dismissible? | yes, by re-stamping — that *is* the answer | no; true until the manifest or the preset changes |
| §8.1's words | — | "the authority" |

Because applicability never reads the reference, Accept **structurally cannot**
hide a broken parameter. That is the safeguard — not a form of words, and there
is a test in `4-accept-restamp` whose whole job is to stop a future optimiser
re-merging the two axes.

Ungating also catches a case the gated version misses: `PresetStore.save`
validates via `validate_document`, which never consults the manifest, so an
out-of-range stored entry is reachable today by hand-editing a preset JSON or
by a narrowing that happened between two saves. Hash-gating reports it clean.

## Second finding — `reference.schema` is stamped with one meaning and compared with another

- `presetReference()` (`show.js:691-697`) stamps `entry.schema` from
  `preset_catalog`, which is `document["schema"]` — *the schema the preset file
  was saved against* (`preset_store.list`, `preset_store.py:364`).
- `show_reference_warnings` compares it against
  `schema_fingerprint(current manifest)` — *the patch's current schema*.

Consequence today: pick a preset that is itself drifted (the dropdown already
shows it `*`) and the brand-new show message warns `schema_drift` the instant
it is authored, with nothing the operator can do about it.

Consequence for Accept: it would stamp a value the dropdown never produces, so
the next touch of the preset picker silently undoes the acknowledgement. This
is why `2-reference-schema-meaning` is a hard dependency of `4-accept-restamp`
rather than a nice-to-have.

Related, and why the re-stamp must be **server-side**: `preset_patches()`
(`server.py:1844`) returns only the fleet patch, the editor patch and device
pins. A show referencing anything else has no `preset_catalog` entry at all, so
the client physically cannot construct a reference. `show_warnings()` has no
such limit — it loads any manifest by name.

## Children

1. `1-resolution-authority` — the panel stops lying. Ships alone and resolves
   the reported symptom on its own. The headline stitch; do it first.
2. `2-reference-schema-meaning` — make the stamp and the comparison agree.
   Small, a standalone defect, and a hard prerequisite for `4`.
3. `3-drift-marks` — provenance becomes a `⚠` on the `PRE` pill and a block in
   the inspector. Needs `1` for the `severity` field it reads.
4. `4-accept-restamp` — the acknowledgement: a new show mutation, one undo
   entry, and the button. Needs `2` and `3`.
5. `5-missing-preset-warning` — **`.waiting` on Bob.** A step referencing a
   deleted or corrupt preset warns nothing at all today; playback fails into
   `log.warning` (`server.py:1760-1764`) and the step silently does nothing.
   Nearly free once `1` reads bodies, but it *adds* a warning during a
   simplification pass, so it is parked rather than bundled.

`1` and `2` are independent and can be worked in either order; `1` is first
because it is the reported bug. `.loom/queue` states the preference.

## Found, not scoped

**`show_target_warnings` fans out identically.** Five messages in one step
targeting `group:Missing` give five identical paragraphs — the same defect one
path over, from the same missing collapse. Deliberately not bundled here: it
widens the blast radius across a path that works today and has a passing
browser guard. If Bob wants it, it is a clean later stitch, and *then*
unifying every warning on `refs` becomes the simplification rather than a
second shape invented up front.

## Standing constraints for all five

* **R5 holds throughout.** Warnings stay derived, never stored, never blocking.
  The re-stamp writes `items[].messages[].reference` — authored show content,
  layer 4 of the ratified model — which is byte-identical to what re-selecting
  the same preset in the inspector dropdown already writes today
  (`show.js:1455` → `presetReference()` → `update_message`). No verdict, badge,
  dismissal flag or timestamp is ever persisted.
* **No new colour.** `cyan = modulation` is ratified and off-limits for fault
  states; `--amber` is already the preset warn ink. Follow `53/3`'s vocabulary:
  the mark **leads** the label so ellipsis can never eat the state.
* **Never edit `.pd` files.**
* Pre-tie: `tools/run-tests.sh fast` and the relevant `browser` journeys.
