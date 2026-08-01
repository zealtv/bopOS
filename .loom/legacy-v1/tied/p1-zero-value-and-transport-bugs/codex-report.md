# Codex report — p1 zero-value and transport bugs

## Changes

1. **Zero-valued parameters:** `renderParamBuilder()` now reads the raw stored
   argument and resolves it with
   `message.args?.[0]?.value ?? declaration.default ?? ""`. A stored numeric
   `0` or stored empty string therefore wins over the manifest default.
2. **Rapid transport clicks:** `sendTransport()` now applies the specified
   optimistic transition to local `playback.steps`, renders it, and then sends
   the WebSocket verb. Start, stop, pause, resume, and stop-all are covered;
   resume also resets `playbackAt`. The next server `show_playback` broadcast
   remains authoritative and replaces the optimistic state wholesale.
3. **Next glyph:** `.show-glyph-next` is now a 15 x 12 px `play-to-bar` drawing
   made from a 10 px triangle and a 3 px terminal bar in `currentColor`, clearly
   distinct from the standalone play triangle.
4. **Stable title position:** `.show-step-transport` reserves the 94 px
   three-button worst-case width and does not flex, so the alias column has the
   same x position for stopped and playing rows.
5. Added `verify_show_polish_bugs.py`, using the real dashboard, simfleet,
   random loopback ports, and headless Chromium. It covers all six checks in
   the task specification.

## `||` fallback audit

| File / site | Result | Reason |
|---|---|---|
| `show.js` `renderParamBuilder()` stored arg -> declaration default -> empty | **Changed to `??`** | Both numeric `0` and string `""` are legitimate stored parameter values and must not fall through. Reading the raw arg preserves the missing-vs-empty distinction. |
| `show.js` `applyModeDefault()` declaration default | Left as existing `??` | Already preserves `0` and `""`. |
| `show.js` `renderRawArg()` and raw-arg change handler | Left as existing `??` | Already preserves `0` and `""`. |
| `show.js` `renderPointBuilder()` via `numberAttr()` | Left alone | `Number.isFinite()` preserves zero and uses the supplied default only for a non-number. |
| `show.js` `secondsParts()`, `typedArg()`, and `readDuration()` numeric `Number(value) || 0` sites | Left alone | Falsy numeric zero produces the same intended zero; the fallback only normalizes empty/invalid numeric input to zero. |
| `show.js` play-count parsing `Number(value) || 1` | Left alone | Zero is invalid here (`play_count` has a minimum of 1), so falling back to 1 is intentional. |
| `show.js` cue argument -> `""` | Left alone | Cue IDs are required strings; numeric zero is not a valid cue ID and empty already means no selection. |
| `show.js` identity/address/type/name/alias/label fallbacks | Left alone | These are string identifiers or presentation labels where empty means missing (or is deliberately normalized to `/`, `null`, or a label). |
| `show.js` declaration/object/list/HTML fallback chains | Left alone | These choose objects, arrays, catalog entries, or empty-state markup rather than stored scalar parameter values. |
| `facilitator.js` `valueForSeat()` and `aggregateValue()` | Left as existing `??` | Seat live-control values already preserve both `0` and `""`. |
| `facilitator.js` mixed range fallback | Left as existing `declaration.default ?? declaration.min ?? 0` | Already preserves a zero default/minimum. |
| `facilitator.js` cue lead `Number(lead.value) || 500` | Left alone | Zero is outside the permitted 100–10000 ms range, so treating it as invalid is intentional and unrelated to live parameter values. |
| `dashboard.js` editor tree `values?.[identity] ?? item.default ?? ""` | Left alone | Patch-editor live parameter values already preserve `0` and `""`. |
| `dashboard.js` manifest min/max/default inputs | Left as existing `??` | Manifest numeric zero already survives rendering and editing. |
| `dashboard.js` remaining `value || ...` candidates (filters, status labels, hostname, byte/time formatting) | Left alone | They are non-parameter presentation/status fallbacks, or normalize an invalid/empty numeric input to zero without changing a legitimate zero result. |

No changes were needed in `facilitator.js` or `dashboard.js`.

## Verification

All requested commands were run with `~/.venvs/bopos/bin/python` and passed:

| Verifier | Result |
|---|---|
| `p1-zero-value-and-transport-bugs.stitching/verify_show_polish_bugs.py` | 6 checks, `0 failure(s)` |
| `.loom/tied/4-tab-ui/verify_show_tab.py` | 8 checks, `0 failure(s)` |
| `.loom/tied/5-inspector/verify_show_inspector.py` | 9 checks, `0 failure(s)` |
| `.loom/tied/5b-compact-rows/verify_show_compact.py` | 12 checks, `0 failure(s)` |
| `.loom/tied/5c-target-model-and-picker/verify_show_targets.py` | 10 checks, `0 failure(s)` |
| `.loom/tied/6-message-editing/verify_show_editing.py` | 18 checks, `0 failure(s)` |
| `.loom/tied/6b-show-management/verify_show_management.py` | 11 checks, `0 failure(s)` |

Additional static checks:

- `node --check dashboard/static/js/show.js` — pass
- `git diff --check` — pass

An initial regression invocation was denied loopback binds by the command
sandbox (`PermissionError: Operation not permitted`). Direct PTY/non-login
invocations were allowed; all exact acceptance scripts then ran and passed.
This was an execution-context issue, not a test or product failure.

## Tied-verifier amendments

None. The fixed transport width remains within the existing compact row and
viewport budgets, and all tied selectors/layout assertions passed unchanged.

## Incomplete or unverified work

Nothing required by this software-only stitch remains incomplete. No hardware,
audio, touch-device, or Pure Data verification was required, and no `.pd` file
was touched.
