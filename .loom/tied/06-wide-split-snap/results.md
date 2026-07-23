# 06-wide-split-snap results

## Outcome

- At Monitor widths of 1000 px or more, tabs are draggable between left and
  right panes. Beginning a drag exposes both pane targets; abort restores the
  prior layout.
- Moving the first tab right creates a 50/50 split. Empty panes collapse
  automatically.
- The split separator supports pointer and keyboard resizing, clamped to
  30/70–70/30.
- Each pane provides a keyboard-accessible `⋯` action menu for moving its
  active tab left/right or returning to one pane.
- Below 1000 px, all tabs return to one canonical strip with no drag affordance.
  The saved wide assignment is restored when width returns.
- Pane assignment, active tabs, ratio, height, and collapse state persist in
  versioned browser-local layout state.

## Verification

```text
node --check dashboard/static/js/monitor.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/20-console-dock/06-wide-split-snap.stitching/verify_monitor_split.py
git diff --check
```

Result: **12/12** real-server + simfleet Playwright checks passed, including
live traffic after the pane refactor, visible drop targets, aborted drag,
non-overlapping split panes, keyboard resize, reload persistence, narrow
fallback, restored wide layout, keyboard return-to-one-pane, and no browser
errors.

Review screenshots:

- `monitor-split.png`
- `monitor-narrow.png`

The deferred Map tab remains waiting by design; Monitor v1 is otherwise
complete.
