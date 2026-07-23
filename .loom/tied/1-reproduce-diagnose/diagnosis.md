# 29/1 — diagnosis: "fleet-patch push leaves the node's engine Stopped"

## Cause (confirmed on real hardware)

The node's software-mute path **stops the audio engine as a fallback whenever
`amixer` can't find a mixer control** — and on the DigiAMP+ hardware it *never*
finds one, because `enforce_mute` targets the wrong ALSA card with the wrong
control names. So a mute (which the fleet-patch push flow applies) kills the
engine and it does not come back until an explicit unmute — which the operator,
seeing "Engine Stopped", has no reason to send.

This is **not** a hang and **not** in the fetch/patch-switch code. The node stays
fully alive: bopos.py keeps heartbeating and answering LAN commands (`/os/patches`,
`/sync/pong`). What "goes unresponsive" is the **engine**: Dashboard shows the node
online ("Last seen 2s ago") with Health = **Engine Stopped**, chip **muted**.

### The mechanism, precisely

`python/bopos.py`:
- `mixer_candidates()` (≈441) returns `[MIXER_CONTROL, "Master", "Digital",
  "PCM", "Speaker", "Headphone"]`. On this Pi there is **no `bopos.config`**, so
  `MIXER_CONTROL` is unset — the list is just the five generic names.
- `enforce_mute()` (≈451) runs `amixer -q sset <ctl> <mute|unmute>` **with no
  `-c <card>`**, so it hits the *default* card. The default card here is
  **card 0 = vc4hdmi** (HDMI), which exposes **no simple controls at all**. The
  DigiAMP+ is **card 1**, and its playback switch is named **`Digital`**
  (`Digital Playback Switch`) — a name that only resolves with `-c 1`.
- Every candidate therefore returns rc=1 `Unable to find simple control`. When
  the action is **mute** and all candidates fail, the `if mute:` fallback
  (≈468) runs `stop-engine.sh` and sets `state.muted_via_stop = True`. Unmute
  (≈459) is the only thing that restarts it.

### Evidence (files in this stitch)

- `evidence-boot-amixer-fail.txt` — bopos.py stdout at startup (`enforce_mute`
  at bopos.py:1821) prints `Unable to find simple control` for all five
  candidates, twice. amixer fails unconditionally on this box.
- `evidence-heartbeat-transition.txt` — live 5550 capture: heartbeat flips
  `eng=1 → eng=0` at the push and **stays eng=0**, node still beating every 10s.
- Dashboard screenshot (in session): Finn Jet / UID `2c:cf:67:b3:0a:58` /
  Seat 0 · ID 0 / IP 192.168.0.102 — **online, Engine Stopped, muted**.
- Proven corrective targeting on the Pi:
  `amixer -c 1 sset Digital mute/unmute` → rc=0, toggles the DAC `[on]/[off]`.
- Node-code exoneration: `evidence-baseline-pyspy.txt` + the capture's py-spy
  dumps show all four bopos threads **idle** throughout (MainThread,
  cue-scheduler, heartbeat_loop, lan_listener_loop) — no blocked/active thread,
  no stuck `subprocess.run`, no fetch stall. The fetch worker (30s urllib
  timeouts) and patch-switch daemon thread never enter the picture.

### Why "freshly-flashed Pi" specifically
A fresh Pi has no `bopos.config` (no `MIXER_CONTROL`) and its default ALSA card
is the HDMI device, not the DAC — so `amixer` is guaranteed to miss. Any node
that is muted (the push flow mutes for the switch) then loses its engine.

## Guard-rot cross-check (instructions' cheap hedge) — done
All four red patch-path guards (`dist-2-node-side`, `patch-switch-lifecycle`,
`fp-2-fleet-state`, `fp-1-identity-module`) are **pure stale drift, no real
regression** — verified independently by codex (`guard-crosscheck-codex.md`) and
by static read. None feeds this bug. Confirms the 2026-07-23 assessment; leave
them for `27-tied-guard-rot`.

## Fix — Bob's ruling (2026-07-23, this session)
> "we don't need such a hard guard on the mute as killing the engine. we can
> always shutdown the node if required. but if the mute needs to target the
> sound device more exactly that should be fixed."

Two-part fix, **Python-only (no PD edit)**, in `python/bopos.py`:
1. **Target the sound device exactly.** Make the mute path card-aware: use the
   configured sound card (the same `SOUNDCARD` start.sh already knows —
   DigiAMP) and include the DAC's real control name `Digital`. i.e. resolve the
   non-default card index / pass `-c <card>` to `amixer`, and add `Digital` to
   the candidate set. Verified working: `amixer -c 1 sset Digital mute`.
2. **Drop the hard engine-kill fallback.** Remove the `stop-engine.sh` fallback
   in `enforce_mute` (and the paired `muted_via_stop` restart on unmute). A mute
   that can't find a control should fail as a mute — never take the engine down.
   Node shutdown remains available if a hard silence is needed.

Wire the sound-card identity from start.sh/bopos config into bopos.py so the
runtime knows which card to target (today only start.sh has `SOUNDCARD`).

→ next stitch **`2-fix`** carries this. Reproduction harness for proving the
repair: `repro-mon_hb.py` (Mac 5550 monitor) + `repro-capture.sh` (Pi process +
py-spy) + the `amixer -c 1 sset Digital` check. Ship the fix with a guard.

## Rig / cleanup notes
- Dev Pi `new-bop` @ 192.168.0.102, ssh key installed (spectre). `py-spy 0.4.2`
  installed in `~/venv`. bopos.py currently running **manually** (pid launched
  this session, stdout→`/tmp/bopos.out`) rather than boot-managed — a **reboot
  restores** the `/etc/rc.local → start.sh` boot path.
- Aside (not this bug): at cold boot the engine sometimes doesn't come up
  (start-engine vs. DigiAMP readiness race). Separate; note for install/boot work.
