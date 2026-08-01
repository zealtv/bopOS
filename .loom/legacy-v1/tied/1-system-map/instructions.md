# 1-system-map

Document the system **as it currently is** — the prerequisite Bob named for
the architecture review ("this really starts with me just being able to
understand the system as it currently is").

Produce a single readable document (suggest `.notes/entity-map-2026-07.md`,
plus a diagram if it helps) covering, for each entity —
**device, seat, group, patch, manifest, preset (current dashboard-side),
show, pinned/promoted control, generator/automation state**:

- Identity: what names it (UID, seat id, patch name, fingerprint…).
- Storage: where it persists (node disk, `dashboard/` state files, patch
  folder, `dashboard/shows/`, browser localStorage) and what owns writes.
- Lifetime: what creates/destroys it; what survives restart, reflash,
  patch switch.
- References: every arrow to another entity, labeled by mechanism
  (selector list, fingerprint, uid, name string) and by direction.
- Wire surface: which contract planes/messages carry it.

Then a couplings section: the actual dependency graph, cycles or
near-cycles, and places where one concept is stored/expressed two ways
(e.g. dashboard presets vs the coming patch presets, seat targeting in
shows vs seat definitions). Descriptive only — no proposals yet; that is
`2-workflows-and-simplification`.

Ground truth is the code and `docs/OSC-CONTRACT.md`, not memory. Read the
relevant server/dashboard state modules and the show/seat/preset
persistence paths; cite files. Accuracy over completeness of prose — this
map is what the simplification stitch and the preset design will stand on.
