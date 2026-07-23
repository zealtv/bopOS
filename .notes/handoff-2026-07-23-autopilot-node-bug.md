# Handoff — 2026-07-23 autopilot (node bug + gdown)

Autopilot session against the tier-1 sweep. Bob's bite was **29 → 30 → 31, stop
at the gate**. Completed **29 and 30** (both tied); **wound down before 31** at
75% session cap (31 grew large — see below — and starting it would have risked a
mid-stitch cutoff with no handoff headroom). Weekly cap only 57%; the binding cap
was the 5-hour session one.

## Done this session

### 29-fleet-patch-sync-hang — TIED (the priority bug)
**It was the software-mute path, not fetch/patch and not a hang.** Reproduced live
on the dev Pi with py-spy + a 5550 heartbeat monitor. On the DigiAMP+, `enforce_mute`
ran `amixer sset` against the **default ALSA card** (vc4hdmi/HDMI — no controls)
with generic control names (`Master/Digital/PCM/…`) that only resolve on card 1
with `-c`. Every call failed, so mute **fell back to `stop-engine.sh`** and set
`muted_via_stop` — leaving the node online + heartbeating but Health "Engine
Stopped", never recovering. The fleet-patch push mutes the node for the switch,
which is why the push triggered it. Full evidence in
`.loom/tied/1-reproduce-diagnose/` (diagnosis.md, py-spy baseline, heartbeat
transition, codex guard cross-check).

**Fix (Bob ruled it, pre-ratified): Python-only in `python/bopos.py`, TIED in
`.loom/tied/2-fix/`.**
- New `mute_targets()` → `(card, control)` pairs, best-first: remembered winner →
  configured `SOUNDCARD`/`MIXER_CONTROL` → auto-detected **non-HDMI** cards with
  DAC-first control names (`Digital, Master, PCM, Speaker, Headphone, Analogue`).
  `enforce_mute` now runs `amixer -c <card> sset <control> …`.
- **Removed the `stop-engine.sh` fallback and `muted_via_stop` entirely.** A mute
  that finds no control fails *as a mute*; it never takes the engine down (Bob:
  "we can always shut the node down if required").
- `read_node_config` gained `SOUNDCARD` so `bopos.config` can name the DAC.
- **Hardware-verified on new-bop:** mute → `Digital [off]` while jackd+pd stay UP,
  across mute/unmute toggles, no amixer failures, no stop/start-engine.
- Guard `.loom/tied/2-fix/verify_mute_targeting.py` (9 checks, green). Repaired the
  superseded `hb-identity` tied guard in place (its "mute degrades to engine stop"
  / "unmute restarts" assertions inverted, `mixer_control` string→tuple, config
  dicts refreshed); its remaining **3** failures (identify /notify, engine-alive
  pidfile ×2) are **pre-existing rot owned by `27-tied-guard-rot`**, not this change.

### 30-gdown-retirement — TIED
Removed `gdown` (only trace was `python/requirements.txt`, imported by nothing).
Bash staleness sweep (codex-assisted, report in `.loom/tied/30-gdown-retirement/`)
→ **no removable scripts**; all eleven are live. `start-engine.sh`
`LEGACY_SAMPLEPACKS` residue-cleanup retained deliberately (can retire once the
fleet is confirmed clean of the old symlink).

## Where the next session starts — 31-install-oneliner
`./.loom/loom.sh next` → `31-install-oneliner/1-install-script`. **Scope grew this
session** — its instructions were updated to require:
1. `install.sh` + README `curl` one-liner (original scope).
2. **Land `bopos.config` at install with sensible defaults** (Bob 2026-07-23,
   "important for later stitches") — fresh Pis have none, which is the root
   contributor to the mute bug. Must include the sound-card / MIXER hint the mute
   path (`29/2-fix`) and stitch 33 read. Coordinate the schema with 33.
3. **Create a `bopos.service`/proper boot mechanism** — today boot is
   `/etc/rc.local → su pi -c start.sh` with no systemd unit (Bob flagged).
4. **Cold-boot engine race** seen on new-bop: at boot the engine sometimes doesn't
   come up (start-engine vs. DigiAMP readiness); running `start-engine.sh` manually
   works. Address in the boot/service work.
5. Still Bob-gated: the hosting URL for the raw script.
Depends on 30 (done). Breadcrumbs are already in stitches 31 and 33.

## Dev Pi state (new-bop @ 192.168.0.102) — READ THIS
- Memory [[bop000-dev-pi-access]] updated: fresh-install Pi `new-bop`, my spectre
  key installed, `ssh -i ~/.ssh/id_ed25519_spectre pi@192.168.0.102`. Bob's
  authenticated console is local tmux `0` pane `0:0.0`. `py-spy 0.4.2` installed
  in `~/venv` (great for node hang diagnosis).
- **The fixed `bopos.py` is deployed to the Pi's checkout** and running **manually**
  (`setsid … >/tmp/bopos.out`), NOT boot-managed. Original at `/tmp/bopos.py.orig`.
  The working tree is dirty (bopos.py). Once Bob pushes 29's fix to main, the Pi's
  file already matches HEAD so `/update`'s `git pull` fast-forwards cleanly. **A
  reboot restores boot management** and runs the same fixed file.
- Node id 0 / Seat 0, alias "Finn Jet", uid `2c:cf:67:b3:0a:58`.

## Not pushed / not done
- Nothing pushed to main (Bob's deploy call). Two commits this session on `main`:
  the 29 diagnosis+fix and the 30 cleanup.
- `dashboard/shows/` left untracked/unstaged (unrelated, as prior handoffs note).
- Gotcha logged for future ssh-driving: `pkill -f "<pattern>"` matches the ssh
  `bash -c` command line itself — a `pkill -f "pd -nogui"` silently killed my own
  session. Use exact `pkill -x <comm>` or explicit PIDs when driving the Pi.
