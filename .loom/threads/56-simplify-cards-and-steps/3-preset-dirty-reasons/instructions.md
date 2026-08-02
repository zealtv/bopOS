# 3-preset-dirty-reasons

**BUG.** `preset_dirty` is a boolean standing in for three unrelated causes, so
three different situations needing three different operator responses all render
as the same appended `*`.

Raised independently by two of the three UX consultants, then **verified in
code** (2026-08-02):

| cause | where | what it means | what the operator should do |
|---|---|---|---|
| a value moved | `preset_application.py:274-291` | you nudged a fader, or automation is running | save, re-apply, or ignore — it's yours |
| the preset can't be read | `server.py:1979-1981` (store error → `True`) | the file is missing or unreadable | the preset is GONE; saving overwrites nothing, re-applying fails |
| the seat is on a foreign patch | `preset_application.py:269-271` | this panel doesn't control that seat's patch | neither save nor apply is meaningful |

Bob asked for exactly this legibility, from the interface side:

> I think part of this comes back to it being clear when a preset is dirty. I
> think we might need a clearer visual representation of that.

## Scope

**Host-side first, and possibly only.** The minimum honest fix is that
`preset_dirty` carries a *reason* rather than a boolean, and
`refresh_preset_dirtiness` records which branch it took. That is small,
testable without a browser, and unblocks the UI work without prejudging it.

Note this is **independent of `1-capture-retirement`** — the flag is computed for
the display on every `public_state`, so removing capture does not touch it.

## Explicitly NOT this stitch

The **visual treatment**. It belongs to `53-ui-niggles/3-preset-dropdown-menu`,
which is already rebuilding that exact control (dirty `*` and drift `⚠` move to
the front of the label because a native `<select>` ellipsises the tail, and the
control becomes a disclosure menu). Do that work there, consuming the reasons
this stitch produces. Land the two in that order or the menu gets rebuilt twice.

Two consult findings to hand over rather than act on here:

* Both the interaction and systems consults **decline Bob's suggested column
  border** for this state, on the same grounds: §18/D1 made the column *be* the
  card and deleted exactly that kind of tint. Under R1 the card is one target,
  so a card-level treatment is at least truthful now — but it is still a design
  call for `53/3`, not a foregone one. Bob has not ruled.
* **No new colour.** `cyan = modulation` is ratified and the consults were
  unanimous that fault states must not borrow it. `--amber` is already the
  preset row's warn ink.

## Verify

Browser-free unit coverage in the appropriate `tests/` module: each of the three
causes produces its own reason, and a clean applied preset produces none.
Include the case where a preset file is deleted underneath a seat that has it
applied — that is the branch most likely to regress silently, because it lives
in an exception handler.
