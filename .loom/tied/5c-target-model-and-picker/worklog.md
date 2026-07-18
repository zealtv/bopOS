# 5c-target-model-and-picker worklog — 2026-07-18

Message targets become selector lists with a direct chip picker.

## Model (`dashboard/show_model.py`)

`clean_target` now accepts a non-empty list of selectors (`"all"`, seat id,
`"g<id>"`); a legacy single string is normalized to a one-item list, exact
duplicates collapse (order preserved), and any list containing `"all"`
collapses to `["all"]`. Empty lists are invalid — the UI guarantees at least
one selection by falling back to All. Design note amended (appended
"Amendment — 2026-07-18, stitch 5c" section; history untouched).

## Engine (`dashboard/show_engine.py`)

`_send_message` fans `/p/` messages out as one `set_param(selector, ...)`
call per listed selector. Per the instructions, no set-algebra: a seat
covered both directly and via a listed group receives the (idempotent,
full-state) write twice — noted in a code comment. `/cue` and `/pt` still
ignore `target`. Tolerates a legacy string target at runtime.

## Picker UI (`static/js/show.js`, `static/css/style.css`)

Replaced the dropdown with toggle chips inside a Target section:
an **All** chip, group chips with GROUP_SLOTS swatch colours (slot colour by
catalog index % 4, matching the four-slot rail precedent), and a numbered
seat-chip roster bounded to 132px with overscroll containment (the
seat-roster idiom). Selected targets also render as removable ×-chips in a
summary row, and the terse form (`3+7+g1`) shows in the section header, the
wire preview, and pill titles.

Interface reasoning (Bob delegated the call): I considered making the
summary row the only representation (chips appear as you add from a
palette), but toggle-state-on-the-roster is one tap per change, shows
availability and selection in the same place (Ableton-style), and never
needs a modal; the summary row adds glanceable "what's selected" plus
one-tap removal without hunting the roster. Kept both — they're cheap.

Toggle semantics: tapping All → `["all"]`; tapping a seat/group while All is
selected replaces All with that selector; toggling off the last selector
falls back to `["all"]`. Greyed (disabled section) for cue/point payloads as
before.

## Verify

- `verify_show_targets.py` (this dir): real server + **3 sim devices** bound
  to seats 1–3, group g9 = {seat 2}. Waits for sim2's persisted membership
  ack, then via the chip UI: legacy string target renders as All; seats 1+3
  toggled → play → sim1 & sim3 log `p/gain=0.77`, sim2 receives nothing;
  add g9 → play → sim2 receives via the group datagram; saved show file
  normalizes to `["1","3","g9"]`; removing all summary chips falls back to
  All; cue mode greys the picker; no page errors. **0 failures.**
  Screenshot: `target-picker.png`.
  (Gotcha: sim hostnames follow seat names after assignment, so the fleet
  log filter matches the ` id=<n> ` token, not `simN`.)
- Amended tied verifies (target is now a list / dropdown became picker):
  - `2-model-and-persistence/verify_show_model.py`: three `== "3"` target
    equalities → `== ["3"]`. 0 failures.
  - `5-inspector/verify_show_inspector.py`: greyed-target check now asserts
    the disabled picker section. 0 failures.
- Re-ran untouched tied verifies `3-playback-engine` (all passed),
  `4-tab-ui`, and `5b-compact-rows` (0 failures each).
