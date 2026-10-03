# 72-test-gate

**Status:** ready · do first
**Goal:** a broken test can't go unnoticed for weeks again. The fast tier runs
before every commit; the browser tier runs on a regular, visible cadence.

Why: there's no CI, and the browser tier was red from before 2026-09-03 until
the October review found it (`lore:2026-10-03-bopos-code-review-2026-10`). The refactors in `69` are only safe if
the tests are trustworthy.

## Do

- **Fast tier on every commit:** a versioned pre-commit hook (e.g.
  `tools/hooks/pre-commit` + a one-line install step in the docs and
  `install-dashboard.sh`) running `tools/run-tests.sh fast` (~3 s). Agents
  commit too — make sure the hook runs for them, and that a failure is loud.
- **Browser tier on a cadence:** the repo is on GitHub (`zealtv/bopOS`). Weigh
  a GitHub Actions workflow (fast tier on push; browser tier nightly or on PR,
  Playwright + Chromium) against a local scheduled run. Note that some
  journeys depend on local `patches/` (gitignored) — make CI self-contained or
  say which journeys can't run there.
- Say in `docs/VERIFICATION.md` and `glean:verification` what runs when.

## Done when

- A commit with a failing fast test is refused (or flagged loudly) locally.
- The browser tier runs without anyone remembering to, and its result is
  visible. It goes green once `67-repair-pass/5-browser-tier-red` lands.
