# theme-1 completion notes

Implemented the daylight theme and persistent theme control on both Dashboard
pages:

- remaining shared backgrounds, panels, inputs, controls, rows, canvas areas,
  and border/mark colours now resolve through paired surface tokens;
- `System`, `Light`, and `Dark` are available in both headers, with explicit
  choices stored as `bopos-theme` and System following live OS preference
  changes;
- the early shared `theme.js` stamps the effective `data-theme`, updates
  `color-scheme` and `theme-color`, and synchronizes same-origin tabs/frames;
- the embedded Dashboard follows the technical page immediately;
- light accents were finalized against the actual surfaces, including a
  legible warning-row treatment; semantic green/amber/red and the ratified Show
  pill colours remain intact.

## Verification

Passed 2026-07-20:

```text
node --check dashboard/static/js/theme.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  .loom/threads/dashboard-theme-toggle/theme-1-surfaces-and-toggle.stitching/verify_theme.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/dashboard-theme-toggle/theme-1-surfaces-and-toggle.stitching/verify_theme.py
git diff --check
```

The focused Playwright verifier passed all checks on the real server plus one
simulated device: both pages, emulated system default, live system-preference
change, explicit toggle, reload persistence, cross-frame synchronization,
theme metadata, computed surface/accent changes, Show pills, automation
colours, no browser console errors, text contrast >= 4.5:1, and mark contrast
>= 3:1. It retained dark/light screenshots for all six technical tabs and the
standalone facilitator page.

Two older adjacent verifiers were also inspected honestly:

- `automation-5-waveform-marker/verify_waveform_marker.py` passed its first
  five current marker checks twice, then timed out waiting for a short-lived
  fade-progress node; this is a pre-existing timing assumption and no
  automation JS changed here.
- `facilitator-view/verify_facilitator.py` is obsolete against the ratified
  current contract (`role` is retired) and old `.card` DOM; it failed those old
  expectations before reaching a meaningful theme assertion.

No hardware, iPad, or physical touch test was performed. Screenshot review was
performed at 1280 x 1000 in headless Chromium. Bob's untracked
`dashboard/shows/` working material was untouched.
