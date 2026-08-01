# decisions — 23-waveform-marker-guard-regression

## The verdict: all four were stale guards. Zero runtime defects.

The stitch framed the central question as "real defect or stale guard?" for each
of the four red guards, and warned that the `07-seats-workspace` binding failure
was "the sort of thing that is a genuine runtime defect rather than a stale
assertion". It is not. Every one of the four traces to a **deliberate later
change** whose commit is identifiable, and in three of the four cases the change
was Bob's own.

| # | red guard | cause | commit |
|---|---|---|---|
| 1 | waveform marker fade progress | the CSS fade progress bar was **retired by design** | `fbea2b0` |
| 2 | `verify_bop_palette` / `verify_theme` | guard mechanics (already repaired by `21-theme-cyan-tint`) | — |
| 3 | `07-seats-workspace` ×2 (`node-moved`, `node-stale`) | heartbeat became a mute-convergence edge | `d23bba0` |
| 4 | `07-seats-workspace` ×1 (copy scrape) | terse-copy pass cut the sentence | `149c794` |

### 1. The waveform marker — the original item

`.loom/tied/automation-5-waveform-marker/verify_waveform_marker.py` waited for
`.seat-card[...] label[data-param-path="fade"] [data-auto-fade-progress]`, which
does not exist anywhere in the codebase — not renamed, *gone*.

`fbea2b0`, "Automated sliders finally move like they mean it"
(`17-automation-polish`, 2026-07-20), says so in its own message: *"the 4x8
marker dot grows into a 12x34 highlight band behind the thumb, **retiring the
fade progress bar**"*, with design authority in that stitch's `design.md`,
amending the automation-4 judgment **at Bob's request**. A deterministic fade now
moves the real slider thumb from a rAF animator driven by `data-fade-*`
attributes on the `<input>`; there is no progress element and no CSS animation to
read a duration from.

So the guard pinned a design Bob had explicitly ruled away — exactly the
"superseded, not authoritative" case in CLAUDE.md. **Repaired in place**, keeping
the subject and changing the mechanism: an in-flight fade must carry a finite
`data-fade-duration`, be anchored to a real start time, carry its segment ramp,
and clear the annotation on completion. 19/19 green.

### 3. The `07-seats-workspace` "binding issue" — not a binding issue

`assertEqual([("node-moved", "unassign")], commands)` got
`[("node-moved", "unassign"), ("node-moved", "mute")]`. The unassign handshake
is intact and correct; there is simply **one more command in the list**.

`d23bba0` ("Complete Dashboard live controls" — Bob, stage 7, persistent
exact-UID device mute) made every non-virtual heartbeat a mute-convergence edge:

```python
if not device.get("virtual"):
    # Heartbeat is a convergence edge. Old nodes safely ignore the
    # additive UID verb and remain publicly unconfirmed.
    self.set_device_mute(uid, self.state.device_muted_for(uid))
```

The guard was pinning the *entire* `uid_command` list when its subject was only
the unassign handshake — so it broke on the first additive convergence verb, and
would break again on the next one. **Repaired** to filter to the `unassign` verb,
which is what it is actually about (sent once, not replayed).

### 4. The copy scrape

`149c794` ("Polish Dashboard hierarchy and diagnostics", the terse-copy pass) cut
the sentence "Seat naming, IDs, positions and assignment live in the Seats
workspace." from the device detail. Deliberate.

The check's *subject* — the Devices detail points at the Seats workspace rather
than duplicating it — still holds, so it was **repaired** to assert the durable
structural affordances (`id="device-open-seat"`, and the surviving "Seat
transaction" copy) instead of a sentence. A structural anchor ages better than
prose. 15/15 green, and the browser half of that suite was also run: green.

## The lesson these four share

Three of the four broke because a guard **pinned more than its subject**: an
exact list where it cared about one verb, a whole sentence where it cared about
an affordance, a specific CSS mechanism where it cared about "the fade is
annotated with a finite duration". None of the three broke because the system
got worse.

That is worth carrying into how guards get written, and it is the honest reading
of the `21-theme-cyan-tint` lesson already recorded in this stitch ("a guard
asserting a literal colour that never matched means it was passing for the wrong
reason"). Over-specified guards do not fail safe; they fail *noisily and
wrongly*, which trains people to disbelieve them.

## The broader question — raised, not built

The stitch says: decide whether a periodic full sweep of
`.loom/tied/*/verify_*.py` belongs in the workflow, say so to Bob, and **do not
build it without raising it first**. Not built. See `proposal-guard-sweep.md`
in this stitch directory for the recommendation and the evidence behind it.
