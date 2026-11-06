# Working notes for agents

bopOS is a Raspberry Pi + Pure Data framework for networked multi-device sound
installations: nodes run an audio engine, a dashboard on the host orchestrates
them over OSC. `README.md` is the system overview; `docs/OSC-CONTRACT.md` is
the ratified wire contract.

## The primitives

This repository's shape is held by the dotdirs at its root. Each is a
self-contained file-based protocol bundling its own script and data; read its
README before working with one.

- 🔮 glean — `.glean/` — memory: small, current, revisable guidance.
- 🪡 loom — `.loom/` — finite work: threads, stitches, dependencies, queue order.
- 🐉 lore — `.lore/` — the library: complete, dated records, kept whole.
- 🪺 nestlings — `.nest/` — arrivals: inbox, claimed, completed.

### Start here

1. Read `.glean/findings/INDEX.md` — the house rules and current guidance live
   there. Fetch a body when it's relevant (`./.glean/glean.sh fetch <terms>`).
2. Run `./.loom/loom.sh status`. The loom alone owns open work, blockers and
   queue order. Claim a stitch before working it; tie it only once verified.
   Existing stitches don't widen the user's current request.
3. Read `.nest/tend.md` and inspect `.nest/in/` for arrivals waiting to be
   tended.
4. Consult `.lore/INDEX.md` only when complete evidence or history is needed.
   Lore is dark by default.

### Ownership

- `.glean/` holds what is true *now*. Revise a finding when it changes; retire
  it with `glean.sh drop` when it stops earning its place.
- `.loom/` holds what is still to be done. Working artifacts (measurements,
  decisions, verification) live in the stitch directory.
- `.lore/` holds what happened. Never edit an item; a new edition is a new
  capture.
- `.nest/` holds what just arrived. Route it, then hatch a receipt.

One arrival may earn several routes — evidence in lore, a constraint in glean,
a stitch on the loom. Those are different consequences of one thing, not
competing copies of it.

## Memory lives in Glean

Glean is this repository's only memory. Don't keep project knowledge in a runtime's private memory store (for example Claude Code's per-project `~/.claude/projects/.../memory/`), a `memory/` directory or a handoff note: they drift from the repository and travel with one tool on one machine. When you learn something worth carrying into the next session, it becomes a finding in `.glean/findings/`. Claude Code's auto memory is switched off here in `.claude/settings.json` (`autoMemoryEnabled: false`).

`CLAUDE.md` is a symlink to this file, so every agent runtime reads the same notes.
