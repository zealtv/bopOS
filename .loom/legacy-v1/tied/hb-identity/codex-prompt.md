Implement the `hb-identity` stitch of the bopOS OSC contract: move the fleet
heartbeat out of Pure Data into python/helper.py with real identity, and add
the ping/identify/mute verbs; extend tools/simfleet.py with a contract-v1
mode. The design is already decided — read these two files first and follow
them exactly:

- .loom/threads/osc-schema-contract/hb-identity.stitching/design-decisions.md
  (authoritative for every behavior; sections numbered 1–11)
- docs/OSC-CONTRACT.md sections 3–6 and 12 (the ratified protocol spec)

Context on today's wire protocol (for the simfleet legacy mode you must not
break): .loom/tied/dashboard-0-sim-fleet/wire-protocol-today.md

## Files to change

1. **python/helper.py** (runs on Raspberry Pis, Python 3, pyOSC3 — keep the
   existing 7770 OSCServer, its handlers, and the 6661 client exactly as they
   are, except where listed):
   - NodeState: resolve `uid` (design §3 ladder: `$BOPOS_DIR/state/uid` file →
     `sys.argv[1]` if present and not "unknown" → self-discovered
     primary-interface MAC, mirroring bash/start.sh's ladder (default-route
     iface via `ip route get 1.1.1.1`, else first non-lo iface with operstate
     up, else first non-lo iface; MAC from /sys/class/net/<if>/address) →
     `uuid.uuid4()` per boot). Resolve `id` from ../bopos.devices (CSV:
     mac,hostname,id) matched by uid, else -1 (int). Resolve `version` =
     `git -C <BOPOS_DIR> rev-parse --short HEAD` else "unknown".
   - Node config parser: `$BOPOS_DIR/bopos.config`, shell-style KEY=VALUE
     lines ('#' comments, blanks ignored, optional quotes stripped); keys
     HB_TARGET (default "255.255.255.255"), HB_RSSI (default "1"),
     MIXER_CONTROL (default unset). Absent file = defaults.
   - Heartbeat daemon thread (design §2): every beat send OSC `/hb` with args
     uid (string), id (int), version (string), engine-alive (int 0/1), and
     rssi (int) only when available and HB_RSSI != "0" — the arg is OMITTED
     when unavailable, never null/0. Own UDP socket with SO_BROADCAST, sendto
     (HB_TARGET, 5550). Interval: 2.0s while id == -1, else 10.0s, re-checked
     every beat. Build the message with pyOSC3.OSCMessage and explicit
     typehints ('s'/'i'); send raw via socket.sendto(msg.getBinary(), ...).
   - engine-alive (design §4): read <BOPOS_DIR>/run/pd.pid, check
     /proc/<pid>/comm starts with "pd"; on missing/stale pidfile fall back to
     scanning /proc/*/comm for "pd". Pure stdlib, no subprocess.
   - rssi: import sys_wireless from python/io (sys.path append) and use
     read_wireless() — see change 2 below.
   - LAN listener daemon thread (design §1): UDP socket, SO_REUSEADDR +
     SO_REUSEPORT (guard hasattr), SO_BROADCAST, bind ("", 6660). If bind
     fails: print a loud warning and retry every 30s in the same thread; never
     crash. On each datagram, decode with pyOSC3.decodeOSC (returns
     [address, typetags, arg...]). Only handle addresses matching
     /<selector>/os/<member>: selector "all" matches always, otherwise
     numeric selector == current id (an unassigned node answers selector
     "-1"). Members:
     - `ping <token>`: reply OSC `/os/pong <token> <uid>` (token echoed with
       its incoming type, uid string) unicast via sendto to
       (source_ip, 5550).
     - `identify [uid]`: if a uid arg is present and != our uid, ignore.
       Else (a) send OSCMessage "/identify" to the existing 6661 client,
       (b) best-effort ACT LED flash: for led name in ("ACT", "led0") under
       /sys/class/leds/, read trigger (bracketed token), write "none", toggle
       brightness 0/1 six times 0.25s apart in a short-lived thread, restore
       the trigger; every step try/except-silent, (c) print a log line.
     - `mute <0|1>` (design §9, follow it precisely): value 1 → run
       ["amixer","-q","sset",<ctl>,"mute"] over candidates (MIXER_CONTROL
       first if configured, then Master, Digital, PCM, Speaker, Headphone),
       first returncode-0 wins and is remembered for next time; if none
       succeed, run bash/stop-engine.sh (subprocess) and set a
       muted_via_stop flag. Value 0 → "unmute" on the remembered control
       (else try all candidates); if muted_via_stop, launch
       bash/start-engine.sh exactly once via the same detached
       subprocess.Popen pattern restart_engine_callback already uses, then
       clear the flag. Re-apply mute 1 on every receipt (no state
       short-circuit); guard only the unmute engine-restart.
     All amixer/stop/start invocations must go through a single module-level
     function (e.g. `run_command(argv) -> returncode`) so tests can
     monkeypatch it.
   - `config_callback` must now also update the live NodeState id when it
     finds the row (it currently only messages PD).
   - Main loop (design §10): set `server.timeout = 1.0` and drop the
     `sleep(1)`; start the two daemon threads only under
     `if __name__ == "__main__":` so importing the module for tests has no
     side effects beyond what exists today (module-level server/client
     creation stays as-is).
   - Keep the file's existing plain-print, function-per-callback style. Do
     not add type annotations or dataclasses that would look foreign next to
     the current code.

2. **python/io/sys_wireless.py**: `read_wireless(iface=None)` — when iface is
   None, use the first interface listed in /proc/net/wireless; keep the
   existing (None, None) degradation and docstring accuracy.

3. **.gitignore**: add `bopos.config` (root, node-local) and `state/` if not
   covered. Check what's already there first.

4. **tools/simfleet.py** (python-osc, NOT pyOSC3 — design §11):
   - `--protocol {legacy,v1}` default v1. legacy mode must stay byte-identical
     to today (all current tests of behavior unchanged).
   - Add a ContractProtocol (v1) path: per-device `/hb` to the report target:
     uid (device MAC, string), id (int; -1 for unassigned), version (string,
     short-sha-looking, e.g. "a1b2c3d" bumped to a new fake value on update),
     engine-alive (int), rssi (int, random walk -35..-80 per beat) — rssi
     omitted for wired devices. Interval 2.0s while unassigned, else
     --hb-interval; per-device stagger as now.
   - engine-alive: 1 in booting/running, 0 otherwise; after
     `helper restart-engine`, report 0 for ~3s then 1 again.
   - v1 devices still answer all legacy 6660 commands exactly as legacy mode
     does (a real updated Pi's PD side is unchanged), and additionally parse
     /<selector>/os/<member> datagrams: ping → unicast /os/pong <token> <uid>
     to (source_ip, report_port) from the shared socket; identify (optional
     uid-filter arg) → mark the device row in the TUI (e.g. "IDENT" flag for
     3s) and log; mute <0|1> → set device.muted, shown as a column.
   - `--legacy-reports` default ON in v1 mode (`--no-legacy-reports` to turn
     off): when on, v1 devices also keep emitting today's PD-side
     /rpt hb + version + aloha exactly as legacy mode does (real migration
     state); when off, those stop entirely.
   - `--unassigned N`: last N devices boot with id -1 (uid still their MAC);
     `--wired N`: last N devices have no rssi; `--engine-dead N`: last N
     devices heartbeat with engine-alive 0. Validate counts like the existing
     flags.
   - Keep the "message bytes live only in protocol classes" separation and
     the existing code style.

5. **New test file**
   .loom/threads/osc-schema-contract/hb-identity.stitching/test_hb_identity.py
   in the same style as .loom/tied/node-contract-fixes/test_node_fixes.py
   (plain check() functions, PASS/FAIL lines, exit nonzero on failure, no
   pytest). Cover at least: uid ladder (token file wins; argv MAC; fallback
   uuid when no argv and discovery mocked out), node-config parsing (absent
   file, comments, quotes), bopos.devices id resolution (match and miss),
   selector matching incl. -1, ping → pong bytes unicast to (src, 5550)
   (monkeypatch the reply sendto or use a real loopback socket), identify
   uid-filter, mute: mixer success remembered / degrade-to-stop /
   unmute-restarts-once, heartbeat message args with and without rssi
   (inspect the built OSCMessage or capture via loopback), engine-alive
   pidfile logic (point BOPOS run dir at a temp dir), and
   sys_wireless.read_wireless(None) parsing from a fake proc file (make the
   proc path module-level so the test can repoint it — change sys_wireless
   accordingly). Structure helper.py so all of this is testable by importing
   and calling functions with monkeypatched seams — no sleeps over 0.5s in
   tests, no real amixer/systemctl/reboot calls ever.

## Hard constraints

- NEVER touch any .pd file.
- helper.py must keep working on a stock Pi: pyOSC3 only, no new pip
  dependencies, Python 3.7-compatible stdlib.
- uid and version cross the wire as OSC strings, never floats/ints (32-bit
  float truncation is the reason — contract §12).
- The heartbeat address on the wire is exactly "/hb"; the pong address is
  exactly "/os/pong".
- Nothing may crash or exit on missing hardware/files: no bopos.devices, no
  git, no /proc/net/wireless, no amixer, no LED sysfs — every one degrades
  per design-decisions.md.
- Do not change ports, message names, or behavior beyond what design §1–§11
  lists (the sleep(1)→server.timeout change is in scope).
- To run things locally: PYTHONPATH must include
  /tmp/claude-1000/-home-bob-repos-bopOS/acefa5c4-dc77-444e-ae85-2f703d1fd07f/scratchpad/pylib
  (has pyOSC3 and pythonosc), plus python/ and python/io/ for imports. The
  test file must pass when run as:
  PYTHONPATH=<that pylib>:python:python/io python3 .loom/threads/osc-schema-contract/hb-identity.stitching/test_hb_identity.py

When done, summarize what you changed, how you verified it (including the
test run output), and anything you could not do. If you could not complete
the task, say so explicitly.
