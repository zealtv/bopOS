# Distil

This is the local brief for distillation in this glean.

Distil is the act of shaping the carry-forward corpus — both digesting new
material from `in/` and curating `findings/` over time. The two rhythms
share one posture; they differ in what triggers them and which verbs they
use. Edit this file freely; the protocol doesn't care what you write here.

## Posture

Glean stays small, legible, and revisable. Keep it that way.

- Do not force synthesis.
- Do not mistake compression for understanding.
- Do not create a new finding when revising an existing one is enough.
- Do not let `findings/` grow into a heap.
- Do not carry forward material that does not improve judgment.

A heap of findings is just another inbox. The value of memory comes from the
discipline of distillation, not the volume of capture.

## Per-item distillation

When an item arrives in `in/`, read it and choose one of three outcomes:

1. **Revise** an existing finding — edit `findings/<id>.md`.
2. **Create** a new finding — write `findings/<new-id>.md` directly.
3. **Nothing earned** — the material doesn't merit carry-forward.

In all three cases, close the inbox item:

```
glean.sh complete <in-id>      # in/<id> → out/<id>
```

`out/` is the audit residue: every inbox item that was considered passes
through it, regardless of whether a finding was produced. No reason needed.
`out/` is swept on retention.

The inbox item leaves `in/` only via `complete`. Items remaining in `in/`
are still awaiting distillation.

## Curation, in the same pass

Curation is not a separate rhythm — it rides on per-item distillation. The
moments below all happen *while* working an inbox item, so act on what you
notice in the same pass:

- **Before creating** a new finding, search `findings/` for similar ones.
  If one already covers the ground, revise it instead.
- **While revising**, if the finding has drifted to cover two ideas, split
  it. If it now overlaps with another, merge them and `drop` the loser.
- **When writing or revising**, link related findings under
  `## Associations`.

These moves are file edits plus `glean.sh drop`. Don't defer them — the
in/ item is the trigger, and you only have this brief in context now.

## Corpus review

A deliberate "look across `findings/` as a whole" pass only happens when a
human asks for it — the agent has no rhythm of its own to schedule one. On
review, read across `findings/` and apply the same merge / split / link /
retire moves at scale.

`drop` retires a *finding* into `dropped/` with a reason file. `dropped/` is
the reflection drawer for retired ideas — durable and not swept. Read it by
hand when you want to remember what was let go and why.

## What a finding looks like

A finding is one markdown file at `findings/<id>.md`:

- **Title** — first line, an H1 (`# Some claim`). Required.
- **Description** — first non-empty line after the title. One sentence. It is
  the **recall cue**: surfaces in `INDEX.md`, where an agent reads it to decide
  relevance. Write it the way the finding would come up, not as an abstract.
- **Body** — free markdown. Common sections (all optional):
  - `## Why` — motivation, source, the experience that earned this finding.
  - `## Triggers` — a short list of literals you'd lose to paraphrase: product
    names, error strings, identifiers, user shorthand aliases the description
    wouldn't contain (`roo burger`, `model exited 127`, `DEMO_KEY`). Not a
    keyword dump, not a restatement of the title. `recall` matches them on
    **whole words**, so write the bare word a real message contains — one-word
    aliases like `chai`, `tempeh` are fine. `fetch` searches them loosely too.
  - `## Associations` — wikilinks to related findings: `- [[other-id]]`.
  - `## Context` — examples, references, longer notes.

Run `glean.sh index` after writing or revising a finding to refresh
`findings/INDEX.md`.

## Local notes

(Anything host-specific goes here.)
