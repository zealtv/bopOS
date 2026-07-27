# Decisions — event plane and kind grammar

Bob ratified the proposal on 2026-07-28. The contract revision is **v1.14**.

## Ratified as proposed

- **The `kind` grammar** — `float` / `int` / `toggle` / `enum` / `text`
  replacing `type: i|f|s` plus inferred enums, as a hard break. `type` becomes
  invalid and is rejected loudly (the `role` precedent), not silently ignored.
- **Events stay a separate top-level manifest list**, not a sixth `kind` in
  `params`. Reason on the record: params are replayed on reconnect, and an
  event that replays fires at hardware — an output-safety defect of the
  thread-29 family. A separate list keeps every existing param loop correct by
  construction.
- **BOB-1 — `text`** is the fifth kind's name (not `string`).
- **BOB-2 — identity lives in the address**: `/<selector>/e/<identity>`, with
  the `[A-Za-z0-9_-]+` segment grammar and nesting that `/p/*` uses. The
  narrowing from the old permissive `cueId` costs nothing in-repo (measured:
  zero declared cues, zero `/cue` show messages).
- **BOB-3 — no show-document migration.** Nothing exists to migrate; a
  `SCHEMA` bump would have been dead code on arrival. A `/cue` message in a
  hand-authored document fails validation loudly like any other unknown
  address.
- **BOB-4 — pill code `EV`.** The `cue` category is renamed to `event`, not
  joined by one; the flat set stays eight, so the tied
  `25-message-pill-encoding` taxonomy survives intact.
- **Lead `0` uses a sentinel**, not the late-grace window: `sharedTimeNs` of
  `"0"` means fire on arrival and bypasses the scheduler. This makes "global
  lead 0 is sync-off" exact rather than dependent on the hop landing inside
  `CUE_LATE_GRACE_NS` (50 ms).
- **`cue_lead_ms` → `event_lead_ms`** with a load-time fallback read of the old
  key (settings loading, not a wire shim).

## BOB-6 — sequencing

Bob: "don't mind — I'm mostly working sequentially." So the children run in
order rather than branching `41-preset-primitive` off early. 41 stays behind
the whole thread; if a later session wants to parallelize, child `2` is the
only prerequisite it actually has.

## BOB-5 — PD adoption

Not a fork, and left open deliberately: the `bopos~.pd` / `babs.blineseq.pd`
receiver change is **Bob's edit** (house rule — agents never touch `.pd`). It
is written to `.notes/pd-edits-for-bob.md` by child `3` and adopted in child
`5`. The software children tie on software gates; real PD reception and
audible timing are a hardware adoption check on the Finn Jet + Ciro Toast rig
and must be stated as such, not claimed.

## New scope Bob added this session — the `text` kind's UI

Bob: "we currently don't have any UI for strings. That can be put off to later
but if strings are in the contract, they should be implemented in the manifest
and given styled control panel components in the future."

Measured state: the control surface **does** render a string param today —
`declaration.type === "s"` maps to a `"string"` shape and a plain
`<input type="text">` ([dashboard/static/js/control-surface.js:282,352]) — but
it is excluded from aggregation and automation, and the tied
`6-non-float-kinds` slice covered toggle/int/enum/event and **skipped strings
entirely**. So there is an unstyled control, not no control.

Split accordingly:

- **manifest side is not deferred** — `text` is a first-class kind in child
  `2`, validated like any other.
- **styled control side is deferred** — child `6-text-kind-control`, kept in
  this thread per Bob's instruction, working from the ratified design language
  in the tied `2-control-panel-design`.

## Consequence for already-shipped work

The tied `6-non-float-kinds` shipped the inert event row **with a sync
toggle**, per the original mockup. The forward-sync ruling removes it — every
event forward-syncs, so there is one fire button per row. Child `4` drops the
toggle. This is a superseding ruling, not a regression in that stitch.
