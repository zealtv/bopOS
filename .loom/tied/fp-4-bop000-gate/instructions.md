# fp-4-bop000-gate

Live hardware gate for the fleet-patch model. Needs fp-3 tied and bop000
reachable (confirm in-session; ssh access per memory/skill notes — sudo
needs Bob).

Drive the real flow end to end on the dev Pi: stage a fleet patch →
converge → switch → confirm `current` → induce drift on the node (edit a
file in the patch copy) → observe `stale` after a listing refresh →
operator retry → back to `current` → Revert. Confirm the fingerprint the
node reports matches the host's for identical trees, and that a git-managed
patch reports honestly.

Record the run as a working artifact in this stitch. Audible confirmation
(patch actually sounding after switch) needs Bob or the room — say so
rather than claiming it verified.
