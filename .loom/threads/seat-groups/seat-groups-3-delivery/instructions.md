# seat-groups-3-delivery

Complete the ratified Seat-group feature after both children are resolved:

- core protocol, persistence, state, and synchronization behavior is verified;
- the spatial membership visualization has a ratified UX direction.

Then implement group authoring in Seats, apply the UX design to the spatial
Seats view, and verify group creation/membership/visualization against the core
state. Expose the finished group catalog and selector data to the existing
dashboard state API.

All / Group / Seat patch controls and the combined flat/nested parameter ×
all/Seat/group selector browser matrix belong to the downstream
`ui-tabs/.../12-dashboard-live-controls` stitch. Do not build a parallel live
control surface here.

The binding protocol/data proposal is in
`.loom/tied/seat-groups-0-design/proposal.md`. Never edit `.pd`; engines receive
the selector-free standard OSC surface.
