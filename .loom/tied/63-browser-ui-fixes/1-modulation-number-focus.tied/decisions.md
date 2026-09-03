# Decisions

## Keep interaction ownership separate

The document pointer guard and `ControlSurface`'s component guard now own
separate booleans. A primary click on a number input does not qualify as the
range/toggle/enum gesture guarded by the document listener, so its `pointerup`
must not be allowed to release a focus guard acquired later in the same event
sequence.

This keeps the existing render suppression semantics intact while removing the
order-dependent shared flag. It also covers drawer selects, checkboxes,
precision fields, preset drawers, and timed fire feedback without expanding
the document selector or special-casing number inputs.
