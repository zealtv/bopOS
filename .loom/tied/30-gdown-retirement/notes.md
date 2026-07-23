# 30-gdown-retirement — done

## gdown removed
`python/requirements.txt` — deleted `gdown` and its `# sample downloading`
comment (was line 14-15). gdown appeared **only** there — not imported by any
`python/*.py`, not called by any `bash/` script. Assets flow through
`python/fetcher.py` (`_http_fetch`). `requirements-laptop.txt` and
`dashboard/requirements.txt` never listed it.

## Bash staleness sweep — no removals
Full script-by-script usage classification in `bash-staleness-report.md`
(codex read-only investigation, cross-checked). Result: **every** bash script is
still on a live path — boot (`start.sh`/`rc.local`), the OSC lifecycle in
`bopos.py` (`start-engine.sh`/`stop-engine.sh`/`pull_active_patch.sh`),
provisioning/update (`provision.sh`/`install-power-control.sh`/`update.sh`,
documented in `docs/INSTALL.md`), or legit manual helpers (`checkout.sh`,
`restart.sh`, `stop.sh`). Nothing orphaned; nothing removed. No lingering
`gdown`/`getsamples.sh`/`SAMPLEPACKSURL` references anywhere in `bash/`.

## LEGACY_SAMPLEPACKS (item 3) — retained, deliberately
`bash/start-engine.sh:62-69` still removes any residual
`$PATCH_PATH/bop/samplepacks` symlink + empty `assets/samplepacks` dir. This is
the last vestige of the retired compat path — but it only *cleans up* old state,
it doesn't recreate it (the retirement itself is done, stage-5). It's a no-op on
clean/fresh nodes and harmless insurance on any node updated from the old era.
Kept per the stitch's "confirm, don't re-break it." **Recommendation:** it can
retire in a future pass once Bob is confident no fleet node still carries the old
symlink — low priority, not worth the (small) risk now.

## Verify
No scripts changed → engine start/stop stack untouched. requirements.txt change
is a pure line deletion of an unused dep; nothing imports gdown (grep-confirmed).
