# 51-control-column-first-render-flake — verification

## The reproduction

`probe_first_render.py` (kept here), which stalls `control-host.js`'s fetch by
1.5 s with `page.route` and otherwise loads the real dashboard.

**Before the fix:**

| | no delay | `control-host.js` stalled |
| --- | --- | --- |
| card painted | yes | **no** |
| `.live-card` count | 1 | **0** |
| column HTML length | 3595 | **503** |
| `ws.handlers.state.length` | 6 | 6 |
| `ws.pending.state` | absent | absent |

The handler count is the point: `control-host.js` **had** registered. The
message had already been delivered to `dashboard.js` and buffered for nobody,
so the handler was simply never called.

**After the fix:** both columns identical — `painted: True`, `cards: 1`,
`columnHtml: 3595`. The stalled load renders byte-identically to the control.

## Guards, verified in both directions

### `tests/verify_ws_snapshot_replay.py` (browser, new)

On the fixed tree: 7/7 pass.

On the unfixed tree (`git stash push dashboard/static/js/ws.js`):

```
[FAIL] the Control column paints although its script loaded after the connect burst
       -- Locator.wait_for: Timeout 15000ms exceeded.
[FAIL] every connect-burst type is retained for replay -- []
[FAIL] a handler registered later still receives the state -- '__never__'
3 check(s) failed
```

`'__never__'` is the whole defect in one value: a handler registered after the
burst receives nothing, ever.

*This run is also how the guard's own hang was found* — the first version of
that third check awaited an unbounded promise and burned the full ten-minute
timeout rather than failing. Bounded to 5 s with a sentinel.

### `tests/test_ws_snapshot.py` (browser-free, 3 tests)

Pins `ws.js`'s `SNAPSHOT_TYPES` against the message types
`Dashboard.websocket` actually sends before its receive loop, in **both**
directions, plus a check that the event-queue branch survives alongside the
snapshot branch.

Verified by deleting `show_playback` from the client list:

```
AssertionError: Items in the first set but not the second:
FAILED (failures=1)
```

## Suites

* `fast` — **267** tests, OK (264 before, plus this stitch's 3).
* `tools/run-tests.sh browser` — see below. The suite is now 22 journeys.

## Browser runs

Both clean — no edits to the tree while running, unlike thread `50`'s first two.
The suite is now 22 journeys.

| run | result |
| --- | --- |
| 4 | 21/22 — `verify_preset_control_surface.py` failed |
| 5 | 21/22 — `verify_preset_control_surface.py` failed |

**`verify_show_capture.py`, the journey that motivated this stitch, passed in
both.** So did the new `verify_ws_snapshot_replay.py`.

**The suite is not green, and this stitch does not claim it is.** The same
journey failed both times, at its **first** assertion — which is not a flake
pattern, it is a reproducible defect. Chased down: a preset name typed into the
save drawer is discarded by the next heartbeat re-render, so `commit` sees an
empty name and saves nothing. Reproduced 3/3 by
`probe_drawer_typing.py`. That is **not** this stitch's defect and not caused by
this stitch's fix — the fix was re-run 4/4 concurrently against that journey
with no failures, and the journey also failed in run 0, before `ws.js` was
touched. It is written up with its evidence as
`52-preset-drawer-name-discarded`, including the two hypotheses that were tested
and did **not** explain it, so the next session does not re-walk them.

**What this does and does not settle.** The defect diagnosed here is proved by
deterministic reproduction, not by run counts, and its guard fails every time on
the unfixed tree rather than one run in three. Full-suite runs are corroboration,
not the evidence. Of the three journeys thread `50` saw fail, only
`verify_show_capture` is explained here; `52` now explains the preset one, which
means `50`'s host-scoping fix — real as it was — was not the whole story for
that journey either.

## Not covered

Nothing here touches PD or hardware — `ws.js` is browser-side wiring.

Reconnect behaviour is exercised only incidentally: the server re-sends the
burst on reconnect, so `latest` is refreshed, but no guard drives a socket drop
and reconnect. Worth a check if this area is touched again.
