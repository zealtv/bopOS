# 52-preset-drawer-name-discarded — verification

## The diagnosis

A timestamped trace (temporary instrumentation in `control-host.js`,
`control-column.js` and `control-surface.js`, all three reverted) logging every
`setInteracting` call, every `renderCards` entry and every `drawer` focus event:

```
   t=176  renderCards  REBUILD  focus=BODY
   t=261  pointerup    False    focus=SUMMARY
   t=333  pointerup    False    focus=BUTTON
   t=334  renderCards  REBUILD  focus=BUTTON
   t=349  renderCards  REBUILD  focus=BODY
  t=1577  renderCards  REBUILD  focus=preset-name   ← the loss
```

No `drawer.focusin`. No `setInteracting`. The guard was never armed, and one
run of the right instrument said so unambiguously where six runs of end-state
probing had not.

Platform fact, measured on a fresh element rather than assumed:

| property | exists on a fresh `<div>` | handler fires when assigned |
| --- | --- | --- |
| `onfocusin` | **false** | **0** |
| `onfocusout` | **false** | — |
| `onfocus` | true | — |
| `onclick` | true | — |

`addEventListener("focusin", …)` on the same element fires once.

## Behaviour, before and after

`probe_drawer_typing.py` (kept in this stitch) types `Dawn` into the drawer and
waits ~3 s with a 0.5 s heartbeat:

| | before | after |
| --- | --- | --- |
| value after heartbeats | `''` (3 of 3 runs) | `'Dawn'` (3 of 3 runs) |
| input node replaced | yes | **no** — the guard now holds |

## Guards, verified in both directions

### `tests/verify_interaction_guard.py` (browser, new)

9/9 pass on the fixed tree. On the unfixed tree (`git stash push
dashboard/static/js/control-surface.js`), **5 of 9 fail**:

```
[FAIL] a typed preset name survives the heartbeat -- ''
[FAIL] the focused field is not even rebuilt
[FAIL] the name survives a rebuild that happens anyway -- ''
[FAIL] the preset actually saves
[FAIL] the generator drawer's field is not rebuilt under focus
```

Including `the preset actually saves`, which is the operator's whole point, and
the generator drawer, which had the same defect and no symptom anyone had
reported.

The write-through is pinned *separately* from the guard: the journey blurs out
of the drawer, asserts the rebuild really happened (otherwise the next
assertion would pass vacuously), and only then requires the name to have
survived it.

### `tests/test_dom_event_handlers.py` (browser-free)

Green on the clean tree. Restoring one `drawer.onfocusin = …` makes it name the
file and line. Its comment-stripping was added because the first version flagged
the fix's own explanatory prose — a false positive that would have been
inherited by anyone documenting the rule.

## Two wrong turns worth recording

* The journey's first fixture used an unbound seat with no params, so
  `the preset actually saves` failed on the *fixed* tree — nothing to capture,
  not a defect. Aligned with `verify_preset_control_surface.py`'s fixture.
* The generator-drawer assertion first focused an `input[type=range]`, which
  cannot show whether focus holds the guard: `control-host.js` arms the guard on
  a range's `pointerdown` and deliberately releases it a tick after `pointerup`.
  It reported a failure that was an artifact of the probe. Now uses
  `input.live-gen-num`. Recorded as Playwright gotcha 23.

Both were caught because the guard was run against the *fixed* tree first and
its failures interrogated rather than assumed to be the bug.

## Suites

* `fast` — **268** tests, OK (267 before, plus this stitch's 1).
* `tools/run-tests.sh browser` — **23/23 green, twice** (runs 6 and 7, both
  clean, no edits to the tree while running).

**These are the first fully green full-suite runs in this line of work.** Runs
0, 2, 4 and 5 each failed a journey; runs 1 and 3 are void or green for other
reasons (see `50` and `51`). The preset journey that had been failing
intermittently since run 0 now passes twice, which is consistent with this
having been its cause — though two runs is corroboration, not proof, and the
real evidence is that the guard fails 5/9 on the unfixed tree every time.

## Not covered

Nothing here touches PD or hardware.

The Device panel and patch editor mount the same drawer and therefore inherit
both fixes, but this journey exercises only the Control tab; `verify_preset_editor.py`
covers the editor's own save path and passes. No guard drives the drawer on a
touch device — `49-remote-ipad-restyle` remains the hardware-gated pass for that.
