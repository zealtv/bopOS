# Today's deployed wire protocol (as read from the code, 2026-07-07)

Ground truth for `tools/simfleet.py`. Decoded from `pd/bopos.osc.pd`,
`python/helper.py`, `DASHBOARD.pd`, `pd/bopos.gui.pd`, `bash/start.sh`,
`patches/default/main.pd`. This is what real Pis speak **today**, pre-contract;
the `osc-schema-contract` children will migrate these shapes (see contract §13).

## Node → dashboard: UDP broadcast to 255.255.255.255:5550

Every outbound report goes through one path in `bopos.osc.pd`:
`s osc-out` → `list prepend <ID>` → `oscformat rpt` → `netsend -u -b` (5550).

So **every** message has OSC address `/rpt`, first argument the device id
(float), then the payload:

| wire message | when |
|---|---|
| `/rpt <id> hb` | every 10 s (`metro 10000`), first beat ~1 s after PD loads |
| `/rpt <id> version <v>` | sent immediately after each `hb` (same metro tick, two datagrams) |
| `/rpt <id> aloha 1` | boot announce ~1 s after PD loads (`loadbang → delay 1000 → aloha`), and reply to an incoming `aloha` command |
| `/rpt <id> helper-reply <verb> [args]` | helper.py confirmations forwarded from 6661 (`reboot`, `shutdown`, `update`, `getsamples`, `addpatch <repo>`, `checkout`, `patch`) |
| `/rpt <id> <payload…>` | echo mode: when `echo 1` has been received, every incoming osc-in payload is echoed back (`babs.gate`) |

Details:
- **Reported** `id` starts at **0** (the `list prepend 0` initial argument) until
  helper.py answers the loadbang `helper config` with `/id <n>` on 6661.
  Unassigned/unknown devices keep id 0 forever — `DASHBOARD.pd` shows
  `bopos.gui 0` as "unassigned device". (Contract v1 uses −1; today is 0.)
- **Listened-for** id is asymmetric: `route-by-id`'s creation argument is `-1`,
  so until `/id` arrives a device *reports* as 0 but *matches selector −1*.
- `version` is **always 0 on the wire today**: the heartbeat reads
  `value version`, but nothing ever writes that value — the patch's loadbang
  `version 1` lands on `s version`, which has **no receiver** anywhere in the
  repo. Dead wiring; flagged for Bob (see the osc-schema-contract thread's
  `pd-edits-for-bob.md`), and `hb-identity` replaces version reporting anyway.
- id and version are floats on the wire (PD sends everything numeric as f).

## Dashboard → node: UDP broadcast to 255.255.255.255:6660

`bopos.gui.pd` sends via `oscformat <deviceN>`: the OSC **address is just the
selector** (`/<id>` or `/all`) and the command rides as **arguments**
(symbol + values), e.g. address `/1`, args `["gain", 0.5]`.

Node side, `netreceive 6660` → `oscparse` → `list trim` flattens address
components and arguments into one list, so path-encoded (`/all/gain 0.5`) and
arg-encoded (`/all gain 0.5`) are **equivalent**. A faithful simulator must
flatten the same way: `tokens = address_parts + args`.

Routing: `route all` passes `all …` to every device; anything else goes through
`route-by-id` which matches `tokens[0]` against the device's current ID (float
compare; ID 0 matches selector `0`).

Commands (payload after the selector):

| payload | node behaviour today |
|---|---|
| `gain <f>` / `gain2 <f>` / `backing <f>` | patch parameters — patch consumes from osc-in; no reply |
| `echo <0|1>` | opens/closes the echo gate (see above) |
| `aloha [x]` | reply `/rpt <id> aloha 1` |
| `id <n>` | sets the runtime ID directly (`route id` → `s ID`) |
| `version <v>` | **no-op**: `route version` → `s version` has no receiver (dead wiring) |
| `helper reboot` | PD delays 500 ms, forwards `/reboot` to helper 7770; helper replies (→ `/rpt <id> helper-reply reboot`), then `systemctl reboot` → silent, returns after boot |
| `helper shutdown` | same dance with `/shutdown` → silent, never returns |
| `helper update` | `/update` → `helper-reply update`, runs update.sh (git pull, `sleep 5`, reboot) → silent, returns after boot; version may change |
| `helper getsamples` | `/getsamples` → `helper-reply getsamples`, runs getsamples.sh |
| `helper patch <name>` | writes active_patch.txt, pkill pd, git pull, reboot (no helper-reply; PD also self-triggers `/update` path with a 1 s delay → `helper-reply update`) |
| `helper addpatch <user> <repo>` | clones repo; on success replies `/addpatch <repo>` → `/rpt <id> helper-reply addpatch <repo>`; PD self-triggers update |
| `helper pullpatch` | runs pull_active_patch.sh (no reply) |
| `helper checkout <branch>` | **unreachable from the LAN**: helper.py has a `/checkout` handler, but PD's `process-helper-messages` route list omits `checkout`, so it is never forwarded |
| `helper config` | helper re-reads `bopos.devices` by MAC, replies `/id <n>` on 6661 (sets ID; nothing on the wire) |
| `io create/poll/list …` | forwarded to io/main.py on 8880; replies come back on 6662 into osc-in (patch-facing, not reported to 5550) |

## Localhost plumbing (per device — simfleet collapses this)

7770 helper listens, 6661 helper→PD replies, 8880 io listens, 6662 io→PD.
simfleet simulates the *observable LAN behaviour* of the whole box (PD +
helper.py together), not the localhost hops.

## Identity

`start.sh` passes the wlan0 MAC to helper.py; `bopos.devices` maps
`MAC, hostname, ID, POSL, POSR`. Real fleet MACs are in the repo's
`bopos.devices`; the simulator generates locally-administered fake MACs by
default (`02:xx:…`) so a sim fleet can't be confused with real Pis on the LAN,
and can load a `bopos.devices`-format file with `--devices-file`.

## Timing summary

- heartbeat period 10 s, phase = PD start time (sim: stagger start ~0–2 s)
- reboot ≈ 30–60 s silent on a real Pi (sim default shorter, flag-tunable)
- update ≈ git pull (2–10 s) + `sleep 5` + reboot
