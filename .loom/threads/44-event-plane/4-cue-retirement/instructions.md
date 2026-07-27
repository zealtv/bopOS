# 4-cue-retirement

Delete `/cue`. Authority: tied `1-event-plane-design` (proposal §§5–6,
decisions.md). Bob's ruling: **hard break, no compatibility shim, no
deprecation path** — no production shows rely on cues, so keep the code clean.
After child `3`.

**Measured before ratification, and worth re-confirming at the start of this
stitch:** no `bopos.patch.json` in the repo declares `cues`, and
`dashboard/shows/test.json` — the only show document — contains zero `/cue`
messages. The machinery is fully built and completely unused. If that has
changed by the time this is worked, stop and re-check with Bob.

## Sweep (263 references, 15 files)

| surface | what goes |
|---|---|
| `docs/OSC-CONTRACT.md` | `/cue` planes row, §3.1 table row, §8 `cues` key, §4.2 term; the "two framework addresses that omit the selector" grammar note becomes one (`/sync/ping` alone) |
| `python/manifest.py` (18) | the `cues` block and `CUE_ID` deleted outright — cue declarations become zero-arity `events` entries |
| `python/bopos.py` (15) | the `parts == ["cue"]` dispatch |
| `python/sync_node.py` (23) | residual cue naming; `CUE_LATE_GRACE_NS` **stays** (it governs scheduled event fires) |
| `dashboard/osc_bridge.py` (6), `show_engine.py` (6), `state.py` (9) | the `/cue` address branch and remaining naming |
| `dashboard/server.py` (34) | cue command surface, roster/manifest plumbing |
| `dashboard/static/js/show.js` (34) | cue step builder; pill category (below) |
| `dashboard/static/js/dashboard.js` (38), `facilitator.js` (35) | cue trigger buttons → the control panel's events section |
| `tools/simfleet.py` (12), `tools/audition.py` (14) | `handle_cue` / `schedule_cue` |

`pd/*.pd` cue receivers are **Bob's edits** — child `5`.

## Pills

`inferMessageMode` (`dashboard/static/js/show.js:275`) keys purely off the
address, so this is close to a one-line change: `/e/` → `event`. The `cue`
category is **renamed** to `event` with code `CUE` → **`EV`**, not joined by a
second category — a cue *is* an event. **The flat set stays eight**, so the
tied `25-message-pill-encoding` taxonomy survives intact. Arity is not encoded
in the pill; the identity label carries it and the inspector shows elements.

## Control panel

Cue triggering moves onto the control panel's **events section** (the ruled
parameters/events split), targetable at all seats / a group / one seat — which
`/e/*` supports natively and `/cue` never could.

**Drop the sync toggle from the event row.** The tied `6-non-float-kinds`
shipped the inert row as "1–3 boxes + sync toggle + send momentary", per the
original mockup. Bob's forward-sync ruling supersedes that: every event
forward-syncs, so there is **one fire button per row**. Record the
supersession in this stitch's `decisions.md`, naming `6-non-float-kinds` — the
narrow interim rule in CLAUDE.md, applied properly.

No show-document migration (BOB-3): there is nothing to migrate, and a
`SCHEMA` bump would be dead code on arrival. A `/cue` message in a
hand-authored document fails validation loudly like any unknown address.

Verify: full `tools/run-tests.sh all` green; a living journey firing an event
from the control panel's events section at each of the three target scopes and
observing it on the wire via simfleet; `grep -rn cue` over `python/ dashboard/
tools/` returning only the deliberate survivors (`CUE_LATE_GRACE_NS` and its
comment), which is the honest completeness check for a deletion sweep.
