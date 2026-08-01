# 51-control-column-first-render-flake — decisions

## It was hypothesis (1), and it is an operator-facing defect

The stitch named two candidate gates and said to instrument before patching.
Hypothesis (2), `isInteracting`, is **ruled out by construction**: every
`setInteracting(true)` in `control-surface.js` fires from focus or pointer on an
already-rendered control, and the host's own `pointerdown` listener requires a
target inside the stage. On a freshly loaded page with no card, nothing can set
it. Hypothesis (3), empty `declarations`, is also wrong — a card renders without
them; `available` only gates what is inside it.

Hypothesis (1) was right, but the mechanism is sharper than "the first `state`
can be delayed". **`state` is not delayed. It arrives, and is thrown away.**

## The mechanism

`ws.js`'s `emit` buffered a message only while a type had **no** handlers:

```js
if (!handlers.length) { (this.pending[type] ||= []).push(data); return; }
```

So `pending` protected the **first** registrant for a type and nobody else.

`dashboard.js:1` opens the socket and `dashboard.js:140` registers
`ws.on("state", …)`. The server sends its snapshot burst the instant the socket
opens (`Dashboard.websocket:287`). `control-host.js` is a **separate classic
`<script>`**, five fetches further down `index.html`, and the event loop is free
to deliver socket messages while those files are being fetched. If `state`
lands in that window it is dispatched to `dashboard.js` alone and buffered for
nobody. `control-host.js` then registers its handler, which is never called.

`venueKnown` stays `false`, so `renderAll` returns early on every subsequent
`device_update` — the tab never paints a card. And nothing recovers it:
heartbeats are `device_update`, the offline sweep sends `device_offline`, and
there is **no periodic full-`state` broadcast anywhere** (established by
`4-current-show-broadcast`). Recovery waits for someone to happen to run a verb
that broadcasts `state`. On an idle dashboard, that is never.

So: **load the dashboard on a slow enough connection and the Control tab is
silently, permanently blank.** That is the call `47` got right and this one is
the same — a real defect wearing a flake's clothing.

## Six consumers, not one

`stateHandlers: 6`. Two in `control-host.js`, two in `monitor.js`, one in
`show.js`, all registered after `dashboard.js` and all exposed to the same loss.
The Control column is merely the one with a visible, total symptom. The server's
connect burst is **seven** snapshot types (`state`, `distribution`, `venues`,
`shows`, `show`, `show_warnings`, `show_playback`), every one at risk.

That is why the fix is in `ws.js` and not in `control-host.js`. The stitch
anticipated a local guard; a local guard would have fixed one of six symptoms
and left the cause.

## The fix

`ws.js` keeps the **latest** payload per snapshot type and replays it to any
handler registering later. Events keep the existing `pending` queue, which
covers a genuinely different case — an event must not be dropped merely because
no handler exists yet, whereas a snapshot should supersede rather than
accumulate.

Latest rather than a backlog is deliberate: a handler that registers long after
connect wants current state, not a replay of every superseded snapshot in order.

**The snapshot list is coupled to the server's connect burst**, and the coupling
is invisible from either file. If the server adds an eighth snapshot and `ws.js`
does not know it is one, that type silently reverts to first-registrant-wins
with no error anywhere. `tests/test_ws_snapshot.py` parses both sides and fails
on drift in either direction, which is the only reason it is safe to write the
list down twice.

## Reproduction, not load-chasing

Stalling `control-host.js`'s fetch with `page.route` makes the window
deterministic. The route does not create the race — network latency does — it
only makes it reliable enough to test. That turned a flake reproducible in
roughly one full-suite run in three into a guard that fails every time.

`probe_first_render.py` (kept in this stitch) reports the before/after directly:
with the stall, `cards: 0` and `columnHtml: 503` before the fix; `cards: 1` and
`columnHtml: 3595` after — byte-identical to the un-stalled control.

## One thing the guard had to learn about itself

The first version of the "a later handler still receives the state" check
awaited an unbounded promise. On the unfixed tree that promise never resolves,
so the guard **hung the run for ten minutes instead of failing it**. It now
resolves to a `"__never__"` sentinel after 5 s. A regression guard that hangs on
the regression is not a guard — and this was only discovered by running it
against the broken tree, which is the same step that proves it guards anything
at all.

## Verification

See `verification.md`.
