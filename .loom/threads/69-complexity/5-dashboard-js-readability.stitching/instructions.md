# 5-dashboard-js-readability

**Status:** ready · after `68` and `65` remove their UI (less to move)
**Goal:** `dashboard/static/js/dashboard.js` reads like the rest of the
frontend.

## Today

1,777 lines; 74 lines over 200 characters, the longest ~1,500-character
template literals (`patchDiagnostics` around line 1155 is the worst). It holds
several tabs' worth of rendering in one file.

## Do

- Break long templates into small render functions, one element or section
  each.
- Split by tab/area where the seams are clear, matching how `show.js`,
  `monitor.js` and the control-* modules are already separated.
- Pinning UI is likely to go with `66` — don't polish it.

Done when: no line over ~160 characters in the files touched; browser tier
green; no visible change.
