# Verification — 2026-07-07

Build delegated to codex-implement (prompt in `codex-prompt.md`); the codex run
died at "model at capacity" **after** writing all files but before its summary
(no result doc — 69k tokens in, exit 1). The code was complete; review found
three defects, fixed by hand (below). All checks ran live on the laptop,
loopback UDP, Python 3.12, pyOSC3 1.2 + python-osc 1.10.2 via scratchpad
PYTHONPATH (no pip on this laptop).

## Unit checks — `test_hb_identity.py` (24/24 pass)

Run:
```
PYTHONPATH=<pylib>:python:python/io python3 .loom/threads/osc-schema-contract/hb-identity.stitching/test_hb_identity.py
```
Covers: uid ladder (pinned token → argv MAC → UUID), node-config parsing,
bopos.devices id resolution, selector matching incl. −1, ping→pong byte shape
and (src, 5550) unicast, identify uid-filter, mute (control remembered +
reapplied on spam / degrade-to-stop / unmute-restarts-once), heartbeat
typetags `,sisii` with rssi and `,sisi` without, engine-alive pidfile + /proc
scan + pd-prefixed-stranger rejection, `read_wireless(None)` first-interface
parse.

## Live helper.py (observed on real 5550/6661 listeners)

- Unregistered MAC: `/hb 'aa:bb:cc:dd:ee:99' -1 '79bee19' 0 -38` every **2.0 s**
  — uid from argv, id −1, version = the repo's actual short sha as a string,
  engine-alive 0 (no pd running), real laptop rssi.
- Registered MAC `b8:27:eb:b4:64:79` → id 111, **10 s** cadence.
- **Co-bind proof:** a PD stand-in socket (SO_REUSEADDR only, PD's netreceive
  flags) held 6660 the whole time; broadcast `/all/os/ping tok7` still reached
  helper → `/os/pong 'tok7' <uid>` unicast to (sender-ip, 5550). Kernel
  semantics verified separately in both bind orders (`reuse_test.py`,
  scratchpad).
- `/all/os/identify` → `/identify` arrived on 6661 (PD chirp hook is Bob's
  edit, pd-edits-for-bob.md §2); `/7/os/identify` correctly ignored by id −1.
- `/-1/os/mute 1` → `amixer -q sset Master mute` (PATH-shimmed amixer — the
  laptop's real mixer was not touched); `/all/os/mute 0` → unmute.

## Live simfleet

v1 (default), 4 devices, `--unassigned 1 --wired 1 --engine-dead 1`:
- `/hb` typed args per contract; wired device omits rssi (absent, not zero);
  unassigned device heartbeats at 2 s with id −1; legacy `/rpt hb`/`version`/
  `aloha` interleaved (`--legacy-reports` default, the true migration wire).
- Engine-dead device sends `/hb … 0 …` and **no** PD-side `/rpt`/`aloha`
  (PD is the dead process — dashboards must see exactly this split).
- `/all/os/ping` → four unicast pongs; `/all/os/identify <uid>` marks only the
  matching device; `/2/os/mute 1` mutes only id 2; legacy `/all gain 0.5`
  still applies in v1 mode.
- `--protocol legacy` regression: wire matches dashboard-0's record (id-0 boot
  window, `version 0.0`, aloha; no `/hb`).

## Hand-fixes to codex's draft (review findings)

1. engine-alive matched `comm.startswith("pd")` — accepts `pd-mapper`/`pdns`;
   a false "engine alive" is the exact mid-show failure the flag exists to
   catch. Now exact `== "pd"`, consistent with stop-engine.sh's `pkill -x pd`.
2. simfleet v1: unresponsive/rebooting/off devices still answered
   ping/identify/mute — a dead box's helper can't pong. Gated on device state.
3. simfleet v1: engine-dead devices still emitted PD-side legacy reports
   (see above). Gated on `engine_alive()`.
4. (Scope creep reverted) codex compressed pre-existing helper callbacks and
   dropped fail-loud prints — restored `/patch` git-pull returncode check and
   `/addpatch` clone/main.pd diagnostics.

## Not verified — needs Bob or a live rig

- Real-Pi run: broadcast `/hb` across a real WLAN, PD (not a stand-in)
  co-holding 6660 on Pi OS, boot-order via rc.local.
- The right amixer control name on DigiAMP hardware (candidates
  Master/Digital/PCM/… + `MIXER_CONTROL` override in `bopos.config` are the
  hedge) and the degrade-to-engine-stop path against real jack/pd.
- ACT-LED identify flash (needs root-writable sysfs; degrades silently).
- rssi values from a Pi's wlan0 under load.
