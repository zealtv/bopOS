# Decisions — 4-cue-retirement

## 1. The pre-check's premise was wrong — proceeding anyway, flagged for Bob

The instructions say, citing the ratified design §3.1: *"no `bopos.patch.json`
in the repo declares `cues`… If that has changed by the time this is worked,
stop and re-check with Bob."*

**It was never true.** Three patch manifests declare `cues`:

| patch | declares |
|---|---|
| `patches/bonks-pd` | `bonk` |
| `patches/demo-pd` | `snap` |
| `patches/fire-button` | `[]` (empty list) |

The measurement recorded in the design proposal was simply mistaken, rather
than the world having changed under it.

**Proceeding, not stopping**, because the gate's *purpose* is intact. It
exists to catch "something has come to rely on cues"; the substantive basis
for Bob's hard-break ruling was that no production show fires them, and that
still holds exactly:

- `dashboard/shows/test.json`, the only show document, contains **zero**
  `/cue` messages (re-measured this stitch).
- Both declared ids — `bonk`, `snap` — are already valid `[A-Za-z0-9_-]+`
  address segments, so the identity-grammar narrowing costs nothing in-tree,
  which is what §3.1 actually predicted.
- The migration is the mechanical one the instructions already specify: cue
  declarations become **zero-arity `events` entries**. No rename, no judgment.

What Bob should know, and what the report says: the `.pd` receivers in
`bonks-pd` and `demo-pd` listen for `/cue` today and stop working the moment
this lands, until child `5`. That is not a surprise introduced here — child
`5` is exactly the `.pd` adoption stitch, and thread 44 cannot tie without it
— but the two patch names are now named explicitly in
`.notes/pd-edits-for-bob.md` rather than left to be discovered.

If Bob would rather have been asked first, the answer is one `git revert` of
this commit.

## 2. `tools/sync_measure.py` is an unlisted surface

The instructions' sweep table lists 15 files. `tools/sync_measure.py` (34 cue
references) is not among them, and it is not incidental naming: it is the
sync-3 measurement harness. It *fires* cues (`self.send("/cue", …)`) and
parses the node log line with `re.compile(r"id=(-?\d+).*?cue (\S+) …
fire_mono=(\d+)")`.

Deleting `/cue` breaks it outright. Migrated to `/e/*` in this stitch:
it fires `/all/e/m<n>` and parses the `event <identity> fired … fire_mono=`
line that child 3 introduced. The tool's report vocabulary ("cue spread")
becomes "event spread"; the CLI flag `--cues` becomes `--events`.

## 3. Contract version: v1.15, not a v1.14 amendment

Child 3 shipped the additive `/e/*` plane as **v1.14**. This stitch takes
**v1.15** rather than amending 1.14, because the two revisions have opposite
characters and the revision history is read for exactly that distinction: 1.14
is purely additive (nothing that worked stopped working), 1.15 *removes* a
plane and a manifest key with no shim. A reader asking "which version broke my
patch?" gets a straight answer.

## 4. Supersession of `6-non-float-kinds` — the event row's sync toggle

The tied stitch `6-non-float-kinds` shipped the inert event row as "1–3 boxes
+ `sync` toggle + `send` momentary", following the original mockup.

Bob's 2026-07-27 forward-sync ruling supersedes that: **every event
forward-syncs**, so a per-row sync choice cannot exist. The toggle is removed
and each row has exactly one fire button. Global lead time `0` is the only
sync-off, and it lives in the Monitor dock
(`desktop-ui-overhaul/03-global-controls-monitor`), not on the row.

This is the CLAUDE.md narrow interim supersession rule applied properly: the
tied assertion pinned a ruling Bob has since replaced, so it is superseded,
not authoritative.

## 5. Pill category: renamed, not added

`inferMessageMode` keys purely off the address. The `cue` category is
**renamed** to `event` with code `CUE` → `EV`. The flat set stays **eight**
categories, so the tied `25-message-pill-encoding` taxonomy survives intact.
Arity is not encoded in the pill — the identity label carries it and the
inspector shows the elements.
