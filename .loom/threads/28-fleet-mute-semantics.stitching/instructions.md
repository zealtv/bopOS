# 28-fleet-mute-semantics

Investigate the three `12-dashboard-live-controls/verify_live_controls_backend.py`
failures about fleet-overlay mute semantics. Suspected live defect (thread 23,
2026-07-22); Bob ruled 2026-07-22 to pull it out ahead of the rest of the rot
cleanup because fleet mute is a safety surface.

Failing checks:

- `fleet safety overlay blocks individual mute mutation`
- `fleet release reasserts persistent per-UID state`
- `host-global device mute survives restart`

Settle whether the safety property is actually broken before changing anything.

**Outcome: not a defect.** See `decisions.md` — the safety property holds, and
the guard was pinning a ruling Bob himself superseded. Guard repaired.
