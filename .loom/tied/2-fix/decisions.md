# 2-fix — decisions & verification

## What changed (python/bopos.py, Python-only, no PD edit)
1. **Mute targets the DAC exactly.** New `mute_targets(state)` yields `(card,
   control)` pairs, best-first: a remembered winner, then configured
   `SOUNDCARD`/`MIXER_CONTROL`, then **auto-detected non-HDMI cards** (a fresh
   Pi's default card is the HDMI device, not the DAC — the root cause), each with
   DAC-first control names `KNOWN_MIXER_CONTROLS = (Digital, Master, PCM, Speaker,
   Headphone, Analogue)`. `enforce_mute` now runs `amixer -q -c <card> sset
   <control> <mute|unmute>` and remembers the winning pair in `state.mixer_control`
   (now a tuple, was a bare string).
2. **No engine-kill fallback.** Removed the `stop-engine.sh` fallback and the
   `muted_via_stop` flag entirely (init + unmute-restart branch). Per Bob's ruling
   (2026-07-23): a mute that finds no control fails *as a mute* — it must never
   take the engine down. Node shutdown remains for hard silence.
3. **`SOUNDCARD` added to `read_node_config`** (defaults `None`) so `bopos.config`
   can name the DAC. Landing that file with sensible defaults at install is
   seeded to stitch 31 (creation) + 33 (Device-tab edits) — see those instructions.

## Hardware verification (new-bop, DigiAMP+ = ALSA card 1) — PASSED
Deployed the fixed `bopos.py`, restarted, engine up, toggled mute over OSC
(`/all/os/to <uid> mute 0|1` → `set_device_mute`):

| action | DAC `Digital` | jackd | pd |
|---|---|---|---|
| unmute | `[on]`  | UP | UP |
| mute   | `[off]` | UP | UP |
| unmute | `[on]`  | UP | UP |

`/tmp/bopos.out` showed **no amixer failures and no stop/start-engine calls** —
the mute silences the DAC and the engine survives every transition. At startup the
node's *persisted* mute was correctly applied to the DAC (`Digital [off]`) with the
engine running — the exact scenario that previously produced "Engine Stopped".
(Transcript: `evidence-hw-mute-toggle.txt`.)

## Guard work
- **New guard** `verify_mute_targeting.py` (in this stitch) — 9 checks, all PASS,
  exit 0. Covers: auto-detect `-c DigiAMP Digital`; HDMI cards never targeted;
  winner remembered + retried first; configured card/control win; **no control ->
  mute returns False and never calls stop-engine**; unmute never calls
  start-engine; `muted_via_stop` gone. Run:
  `PYTHONPATH=<repo>/python python3 .../verify_mute_targeting.py`.
- **Repaired a superseded tied guard** `.loom/tied/hb-identity/test_hb_identity.py`
  in place (I'm the orchestrator; house rule for superseded guards). Its
  `"mute degrades to engine stop"` / `"unmute restarts stopped engine once"`
  assertions pinned exactly the fallback Bob ruled away — inverted to
  `"mute never stops the engine"` / `"unmute never starts the engine"`, updated the
  `mixer_control` string→tuple and the `amixer` argv matcher, and refreshed the two
  node-config-default dicts (added `SOUNDCARD`; `AUDIO_CHANNELS` was prior drift).
  Each edit carries an inline comment naming this stitch.
  **Left untouched (pre-existing rot, belongs to gated `27-tied-guard-rot`, NOT my
  change):** `identify tells PD and flashes` (/identify→/notify), `engine alive
  from pidfile`, `engine alive stale pidfile scans proc`. The guard is still red on
  those three; that is stitch 27's job, not this fix's.

## Notes / cleanup (new-bop)
- Fixed `bopos.py` is deployed to the Pi's checkout (`~/bopOS/python/bopos.py`) and
  running manually under `/tmp/bopos.out`; original saved at `/tmp/bopos.py.orig`.
  Working tree is dirty until this change reaches main and the Pi `/update`s
  (git pull will fast-forward — the file already matches the committed content).
  A reboot restarts boot-managed bopos with the same fixed file.
- Simfleet unchanged: it doesn't model amixer/ALSA, so there's no node-mute
  hardware surface to mirror.
