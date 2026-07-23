# 30-gdown-retirement

**CLEANUP / staleness pass.** Remove the now-stale `gdown` dependency and sweep
`bash/` for scripts left over from the old sample-download era.

Bob, 2026-07-23: "I noticed when setting up the Pi that the gdown Python
requirement is still there and I think that's now stale given the way we have the
asset packs set up. So I'd like to remove gdown and do a staleness pass — that
might involve removing a script or scanning the bash scripts folder for
staleness."

## What's confirmed stale

- `python/requirements.txt:15` — `gdown` under `# sample downloading`. Nothing
  in `bash/` or `python/*.py` invokes it; assets now flow through
  `python/fetcher.py` (`_http_fetch`). The old `getsamples.sh` /
  `SAMPLEPACKSURL` / `gdown --fuzzy` pipeline is already gone. `gdown` only
  survives in `.lore/` history (leave lore untouched — it's a dated record).

## Do

1. Remove `gdown` (and its comment) from `python/requirements.txt`. Check
   `python/requirements-laptop.txt` and `dashboard/requirements.txt` too.
2. Staleness sweep of `bash/`: `checkout.sh install-power-control.sh provision.sh
   pull_active_patch.sh rc.local restart.sh start-engine.sh start.sh
   stop-engine.sh stop.sh update.sh`. For each, confirm it's still on a live
   path (referenced by rc.local/systemd, the update/convergence flow, the engine
   start/stop stack, or docs). Flag anything orphaned; remove only what's clearly
   dead, and note removals + reasoning in the stitch.
3. Note the vestigial `LEGACY_SAMPLEPACKS` symlink cleanup in
   `bash/start-engine.sh:62-69` — decide whether it's still earning its keep or
   can retire now that the compat path is gone (that retirement was already
   claimed in stage-5 work; confirm, don't re-break it).

## Constraints

- Don't touch `.pd` files or `.lore/` artifacts.
- Verify the engine still starts (start/stop stack) after any script removal.
- Keep it small — this is debt cleanup, not a refactor.
