# 3-drift-marks

`1-resolution-authority` filters provenance notices out of the warning panel.
This stitch gives them somewhere honest to live: a mark on the step's `PRE`
pill and a block in the inspector.

**Needs `1`** for the `severity` field and the per-message scalars it reads.
Read-only — the Accept action is `4`.

> Bob, 2026-08-03, on placement: pill mark + inspector action. The panel stays
> non-interactive.

## The mark on the pill

`messagePills` (`dashboard/static/js/show.js:375`). Build an index of
`severity === "notice"` warnings keyed on `message_uid` **once per render**, not
per pill.

Insert a dedicated span **between** the kind code and the label:

```html
<span class="show-pill-kind">PRE</span><span class="show-pill-mark" aria-hidden="true">⚠</span><span class="show-pill-label">…</span>
```

```css
.show-pill-mark { flex: none; color: var(--amber); }
```

beside `.show-pill-kind` in `dashboard/static/css/style.css:323`.

**Why between, and why `flex:none`.** `.show-pill-label` is the ellipsised
element (`style.css:324`) and `.show-message-pill` is `max-width:110px`, so a
`flex:none` span ahead of the label can never be truncated. This is exactly
`53-ui-niggles/3-preset-dropdown-menu`'s ratified rule — *the mark leads, so
ellipsis removes the name's tail and never its state* — applied to the same
class of problem on a different control. Do not append it.

**`⚠` and `--amber`, no new colour.** `53/3` already assigns `⚠` to schema
drift on the preset control, so reusing it here is consistent rather than a
second vocabulary. `--amber` is the ratified warn ink; `cyan = modulation` is
ratified and off-limits for fault states.

The explanation goes into the pill's existing `title` / `aria-label`, which
already carry a composed string — extend it, don't add a second attribute.

If a message carries both `patch_drift` and `schema_drift`, it gets **one**
mark. The pill is a glance, not a report; the inspector is where the two are
distinguished.

## The block in the inspector

`renderPresetBuilder` (`dashboard/static/js/show.js:~700`).

Add a provenance block naming **which** fingerprints differ — patch content,
parameter schema, or both — below the existing `selected?.drift` line.

**Keep that existing line.** It reports the preset file versus the current
manifest, a different fact from this message's authored reference; `2` rules on
why the two are separate. Two lines that look similar and mean different things
need their wording to do the work: say "this message was authored against…" for
provenance, and leave the existing "preset schema differs from the current
patch" alone.

Leave room for `4`'s Accept button here — mirror the shape and binding style of
the existing `#show-flatten-preset` button rather than inventing a new one.

## The discoverability trade-off, stated

With provenance out of the panel entirely, the **only** cue is the pill mark,
and reaching the explanation means selecting the message. That is the ruled
placement and this stitch implements it. If it proves too quiet in use, the
alternative on the table was one collapsed provenance line per patch in the
panel with an inline Accept — which would make a `role="status"` region
interactive for the first time. Record the outcome in `decisions.md` either
way so a later review has the observation rather than re-deriving the option.

## Verify

Extend `tests/verify_show_reference_foundation.py` — it already has the fixture
server and the three-attempt reload loop for the initial full-state race.

* the panel does **not** contain "has changed" for a drifted patch (this is
  `1`'s claim, re-asserted here at the surface Bob actually looks at)
* the `PRE` pill for a drifted message carries the mark, and a non-drifted
  message's pill does not
* the mark survives a long enough alias to ellipsise the label — fail this
  first if you can, since it is the whole reason the mark leads
* the inspector block names the differing fingerprints

Playwright gotchas that bite on this surface: (8) an element in a non-active
tab panel resolves but never goes visible — wait `state="attached"`; (17) scope
every selector to `#show-root`; (1) `inner_text` applies `text-transform`, so
lowercase before matching; (9) gather all bounding rects in a **single**
`page.evaluate` if you measure the pill, since per-element `scrollIntoView`
between measurements makes y-coordinates incomparable.

`tools/run-tests.sh fast` and `browser` green.
