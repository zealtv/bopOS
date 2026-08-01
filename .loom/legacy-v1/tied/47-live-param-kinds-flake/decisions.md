# Diagnosis and decision

The flake exposed a real operator-facing keyboard defect, not only a
Playwright actionability problem.

`renderCards()` replaces the facilitator's live-card DOM on every heartbeat.
The host already suppresses that replacement from pointerdown through the
click/change event, but keyboard or programmatic focus has no pointerdown.
Consequently a focused range can be replaced before its next key activation,
losing both focus and the node Playwright intended to press.

The component now holds the existing host render guard while a live control is
keyboard-focused. Pointer focus stays on the host's existing pointer guard, so
a clicked control does not freeze heartbeat rendering merely because browsers
leave it focused. A deferred keyboard reassertion prevents a queued pointerup
release from an immediately preceding control from clearing the new guard
under load.

The regression checks page-side state after three heartbeat opportunities:
the same slider remains `document.activeElement` and still owns both `oninput`
and `onchange`, before its ArrowRight write is checked on the wire.

The only adjacent range-key presses in the living browser suite are the float
and integer assertions in `verify_live_param_kinds.py`; both use this shared
binding. The neighbouring toggle and enum assertions exercise the same
component and remained green. No wait-only test workaround was used because
losing an operator's keyboard focus is itself incorrect runtime behaviour.
