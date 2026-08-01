# Decisions — 6-non-float-kinds (2026-07-27)

Authority for everything below: the tied `2-control-panel-design` stitch
(`control-panel-design.md` §2 and its Q1–Q4 rulings). These are the calls this
stitch had to make on top of it, plus the two that want Bob.

## 1. The enum manifest shape (additive)

```json
{"name": "mode", "type": "i", "options": ["dry", "hall", "plate"], "default": 1}
```

- `options`: 2–64 unique labels, 1–32 characters, no newlines. Only on
  `type: "i"`.
- **`min`/`max` are derived** (`0`…`n-1`), not authored. An absent pair is
  filled in by the validator; an authored pair that *agrees* is accepted so a
  manifest the editor saved round-trips; one that disagrees is invalid.
- Deriving the range is what makes Q2 ("enums automate like ints") free: the
  §3.2 generator path, the quantization, replay, presets and the wire are all
  the integer ones, unchanged. The labels are read only by the control
  surface.
- Not chosen: a new `type: "e"`, or a `kind` field. `44-event-plane` is
  explicitly chartered to settle the kind grammar (its question 1), and a new
  type value would have to be honoured by every manifest consumer today for a
  presentation difference. `options` is reversible into whatever 44 ratifies.

## 2. The event manifest shape (provisional — 44 owns it)

```json
"events": [{"name": "note-on", "arity": 2, "labels": ["note", "velocity"],
            "defaults": [64, 127], "dashboard": true}]
```

A **top-level list beside `params`**, not a param type. Rationale: an event is
not a `/p/*` value, and putting it in `params` would leak it into every
consumer of the parameter schema (Seat replay, presets, the Show message
builder) that has no idea what to do with it. The same logic governs the
server surface: `live_controls.events`, folded into the rendered row list by
each host at the point of render.

`arity` 1–3, optional `labels` and `defaults` of exactly that length,
identity qualified exactly like a param and forbidden from colliding with one.

**Nothing is sent.** The row renders with `disabled` buttons and carries no
`data-live-param`, so there is no binding that could reach the wire. Whether
events live on `<target>/e/*` or extend `/p/*`, how `sync` expresses forward
synchronization, and what a preset stores for one are 44's to ratify — this
stitch exists so 44 designs against a surface that already exists, per the
design's own instruction.

## 3. Contract documentation

`docs/OSC-CONTRACT.md` §8 now documents both fields, `options` as additive
with **no wire change** and `events` as *declared but not wired*, each
naming 44 as the ratification vehicle. Rationale: the validator now enforces
them, and §8's whole point is that the manifest cannot silently drift from
its validator. Flagged for Bob as documentation of shipped validator
behaviour, not a contract amendment.

## 4. Deviations from the mockup's panel 3 — for Bob

- **The toggle button spans the value + slider columns** rather than the
  mockup's fixed 96px. The mockup's 96px sat beside an annotation column that
  does not exist in the shipping panel, and an empty 58px value column is
  exactly the wasted space the overhaul is removing. The ∿ icon still lands in
  the same column as every other row, which is the alignment that matters.
- **The `auto·mixed` word legend is retired** from the toggle and enum rows.
  It had no cell in the new grids, and `4-row-regrind` had already ruled the
  equivalent question for the numeric row: the hatch is the state, the words
  live in the accessible name.

## 5. Open question for Bob — the flashing toggle

The design says a generator-driven toggle "flashes its live value". The
heartbeat re-render is far slower than an LFO, so the value alone
under-reports it. What shipped: under an **LFO** the button face animates at
the generator's own period, phase-anchored by `--auto-elapsed` like the
slider marker. The crossing *rate* is exact for any symmetric shape and the
phase is anchored, but the **duty cycle is a fixed 50%** rather than the true
threshold crossing of an asymmetric shape (a skewed saw, a pulse with a
non-centred min/max window). Fades and loops are not periodic, so they show
the heartbeat value with the modulation ink and do not flash.

The honest alternative is computing the modulated value client-side per frame
(what the fade animator does), which is a real chunk of work for a control
with two states. Recommend keeping the approximation; Bob may disagree, and
`44-event-plane` is a natural place to revisit it alongside the other kinds.

## 6. Pre-existing flake, not this stitch

`tests/verify_control_surface_component.py`'s three **reload**-persistence
accordion checks (from `5-hierarchy-and-persistence`) fail intermittently on
clean `main` — confirmed by stashing this work and running the file three
times (1 pass, 2 fail). The heartbeat-re-render persistence check beside them
is stable; it is the post-`page.reload()` trio that races. Left alone here
rather than repaired inside an unrelated stitch.
