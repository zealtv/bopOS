# 6-group-name-rule

Force addressable group names, per `2-dashboard-osc-input.tied/proposal.md` §2 (Bob, 2026-10-26: *"force
compatible groupnames upfront"*):

- lowercase `a-z 0-9 _ -`, 1–32 characters;
- not `all`, `bop`, all digits, `g<digits>`, or `os` `io` `sync` `e` `p`.

The group editor enforces it. Existing names convert on load (lowercase,
other characters to `_`, suffix on clash) through `adopt_group_names` and
its notice. Independent of the event work.
