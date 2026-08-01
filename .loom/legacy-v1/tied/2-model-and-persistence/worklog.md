# Worklog — 2-model-and-persistence (2026-07-18)

Implemented by a Sonnet delegate against the design note; diff reviewed and
verify re-run by the orchestrator (Fable).

Delivered: `dashboard/show_model.py` (580 lines — schema cleaning, section
derivation, uid minting with collision retry, nine immutable edit ops,
atomic order-preserving persistence in `dashboard/shows/<name>.json`);
`server.py` WS surface (catalog + edit messages funneled through one
`apply_show_mutation` persist-then-broadcast helper; `shows`/`show` sent on
connect); `state.py` `current_show` pointer (excluded from venue snapshots).

Verification (run by orchestrator):
`~/.venvs/bopos/bin/python .loom/threads/14-show-tab/2-model-and-persistence.stitching/verify_show_model.py`
→ "0 failure(s) / show-model verify passed" (~90 checks incl. real-server WS
CRUD on ports 18097/15586/16696 and kill+restart persistence).

Recorded deviations (all reasonable, confirmed on review):
- `after_uid: null` = insert/move to front — stitches 4–6 confirm against UI.
- `create_show`/`save_show_as` adopt the new show as current.
- `current_show` excluded from venue snapshots (session fact, not topology).
- Playback hooks left as TODO(stitch 3) in `load_show`/`remove_item`.
