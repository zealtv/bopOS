# Results

## Outcome

The primary navigation is now:

**Show · Dashboard · Seats · Devices · Patches · Assets**

Show is both the leading tab and the default workspace at bare `/`. Existing
tab IDs, panels, `#dashboard` and other deep links, click behavior, and ARIA
relationships remain unchanged. ArrowLeft/ArrowRight/Home/End now follow the
new visual order. The operator README reflects the current order.

The Dashboard label is deliberately unchanged. Its broader terminology review
is tracked separately as a waiting design stitch.

## Verification

Commands:

```sh
node --check dashboard/static/js/dashboard.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile .loom/threads/dashboard-tab-order-show-first.stitching/verify_tab_order.py
git diff --check
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/threads/dashboard-tab-order-show-first.stitching/verify_tab_order.py
```

Focused real-browser result: **11 / 11 passed**. Coverage includes the README
order, rendered order, Show default state, direct Dashboard hash, click/hash
behavior, bidirectional arrows, Home/End, the leading tab at 420 px, and browser
console/page errors.

Review artifact: `review-show-first-tabs.png`.

No `.pd` file changed. Bob's untracked `dashboard/shows/` was not touched. No
physical hardware or physical iPad was tested.
