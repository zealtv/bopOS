# Audio hardware onboarding

How to bring a new audio board or interface into bopOS, how mute interacts
with the board zoo, and how to fold what the bench teaches back into the
repo. Companion to `OSC-CONTRACT.md` §2 (declared facts) and §6 (mute).

The framework's stance: bopOS treats hardware as **declared facts, never
assumptions** — a node self-reports `audio_out` (or `none`) and
`AUDIO_CHANNELS`; nothing in the framework requires a particular card, and a
node with no audio hardware must still boot, heartbeat, and answer the
dashboard. Untested boards **fail honest**: this doc tells you how to check,
it never guesses.

## The audio chain on a Pi

```
/boot/firmware/config.txt        dtoverlay=… enables the board's driver
        ↓
ALSA card                        name it appears as (cat /proc/asound/cards)
        ↓
jackd -d alsa -dhw:$SOUNDCARD    bash/start-engine.sh (default: DigiAMP)
        ↓
engine (PD / scsynth / …)        the patch's sound
        ↓
amixer mute                      the one framework-owned output control
```

Two knobs belong to bopOS:

- **`SOUNDCARD`** — the ALSA card jack opens. Default `DigiAMP` in
  `bash/start-engine.sh` (and legacy `bash/start.sh`); override with the
  `SOUNDCARD` environment variable or edit the default.
- **`MIXER_CONTROL`** — in the node's `bopos.config` (repo root on the Pi,
  *not* the per-patch `patches/<name>/bopos.config`). Names the amixer
  simple control that mute should drive. Optional: when unset, `set_mute`
  in `python/bopos.py` walks a candidate list (`Master`, `Digital`, `PCM`,
  `Speaker`, `Headphone`) and remembers the first one that works.

## Bench procedure for a new board

Work on a bench Pi, not an installed one. Each step has a visible
pass/fail; stop at the first failure and fix it before moving on.

1. **Fit the board and enable its driver.** Add the vendor's `dtoverlay=`
   line to `/boot/firmware/config.txt` (see the table below for known
   boards), disable the onboard audio (`dtparam=audio=off`) if the vendor
   recommends it, reboot.
2. **Confirm ALSA sees it:** `cat /proc/asound/cards`. Note the card *name*
   — that string is your `SOUNDCARD` value. USB interfaces appear here too,
   no overlay needed.
3. **Point bopOS at it:** set `SOUNDCARD=<name>` (env var, or edit the
   default in `bash/start-engine.sh`) and restart the stack
   (`bash/stop-engine.sh && bash/start-engine.sh`, or `/os/restart-engine`
   from the dashboard).
4. **Prove sound:** the `demo-pd` patch through the dashboard, or
   `speaker-test -D hw:<name> -c 2 -t wobble` before involving jack. If
   jack fails to start, its log line in the engine output names the device
   it tried.
5. **Find the mute control:** `amixer -D hw:<name> scontrols` lists the
   simple controls. Try `amixer -D hw:<name> sset <Control> mute` (then
   `unmute`) for each candidate while sound plays. The winner is the
   control where audio dies **and the engine keeps running** (check the
   dashboard: `engine alive` stays green).
6. **Wire it to bopOS mute:** if the winning control is not already in
   `set_mute`'s candidate list, set `MIXER_CONTROL=<Control>` in
   `bopos.config`. Then verify end-to-end: dashboard **silence** →
   audio stops, engine alive; **resume** → audio returns.
7. **Check the degraded path honestly:** if *no* control mutes, bopOS falls
   back to stopping the engine (`muted_via_stop`) — silencing but
   engine-lethal, and unmute restarts the engine cold. That is a **degraded
   mode, not the design centre** (contract §6): record it in the table
   rather than shipping a board that pretends to mute.

## Folding results back into the repo

A benched board is only benched once it's recorded. In one commit:

1. **Add the row** to the table below: board, overlay, ALSA card name, the
   mixer control that accepted mute, and who/when verified it.
2. **Grow the candidate list** in `python/bopos.py` (`mixer_candidates`)
   if the control is generic enough that other boards likely share it —
   that's how the next board gets mute for free. Board-specific oddballs
   stay in that node's `bopos.config` instead.
3. If setup needed anything beyond a `dtoverlay` line (kernel params, a
   vendor script), note it in the row or a footnote — the next bench run
   starts from this table, not from the vendor's site.

## Board table

Verified means: benched with the procedure above, mute confirmed
engine-safe. Blank cells are unknown — check, don't guess.

| Board | `dtoverlay` | ALSA card (`SOUNDCARD`) | Mute control | Verified |
|---|---|---|---|---|
| IQaudIO DigiAMP+ | `iqaudio-dacplus,unmute_amp` | `DigiAMP` | `Digital` | Bob, 2026-07-12 (Pi OS Trixie, audible mute/resume) |
| Pimoroni Audio SHIM | | | | — |
| Class-compliant USB interface | *(none — USB)* | *(from `/proc/asound/cards`)* | *(often `PCM` or `Speaker`)* | — |
| Onboard headphone jack | *(none — `dtparam=audio=on`)* | `Headphones` | | — |

On the verified DigiAMP+ image, the board's mute light did not change with
the ALSA `Digital` switch and is not a reliable mute indicator. Audible output
and `amixer sget Digital` are the bench checks. ALSA percentages on this
control are also misleadingly quiet: 10% mapped to -93 dB; use an explicit dB
value when setting a safe bench level (-40 dB was audible but very quiet).

## Input-capable boards

Boards with capture (audio-in HATs, USB interfaces with mics) belong in
this same table once the `audio-input` thread opens — its `input-1-hw-recipe`
stitch adds the capture columns (capture device, channels, tested rate)
rather than starting a second document. Until then, `AUDIO_CHANNELS` in
`bopos.config` declares output channel count only.
