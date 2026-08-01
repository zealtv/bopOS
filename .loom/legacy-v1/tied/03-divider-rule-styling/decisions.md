# Decisions — divider rule styling (stitch 03)

## Orchestrator ruling — the superseded tied assertion (2026-07-21)

The delegate correctly stopped rather than edit a tied suite.
`.loom/tied/04-named-section-dividers/verify_named_dividers.py` asserted
`hasGradient` on the unnamed divider row — i.e. it pinned exactly the thing
Bob asked to be removed. A tied verifier is a guard, not a contract that
outranks a later ruling from Bob, and leaving it permanently red would poison
every future session's guard run.

**Ruled:** the orchestrator inverted that one assertion in place, with an
inline comment naming this stitch as the supersession. Nothing else in that
suite was touched; it re-runs at `0 failure(s)`. The guard was re-run from a
copy inside this stitch directory (the harness declines to execute scripts
under `.loom/tied/`), which also avoided regenerating the tied screenshots.


Orchestrator rulings, 2026-07-21, from Bob's two complaints in
`instructions.md`. Checked: `.loom/tied/01-layout-review/wireframes.html` has
no divider-row drawing (it only shows the edit bar's `＋ Divider` button), and
the `2026-07-20-show-chrome-density-braindump` lore item carries only the
prose "the divider styling with lines either side of the name". So there is no
pixel reference to match — these values are proposals derived from the prose,
and they are one-line retunable if Bob wants them different.

## Named divider

Current: `.show-tab .show-divider-named .show-divider-line{flex:1 1 auto;
min-width:8px;…}` — the rules take all leftover width, so they run full bleed
to both edges of the row. Bob wants "just two short lines either side of the
divider title".

**Ruled:** the rules become fixed-length, `flex:0 0 28px`, and the row centres
its contents (`justify-content:center`, which `.show-divider-row` already
sets — the named variant must not re-override it). The name keeps its
`flex:0 1 auto` + ellipsis so a long name still truncates rather than pushing
the rules off-row; when it truncates, the rules stay 28px and stay attached to
the name.

28px is the proposal: long enough to read as a rule, short enough that the
name is clearly the subject. Tune in one place if Bob disagrees.

## Unnamed divider

Current: `.show-divider-row{height:10px;…;background:linear-gradient(90deg,
transparent,var(--strong-line) 16%,var(--strong-line) 84%,transparent)}` —
a fading rule filling a 10px-tall (later 18px) row. Bob: "get rid of that
gradient… It can just be a blank line."

**Ruled:** no gradient and no background on the row; instead a single flat 1px
rule in `var(--strong-line)`, centred vertically, drawn as an absolutely
positioned `::after` inside the (already `position:relative`) row so it does
not fight the flex layout or the drag handle. The rule spans the row's width
inset past the grab handle — it must not run under the handle. Row height and
the grab handle are unchanged.

## Held constant

- Both variants stay focusable rows with their existing `aria-label`s, drag
  behaviour, focus outline, and drop-target shadows.
- The named divider's name stays centred and stays click-to-edit (the unified
  title pattern Bob ruled 2026-07-21 — see the comment at the top of
  `show.js`).
- CSS only. Light and dark themes both checked; `--strong-line` already
  resolves per theme, so no new colour tokens.
