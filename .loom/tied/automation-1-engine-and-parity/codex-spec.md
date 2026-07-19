# Task: bopOS parameter-automation generator engine + simfleet parity

Repo: /Users/bob/repos/bopOS. Files: new `python/paramgen.py`, wiring in
`python/bopos.py`, parity in `tools/simfleet.py`, one new verify script.
Never touch `.pd` files or anything under `dashboard/`.

## Background

The ratified spec is `docs/OSC-CONTRACT.md` §3.2 (read it first — it is the
authority for the grammar). bopOS nodes run `python/bopos.py` (threaded, not
asyncio): `handle_lan_datagram` routes LAN OSC; `/p/*` messages currently
relay verbatim to the engine via `relay.shape_provided_term` +
`relay_provided_term(address, args)` (selector stripped). The synced clock is
`sync_state` (`python/sync_node.py` `SyncState`): `offset()` returns the
current slewed offset in ns where `offset == deviceClock - leaderClock`
(leader time = `time.monotonic_ns() - offset`); `synced()` says whether an
offset was ever pushed. `python/manifest.py` parses `bopos.patch.json`;
declarations carry `type` (`"f"`/`"i"`/`"s"`) — the automation grammar
applies **only to numeric (f/i) declared params**.

`tools/simfleet.py` simulates N nodes for dashboard development; it already
imports modules from `python/` (see its `sys.path.append`) precisely so wire
behavior can never drift from the real node. It logs param writes as
`p/<member>=<value>` and drops undeclared members.

## Deliverable 1 — `python/paramgen.py` (new module)

Stdlib only (`threading`, `time`, `math`, `random`, `re`). Two halves:

### Parser

`parse_message(args, param_type)` → a small spec object (dataclass or dict)
of kind `set` / `fade` / `loop` / `lfo` / `stop`, or raises `ParamGrammarError`
with a readable message. Follow §3.2 exactly:

- args arrive as OSC-decoded Python values (floats/ints/strings).
- 1 numeric elem → set. 2 elems → go to x in dur from current. 3 → from x
  to y in dur. 4+ even → dest/dur pairs from current. Odd count ≥5 → error.
- Durations: bare number = ms; strings `250ms` `10s` `1.5m` `2h`
  (float value + unit suffix ms/s/m/h; anything else = error).
- `loop` keyword leads a fade-form tail; ignored (plain fade) for 1–2
  element tails. `stop` alone. `lfo <shape> <min> <max> <period>` with
  shapes `sine tri saw square sh drift`.
- Trailing options in any order after the positional tail: `c:<n>`
  (`curve:<n>`), `p:<0..1>` (`phase:<0..1>`), `f` (`free`). `p:`/`f` are
  lfo-only (error elsewhere); `c:` valid on fades, loops, and lfo.
- Case-sensitive lowercase keywords. Unknown keyword/option = error.

### Generator engine

`GeneratorEngine(emit, sync_state, now_ns=time.monotonic_ns)` — one slot per
param identity, last message wins. `apply(identity, spec, declaration)`
replaces that identity's generator. One daemon scheduler thread total
(condition-variable wait until next due event; started lazily, stoppable via
`close()` for tests). Emission goes through the `emit(identity, args_list)`
callback:

- **Float fades**: at each segment boundary emit the engine's existing go-to
  primitive: `[target, duration_ms]` (2-element). Linear segments are one
  emission; curved segments (`c:` ≠ 0) are subdivided into short linear
  sub-segments at ~33 Hz (cap subdivision count for very short segments).
  Curve law: for a segment normalized to t ∈ [0,1],
  `shaped = t**(2**n)` — n>0 ease-in-ish, n<0 ease-out-ish, n=0 linear —
  applied to the value ramp between the segment's endpoints.
- **Int fades/LFOs**: never emit go-to pairs; emit 1-element `[int_value]`
  sets, exactly once per integer crossing (floor of the continuous value;
  either direction; no duplicates, no skips). Tick at ~33 Hz and emit every
  integer between the last emitted floor and the current floor, in order.
- **Constants** (set / stop / completed fade): a single 1-element emission.
  `stop` freezes at the current computed output.
- **LFO floats**: emit `[target, tick_ms]` smoothing segments at ~33 Hz
  toward the next tick's value. Phase: sync-anchored by default —
  `phase01 = ((leader_now_ns / period_ns) + p) % 1` recomputed from the
  clock at every tick (never integrated), so a re-applied identical LFO is
  bit-identical in phase. If `sync_state.synced()` is false, use local
  monotonic. `f` (free): one random phase offset chosen at `apply`.
  Shapes: `sine` (min..max), `tri`, `saw` (rises min→max), `square`
  (half period high=max), `sh` (new random value in [min,max] each period),
  `drift` (smoothed random: interpolate between per-period random targets).
  `c:` shapes tri/saw/drift segment interpolation; ignore elsewhere.
