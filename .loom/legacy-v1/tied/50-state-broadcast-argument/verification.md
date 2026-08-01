# 50-state-broadcast-argument — verification

## The measurement that started it

A probe (not preserved; reproduced by `tests/test_state_broadcast.py`) built a
real `Dashboard`, registered a fake client, and broadcast `state` four ways:

| passed | `live_controls` delivered | `supervisor` | `host_version` |
| --- | --- | --- | --- |
| nothing | yes | yes | yes |
| `None` | yes | yes | yes |
| `state.public()` | yes | yes | yes |
| `await public_state()` | yes | yes | yes |

Identical key sets throughout. `broadcast()` recomputes the payload for the
`state` type and ignores the argument.

## Guard, verified in both directions

`tests/test_state_broadcast.py` — 4 tests, browser-free, in `fast`.

**Fails when the coercion is weakened.** Replacing
`data = await self.public_state()` with
`data = data if data is not None else await self.public_state()`:

```
FAILED (failures=2)
AssertionError: Items in the first set but not the second:
'host_version'
'live_controls'
```

**Fails when a payload is reintroduced.** Restoring one
`broadcast("state", self.state.public())`:

```
- ['server.py:447: await self.broadcast("state", self.state.public())']
+ [] : `state` broadcasts take no payload; see tests/test_state_broadcast.py
FAILED (failures=1)
```

Tree restored after each; both then green.

## Suites

* `fast` — **264** tests, OK (260 before, plus this stitch's 4).
* `tools/run-tests.sh browser` — see below.

## Browser runs, and what they are worth

Four full-suite runs were made. The first two are **void as evidence**: both
overlapped edits to the tree they were testing.

| run | result | reading |
| --- | --- | --- |
| 0 | 20/21, `verify_preset_control_surface` failed | void — `server.py` was being edited mid-run |
| 1 | 20/21, `verify_preset_editor` failed, `NameError: name 'bound' is not defined` | void — caught a half-applied edit of mine |
| 2 | **20/21, `verify_show_capture` failed** | clean |
| 3 | **21/21 green** | clean |

Run 1's failure is self-inflicted and carries no information. Run 0's does:
`verify_preset_control_surface` failing there, and passing standalone
immediately after, is what pointed at `open_authoring` and led to the
host-scoping defect in §4 of `decisions.md`. Both edited journeys pass
standalone and passed in runs 2 and 3.

**Run 2 is the important result, and it is not a green one.** A third distinct
journey failed, on a clean tree, on a *different* mechanism — no binding race,
the element never appeared at all:

```
waiting for locator("#control-column-host .live-card[data-live-scope=\"all\"]")
to be visible — Timeout 15000ms exceeded
```

That is captured as its own loose end, `51-control-column-first-render-flake`,
with the two candidate gates (`venueKnown`, `isInteracting`) named and the
instruction to instrument before patching. It is **not** fixed here and this
stitch does not claim it is.

**So: four runs, three distinct journeys failed across them, and the suite went
green once.** The host-scoping defect `50` fixed is real and was found by
reading rather than by reproduction; it is one instance, not the class. The
`47` family remains open, which is now what CLAUDE.md says.

## Not covered

Nothing here touches PD or hardware. `broadcast` is host-side only.
