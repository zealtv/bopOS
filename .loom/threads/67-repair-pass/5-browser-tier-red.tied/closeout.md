# Browser gate close-out — 2026-10-03

The complete browser tier is green: **23/23 living journeys passed**, exit 0.
The obsolete preset journeys were removed with their feature in `63d3967`;
no remaining journey was skipped or softened for this close-out.

The first full run found one Show generator assertion reading an empty CSS
grid (`['']`) immediately after a phase write rebuilds the inspector. The
focused retry reproduced it. Resolve the currently connected row and read its
computed style in one browser call, with a bounded wait for a nonempty result.
The original exact 58px / slider / 18px width assertion is unchanged. The
focused corrected journey and then the complete tier passed. No product
implementation changed for this repair.

Evidence:

- `closeout-browser-initial.log`: first full run, 22 passes and the empty-grid
  assertion failure; `closeout-show-retry.log` reproduces it independently.
- `closeout-show-fixed.log`: focused corrected journey passed, no page errors.
- `closeout-browser.log`: complete final tier, 23 passes, exit 0.
- `closeout-fast.log`: all 343 browser-free tests passed. The installed commit
  hook runs the fast tier again before allowing the commit.

Requested fixups are included in the same commit: tie and archive the completed
`65-remove-presets` goal using Loom's lifecycle command; remove leftover blank
lines and redundant `any(...)` condition parentheses in `python/identity.py`.
The goal's child records are retained whole under `.loom/tied/65-remove-presets/`.

Whitespace check passed. Existing Show edits, `.codex/` and `.obsidian/` are
outside this commit. This is software/simfleet verification; no hardware claim.
