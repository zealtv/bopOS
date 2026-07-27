# 2-kind-grammar

The declaration break, with **no wire change**. Authority: the tied
`1-event-plane-design` (proposal.md §1, decisions.md). Ratified by Bob
2026-07-28.

Replace `type: "i"|"f"|"s"` plus inferred enums with an explicit `kind`:

| `kind` | wire | fields |
|---|---|---|
| `float` | float | `min`, `max`, `default` |
| `int` | int | `min`, `max`, `default` |
| `toggle` | int `0`/`1` | `default`; `min`/`max` **derived**, authoring them is invalid |
| `enum` | int index | `options`, `default`; `min`/`max` derived `0`…`n-1` (as shipped) |
| `text` | string | `default` (optional) |

`type` is **removed and rejected loudly**, following the `role` precedent —
a silently-ignored old key is how manifests drift. Nothing in production, so
no compatibility path.

Scope:

- `python/manifest.py` — `PARAM_TYPES` → a `PARAM_KINDS` table; move the
  `options` block under `kind == "enum"`; give `toggle` the same derived
  `min`/`max` treatment enum already has. **Fix the silent-failure trap while
  here:** today a `text`/`s` param carrying a numeric-only `default` makes the
  whole manifest fail to load with no message (CLAUDE.md Playwright gotcha 7)
  — make it a loud, named error.
- `dashboard/show_model.py` — **stop importing `PARAM_TYPES` from
  `manifest.py`** (line 43) and own an `i/f/s` arg-tag set locally. Message
  args are wire types; declarations are control kinds. The comment at line 36
  says the reuse prevents drift; after this break the coupling *is* the drift
  risk, since the two sets now have different jobs. Keep the show-document
  arg grammar byte-identical — this is a decoupling, not a format change.
- The patch editor's declaration UI — a kind `<select>` replacing the type
  select and the inferred-enum handling.
- `dashboard/static/js/control-surface.js` — the three `declaration.type ===
  "s"` sites (lines 64, 101, 282) read `kind === "text"` instead. Behaviour
  unchanged here: text params stay out of aggregation and automation, and
  keep today's plain `<input type="text">`. The **styled** text control is
  child `6`, deliberately not this stitch.
- Every fixture manifest under `tests/` and every `patches/*/bopos.patch.json`.

Not in scope: events (child `3`), `/cue` deletion (child `4`), any wire
change at all.

Verify: `tools/run-tests.sh fast` plus the manifest suite; a rejected `type`
key and a rejected authored `toggle` min/max are both worth explicit
assertions, as is the newly-loud text-default error. Browser suite green
proves the control surface still renders every kind.
