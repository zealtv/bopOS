# 1-dead-code

**Status:** verified within the user's boundaries; see `verification.md`.
**Goal:** delete what nothing uses. Verify each item is really unused before
deleting (grep tests and the frontend, including computed message names).

## Checklist

- [x] **Websocket verbs the server handles but the UI never sends:**
      `switch_patch`, `sync_distribution`, `set_points`, `list_venues`,
      `save_show_as`, `restart_edit` (alias of `relaunch_edit`). `set_param`
      is used only by tests — move those tests to `set_live_param` or confirm
      it's needed. (`add_patch` goes with `68`.)
- [x] **Unused methods:** `server.py` `active_param_identities`,
      `_current_patch_fingerprint` (may go with `65`), `device_elements`
      (also missing `self`); `simfleet.py` `wire_id`, `match_id`,
      `admin_request` (retained for 68 under the user's Git-route boundary).
- [x] **Superseded scripts:** `bash/update.sh`, `bash/checkout.sh` —
      `converge_framework` in `bopos.py` replaced them. Update the hint in
      `bash/provision.sh`.
- [x] **Leftovers:** `add_seat` / `update_seat` still pass a per-seat `patch`
      that `clean_seat` drops; the redundant conditional in the `/os/fetch`
      short-args branch of `handle_lan_datagram`.
- [x] **Patch editor allows only element 0/1** (`set_editor_point_element`)
      though positions now support any number. Decide: allow N, or document
      why two. Recommendation in `element-recommendation.md`; behavior unchanged.
- [x] **pyflakes:** unused `json` (`server.py`), unused `patch_manifest`
      (`show_model.py`), `identity` shadowed by loop variables
      (`server.py:1831`, `2067`), unused `socket` and placeholder-less
      f-strings (`io/main.py`), unused `global` (`nodelog.py`), unused `HEIGHT`
      (`io_ssd1306.py`).
- [x] **simfleet docstring** still describes `LegacyProtocol`,
      `bopos.osc.pd` and a retired stitch's `wire-protocol-today.md`.

Done when: `pyflakes` is clean on `dashboard/ python/ tools/`; fast + browser
green.
