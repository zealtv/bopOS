# Facilitator view — design proposal

Design proposal for the iPad facilitator view (`/facilitator`), written at the
`facilitator-view` decision gate: the pre-contract dashboard design sketched
per-device volume cards, master volume, Silence All, Start All, and presets;
the contract era made params manifest-declared, so the proposal's central
question is which declared param a volume card drives (proposed: a
`"role": "volume"` manifest marker with `gain` fallback). Also proposes
VCA-style proportional master, mute-based Silence All, aloha-based sound
check, a partial-state preset model with `master`, and a facilitator scope
guard (no admin verbs, no assignment). Six questions for Bob, each with a
recommendation and rejected alternatives.

## Source

Autopilot session 2026-07-08, stitch
`dashboard/dashboard-2-spatial-facilitator/facilitator-view` (marked
`.waiting` on this ratification). Sibling `spatial-map` was built and tied
the same day.

## Outcome

Awaiting Bob's ratification. Read `content/proposal.md`.

## Tags

bopos, dashboard, facilitator, design-proposal, decision-gate
