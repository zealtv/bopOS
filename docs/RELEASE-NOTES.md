# Release notes

## OSC contract v1.22 — typed event fields (2026-10-26)

Update **every node** before a patch relies on typed events. Older nodes
silently drop events containing integer or text fields, and events with more
than three fields. No mixed-version fleet warning is shown in the dashboard.

Event manifests now declare up to 16 named `fields` using parameter kinds.
`arity` and `defaults` are rejected. Push migrated patch manifests together
with the bopOS update: patches reach nodes through dashboard push, not Git.
The local `bonks-pd`, `demo-pd` and `kc-test` manifests have been migrated.

Pd symbol delivery and audible rig verification remain Bob's separate
`5-pd-event-fields` check. No Pure Data patches were changed here.
