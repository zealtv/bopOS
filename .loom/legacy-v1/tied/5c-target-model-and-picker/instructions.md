# 5c-target-model-and-picker

Bob (2026-07-18, from screenshot review): "think about how one can easily
target a seat, a number of specific seats, or a group, groups, or a mix of
all. a drop down is likely not the best interface."

So: a message's target must be able to express **any mix** of seats and
groups (one seat, several specific seats, a group, several groups, all,
or seats+groups combined), and the picker must make that fast. This
touches schema + engine + inspector; keep it one stitch (split if it
fights back).

Scope:

1. **Model:** extend the message schema's `target` from a single selector
   string to a list of selectors (`["3", "7", "g1"]`; keep `"all"` as a
   plain special case, and accept the legacy single string on load for the
   shows already written — normalize to a list on save). Update
   `show_model.py` validation and the design note
   (`.notes/show-tab-design-2026-07-18.md` §2 — append an amendment
   section, don't rewrite history).
2. **Engine:** `show_engine.py` fans a message out to each selector in the
   list through the same bridge paths (dedupe: a seat already covered by a
   listed group or by `all` may be sent twice — full-state idempotent
   writes make the duplicate harmless; note it, don't build set-algebra).
3. **Picker UI (the substance):** replace the dropdown with a direct
   chip/tap interface — think Ableton/QLab economy: an "All" toggle, the
   group swatches (reuse GROUP_SLOTS colours and the bounded four-slot
   rail precedent from seat-groups), and a compact seat roster (numbered
   chips, tap to toggle, using the bounded-roster idiom from diagnostic
   density) so multi-select is direct manipulation, not a modal or a
   dropdown. Selected targets render as removable chips on the message
   inspector and a terse form on the pill/wire preview (e.g.
   `3+7+g1`). Greyed for /cue and /pt as before. If a materially better
   interface emerges while working, sketch both in the worklog and pick —
   Bob delegated the call but wants the reasoning visible.
4. Wire-form preview and stitch-5 verify expectations updated; simfleet
   assertions extended to prove a multi-target message reaches each
   selector (e.g. two specific seats but not a third).

Verify: `verify_show_targets.py` in this stitch dir (Playwright + simfleet
with ≥3 devices): build a message targeting seat 0 + seat 2 + a group via
the chip UI, assert the wire sends land per selector, legacy
single-string show file still loads, and the tied stitch-5 verify still
passes (amend its selectors if the picker markup changed; log it).
