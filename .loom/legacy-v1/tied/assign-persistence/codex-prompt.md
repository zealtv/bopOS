Implement the `assign-persistence` stitch of the bopOS OSC contract: the
`/os/assign` verb, a file-backed persistence store, boot resolution from the
persisted assignment, and the matching simfleet behaviour. The design is
settled — read these first and follow them exactly:

- .loom/threads/osc-schema-contract/assign-persistence.stitching/design-decisions.md
  (authoritative, sections 1–6)
- docs/OSC-CONTRACT.md sections 5 and 10 (plus 4 for unicast discipline)

This builds on the hb-identity stitch that just landed (commit f604fde):
python/helper.py already has NodeState, resolve_id, the LAN listener on 6660
(handle_lan_datagram with ping/identify/mute members), the heartbeat thread,
read_node_config, and run_command. tools/simfleet.py already has
--protocol v1, ContractProtocol, and receive_contract. Extend those; do not
restructure them.

## Files to change

1. **New python/store.py** (pyOSC3-free, stdlib only, same plain style):
   - `class Store` with `__init__(self, root, persistent=True)`,
     `get(key) -> list`, `put(key, values) -> bool`, `delete(key)`.
   - Persistent: one JSON file per key under `<root>/<key>` (root will be
     `$BOPOS_DIR/state/store`), written atomically (write `<key>.tmp` then
     `os.replace`), directory created on first put. Ephemeral
     (persistent=False): RAM dict only, same API.
   - Key validation: `re.fullmatch(r"[A-Za-z0-9._-]+", key)` and key must not
     start with "." — invalid keys print a loud message and return False /
     empty list. All file errors degrade to print + empty/False, never raise.

2. **python/helper.py**:
   - NodeState gains `self.update_model` from config key `UPDATE_MODEL`
     (default "persistent"; anything except "ephemeral" means persistent) and
     `self.store = Store(os.path.join(BOPOS_DIR, "state", "store"),
     persistent=(update_model == "persistent"))`. Add UPDATE_MODEL to
     read_node_config defaults.
   - `resolve_id` order becomes: store key "assignment" (first value, int) →
     bopos.devices by uid → -1. Note resolve_id currently runs before the
     store exists in NodeState.__init__ — reorder NodeState so config/store
     come first and pass the store to resolve_id as an argument.
   - Extract the hostname-change block from config_callback into
     `set_hostname(hostname)` (hostnamectl + /etc/hosts sed + avahi restart,
     only when different from current); config_callback calls it.
   - Heartbeat thread: replace `sleep(interval)` with a module-level
     `hb_wake = threading.Event()`; wait(timeout=interval) then clear. An
     immediate beat is requested by `hb_wake.set()`.
   - New LAN member in handle_lan_datagram, `assign`, args
     `<uid> <id> <name> [posx posy pos2x pos2y]` (4 positions or none;
     numbers may arrive as int or float):
     if str(args[0]) != state.uid → return False. Else: state.id =
     int(args[1]); set_hostname(str(args[2])); send OSCMessage "/id" with the
     id as 'f' to the 6661 client (exactly what config_callback sends);
     store.put("assignment", [id, name, *positions]); hb_wake.set(); print a
     line. Return True.
   - New LAN members `store` and `load`:
     - `store <key> <values…>` → state.store.put(key, list(values)).
     - `load <key>` → reply "/os/load" with key ('s') plus each stored value
       typed by its Python type (int→'i', float→'f', else 's'), unicast via
       reply_socket.sendto to (source[0], 5550). Missing/empty key → reply
       with just the key.
   - Localhost path: register handlers "/store" and "/load" on the existing
     7770 server: /store persists same as above (args[0]=key, rest values);
     /load sends OSCMessage "/load" (key + typed values) to the 6661 client.
   - Keep the existing file style (plain functions, prints, no type hints).

3. **tools/simfleet.py** (python-osc):
   - `--state-dir <dir>` (default None) and `--ephemeral N` (validated like
     the other count flags).
   - Device gains a `name` concept: hostname doubles as name (assign updates
     device.hostname).
   - v1 `assign` member in receive_contract (goes through the same
     state/unresponsive gate as ping): args uid,id,name[,4 positions]; only
     the device whose mac == uid applies it: device.device_id = int(id),
     hostname = str(name), persist (below), and ack with an immediate
     non-rescheduling heartbeat (self.heartbeat(device, reschedule=False)).
     The regular schedule then picks up the new 2s/10s cadence automatically
     because interval is computed per beat.
   - Persistence: when --state-dir is set and the device is not ephemeral,
     write `<state-dir>/<mac with : replaced by ->.json` containing
     {"id": ..., "name": ..., "positions": [...]} on assign. At load_devices
     time (v1 only), if such a file exists for a device's mac, it overrides
     the seeded id/hostname (including --unassigned). Ephemeral devices
     (last N) never read or write these files and boot with id -1 when
     --state-dir is set (they "re-hello each boot"); without --state-dir
     ephemeral devices just boot id -1.
   - Keep legacy mode byte-identical; keep the protocol-class byte-boundary
     separation (add an `assign_ack`-free design — the ack IS the heartbeat,
     no new message type).

4. **Extend the test file** — copy
   .loom/tied/hb-identity/test_hb_identity.py's harness style into a new
   .loom/threads/osc-schema-contract/assign-persistence.stitching/test_assign_persistence.py
   (same FakeServer/FakeClient stubbing, plain check() lines, exit 1 on
   failure). Cover at least: Store put/get round-trip with mixed types,
   atomicity artifact absence (no .tmp left), invalid key rejected, ephemeral
   Store isolation (nothing on disk); resolve_id prefers store over
   bopos.devices and falls back correctly; assign via handle_lan_datagram
   (uid match applies id+hostname+store+/id message+hb_wake set; uid mismatch
   does nothing); assign idempotence (same assign twice = same state); store
   member persists; load member replies typed values unicast to (src, 5550)
   and empty for a missing key; localhost /store & /load handlers; simfleet:
   run load_devices with a temp state dir + a fake assignment file and check
   the override, and check ephemeral devices ignore it. Monkeypatch
   set_hostname (no hostnamectl in tests) and use tempfile dirs throughout.
   Must pass with:
   PYTHONPATH=/tmp/claude-1000/-home-bob-repos-bopOS/acefa5c4-dc77-444e-ae85-2f703d1fd07f/scratchpad/pylib:python:python/io python3 <test file>
   (that pylib has pyOSC3 and pythonosc; simfleet imports need pythonosc).

## Hard constraints

- NEVER touch any .pd file.
- helper.py/store.py: pyOSC3 + stdlib only, Python 3.7-compatible.
- No port changes; replies unicast to (source_ip, 5550); broadcast only for
  the heartbeat.
- uid and any value that might exceed 6 significant figures crosses the wire
  as an OSC string.
- Nothing may crash on missing files/dirs/hardware — degrade with a print.
- Do not remove or alter existing verbs/behavior beyond what design-decisions
  lists.

When done, summarize what you changed, how you verified it (including test
output), and anything you could not do. If you could not complete the task,
say so explicitly.
