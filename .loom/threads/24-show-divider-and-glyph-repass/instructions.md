# 24-show-divider-and-glyph-repass

Bob's reaction (2026-07-21) to the just-tied `19-show-chrome-fixes`, seen
live. Two corrections, both reversing a call the autopilot session made:

1. The unnamed divider's flat rule should not span the row. It should be a
   **short rule, centred where the alias would go** — so a named and an
   unnamed divider read as the same row with the name present or absent.
2. The inline-SVG "add" glyphs are **messy** — remove them. Step goes back to
   a plain `+`, divider becomes `/`. Bob: "find icons for those symbols that
   match the existing style" — i.e. the plain-character glyph vocabulary the
   edit bar already uses (`⧉` duplicate, `✕` delete), not drawn icons.

Note what this supersedes: `19/02-step-and-divider-icons` argued that a bare
`+` beside a bare `—` read as an opposed add/remove pair. `/` is not the
opposite of `+`, so the original defect does not return — but say so in the
stitch rather than silently dropping the reasoning.

Both stitches will invalidate assertions in the tied `19/02` and `19/03`
guards. Those guards are **superseded, not authoritative** — repair them in
place with an inline comment naming this thread, per the ruling recorded in
`.loom/tied/03-divider-rule-styling/decisions.md`.

Relevant code: `dashboard/static/js/show.js`, `dashboard/static/css/style.css`.
