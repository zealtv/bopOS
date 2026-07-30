# 02-token-promotion — verification

2026-07-30.

## Suites

- `tools/run-tests.sh fast` — **250 tests, OK**, no failures.
- `tools/run-tests.sh browser` — **17/17 PASS**, no failures. Both known-red
  entries came up green this run: `45-device-enabled-replay-red` is resolved
  (fix `e9e25cc`, commit `c51eb90` records why it can look red host-dependently),
  and the `47-live-param-kinds-flake` slider assertions did not trip in this
  full-suite run. Nothing regressed either way.
- No living code, test, or template referenced the retired tokens
  (`grep -rn -- '--chrome-\|--feature-line\|--feature:'` across `dashboard/`,
  `tests/`, `tools/`: zero hits outside `.loom/tied/`, `.lore/` and prose).
  The archived guards under `.loom/tied/05-compact-chrome/` still assert the
  old `--chrome-*` values; per CLAUDE.md they are historical evidence, not a
  regression suite, and were deliberately not touched.

## Screenshot evidence

`shoot.py <dir>` boots the real `dashboard/server.py` + `tools/simfleet.py` on
free ports against a temp fixture, then captures, in light **and** dark:

- every app tab (`control`, `show`, `seats`, `devices`, `patches`, `assets`) at
  **1280** and **1680**,
- the expanded Monitor dock's Globals panel at both widths,
- the standalone Remote view and the All card at 900 (the original 2026-07-30
  palette shots).

The `before-*.png` set (32 shots) was re-taken with
`git checkout HEAD -- dashboard/static/css` so the pair is matched
shot-for-shot; `after-*.png` (32 shots) is this stitch. `shoot.py` writes them
into the directory it is given; they are flattened into the stitch with
`before-`/`after-` prefixes because the loom counts a subdirectory as an
unresolved child and refuses to tie the parent (same reason as commit
`1ca872d`). `baseline-2026-07-30-*.png` are the four narrower pre-change shots
from the palette correction, kept as they were.

Harness additions this stitch: the every-tab 1280/1680 sweep, `populate_show()`
(an empty Show tab exercises none of the metrics that matter — no edit bar, no
step rows, no sticky inspector), and the Monitor dock expansion.

## Measured density

Sampled from the retained `app-patches-1280-dark.png` pair (`before-`/`after-`) (bright rule rows in
the right margin, `PIL`):

| | before | after |
|---|---|---|
| header bottom border | y=63 | y=39 |
| tab-bar bottom border | y=117 | y=72 |
| **chrome above content** | **118px** | **73px** (−38%) |

That second number is the one `.tab-stage`'s `calc(100vh - 73px)` and the Show
inspector's `top:45px` are derived from, so the arithmetic in the CSS is
confirmed by the pixels rather than asserted.

Visible in the pair: the Patches tab gains a whole extra manifest parameter row
in the same viewport; the 24px control panel no longer sits inside visibly
bloated 32px chrome (the remaining tall row on the Control tab is the
facilitator iframe's own target filter, which belongs to `07`/`08`);
`#editor-panel` is flat `--panel` instead of the teal gradient; and the light
ground is one pink everywhere instead of `#f8f0fc` under the OS preference and
`#f4f1f8` under the explicit toggle.

## Not verified here

- Touch/coarse-pointer behaviour is unchanged by construction — `--row-h`
  already widens to 34px under `@media (pointer:coarse)` and the existing
  `max-width:760px` 44px floors are untouched — but no coarse-pointer shots
  were taken.
- Bob's eye on the density itself. The drop is what the stitch authorizes
  ("expect a real density drop app-wide; that is the point"), not a design gate,
  but it is the first app-wide visual change of the thread and he should see the
  before/after pair.
