# notes — 02-retire-listener-toolbar

## Verification

```
~/.venvs/bopos/bin/python \
  .loom/tied/26-listener-range-fixes/02-retire-listener-toolbar/verify_listener_toolbar_retired.py
```

19/19 pass. The guard's shape is deliberate: proving the bar is *gone* is one
selector and proves nothing worth knowing. The rest proves nothing was lost with
it — range by collar scrub, heading by tip drag, position by puck drag, range and
heading by keyboard, values round-tripping through `set_listener` and surviving a
reload, and the `aria-label` tracking mid-gesture rather than only at render.

It also asserts the puck still renders, so the suite cannot pass by way of the
whole panel failing to draw.

Tied guard `.loom/tied/02-listener-range-implementation/verify_listener_range.py`:
32/32 after its second in-place repair (see `decisions.md`).

Screenshots: `after-{dark,light}-{wide,narrow}.png`. The header row reads
correctly with the bar gone — "Add Point / No points" sits on its own at both
widths and does not look orphaned.

## Removed

- `#listener-bar` and its three controls (`index.html`)
- `bindListenerBar()` and its call site (`spatial.js`)
- the toolbar writes at the tail of `paintRange()`
- `#listener-bar` rules (`style.css`)

`grep -rn "listener-range\|listener-heading\|listener-readout" dashboard/` is
clean of the retired ids (the surviving hits are the `.listener-range-at` /
`.listener-range-field` SVG classes from stitch `01` and the `.listener-heading`
handle line, which are unrelated).

## Gotchas worth carrying

- **A re-render wipes gesture-local DOM state.** `render()` calls
  `svg.replaceChildren()`, so anything a gesture sets on an element — a class, a
  text node — is destroyed by the next heartbeat broadcast. Pointer drags are
  immune because `render()` early-returns while a drag is live; the keyboard and
  wheel paths are not. State that must outlive a render has to live in a module
  variable and be re-applied during render.
- **Don't reset a fade timer from the render path.** The corollary: re-applying
  that state must not restart its expiry, or a heartbeat keeps it alive forever.
  Deadline, not timer reset. (Both directions are pinned by guard checks.)
- **The wheel steps per event, not per `deltaY`.** `page.mouse.wheel(0, -8000)`
  is one notch, not thirty-two.
