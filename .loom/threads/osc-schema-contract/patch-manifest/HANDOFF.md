# patch-manifest — session handoff (2026-07-07, paused mid-stitch)

Bob asked for a pause. This stitch is **~30% done, parked at a clean seam**:
groundwork files exist and are committed; no existing file has been touched
for this stitch yet, so nothing is half-edited.

## Done (committed)

- `design-decisions.md` (this dir) — **read it first, it is the whole plan**,
  §1–§6 with the judgment calls already made (notably: invalid manifest
  falls back to legacy launch loudly instead of refusing to start — §1 of
  the contract beats a strict reading of §8).
- `patches/default/bopos.patch.json` — contract §8's example made real
  (legacy three params; gain2 deliberately not declared).
- `python/manifest.py` — the shared validator: `load()`, `raw()`, CLI mode
  for the launcher (exit 0 valid / 3 no-manifest-legacy / 1 invalid).
  Smoke-tested: exit 0 + eval-able vars on patches/default, exit 1 on a
  manifest-less dir without main.pd.

## Remaining (in design-decisions.md §3–§6 detail)

1. **helper.py**: `params` + `report` members in `handle_lan_datagram`
   (unicast to (src, 5550), same pattern as `load`); `/patch` validation via
   `manifest.load` or main.pd; engine-alive generalised through
   `run/engine.name` → manifest engine → `pd`. Add `AUDIO_CHANNELS` to
   read_node_config defaults (report uses it, default 2).
2. **bash/start-engine.sh + stop-engine.sh**: eval manifest.py CLI output;
   pd keeps today's launch line; other engines `<engine> <entrypoint>` +
   `BOPOS_*` env; write `run/engine.pid`/`run/engine.name` (keep pd.pid when
   pd); stop via engine.pid + `pkill -x $(cat engine.name)`.
3. **simfleet**: `params`/`report` members (serve the default-patch manifest
   JSON / sim facts), `/p/<name>` plane handling (declared + legacy four
   only; unknown names logged and dropped).
4. **pd-edits-for-bob.md §4**: `route p` spec + the §13 revision proposal
   (skip bare-name aliases per Bob's relaxation — contract edit itself is
   Bob's ratification, don't make it).
5. **Tests**: `test_patch_manifest.py` in this dir, harness style copied
   from `.loom/tied/assign-persistence/test_assign_persistence.py`
   (FakeServer/FakeClient before `import helper`). Cover manifest
   validation cases, params/report replies, /patch validation, engine-alive
   with engine.name.
6. **Verify live** (pattern + scripts from the tied siblings): scratchpad
   listeners + simfleet + real helper.py loopback. Env:
   `PYTHONPATH=<scratchpad>/pylib:python:python/io` — pylib with pyOSC3 +
   pythonosc lives in this session's scratchpad
   (`/tmp/claude-1000/-home-bob-repos-bopOS/acefa5c4-*/scratchpad/`);
   rebuild it from PyPI (curl the sdist/wheel) if the tmp dir is gone.
7. Then `loom tie patch-manifest`, prose-subject commit, update the HQ
   memory (`osc-council-state.md`).

## Standing context

- Codex was at capacity all afternoon (two dead runs) — hb-identity was
  codex+review, assign-persistence and this one are hand-built. Check
  capacity before delegating again.
- Commits `f604fde` (hb-identity) and `623209d` (assign-persistence) are
  **local only** — pushes to main are blocked in auto mode; Bob pushes.
- The stitch claim was released at pause; re-claim with
  `./.loom/loom claim patch-manifest`.
