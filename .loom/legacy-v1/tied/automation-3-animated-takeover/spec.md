# automation-3 spec — generator tracking, take-over, Slice-1 indication

Settled by the orchestrator 2026-07-20. Design authority for all visual
decisions: `.loom/tied/automation-4-waveform-ux-gate/judgment.md` (ratified).
This stitch ships the judgment's **Slice 1** (static layer) plus the tracking
substrate and take-over gesture; marker motion (Slices 2–3) is the later
`automation-5-waveform-marker` stitch — do not build it here.

## Server: track the generator the dashboard sent

- `dashboard/osc_bridge.py`: `set_param` already accepts a list (automation
  args). Add tracking: classify the arg list with
  `python/paramgen.py::parse_message` (use declared type "f" for
  classification; on `ParamGrammarError` treat as constant-equivalent and do
  not track). Non-constant kinds (`fade`, `loop`, `lfo`) record an automation
  entry; a plain value / `set` / `stop` **clears** the entry.
- Entries live runtime-only (never persisted): a dict on the bridge or state
  object, keyed `str(seat_id)` → `{identity: {"args": [...], "kind":
  "fade|loop|lfo", "shape": <lfo shape or None>, "free": bool, "sent_at":
  time.time()}}`. Resolve selectors: `all` → every seat, `g<N>` → group
  members, `<id>` → that seat.
- Expose as a top-level `"automation"` key in `state.public()` and make sure
  every mutation broadcasts a `state` update (reuse existing broadcast
  paths; `show_engine`'s sends go through `bridge.set_param`, so tracking
  there covers Show playback with no show_engine changes).
- Durable full-state law: when tracking a **fade**, also write the fade's
  final destination into the affected seats'/devices' `params[identity]`
  (mirroring what `set_param` scalar writes do; save_debounced + device
  broadcasts). `lfo`/`loop`/`stop` leave stored params untouched.
- `set_live_param` and `replay_live_params` writes clear the automation
  entry for the seats they touch (they send constants).
- Dashboard restart forgets automation (devices keep running generators);
  state after reload honestly shows the stored constants. Acceptable — noted.

## Shared JS parser

Extract `parseParamArgs` (+ its small helpers) from
`dashboard/static/js/show.js` into a new `dashboard/static/js/paramspec.js`
exposing `window.ParamSpec.parse(args, declType)` (behaviour identical —
the tied automation-2 verifier must keep passing). Load it in both
`dashboard/static/index.html` and `dashboard/static/facilitator.html`
before the scripts that use it; `show.js` switches to the shared function.

## Client: Slice-1 static indication + take-over (facilitator.js)

Per the judgment, on the facilitator live cards (`paramControl`):

- Add the `--auto` token to `dashboard/static/css/style.css` and
  `facilitator.css` exactly as ruled: `:root{--auto:#7fb0e8}`,
  `@media (prefers-color-scheme: light)` + `:root[data-theme=light]`
  → `#2464a8`, `:root[data-theme=dark]` → `#7fb0e8`.
- When `installation.automation[seat][identity]` is non-constant, the
  control's label gains an `aria-hidden` kind glyph in `--auto`:
  fade `╱`, loop `⟳`, smooth LFO family (sine/tri/drift) `∿`, stepped
  family (saw/square/sh) `⌁`. Strings never. `aria-label` gains the state:
  `"gain, automated, sine LFO"` etc.
- Aggregate rows (all/group): extend the aggregation to compare member
  automation entries (JSON-compare args). All members automated with equal
  args → render the single-control treatment. Any divergence (or a mix of
  automated and not) → static `auto·mixed` text + glyph with the existing
  `.mixed` affordance, no motion, no invented shape.
- Offline/unbound seat rows: glyph rendered dimmed (reuse existing dimming),
  never animated (nothing animates in this stitch anyway).
- Take-over: on `pointerdown` over an automated range input add a
  `.taking-over` class to the `.live-param` (and set it directly for
  checkboxes — the `interacting` guard only covers ranges); the existing
  change/send path then emits the plain value; when the cleared automation
  state comes back the glyph is gone. Add one `aria-live="polite"` region
  per card body announcing once: `"<name> automation stopped, set to <v>"`.
  A ~180ms opacity drain on `.taking-over .live-param-glyph` via CSS
  transition; under `prefers-reduced-motion` it clears instantly.
- No rAF, no markers, no waveforms, no checkbox flicker. Keep density.

## Files you may touch

`dashboard/osc_bridge.py`, `dashboard/server.py` (only if public()/clear
hooks need it), `dashboard/static/js/paramspec.js` (new),
`dashboard/static/js/show.js` (extraction only), `dashboard/static/js/facilitator.js`,
`dashboard/static/index.html`, `dashboard/static/facilitator.html`,
`dashboard/static/css/style.css`, `dashboard/static/css/facilitator.css`,
`tools/simfleet.py` **only if** parity needs nothing — it already speaks the
grammar; leave it alone unless a check fails, and
`.loom/threads/16-param-automation/automation-3-animated-takeover.stitching/verify_automation_takeover.py`
(new). Nothing else: no `.loom` claims/ties, no `.pd`, no `python/paramgen.py`
changes, no commits.

## Verify script

`verify_automation_takeover.py` in the stitch dir, house pattern (copy the
harness shape from
`.loom/tied/automation-2-show-builder-gui/verify_show_param_builder.py`):
real server + simfleet (2 devices), fixture manifest with `f`/`i`/`s`
params, a show whose step sends: an LFO to seat 0, a fade to seat 1.
Drive the **facilitator page** (`/facilitator.html` — check the actual
route in server.py) with Playwright:

1. Play the step; assert seat 0's control gains the `∿` glyph and
   aria-label contains "automated"; seat 1 shows `╱` while in flight.
2. All-row shows `auto·mixed` (different generators across members).
3. Fade destination lands in durable seat params (assert via saved state
   file or a reload showing the destination value).
4. Take-over: drag seat 0's slider; assert simfleet receives exactly one
   plain single-arg `/p/` datagram for that identity after the automation
   args, and the glyph clears.
5. String param never gains a glyph; offline-bound seat (bind a seat to a
   nonexistent uid in the fixture) renders the dimmed static glyph if
   automated, and nothing animates.
6. Zero-added-OSC: between playback and take-over, assert no additional
   `/p/` traffic arrives at simfleet (animation is local).
7. Reduced-motion emulation still shows glyphs. No console errors.

Sandbox cannot bind sockets: write the script, state you could not run it.

## Acceptance checks (orchestrator runs)

```sh
node --check dashboard/static/js/show.js
node --check dashboard/static/js/facilitator.js
node --check dashboard/static/js/paramspec.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/16-param-automation/automation-3-animated-takeover.stitching/verify_automation_takeover.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/automation-2-show-builder-gui/verify_show_param_builder.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/automation-1-engine-and-parity/verify_param_automation.py
git diff --check
```

When done, summarize what you changed, how you verified what you could, and
anything you could not do. If you could not complete the task, say so
explicitly.
