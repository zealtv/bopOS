# Verification — unnamed divider short rule (24/01)

## Change

`dashboard/static/css/style.css`, one declaration block:

```
-.show-tab .show-divider-row:not(.show-divider-named)::after{…left:36px;right:8px;top:50%;height:1px;transform:translateY(-50%);…}
+.show-tab .show-divider-row:not(.show-divider-named)::after{…left:50%;top:50%;width:28px;height:1px;transform:translate(-50%,-50%);…}
```

**Length chosen: 28px** — identical to the named divider's two flanking
rules, so every divider mark in the Show tab is one length and the two states
read as the same row with the name present or absent. The rule centres on the
row's true centre (`left:50%` of the row), which is where the named row puts
its name — the named row already takes its grab handle out of flow for
exactly that reason, so the two centres line up.

No gradient (the `19/03` ruling stands), handle untouched, rule stays
`pointer-events:none`.

## Verifier

`verify_unnamed_divider_rule.py` in this directory, derived from
`.loom/tied/03-divider-rule-styling/verify_divider_rules.py`. The unnamed-row
geometry probe gained `afterWidth` and a `ruleCentre` that resolves a
percentage `left` against the row box; the two full-width-span assertions
were replaced with width/centring/handle-clearance assertions.

```
$ ~/.venvs/bopos/bin/python .loom/threads/24-show-divider-and-glyph-repass/01-unnamed-divider-short-rule.stitching/verify_unnamed_divider_rule.py
…
[PASS] unnamed divider rule is exactly 28px wide
[PASS] unnamed divider rule is far narrower than the row
[PASS] unnamed divider rule is centred in the row
[PASS] unnamed divider rule does not overlap the grab handle
[PASS] unnamed divider keeps its row aria-label
[PASS] unnamed divider keeps its drag-handle aria-label
[PASS] focused divider row keeps a visible outline
[PASS] committed divider name shows on the row
[PASS] renamed divider keeps 28px rules
[PASS] renamed divider row aria-label follows the new name
[PASS] no page-level horizontal overflow at 1280px
[PASS] browser emitted no page errors

0 failure(s)
```

Screenshots retained here (`divider-rows-*`, `dividers-1280-*`, light and
dark) — the row crop shows the unnamed rule sitting in the alias slot above a
named divider for comparison.

## Superseded tied assertion (repaired in place)

`.loom/tied/03-divider-rule-styling/verify_divider_rules.py` asserted
`unnamed divider rule spans most of the row width` — exactly what Bob asked
to be changed. Inverted to `unnamed divider rule is short and centred, not a
full-width span`, with an inline comment naming this stitch, per the ruling
in that stitch's `decisions.md`. Re-run from a copy (the harness declines to
execute scripts under `.loom/tied/`): **0 failure(s)**.
