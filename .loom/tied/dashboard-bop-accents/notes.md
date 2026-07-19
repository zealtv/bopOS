# dashboard-bop-accents notes — 2026-07-20

Bob's brief (2026-07-20 session): keep the dark interface, draw accents from
the bop aesthetic (`bop.casio~`: lavender/periwinkle panels, ice-cyan value
fields, cream toggle, yellow warning). Design pass by an Opus UI designer
(`proposal.md`); safe-core implementation delegated to GPT 5.6 Sol (codex).

Landed: the token block (periwinkle `--accent`, lavender `--accent-bright`,
`--accent-soft`, ice `--accent-cyan`/`--accent-cyan-soft`, cream
`--accent-warm`, harmonised `--sim`) as dark/light/`data-theme` triples in
both stylesheets, plus the safe-core hex migration: focus-visible outlines,
selected/active states (tabs, rows, chips, focused inspector), spatial point
handles, sim-device indicators, Seat input focus. Untouched by design:
`--bg/--panel/--line/--text/--dim`, green/amber/red semantics, `--auto`,
Okabe-Ito group swatches, the 8 Show pill sets, slider/toggle accents.

Open questions for Bob remain in `proposal.md` §6 (notably: cyan slider
fills + cream toggle `accent-color` — the signature move — was deliberately
NOT applied as it is listed there; apply after Bob's look).

Verification (orchestrator): `verify_bop_accents.py` 9/9 PASS (both pages,
token presence dark+light, focus outline resolves to `--accent-bright`,
selected states resolve to `--accent`, no console errors; needed the house
`#ws-status` `state="attached"` fix). Tied a3 take-over regression green.
`git diff --check` clean.
