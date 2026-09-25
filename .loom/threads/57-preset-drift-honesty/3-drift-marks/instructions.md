# 3-drift-marks

**Status:** blocked on `1-resolution-authority`
**Goal:** give the provenance notices `1` filters out an honest home — a ⚠ on
the step's `PRE` pill and a block in the inspector. Read-only; Accept is `4`.

## Pill mark

In `messagePills` (`show.js`), index `severity === "notice"` warnings by
`message_uid` once per render. Insert the mark **between** kind and label:

```html
<span class="show-pill-kind">PRE</span><span class="show-pill-mark" aria-hidden="true">⚠</span><span class="show-pill-label">…</span>
```

```css
.show-pill-mark { flex: none; color: var(--amber); }   /* beside .show-pill-kind in style.css */
```

- Leading + `flex:none` so the 110px pill's ellipsis eats the label, never the
  mark (same rule as `53/3`).
- One mark even if both `patch_drift` and `schema_drift` apply.
- Extend the pill's existing `title` / `aria-label`; don't add attributes.

## Inspector block

In `renderPresetBuilder` (`show.js`), below the existing `selected?.drift` line,
add a block saying **which** fingerprints differ (patch content, schema, or
both), worded "this message was authored against…".

Keep the existing "preset schema differs from the current patch" line — it's a
different fact (see `2`). Leave room for `4`'s Accept button, styled like
`#show-flatten-preset`.

## Trade-off to record

With provenance off the panel, the pill mark is the only cue. If that proves too
quiet, the alternative is one collapsed line per patch on the panel with inline
Accept (making the status region interactive). Note the outcome in
`decisions.md` either way.

## Done when

Extend `tests/verify_show_reference_foundation.py`:

- panel does **not** contain "has changed" for a drifted patch;
- drifted message's pill has the mark, a clean one doesn't;
- the mark survives an alias long enough to ellipsise (try to fail this first);
- the inspector block names the differing fingerprints.

Playwright gotchas 1, 8, 9, 17 apply (scope to `#show-root`).
`tools/run-tests.sh fast` + `browser` green.
