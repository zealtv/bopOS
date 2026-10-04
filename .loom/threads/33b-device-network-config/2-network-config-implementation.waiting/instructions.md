# 2-network-config-implementation

**Status:** ready (`1` ratified 2026-10-04)
**Goal:** build the ratified design in `../1-network-config-design/decisions.md`
— read it first; it's the spec. Trust model: `../0-lan-trust-review/ruling.md`.

Work in slices that each verify and commit. The `log-config` / `audio-config`
paths are the precedent; follow their shape file by file.

## 0. Platform (needs a device up — Bob)

- Which network manager the supported Pi OS images use (don't assume
  `wpa_supplicant` / NetworkManager / `wlan0`), and how it marks a hidden
  network, priority, autoconnect-off, root-only secrets, and listing SSIDs
  without secrets. Record the finding here before writing the helper backend.
- Slices 2–4 don't need this; build them against a fake helper first.

## 1. Device helper

- `systemd/bopos-set-wifi`: no arguments; JSON on stdin; strict validation
  (same rules as the wire); writes only bopOS-owned profiles, adopts an
  unmanaged profile by SSID, never deletes unmanaged ones; prints the redacted
  `wifi` object. `--status` prints it without changing anything.
- `systemd/bopos-power.sudoers` + `bash/install-power-control.sh`: authorize
  the exact helper path (and the already-installed check), installed like
  `bopos-set-hostname`. `bash/provision.sh` installs the helper.

## 2. Node (`python/bopos.py`, new `python/wifi_config.py`)

- `/all/os/to <uid> wifi-config <json>` → validate → helper via stdin →
  `/os/wifi-config <uid> <ok|err> <phase> <json>` (`applied`, `invalid`,
  `unavailable`, `failed`); receipt sent before the network re-evaluates.
- `psk: null` with no secret on the device → `invalid`. No enabled network →
  `invalid`.
- `/os/report` gains the redacted `wifi` object (`managed: false` without
  Wi-Fi or helper).
- Never log the request args; nothing in `bopos.config` or the store.

## 3. Dashboard back end (`dashboard/osc_bridge.py`, `server.py`, `state.py`)

- Fleet list (SSIDs, hidden, enabled, order, country) in installation state —
  which, once `66-projects/3-project-storage` lands, is `project.json` (the
  fleet is the project's). Queued after that slice so the list is placed once.
- Passphrases in `state/wifi-secrets.json`, mode 0600; never in WS state,
  installation/venue files or logs; never sent to the browser.
- Send per device: include `psk` only where the device reports `secret: false`
  or the passphrase changed; receipt timeout like `log-config`.
- **Redact `wifi-config` args in the `osc_out` console tap.**
- Per-device sync state for the chips (in sync / differs / needs passphrase /
  no Wi-Fi / sending / error).

## 4. Simulator (`tools/simfleet.py`)

- Virtual devices accept `wifi-config`, keep `secret: true`, never the
  passphrase; report the `wifi` object.

## 5. UI (`dashboard/static/js/dashboard.js`, `css/style.css`)

- Wi-Fi networks panel on the **Devices** tab, above the device list: ordered
  list (▲/▼), SSID, hidden, enabled, masked passphrase ("secret set", blank =
  keep), ✕, country, **Send to all devices**.
- **Passphrase warning + confirm** before any send carrying a passphrase
  (wording in decisions §6 — show Bob in the running app; it's operator-visible
  wording, his to approve).
- ⚠ warning when disabling/removing a network devices are on now; Send
  disabled with no enabled network.
- Per-device chip; unmanaged SSIDs on the device row with "add to list".

## 6. Contract and docs

- Write v1.20 into `docs/OSC-CONTRACT.md` (§6 + §15) from decisions §8, and
  `docs/OSC-REFERENCE.md`. Update the glean `osc-contract` version note.
- Same edit pass: `docs/OSC-CONTRACT.md` ~line 806 still says the facilitator
  allowlist lives in `installation.json`; since `66/3` it is `project.json`
  (editorial, but show Bob with the v1.20 text).
- `docs/INSTALL.md`: helper install; a short note that Wi-Fi is provisioned in
  the workshop on your own network (trust model from `0`).

## Verification gates

- Unit (`tests/test_wifi_config.py`): every rejection, keep-secret semantics,
  helper invoked with no args and secrets on stdin, redaction — console tap,
  WS state, installation/venue files, logs, receipts, report, simulator.
- Browser journey (`tests/verify_wifi_networks.py`): edit, reorder, disable
  with warning, passphrase-warning confirm, send, chips.
- **Real Pi (Bob's hands):** workshop switchover rehearsal — both APs up, push
  the list, disable *testing*, every device reappears on the hidden show
  network; disable show 1, fallback takes over. Record device and framework
  revision (glean `hardware-claims`).

## Waiting on Bob (parked 2026-10-04, built through commit d6b935f)

Slices 1–6 are built and committed. The helper's network-manager backend reports
`unavailable` behind a marked seam. Still owed:
- Slice 0 with a Pi up: choose the network manager and fill in the helper backend.
- The real-Pi switchover rehearsal (verification gates).
- The editorial fix to OSC-CONTRACT (the `installation.json` → `project.json` mention, now ~line 859).

**Ruled 2026-10-04 (Bob, via Tengu):** the passphrase warning wording as built is
approved ("⚠ This sends N passphrase(s)…", with proper plurals, N = distinct networks).
