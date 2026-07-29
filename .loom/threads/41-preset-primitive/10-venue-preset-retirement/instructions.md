# 10-venue-preset-retirement

Remove the old venue-preset system. **Last stitch — needs 04–09 all tied**,
so nothing references a retired path mid-flight.

Authority: proposal §8, Bob's entity-review ruling (venue presets retire when
41 lands; **the store is empty, no migration**).

## Scope

- Delete the `presets` key from installation state and its rename/renumber
  handling in `dashboard/state.py`.
- Remove the `save_preset` / `load_preset` websocket commands and
  `preset_scope_seats` (`dashboard/server.py:821-853, ~1526`).
- Remove the facilitator preset shelf (the standalone facilitator ends this
  thread with **no** preset affordance at all, per Q4 — 07 already removed
  the shared row from that host).
- Sweep tests, fixtures, and docs for the retired commands/state; update the
  operator docs that described venue presets. `grep -rn "save_preset\|load_preset\|preset_scope_seats"`
  across `python/ dashboard/ tools/ tests/ docs/` must come back empty (bar
  historical `.loom/tied/` evidence, which is preserved as-is and never
  swept).
- Existing persisted state files may still carry a `presets` key — loading
  one must not crash; drop the key silently on next save.

## Verify and tie

`tools/run-tests.sh all` green (the full suite — this is the thread's last
stitch and the pre-tie check for the whole replacement). Confirm in the tie
note which behaviours remain hardware-gated (nothing should — this stitch is
pure removal). Then tie this stitch **and assess the thread parent**: with
04–10 tied, `41-preset-primitive` itself is ready to tie; update CLAUDE.md's
queue section and the thread `instructions.md` to record completion, per
house practice.
