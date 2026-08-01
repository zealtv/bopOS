# 29/1 reproduce-diagnose — working notes (in progress)

## Rig
- Fresh-ish dev Pi `new-bop` @ **192.168.0.102** (aarch64), ssh key installed
  (spectre). Bob's authenticated console: local tmux `0` pane `0:0.0`.
- **Not fully fresh** (Bob): 1 successful patch push + **1 unsuccessful** already
  happened before I got it. Pi rebooted ~16:05 today, so the failed-push in-situ
  state is gone — must re-trigger live.
- `py-spy 0.4.2` installed in `~/venv` on the Pi → non-invasive thread-stack dump
  at the moment of hang is available (`~/venv/bin/py-spy dump --pid <bopos>`).

## Node launch / state facts
- bopos.py started at boot via `/etc/rc.local → su pi -c bash/start.sh` (backgrounds
  bopos.py, io/main.py, then `start-engine.sh`). **No systemd unit** — this is the
  `bopos.service` gap Bob flagged → belongs to **stitch 31 install-oneliner**.
- At boot the engine did NOT come up (no jackd/pd/engine pidfiles), but running
  `bash/start-engine.sh` manually **works**: jackd + pd start, jack ready, pd
  connected. DigiAMP+ present as ALSA card 1. So the engine-start path is fine when
  invoked; the boot-time miss is a separate race (start-engine at boot vs. soundcard
  readiness) — note for later, not the reported bug.
- active_patch = `demo-pd`; patches present: `demo-pd`, `demo-sc`.

## Static analysis of the patch-send path (bopos.py / fetcher.py)
Concurrency model = 3 independent loops: `heartbeat_loop` (own thread),
`lan_listener_loop` (own thread, dispatches `handle_lan_datagram` INLINE), main
thread = `server.handle_request()` on 7770 (engine-facing /config,/store,/load,
/report,/admin).
- **Fetch** (`/os/fetch`) → `queue_fetch` → dedicated `_fetch_worker_loop` thread.
  `fetcher.fetch` uses `urllib` with **timeout=30** per request, 3 retries.
  Non-blocking to listener/heartbeat.
- **Patch switch** (`patch` verb) is a PROVISION_VERB → dispatched on its **own
  daemon thread** (bopos.py:1032), only if `update_model == persistent`. Calls
  stop-engine + start-engine (`wait_for_start=True` → blocking `subprocess.run`,
  but jack has a 15s readiness cap → bounded).
- `send_to_engine` = UDP `client.send` under a short-held lock → non-blocking.
⇒ **No infinite hang in the node code under normal conditions.** Heartbeat + 6660
listener should keep running even if a cold fetch stalls or the engine stays down.

## Guard cross-check (instructions' cheap hedge) — DONE, delegated to codex
All four red patch-path guards (`dist-2-node-side`, `patch-switch-lifecycle`,
`fp-2-fleet-state`, `fp-1-identity-module`) = **pure stale drift, no real
regression** (see `guard-crosscheck-codex.md`; matches my read + the handoff).
Signatures: contract 1.3→1.7, retired samplepacks symlink, callbacks now return
`{status,phase}`, refresh-list now includes assets, fake-`SimpleNamespace` state
lacks the new automation `state.data` API. Behavioral fetch/switch assertions all
still pass. So guard-rot does NOT feed the node bug — node bug is real-Pi/
process/resource level, consistent with the 2026-07-23 assessment.

## RESOLVED — see diagnosis.md
Root cause confirmed on real hardware: the software-mute path (`enforce_mute` /
`mixer_candidates` in bopos.py) targets the wrong ALSA card (default vc4hdmi, not
the DigiAMP card 1) with wrong control names (no `Digital`), so every `amixer`
call fails and the mute **falls back to stopping the engine** → "Engine Stopped"
while the node keeps heartbeating. NOT a hang, NOT in the fetch/switch code.
Bob ruled the fix (2026-07-23): target the device exactly (card-aware amixer +
`Digital`) AND drop the engine-kill fallback. Python-only. → `2-fix` created.
Also: fresh Pis ship no `bopos.config` (Bob: land it at install w/ sensible
defaults) — breadcrumbs added to stitches 31 and 33.

## (historical) reproduction plan
Trigger a real fleet-patch push at new-bop with py-spy watching, to capture the
exact blocking call / process state when it "goes unresponsive." Options: real
dashboard on Mac driven by ws script, or Bob pushes from his dashboard while I
instrument. Node-side capture: py-spy dump on hang + heartbeat monitor on 5550 +
process/log watch.
