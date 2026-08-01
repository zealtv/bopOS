# Worklog — 4-tab-ui (2026-07-18)

Implemented by a Codex (GPT-5.5) delegate via codex-implement (chosen to
spare the Claude session cap, which was at 69% when this stitch started);
diff reviewed and the Playwright verify executed by the orchestrator
(Fable). Codex could not run server/Playwright in its sandbox (sockets
forbidden) and said so honestly; it verified with node --check/py_compile.

Delivered: Sequencer tab renamed to Show (index.html, TAB_NAMES, no stale
static references); `dashboard/static/js/show.js` (273 lines, vanilla-JS
matching the other tab modules) rendering from `show`/`shows`/
`show_playback` broadcasts — one-column item table, divider rows, message
pills, per-step trigger/state buttons with pause/resume/trigger-next,
client-side countdown from remaining_s snapshots, single focus model with
inspector shell, transport strip with stop-all + what's-playing, empty
state with create/load show controls; scoped style.css additions.

Verification (orchestrator-run):
`~/.venvs/bopos/bin/python .loom/threads/14-show-tab/4-tab-ui.stitching/verify_show_tab.py`
→ 0 failures (tab rename, rendering from a seeded two-section show,
step_start + playing-state reflection, stop-all, step and pill focus
highlights, no page errors). Green on first run.
