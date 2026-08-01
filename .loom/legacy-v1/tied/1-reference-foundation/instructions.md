# 09/1-reference-foundation

The Show document model cannot yet carry what a preset message needs (first
review D8). Build the foundation before any `/preset/*` code exists.

## The three gaps, with evidence

1. **Reference metadata is discarded.** `show_model.clean_message` returns
   exactly `uid`, `alias`, `address`, `args`, `target`
   (`dashboard/show_model.py:98-122`); server updates accept only those
   fields (`dashboard/server.py:1307-1310`); copy/paste preserves the same
   four (`dashboard/static/js/show.js:878-893`). Extend the model with an
   explicit, validated reference payload — a message kind/reference member
   that survives load, edit, copy/paste, move, duplicate, undo, and
   persistence. Design it as a general mechanism (a message that references
   composition content), not a preset special case; the preset child fills
   it in.
2. **Group targets are ids, not names.** Targets accept only `all`, decimal
   seat ids, and `g<integer>` (`show_model.py:27-30, 59-75`); the picker
   stores `g<id>` (`show.js:248-275`). The ratified entity model says
   portable shows target groups **by name**. Add named-group targets with
   resolution at the dashboard boundary (the wire still sees `g<id>`), and
   non-blocking warnings for a missing or ambiguous name at authoring time
   and at load.
3. **The name invariant does not exist.** Nothing enforces non-empty or
   unique group names (`dashboard/state.py:491-514, 549-588`), and without
   it "first match" makes a portable show nondeterministic. Per Bob's Q3
   ruling: names become **non-empty and unique per venue** — enforce on
   create/rename/load, with a **one-time adoption fix** for existing venues
   (deterministically rename blanks/duplicates, e.g. `group-<id>` /
   `name-2`, surfaced to the operator, not silent).

## Verify and tie

Model-level fast tests: reference payload round-trips through
load/save/clean/copy/undo; named target resolution incl. missing/ambiguous
warnings; invariant enforcement + adoption fix on a fixture venue with
blank/duplicate names. A browser journey for the picker storing/rendering
names. `tools/run-tests.sh fast` and `browser` green. Decisions (payload
shape, adoption renaming rule) in `decisions.md`.