- **`current_value(identity)`** returns the generator's computed output now
  (constants included; None for never-touched identities). A completed
  fade's stored value is its final destination. This is the catch-up hook —
  no wire behavior in this stitch, just an accurate accessor.
- Thread-safe `apply` vs scheduler tick (one lock; emissions outside the
  lock where practical).

## Deliverable 2 — bopos.py wiring

In `handle_lan_datagram`'s `/p/*` relay path (the `relay.shape_provided_term`
branch): after shaping, consult the active manifest declaration for the
qualified identity (`python/manifest.py`; the active patch may have none):

- Declared numeric param, args parse to a non-`set` spec → route into a
  module-level `GeneratorEngine` whose `emit` sends the engine-facing
  message via the existing `relay_provided_term` (same address, new args).
- Declared numeric param, plain 1-element set → `apply` it as a constant
  (kills any running generator) AND relay it verbatim (today's path).
- String/undeclared params, or no active manifest → today's verbatim relay,
  untouched.
- `ParamGrammarError` → log via the module's existing logging/print style
  with the address and reason, drop the message, return True.

Keep changes minimal and localized; do not restructure `handle_lan_datagram`.

## Deliverable 3 — simfleet parity

`tools/simfleet.py` imports `paramgen` (same `sys.path` mechanism as
`identity`/`pointfield`). Each simulated device gets its own
`GeneratorEngine` whose `emit` updates `device.params[member]` and logs
`p/<member>=<value>` exactly like today's plain-set path (spatial verifies
read that log format — do not change it). Route received `/p/*` args through
the same declared-numeric check + parser; plain sets behave byte-identically
to today; grammar errors log `p/<member> grammar error: <reason>` and drop.
Devices that are simulated as unresponsive stay unresponsive.

## Verify script (new)

`.loom/threads/16-param-automation/automation-1-engine-and-parity.stitching/verify_param_automation.py`
— browser-free, run with `~/.venvs/bopos/bin/python`. Locate the repo by
walking up to `tools/simfleet.py` (never fixed `..` hops). Two layers:

**A. Direct module tests** (import `python/paramgen.py`): parser accepts
each grammar form and both option spellings; rejects odd ≥5, bad units,
misplaced `p:`/`f`, unknown keywords. Engine with a fake `emit` collector
and fake clock: fade segment emissions (2-element pairs), curved
subdivision, int single-emission-per-crossing (up and down), loop
snap-back, stop freeze, `current_value` mid-fade and after completion,
sync-LFO phase determinism (same fake leader clock ⇒ same emissions on
re-apply), free-LFO phase differing across applies (seeded).

**B. Wire tests through simfleet**: start `tools/simfleet.py --devices 1`
on random loopback ports with a manifest declaring an `f` and an `i` param
(copy the fixture pattern from
`.loom/tied/1-protocol-node/verify_group_protocol_node.py` or the newest
browser-free tied verify); send real UDP OSC: a plain set (log format
unchanged), a 3-element fade (device value reaches the destination), `stop`,
an `lfo`, and a grammar error (logged, dropped, device still alive to a
follow-up plain set).

`check()`/exit-code shape as in the tied verifies.

## Acceptance checks (run these; all must pass)

```sh
~/.venvs/bopos/bin/python .loom/threads/16-param-automation/automation-1-engine-and-parity.stitching/verify_param_automation.py
~/.venvs/bopos/bin/python .loom/tied/1-contract-model-relay/verify_param_contract_relay.py
~/.venvs/bopos/bin/python .loom/tied/1-protocol-node/verify_group_protocol_node.py
~/.venvs/bopos/bin/python .loom/tied/boundary-3-framework-slimdown/verify_framework_slimdown.py
python3 -m py_compile python/paramgen.py python/bopos.py tools/simfleet.py
```

If a tied verify fails because of a legitimate behavior change, STOP and
record it in the report instead of amending — plain-set behavior must not
change, so any tied failure is a regression in your change.

Do not commit. Do not run loom.sh or touch `.loom` state beyond writing into
this stitch directory. Write a report to
`.loom/threads/16-param-automation/automation-1-engine-and-parity.stitching/codex-report.md`:
what you built (per deliverable), grammar/engine decisions you had to make
beyond the spec, verify output, anything not done. If you could not complete
the task, say so explicitly.
