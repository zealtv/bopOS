# automation-2 spec — Show-tab generator builder GUI

Settled design (orchestrator, 2026-07-20). Implementer: follow this exactly;
where this spec is silent, mirror `python/paramgen.py` semantics.

## Goal

The Show tab's param message builder (`renderParamBuilder` in
`dashboard/static/js/show.js`) grows a generator-mode UI compiling to the
ratified §3.2 wire grammar (`docs/OSC-CONTRACT.md`). The builder is a
compiler: it writes canonical typed args into the existing message model via
`updateMessage`; Show playback already sends args unchanged. No server/python
changes. No second backend model.

## Modes

For manifest-declared `f`/`i` params, a `generator` select with modes:
**value** (constant), **fade**, **loop**, **lfo**, **stop**.
String (`s`) declarations keep the current single value field only — no
generator select, no automation.

### value (constant)
Current behavior: one typed arg via `typedArg(declType, v)`.

### fade
- Segment rows: each row = destination value (numeric input, declaration
  min/max/step hints) + duration amount + unit select (`ms`/`s`/`m`/`h`).
  Add/remove rows (min 1). Removing to fewer than 1 is impossible.
- Optional **from** (explicit start) numeric input, enabled **only when
  exactly one segment row exists** (the 3-element form is the only one with
  explicit start). With >1 rows the from field is hidden/disabled and
  cleared.
- One optional **curve** exponent input (number, default empty/0).

### loop
- Same segment editor. Emitting `loop` requires **≥2 rows**: with fewer,
  show an inline hint ("loop needs at least two segments") and do **not**
  call updateMessage until valid. No explicit-start field ever.
- Curve input as fade.

### lfo
- shape select: `sine tri saw square sh drift`
- min, max numeric inputs; period amount + unit select (period must be > 0);
- phase numeric input 0..1 (step 0.01, default 0);
- free checkbox;
- curve exponent input.

### stop
No fields. Args become the single string `stop`.

## Canonical emission

- Destination/min/max/from values: `typedArg(declarationType, v)` (so `i`
  declarations emit ints).
- Durations/periods: **always OSC strings with unit suffix** as chosen, e.g.
  `{type:"s", value:"500ms"}`, `"10s"`, `"1.5m"`. Format the number without
  trailing zeros (`String(Number(n))`).
- Keywords (`loop`, `stop`, `lfo`) and shapes: OSC strings.
- Options, canonical short forms only, trailing, in this order:
  LFO: `p:<n>` (only when phase ≠ 0), `f` (only when free), `c:<n>` (only
  when curve ≠ 0). Fade/loop: `c:<n>` (only when ≠ 0).
- Never emit `curve:`/`phase:`/`free` long aliases.
- Example wire args for a loop: `["loop", 0.2, "2s", 0.8, "500ms", "c:1.5"]`
  with numbers typed per declaration.

## Round-trip inference (the hard requirement)

Implement `parseParamArgs(args, declType)` in show.js mirroring
`python/paramgen.py::parse_message` **exactly**: trailing-option scan
(accepting `c:`/`curve:`/`p:`/`phase:`/`f`/`free`, duplicate option = error,
phase 0..1), `stop` strict arity, `lfo` 5 positionals + valid shape +
period > 0, one-pair `loop` parses as plain **fade** (honest — builder shows
fade mode), odd ≥5 segment lists reject, `curve` on a constant rejects,
phase/free outside lfo reject, duration strings via regex
`(?:\d+(?:\.\d*)?|\.\d+)(ms|s|m|h)$`, negative durations reject, non-numeric
values reject.

- Rendering/focusing a message **never** calls updateMessage — builder state
  is derived from args on every render. Only user edits write.
- Parse success → populate the matching mode's fields (bare numeric
  durations display as ms; suffixed strings display with their unit;
  long-alias options populate the same fields but re-emission canonicalises
  to short forms **only when the user next edits** — never rewrite on focus).
- Parse failure (hand-authored/invalid) → **raw fallback**: keep param mode
  and the param picker, but show a clearly labelled "unrecognised automation
  form — raw arguments" panel reusing the raw-arg row editor (type select +
  value + remove, plus add) operating on the message args in place. No
  silent coercion, no clobbering.
- Switching generator mode via the select rewrites args to that mode's
  defaults (value: declaration default; fade: one segment to declaration
  default over 1s; loop: two segments; lfo: sine, declaration min/max or
  0..1, 4s; stop: `stop`).
- Switching param via the picker keeps the current generator mode where
  possible, re-emitting with the new declaration's type/default.

## Untouched behavior

- Target picker semantics, alias field, wire preview mechanism
  (`wirePreview` must show the compiled canonical args — it already renders
  message.args; just make sure string args like `500ms` display), cue/point/
  raw builders, transport, drag, undo, keyboard handling.
- p5/p6 inspector density conventions: compact labeled fields inside
  `show-inspector-section`, no new modals, no retired affordances
  (per-step forward_sync, message copy/cut buttons).
- Selective render + CSS progress from `7162943` untouched.

## Files you may touch

- `dashboard/static/js/show.js`
- `dashboard/static/css/` (minimal additions for segment rows if needed —
  check existing classes first and reuse)
- `.loom/threads/16-param-automation/automation-2-show-builder-gui.stitching/verify_show_param_builder.py`
  (new verify script)

Nothing else. Do not touch `.loom` state (claims/ties), `python/`, `tools/`,
`.pd` files, or `dashboard/server.py`. Do not commit.

## Verify script

Write `verify_show_param_builder.py` in the stitch dir, modelled on
`.loom/tied/p3-global-transport-and-cue-lead/verify_show_transport.py` and
`.loom/tied/p5-inspector-defaults/verify_show_inspector_defaults.py`
(repo-root-by-marker — walk up until `tools/simfleet.py` exists; random
loopback ports; real `dashboard/server.py` + `tools/simfleet.py`; headless
Playwright Chromium; teardown). It must:

1. Stage a patch manifest with an `f` param, an `i` param, and an `s` param
   (follow how the tied verifies stage manifests via simfleet).
2. Author each generator kind in the GUI (value, single fade with explicit
   start, multi-segment fade, loop with curve, lfo with phase+free+curve,
   stop) and assert the exact canonical typed args, via the outgoing OSC
   console or simfleet receipt, when the step plays.
3. Reload the page / re-focus messages and assert args unchanged
   (round-trip: no rewrite on focus) and builder fields repopulated.
4. Assert string param shows no generator select and stays constant-only.
5. Hand-author an invalid arg list (e.g. `["lfo","sine",0]`) via raw mode /
   direct model injection, switch to param mode, assert raw fallback panel
   appears and args are untouched.
6. Assert loop with one segment refuses to emit (hint shown, args
   unchanged).
7. Fail on any browser console error (page.on console/pageerror).

Known Playwright gotchas (from CLAUDE.md): `inner_text` applies
text-transform; one type-aware dialog handler only; `wait_for_function`
needs `arg=` keyword. Your sandbox cannot bind sockets — **write the script
but do not fake a run; state plainly that you could not execute it.** The
orchestrator runs it.

## Acceptance checks (orchestrator runs)

```sh
node --check dashboard/static/js/show.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/16-param-automation/automation-2-show-builder-gui.stitching/verify_show_param_builder.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/show-transport-spot-fixes/verify_show_transport_spot_fixes.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/6-message-editing/verify_show_editing.py
git diff --check
```

When done, summarize what changed, how you verified what you could, and
anything you could not do. If you could not complete the task, say so
explicitly.
