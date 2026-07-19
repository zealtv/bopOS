# automation-1-engine-and-parity — worklog

2026-07-19, autopilot session. Implementation delegated to GPT 5.5 (codex)
against `codex-spec.md`; results in `codex-report.md`.

- `python/paramgen.py` (new): the §3.2 grammar parser (arity shorthand,
  string durations, `loop`/`stop`/`lfo`, `c:`/`p:`/`f` + long aliases,
  keyword-lead/option-trail) and the one-slot-per-identity
  `GeneratorEngine` — single lazy scheduler thread, last-message-wins,
  float fades as engine go-to pairs (curved segments subdivided ~33 Hz),
  int output floor-and-emit-once-per-crossing, loop snap-back,
  clock-anchored LFO phase recomputed from leader time every tick,
  `current_value()` as the catch-up hook. `sh`/`drift` seed
  `random.Random` with a stable string (SHA-512 seeding), so sync random
  LFOs are deterministic fleet-wide.
- `python/bopos.py`: the `/p/*` relay branch routes declared numeric
  params through the generator (constants replace the slot and relay one
  unchanged message; grammar errors log and drop; strings/undeclared/no
  manifest keep today's verbatim path). Orchestrator addition: an
  mtime-keyed `declared_param` cache — one `stat()` per datagram instead
  of a manifest read+validate, for Zero 2 W slider-drag rates.
- `tools/simfleet.py`: shared `paramgen` engine per simulated device with
  its skewed clock; `p/<member>=<value>` log format unchanged; grammar
  errors logged, device stays alive.
- Codex decisions accepted in review: fade-from-untouched starts at the
  manifest default (else 0); negative durations are errors; explicit
  3-element form emits its start value first; `c:` on a bare set is an
  error; emissions serialized under the slot lock.

Amendment: tied `boundary-3-framework-slimdown` verify expected the
pre-v1.7 callback list and has been failing since the 2026-07-17 `/admin`
amendment (confirmed failing on HEAD with this stitch's changes stashed);
amended to include `/admin`.

Verification (orchestrator-run, real UDP path — codex's sandbox forced an
in-process fallback): `verify_param_automation.py` 32/32 PASS (re-run
after the cache addition); tied 1-contract-model-relay 28 PASS,
1-protocol-node 37 PASS, amended boundary-3 PASS; `py_compile` clean.
