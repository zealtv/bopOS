# 0-prune-fallback-safety

**A live safety defect on the Control tab, today, at one column.** Found by all
three lenses of the `1-columns-design` UX consult, independently; ratified as
D5 (Bob, 2026-07-31). Pulled out of `4-n-columns` because `4` sits behind `2`
and `3`, and leaving a silent target-widening bug on the live surface for the
duration of the thread is not a trade worth making.

*The `0-` prefix sorts it first. That was the agent's call, not Bob's —
reorder freely.*

## The defect

`prune()` (`target-picker.js:271-287`) drops selectors the venue no longer has,
and when nothing survives **and `allowAll` is true it returns `["all"]`**
(line 283). `resolve()` then persists that (lines 300-309).

So a Control target of Seat 7 silently becomes a target of **every seat** the
moment Seat 7 is deleted or renumbered. The fader that drove one seat now drives
the venue — no confirmation, no announcement, and the operator's original
selection is gone from localStorage with it.

The header does change (`All Seats`, `.all-card`'s stronger border, the picker's
terse readout), so it is visible *if you look at the header*. Mid-show the eye is
on the fader. Probability is low — seats and groups are rarely deleted during a
show — but broadening a target without being asked is the one direction a live
control surface must never fail in, and `4` multiplies the exposure by N.

## The fix

The component needs to separate **"All is offerable"** from **"All is the
fallback"**. Today `prune` reaches `[]` only via `built.allowAll === false`
(lines 283-287), which would also remove the All chip from the picker — not what
the Control tab wants.

Add a `pruneFallback` option (`"all"` default, `"empty"` for the Control host).
On empty, the picker keeps its dead selector rather than substituting one, and
the host renders an explicit unresolved state:

```
Seat 7 is no longer in this venue.   [ choose a target ]
```

**No controls rendered** — not disabled controls; there is nothing they could
act on. An empty target is safe; an All target is not.

## Do not break Assets

The Assets tab's advance-to-next-eligible behaviour is deliberate and
documented in the component (`target-picker.js:266-270`): a device that goes
offline while it is the Assets target should be pruned and replaced, not
targeted. That host keeps today's behaviour. This is why the fix is a new
option rather than a change of the default.

## Verify

`tools/run-tests.sh fast` and `browser`. Extend `tests/verify_target_picker.py`
(it already owns the component and is the worked example for the `about:blank`
localStorage trap, gotcha 18): assert that a seat-targeted Control picker whose
seat disappears prunes to **empty and stays empty**, while the Assets picker
still advances to the next eligible device. The Control assertion is the one
that matters — it must fail loudly if someone later restores the `["all"]`
fallback for this host.
