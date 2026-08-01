# 2-fix — mute must target the sound device, and never kill the engine

Fixes the bug diagnosed in `../1-reproduce-diagnose/diagnosis.md`: on the
DigiAMP+ the node's software mute finds no `amixer` control (wrong ALSA card +
wrong control name), and `enforce_mute` falls back to **stopping the engine**, so
a fleet-patch push (which mutes for the switch) leaves the node online but with
Health = "Engine Stopped" and it never recovers.

**Python-only. No PD edit.** All in `python/bopos.py`.

## Bob's ruling (2026-07-23) — the fix, pre-ratified
> "we don't need such a hard guard on the mute as killing the engine. we can
> always shutdown the node if required. but if the mute needs to target the
> sound device more exactly that should be fixed."

## Do
1. **Target the sound device exactly.** Make the mute path card-aware:
   - Teach bopos.py which ALSA card is the DAC. Today only `bash/start.sh` knows
     (`SOUNDCARD=DigiAMP`); bopos.py has none. Source it from node config
     (see the `bopos.config` item below) / the same SOUNDCARD value, and pass
     `-c <card>` to `amixer` (resolve card name→index, or pass the name).
   - Add the DigiAMP's real control name **`Digital`** to the candidate set.
   - Verified target that works on the hardware:
     `amixer -c 1 sset Digital mute|unmute` (rc=0, toggles DAC `[on]/[off]`).
2. **Remove the hard engine-kill fallback.** Delete the `stop-engine.sh` branch
   in `enforce_mute` (the `if mute:` fallback) and the paired `muted_via_stop`
   restart-on-unmute logic. A mute that finds no control should fail *as a mute*
   — never take the engine down. (Node shutdown stays available for hard
   silence.) Check callers of `muted_via_stop` when removing it.
3. **`bopos.config` at install (Bob, 2026-07-23):** ensure `bopos.config` lands
   during installation **with sensible defaults** — it's currently absent on
   fresh Pis, which is why `MIXER_CONTROL` and card identity are unset. This is
   important for later stitches (31 install, 33 device-audio-config). The *file
   creation* belongs to **`31-install-oneliner`**; here just make the mute code
   read card/control from it (with a safe default when absent) and leave a
   pointer so 31/33 wire it. Don't block this fix on 31 — default sensibly.

## Verify (from ~/.venvs/bopos venv)
- Ship a **guard** proving: with a stubbed/failing generic-control amixer but a
  working card-specific `Digital` control, `enforce_mute(True)` mutes via amixer
  and the engine is **not** stopped; `enforce_mute(False)` unmutes. And that a
  total amixer failure returns False **without** calling stop-engine.
- Real-hardware check on `new-bop` (192.168.0.102, DigiAMP card 1): mute from the
  Dashboard silences the DAC and leaves Health running (engine alive). Reuse the
  repro harness in `../1-reproduce-diagnose/` (`repro-mon_hb.py` 5550 monitor +
  `repro-capture.sh`). Hardware confirmation may need Bob/live rig — say so if so.
- Regression: existing mute/unmute guards still pass (fleet-overlay OR semantics,
  exact-UID device mute persistence).

## Cross-thread
- `31-install-oneliner`: create `bopos.config` at install with sensible defaults
  (incl. sound card / MIXER hint). Also the `bopos.service`/boot-management gap.
- `33-device-audio-config`: sets sound card + JACK rate/buffer from Device tab —
  the card identity this fix reads should be the same one 33 writes.
