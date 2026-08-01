# 4-osc-quickref — notes

New durable doc `docs/OSC-REFERENCE.md`: every OSC message a bopOS node
speaks, both directions, as a complete constructible message (address +
typed args + port + expected reply), per Bob's 2026-07-17 request. Written
after 1–3 were tied so `/admin` and the run-context additions are covered.

## Shape delivered

- §1 "Commands you send to the fleet (LAN 6660)" — identity/liveness/debug,
  safety mute, the exact-UID admin envelope, Seat-group membership,
  assignment, lifecycle/provisioning verbs (generic selector), patch/asset
  distribution + params + storage, patch parameters/master/spatial points,
  sync/cue plane.
- §2 "What comes back on 5550" — every reply/heartbeat shape.
- §3 "The engine surface (localhost)" — bopos.py → engine (6661) and the
  engine-sent 7770 surface including the new `/admin`.
- §4 "Worked examples" — mute, reboot (two spellings: by Seat id and by
  uid), update-patch, switch-patch, and a raw Python (`pyOSC3`) one-liner,
  using `oscsend` syntax throughout.
- Linked from README's technical route (System section), `docs/PORTS.md`
  (both a top-of-doc pointer and the 7770 row now names `admin`), and
  `docs/OSC-CONTRACT.md`'s "How to read it" paragraph, as required.
  `docs/OSC-CONTRACT.md` stays normative; the new doc says so twice
  (its own intro and the contract's pointer back).

## Cross-check process and what it found

Read the full current `docs/OSC-CONTRACT.md` (all 15 sections) and the
complete relevant code paths in `python/bopos.py` before drafting: `handle_
lan_datagram`, `dispatch_uid_admin`/`UID_ADMIN_VERBS`, `dispatch_admin_verb`/
`LIFECYCLE_VERBS`/`PROVISION_VERBS`/`run_admin_verb`/`rev_reply`, the 7770
callback map (`admin_callback`/`ENGINE_ADMIN_VERBS`, `config_callback`,
`store_callback`, `load_callback`, `report_callback`), `apply_assign`,
`apply_unassign`, `apply_groups`, `set_mute`/`set_device_mute`, `identify`,
`set_device_hostname`, `report_reply`, `build_heartbeat`, `apply_points` +
`python/pointfield.py`, and `python/relay.py`'s `shape_provided_term`.

**One real finding, corrected in the doc rather than papered over:** my
first draft claimed several provisioning verbs (`addpatch`, `pullpatch`,
`droppatch`, `dropassets`, `patch`) send **no** LAN reply, or that `patch`'s
`/os/rev` carries a status/phase like `ok converged`. Re-reading
`dispatch_admin_verb`/`run_admin_verb` line by line: **every** verb in
`PROVISION_VERBS` reaches `run_admin_verb` with a real `reply_socket`
(whether invoked from the generic selector path or the exact-uid envelope),
and `run_admin_verb` calls `rev_reply` unconditionally whenever
`reply_socket is not None` — with status/phase only when the callback
returned a dict. Checked which callbacks return a dict:
`update_bopos_callback`/`checkout_callback` do (via the shared
`converge_framework` helper); `add_patch_callback`, `pull_active_patch_
callback`, `drop_patch_callback`, `drop_assets_callback`, and
`switch_patch_callback` all return `None`/`bool` and therefore always
produce a **bare** `/os/rev <sha> <model> <uid>` with no status/phase —
even when the operation was refused (e.g. `droppatch` on the active patch)
or failed. The contract's `[<status> <phase>]` bracket already marks this
optional (v1.6), so this isn't a contract violation, but it's exactly the
kind of thing an operator constructing messages by hand needs to know: you
cannot tell success from failure for those five verbs from the `/os/rev`
alone. Documented this explicitly in the reference (a note under the
Lifecycle/provisioning table) rather than silently "correcting" my draft
to something plausible-looking. Confirmed the same behaviour independently
in `tools/simfleet.py`'s `admin_verb` (its own `send_rev` calls for
`addpatch`/`pullpatch`/`droppatch`/`dropassets`/`patch`-refused are all
bare, no status/phase args — matches production).

No other discrepancy between the contract and the code was found.

## Verification

`verify_osc_quickref.py` (run with `~/.venvs/bopos/bin/python`) — 18/18
checks pass, two layers:

1. **Static cross-check** — regex-extracts the doc's exact-uid zero-arity
   verb set, its lifecycle/provisioning verb set, and its `/admin` action
   set, and asserts each equals the real `UID_ADMIN_VERBS` /
   `LIFECYCLE_VERBS ∪ PROVISION_VERBS` / `ENGINE_ADMIN_VERBS` sets read
   straight out of `python/bopos.py` — so an invented or missing verb in
   the doc fails loudly. Confirms `/admin` is really registered on the
   7770 server. Confirms (via source inspection) which callbacks can
   return a status/phase dict and which cannot, matching the doc's bare-vs-
   status/phase claims per verb. Confirms the three required doc links
   exist (README, PORTS.md, OSC-CONTRACT.md).
2. **Live cross-check against `tools/simfleet.py`** (per the stitch
   instructions) — launches the real simulator on free localhost ports,
   sends the doc's mute worked example **verbatim** (the same `pyOSC3`
   calls the doc's Python one-liner shows) at `/all/os/to
   02:53:49:4d:00:01 mute 1`, and asserts the real `/os/mute <uid> 1 1`
   reply arrives (skipping past heartbeat noise on the same socket).
   Un-mutes, then sends the doc's report example and asserts `/os/report`
   arrives with `contract_version: "1.7"` in the live payload. Also sends
   the doc's fleet-wide `/all/os/mute 1` broadcast example and confirms
   the simulator stays up and accepts it.

Ran: `~/.venvs/bopos/bin/python .loom/threads/patch-admin-surface/
4-osc-quickref.stitching/verify_osc_quickref.py` — `18/18 passed`.

## Honestly out of scope / not verified here

- Every table row was checked against the *code*, not against real Pi
  hardware — the reboot/shutdown/hostname/mute mixer-path rows describe
  contract-documented behaviour that ultimately needs a live rig to see
  fire for real (same caveat as the rest of this thread).
- `oscsend` itself was not run (not installed in this environment); the
  worked examples were validated by construction (matching liblo's
  documented `host port path types args...` calling convention used
  correctly elsewhere) and by the live `pyOSC3` equivalent for the mute/
  report pair, per the instructions' explicit ask.
