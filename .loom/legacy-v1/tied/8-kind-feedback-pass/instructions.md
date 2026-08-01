# 8-kind-feedback-pass

Bob's live review of the tied `6-non-float-kinds` (2026-07-27). Four calls,
all his:

1. **No misleading automation cue.** A control that cannot show its
   generator's precise value (a toggle, an enum, an LFO shape the runtime
   can't sample) must **pulse cyan** — border or fill, implementer's call —
   instead of animating something that reads as a value. Retires the
   50%-duty flash approximation from `6`.
2. **The number box under a generator.** It does not follow the slider.
   Confirm whether that is architectural; if it is, keep the cyan ink but
   show the mixed-mode dots rather than a stale number.
3. **The full-width toggle is ugly.** Make it a clickable box with a label,
   or whatever is cleanest.
4. **`label` (the string kind).** Bob doesn't recognise it as a UI type and
   its row height is inconsistent with the rest. Either remove it or
   clarify its role — and fix the height regardless.

Verify: extend the living journeys under `tests/`; re-shoot the panel.
