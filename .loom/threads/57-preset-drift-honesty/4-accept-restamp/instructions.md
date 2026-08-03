# 4-accept-restamp

The answer to Bob's "what would be a suitable way to dismiss this". Not an
`[x]` that hides the panel and returns on reload — a **re-stamp** that records
the show as authored against the current patch.

**Needs `2`** (or the acknowledgement is silently undone by the next touch of
the preset dropdown) **and `3`** (which owns the inspector block this button
sits in).

> Bob, 2026-08-03: re-stamp the reference — a persisted acknowledgement, one
> undo entry.

## The mutation

`dashboard/show_model.py`, sibling of `flatten_preset_message` (`:830`):

```python
def restamp_references(show, patch, reference):
    """Re-author every preset reference for `patch` against `reference`.

    Returns (new_show, [message_uid, ...], error). The reference is authored
    content, so this is an ordinary edit — the same field the inspector's
    preset picker already writes — and it re-runs `clean_message` so an
    invalid stamp is refused rather than persisted.
    """
```

**Scope: every message for that patch in the show, in one mutation.** The cause
is per-patch, the operator's judgement is per-patch, and re-stamping one of N
leaves N−1 marks that mean the same thing. `apply_show_mutation` appends
exactly one deepcopy to `self.show_undo` (`server.py:1480`), so the existing
`undo_show` reverts the whole acknowledgement as one step. Messages for other
patches are untouched.

Two messages naming the same patch can legitimately hold **different** stored
fingerprints — one authored before an edit, one after — so this is a re-stamp,
not an equality check, and it is idempotent on the already-current ones.

Return an error string when the show contains no reference for `patch`.
Otherwise `new_show == self.show` and `apply_show_mutation` returns silently at
`:1473`, which is indistinguishable from success.

## The server side

New branch beside `flatten_preset_message` (`dashboard/server.py:1388`):

```python
elif kind == "restamp_references":
    await self.restamp_show_references(ws, data.get("patch"))

async def restamp_show_references(self, ws, patch):
    try:
        fingerprint = self._current_patch_fingerprint(patch)   # server.py:1833
        manifest = self.live_control_manifest(patch)
        if manifest is None:
            raise preset_store.PresetStoreError(
                f'patch "{patch}" has no readable manifest')
        schema = preset_store.schema_fingerprint(manifest)
    except preset_store.PresetStoreError as error:
        await self.ws_error(ws, str(error))
        return
    await self.apply_show_mutation(
        ws, show_model.restamp_references, patch,
        {"content": {"name": patch, "fingerprint": fingerprint}, "schema": schema})
```

Reuse `_current_patch_fingerprint` — it already does the guarded
not-installed / not-a-symlink work and raises the right error type. Do not
duplicate the `os.path` checks from `show_warnings`.

**Server-side, not client-side**, because `preset_patches()`
(`server.py:1844`) returns only the fleet patch, the editor patch and device
pins — a show referencing anything else has no `preset_catalog` entry and the
client cannot construct a reference for it at all.

Wire verb `restamp_references`, payload `{"patch": "<name>"}`. Named for what
it does to the document, matching `flatten_preset_message`'s convention, not
for what the operator feels.

## The button

`Accept`, in the inspector's preset builder block that `3` builds, beside the
existing `#show-flatten-preset`. Title: *"Record this show as authored against
the current `<patch>`"*.

It is a facilitator-facing word and Bob ratified `Accept` on 2026-08-03. If
implementation makes a different word clearly better, that is a fresh ruling,
not an implementer's call.

## The safeguard is structural — assert it, don't argue it

Because applicability never reads the reference (`1`), re-stamping **cannot**
clear a `preset_dropped` or `preset_clamped` warning. It clears only the
provenance mark. So Accept cannot imply the dropped entries were fixed, and the
panel line naming them survives it.

That is the payoff for splitting the two axes and it must exist as a test, not
as a paragraph:

> **acknowledgement-does-not-hide** — re-stamp a show whose preset has a
> dropped entry; `show_reference_warnings` still returns `preset_dropped` and
> no longer returns `patch_drift`.

This is the assertion that stops a future optimiser gating resolution on the
schema hash "since we already have it". Say so in the test's docstring.

## R5

The mutation's output is byte-identical to what re-selecting the same preset in
the inspector dropdown already produces today (`show.js:1455` →
`presetReference()` → `update_message` with a `reference` patch). It writes
`items[].messages[].reference` — authored show content, layer 4 of the ratified
model, carrying exactly the `{name, fingerprint}` R2 requires. It stores no
verdict, no badge, no dismissal flag and no timestamp; every warning stays
recomputed from disk on each broadcast and none of them blocks anything. R5
holds.

## Verify

`tests/test_show_model.py`:

* `restamp_references` rewrites every message for the named patch, leaves a
  second patch's messages **byte-identical**, refuses an invalid reference
  through `clean_message`, and returns an error when the patch is not
  referenced
* the acknowledgement-does-not-hide pin above

Browser — extend `tests/verify_show_reference_foundation.py`: clicking `Accept`
rewrites `reference` in the **saved show JSON on disk** and the pill mark
disappears; `undo` restores both in one step.

Gotchas: (16) + (22) — wait on the binding of the **exact host-scoped element
about to be clicked**, not on an ancestor bound in the same sweep, and the wait
and the click must name the same element; (8) attach-wait inside a non-active
tab panel; (17) scope every selector to `#show-root`; (3) one type-aware
`page.on("dialog")` handler if a confirm is added — two handlers race.

`tools/run-tests.sh fast` and `browser` green.
