# 7-osc-input-port

Build the dashboard OSC input, per `2-dashboard-osc-input.tied/proposal.md`:

- UDP **5552**, any source, beside the 5550/5551 listeners.
- Targets `all` / seat number / `g<id>` / group name → selector.
- Identities looked up in the active target's manifest; `/e`/`/p` optional;
  ambiguity rules; **declared only**.
- Events: kind checks with numeric coercion, **clamp** out-of-range values,
  fill optional fields from defaults, reject a missing required field, stamp
  `now + event_lead_ms` (`"0"` when lead is 0).
- Parameters pass through, recorded as the dashboard's own controls are.
- `/pt`, `/point`, `/pt/clear` pass through; the dashboard holds back its own
  point output (motion loop, catch-up frame) for ~2 s after an outside frame.
- `/bop/master <0..1> [dur]` (dashboard ramp ~25 Hz, UI follows, destination
  persists, new value cancels), `/bop/mute`, `/bop/lead` (persists, UI
  mirrors).
- Everything sends through the existing execution routing (Live / Simulation
  / Patch Edit).
- In-memory list of the last ~50 rejections and clamps, for the OSC tab.
- Contract §4.3, §4 port row, §15; `docs/PORTS.md`; `docs/OSC-REFERENCE.md`
  rewritten around the input; revise glean `external-osc-timing`.

Done when `tools/run-tests.sh` passes with unit tests for translation,
ambiguity, defaults, clamping and rejection, a simfleet run where an OSC
client on 5552 reaches simulated nodes with stamped events, and master ramp
steps.
