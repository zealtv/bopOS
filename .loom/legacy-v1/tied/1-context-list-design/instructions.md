# 1-context-list-design

Design how multiple asset slots are modelled and how the slot set reaches the
engine as a list of absolute folder paths. Written proposal, **Bob ratifies**,
then tie with the ratified design as `decisions.md`.

## Decide

- **Slot model.** What is a slot — a top-level directory under `assets/`? An
  arbitrary registered path? How are slots added/named/ordered? Is ordering
  significant to the engine (search order)?
- **Context wire form.** How `bopos-context assets …` carries a *list* of
  absolute paths: repeated atoms, an indexed set of terms, a count+paths, etc.
  Keep it consumable by both PD and the SC engine. Absolute paths, device-local.
- **PD receiver impact.** Exactly what `bopos~.pd` / the `bopos-context`
  receiver must change to accept the list. This is a Bob PD edit — write the
  spec into `.notes/pd-edits-for-bob.md`; the implementation stitch stays
  `.waiting` on it if the engine can't consume the new form without it.
- **Compatibility.** Single-root today vs list: migrate cleanly, or keep the
  one-atom form working as a one-element list. State the call.
- **Contract amendment.** The precise `docs/OSC-CONTRACT.md` §4.2 / run-context
  edit, versioned (next contract rev after v1.8).
- **Touch surface.** `bash/start-engine.sh` (`bopos-context assets` line +
  `BOPOS_ASSETS`), `python/bopos.py` (`ASSETS_ROOT`, `installed_assets`),
  `python/runcontext.py`, and whatever the Assets workspace shows.

## Deliverable

`decisions.md` here; the PD-edit spec in `.notes/pd-edits-for-bob.md`; update the
parent + un-`.waiting` `2-multi-pack-implementation`. Lore item if the artifact
is worth keeping whole.
