# 5-cards-implementation

Build what `4-cards-design` ratified. **Blocked until Bob ratifies it** — a hard
dependency is recorded at `needs/4-cards-design`.

**Expect to split this before starting.** It is one stitch today only because
its shape depends on a design that does not exist yet. On the evidence so far it
is at least four separable pieces, and `08-control-tab-columns` is the worked
precedent for why bundling them is a mistake — it was split for exactly this
reason, and then its `4-n-columns` child was split again:

* the grid layout and derived ordering (R2/R3);
* the single-target collapse in `TargetPicker` and its consumers (R1) — note
  `SeatFilter` was already deleted by `07`, so this is the same seam a second
  time;
* the Control/Remote convergence (R4), which is a cross-document change;
* the state/persistence change replacing `bopos.control.columns`, which likely
  turns several existing guards into deletions.

Split it once the design is ratified and the real seams are visible, rather than
guessing the shape now.

## Carry-forwards

* `1-column-scroll` (commit `a99e982`) is expected to be **partly retired** here
  — see `4`'s question 6. `tests/verify_control_column_scroll.py` should be
  re-aimed or deleted deliberately, with the reason recorded. Its Remote half
  may survive as a regression guard. Do not treat its removal as a regression.
* Gotchas 19 and 20 (a target identifier is not an element identifier; a
  fragment-only `page.goto` does not reload) were written for N columns with
  minted per-column ids. Under R1 identity may become the target itself. If
  that happens, say so in `decisions.md` — the CLAUDE.md gotcha list is read by
  every later session and a stale entry sends people hunting a solved problem.
* `08/4/3` found that a `device_update` heartbeat can beat the initial `state`
  and make a restored layout prune itself permanently, gated behind
  `venueKnown`. If persistence changes shape, re-check that hazard rather than
  assuming the gate still covers it.
