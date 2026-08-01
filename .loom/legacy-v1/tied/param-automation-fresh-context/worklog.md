# Parameter-automation fresh-context worklog

## Outcome

- Audited the live Loom: no claims; Show polish is tied; the next accepted
  stitch is `automation-2-show-builder-gui`.
- Corrected the parent `16-param-automation` instructions, which still claimed
  the now-ratified grammar was unratified. They now identify the ratified lore
  and contract, automation-0/1 as tied, and the remaining 2→3→4 ordering.
- Added audited starting points and compiler constraints to automation-2's own
  instructions, including the actual short-loop behavior, numeric/string type
  boundary, round-trip/raw fallback requirement, and current Show verifier
  runway.
- Clarified that automation-4's prohibition concerns the not-yet-ratified
  waveform UX proposal, not the already-ratified §3.2 generator design.
- Added the newest handoff,
  `.notes/handoff-2026-07-19-param-automation-next.md`, with the exact claim
  command, settled grammar, landed commits/code, GUI seams, verification
  commands, guardrails, and post-automation-2 ordering.
- Did not claim automation-2 and did not touch `.pd` or Bob's untracked
  `dashboard/shows/`.

## Verification

- `.loom/tied/automation-1-engine-and-parity/verify_param_automation.py`:
  32/32 passed on current HEAD (sandbox used its documented in-process OSC
  fallback after loopback UDP was unavailable).
- Every path and verifier named in the handoff exists.
- Terminology sweep confirms the parent/automation-2 instructions and
  `CLAUDE.md` agree that automation-2 is next; the only remaining unratified
  wording is the intentional waveform UX gate and the general repository
  decision-gate rule.
- `git diff --check` passed.

Documentation/orientation-only stitch. No browser, hardware, audio, touch, or
audible PD verification was required.
