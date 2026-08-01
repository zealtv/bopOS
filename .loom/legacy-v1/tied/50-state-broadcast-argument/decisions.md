# 50-state-broadcast-argument — decisions

## 1. The reported hazard does not exist

`4-current-show-broadcast` recorded that 30 of 33 `state` broadcasts pass the
bare `state.public()` and that this leaves a latent "blank the Control columns"
hazard. It does not, because **`Dashboard.broadcast` discards the payload for
the `state` message type**:

```python
async def broadcast(self, message_type, data=None):
    if message_type == "state":
        data = await self.public_state()
```

`server.py:237`, unchanged in substance since `0551ae2` (2026-07-14) — two
weeks before the finding, and before the stitch that reported it.

**Measured, not read.** A probe delivered all four forms to a fake client:
payloadless, `None`, `state.public()`, `await public_state()`, plus a
deliberately sabotaged `{"live_controls": "sabotage"}`. Every one arrived as the
same enriched snapshot, identical key sets, `live_controls` included and never
the sabotage value. The distinction the finding drew between "bare" and
"enriched" call sites had no observable consequence.

The fix `4-current-show-broadcast` shipped is untouched and still correct: the
two broadcasts really were missing, and `installation.current_show` really was
stale indefinitely. Only the rationale was wrong.

## 2. Why remove the argument rather than just correct the note

The queue already carries a worked example of the cost of a stale note: Tier 2
item 11 (`45-device-enabled-replay-red`) says in as many words that its
incorrect "still red" entry *sent a later session hunting a fixed bug*. This was
the same pathology one step earlier — a note inviting a future session to fix 30
call sites that cannot be fixed, because they do not do anything.

Correcting prose alone leaves the generator of the misreading in place: at a
call site, `broadcast("state", self.state.public())` and
`broadcast("state", await self.public_state())` look like a choice, and reading
them tells you nothing about what is sent. Deleting the argument makes the call
site stop making a claim it cannot keep.

All 37 sites in `server.py` and both in `osc_bridge.py` now read
`broadcast("state")`. `broadcast` and `queue_broadcast` take `data=None`.
This is provably behaviour-preserving because the argument was discarded — and
the guard below is what proves it rather than asserting it.

Five test doubles took a strictly-two-positional broadcast callback and had to
accept the payloadless call: `test_monitor_probe`, `test_osc_transport`,
`test_sync_protocol`, `test_event_plane`, `test_preset_application`. The other
four bridge fakes were already `*_args`-tolerant. Making them uniform is the
point — "a `state` broadcast carries no payload" is now true with no exception.

## 3. The guard, and both halves of it verified

`tests/test_state_broadcast.py`, browser-free, in `fast`.

**Behavioural** (three tests): a `state` broadcast delivers `live_controls`,
`supervisor`, `host_version`, `fleet_patch`, `devices`, `editor` — whatever the
caller passed, including a hostile payload. Confirmed to fail on a weakened
tree: relaxing the coercion to `data if data is not None else …` fails two of
the three on the missing `live_controls` and `host_version`.

**Source-level** (one test): no `broadcast("state"` in `server.py` or
`osc_bridge.py` carries an argument. This is deliberately structural, and the
justification is unusual enough to state: the behavioural tests prove a stray
argument would be *harmless*, which is exactly why nothing else would ever catch
one being reintroduced — and a reintroduced argument is the misreading, not a
malfunction. Confirmed to fail by restoring one payload.

Both halves were checked by breaking the tree and watching them go red, which
is the only way to know a regression guard guards anything
(`23-waveform-marker-guard-regression`).

## 4. Thread 47: the record was stale, and there was a real residual

`47-live-param-kinds-flake` is **tied** (`edb0a5f`, "Preserve live parameter
keyboard focus"), and its named defect was a genuine operator-facing bug —
`renderCards()` replacing a keyboard-focused control — not a test workaround.
CLAUDE.md Tier 2 item 12 still described it as open and undiagnosed. Corrected.

The residual flake the last session met is a *different* instance of the same
family, and it was in the helper that session wrote. `open_authoring` in
`verify_preset_control_surface.py` waited for a binding with

```python
document.querySelector('.live-preset-authoring')?.ontoggle
```

page-wide, while clicking `root.locator(...)` scoped to `#control-column-host`.
`.live-preset-authoring` is a component class and the dashboard document carries
several — `#device-control`'s among them, in an inactive tab where it still
resolves (gotcha 8). So **the wait could be answered by an element other than
the one about to be clicked**, and pass while the target was still unbound. The
sibling helper in `verify_preset_editor.py` was correctly scoped to
`#editor-params` all along, which is why the two files behaved differently. That
asymmetry is what identified it.

That is CLAUDE.md gotcha 17 appearing *inside a fix for gotcha 16* — a
host-scoping error hidden behind a green-looking wait, which is worse than no
wait at all, because it looks handled.

A second window was open underneath: `open_authoring` waited on the
**disclosure's** binding, and the caller then clicked an **action button**.
`bindPresets` reassigns `[data-preset-action]` `onclick` in the same sweep as
`ontoggle`, but a re-render between the helper returning and the click means the
click re-resolves onto a node from a later, not-yet-bound pass. Both files now
route every action through `click_action`, which waits on the button actually
about to be clicked. The shared `bound(page, selector, handler)` helper takes a
host-scoped selector as an argument, so the scope is impossible to omit.

An audit of every other `wait_for_function` + `querySelector` pair in the
browser suite found the rest already host-scoped; this helper was the outlier.

## 5. What is not claimed

Two runs of the full suite passing does not prove a load-dependent flake is
gone. The specific defect above is real, identified by inspection, and fixed;
whether it was the *only* cause of what the last session saw is not established
here. Standalone passes prove nothing about it either way — that is the
signature, not the refutation.

## Verification

See `verification.md`.
