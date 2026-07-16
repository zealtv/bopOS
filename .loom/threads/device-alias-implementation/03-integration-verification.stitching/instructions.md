# 03-integration-verification

Finish and verify the device-alias implementation after registry and UI land.

- Add a real-dashboard browser suite covering restart/offline/venue behaviour,
  rename/reset/Forget, duplicate rejection, narrow layout and every identity
  surface.
- Enforce the ratified hierarchy refinement: hostname and full UID/MAC appear
  only in the selected Device detail; the device roster, Seats controls,
  Assets target selector and facilitator Dashboard cards use the alias alone.
- Lint the complete two-word lists and retain a human-reviewed list artifact.
- Run affected Seats, Devices, Assets and Dashboard regressions.
- Update durable documentation, handoff and Loom results with honest hardware
  and accessibility boundaries.
