# Delegate spec — 4-cue-retirement, lane A (backend sweep)

Lane A is the mechanical deletion sweep: Python, tools, docs, patch manifests.
**Lane B (the browser UI — `dashboard/static/`) is the orchestrator's and is
being done in parallel. Do not touch `dashboard/static/`.**

## Goal

Delete `/cue` outright. Hard break: no compatibility shim, no deprecation
path, no migration of show documents. `/e/*` (shipped in the previous commit,
contract v1.14) is the replacement in full.

## Files you may touch

    python/bopos.py
    python/manifest.py
    python/sync_node.py
    dashboard/osc_bridge.py
    dashboard/show_engine.py
    dashboard/state.py
    dashboard/server.py
    tools/simfleet.py
    tools/audition.py
    tools/sync_measure.py
    docs/OSC-CONTRACT.md
    patches/bonks-pd/bopos.patch.json
    patches/demo-pd/bopos.patch.json
    patches/fire-button/bopos.patch.json
    patches/README.md
    .notes/pd-edits-for-bob.md
    tests/**.py

Nothing else. In particular: no `.pd` files, nothing under `.loom/`, nothing
under `dashboard/static/`, and not `dashboard/shows/test.json`.

## The sweep

| file | what goes |
|---|---|
| `docs/OSC-CONTRACT.md` | the `/cue` planes-table row, its §3.1 entry, the §8 `cues` manifest key, the §4.2 engine term. The "two framework addresses that omit the selector" grammar note becomes **one** (`/sync/ping` alone). Add a v1.15 changelog row for the retirement. |
| `python/manifest.py` | delete the `cues` block and `CUE_ID` outright. Event `arity` becomes **0–3**, not 1–3 — a cue is a zero-element event. |
| `python/bopos.py` | the `parts == ["cue"]` dispatch, `fire_cue_to_engine`, the `cue_scheduler` instance and its start/stop |
| `python/sync_node.py` | residual cue naming and the `CueScheduler = EventScheduler` alias. **`CUE_LATE_GRACE_NS` stays** — keep the name and its comment; it governs scheduled *event* fires. |
| `dashboard/osc_bridge.py` | `fire_cue`, `fire_cue_now` |
| `dashboard/show_engine.py` | the `/cue` address branch. `/e/<identity>` messages route to `bridge.fire_event(...)` with the step's targets and `event_lead_ms()`. |
| `dashboard/state.py` | residual cue naming |
| `dashboard/server.py` | rename the websocket commands (contract below); drop cue plumbing from the roster/manifest payloads |
| `tools/simfleet.py`, `tools/audition.py` | `handle_cue` / `schedule_cue` / `fire_cue` / `dispatch_due_cues` and the `/cue` dispatch |
| `tools/sync_measure.py` | **not in the original sweep list, but it breaks without this.** It fires cues and parses the node log line. Migrate: fire `/all/e/m<n>` via the `/e/*` shape, parse `event (\S+) …fire_mono=(\d+)`, rename the `--cues` flag to `--events` and the report's "cue spread" to "event spread". |
| `patches/*/bopos.patch.json` | the three manifests declaring `cues` migrate to zero-arity `events`: `bonks-pd` → `bonk`, `demo-pd` → `snap`, `fire-button` → drop the empty list. Keep label/description as the event's `labels` are per-element — use `name` for the human label. |
| `patches/README.md` | documentation of the `cues` key → `events` |
| `.notes/pd-edits-for-bob.md` | append: `pd/bopos~.pd` and `pd/bop/babs/babs.blineseq.pd` need `/e/<identity>` receivers **and the `/cue` receiver is now dead**; name `patches/bonks-pd` (`/e/bonk`) and `patches/demo-pd` (`/e/snap`) explicitly as the two in-repo patches whose receivers break until Bob adopts. |

## Websocket command contract (lane B depends on this exactly)

Rename, keeping validation behaviour:

- `set_cue_lead` → `set_event_lead`, payload `{ms}`, clamp 0..10000, writes
  `state.data["event_lead_ms"]`.
- `fire_cue` → `fire_event`, payload
  `{selector: str, identity: str, elements: [float], lead_ms: int}`.
  Validates `identity` against the `/p/*` segment grammar (reuse
  `patch_manifest.PARAM_NAME` / `MAX_PARAM_SEGMENTS` /
  `MAX_PARAM_IDENTITY_BYTES`) and `len(elements) <= MAX_EVENT_ARITY`; on
  failure sends the usual `{"type": "error"}` frame. Calls
  `self.osc.fire_event(selector, identity, elements, lead_ms)` and broadcasts
  `event_scheduled` with `{selector, identity, elements, shared_time_ns:
  str, lead_ms}`.
- `fire_editor_cue` → `fire_editor_event`, same validation, edit-mode gated as
  today, fires with `lead_ms=0` (the sentinel — the editor wants immediacy),
  broadcasts `editor_event_fired` with `{identity, shared_time_ns: str}`.

## Boundaries

- Do not add a compatibility shim or an alias for any deleted name.
- Do not touch `.loom/`, `.pd`, `dashboard/static/`, `dashboard/shows/`.
- Lane B is editing `dashboard/static/js/*.js` concurrently — if a JS file
  seems to need a change, leave it and say so in your summary.

## Acceptance checks

- `tools/run-tests.sh fast` green. Update any test that pins `/cue`; do not
  delete a test to make it pass, and say so in your summary if you change
  an assertion's meaning.
- `grep -rn cue python/ dashboard/*.py tools/` returns **only**
  `CUE_LATE_GRACE_NS` and its comment.
- `grep -rn '"cues"' patches/ python/ dashboard/*.py` returns nothing.
- `~/.venvs/bopos/bin/python .loom/tied/3-event-plane-wire/verify_event_wire.py`
  still passes (the `/e/*` plane must be undisturbed). If your sandbox
  forbids binding UDP, say so — the orchestrator will run it.

Report what you changed, how you verified it, and anything you could not do.
If you could not complete the task, say so explicitly.
