# boundary-3-framework-slimdown

Remove superseded framework/report machinery and add demand-driven inspection.

- Remove 7770 admin handlers; retain `/config`, `/store`, and `/load`, and add
  engine-to-framework `/report <name> <values...>`.
- Remove `meter_loop`, `METERS`, `METER_INTERVAL`, the legacy `/rpt`/echo
  machinery outside PD, and manifest/dashboard `role: "meter"` completely.
- Add one-shot `/<id>/os/probe <what>` with unicast
  `/os/probe <id> <what> <values...>` replies from values bopOS already holds.
- Do not implement or contract the leased probe or report UI metadata.
- Run the helper-death drill with systemd restart and mute-spam fallback.
  Control must return within measured seconds; otherwise stop and reopen the
  sole-binder risk before the PD edit wave.
- Verify at the level required by `docs/VERIFICATION.md`; never edit `.pd`.
