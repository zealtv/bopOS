# os-admin-verbs — verification

Date: 2026-07-08. All checks on the dev laptop, loopback only.

## What ran

- `test_admin_verbs.py` — 26/26 PASS.
  - Part 1: helper.py's `handle_lan_datagram` with monkeypatched callbacks
    (nothing executes for real): dispatch of every verb, `/os/rev` shape
    (`sha model uid` unicast to requester:5550), post-action sha in
    provisioning receipts, reply-before-execution ordering for lifecycle,
    selector matching, ephemeral no-op + receipt, ephemeral lifecycle still
    executing.
  - Part 2: real `dashboard/server.py` + real `tools/simfleet.py`
    (4 devices: 1 ephemeral, 2 engine-dead) over the websocket — the stitch's
    verify criterion verbatim: **update-all → every device replies `/os/rev`
    with the bumped sha; the dead-engine devices still answer** (helper owns
    the verbs, not PD); the ephemeral device honestly reports the old sha.
- `verify_browser.py` — 4/4 PASS (headless Chromium): Converged line renders
  the receipt, Restart-Engine button present and answered, update receipt
  shows the bumped sha while Version still shows the pre-reboot one
  (screenshots `03-converged.png`, `04-updated.png`).

## What loopback did NOT cover (needs a real rig / Bob)

- Actual execution of the delegated scripts (`update.sh`, `checkout.sh`,
  `getsamples.sh`, real `systemctl reboot/poweroff`) — the callbacks were
  faked in part 1 precisely so the laptop survives the test.
- The receipt-vs-reboot race on real `update` (design-decisions.md §3): does
  the `/os/rev` datagram reliably escape during the systemd stop window?
- Real-WiFi broadcast behaviour of the new verbs across the fleet.
- PD coexistence on 6660 (SO_REUSEPORT with a live PD instance) — unchanged
  code path, but the new verbs haven't been seen by a real PD next door.

Rebuild the test env: `python3 -m venv venv && pip install pyOSC3 python-osc
websockets playwright -r dashboard/requirements.txt && playwright install
chromium --only-shell`, then run both scripts with that python.
