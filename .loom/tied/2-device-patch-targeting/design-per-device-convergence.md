# Design — per-device convergence generation tracking (Bite 2)

The hard part the progress note flagged. Written before coding.

## The collision

`converge_fleet_patch` uses `self.fleet_generation` as its liveness token: every
loop iteration bails if `generation != self.fleet_generation`. `set_fleet_patch`
→ `stage_and_converge` → `supersede_fleet_operation` does three **global**
destructive things (server.py:1728):

1. `fleet_generation += 1` — invalidates every in-flight convergence loop.
2. cancels `fleet_operation` and every `fleet_retries` task.
3. **wipes `patch_switch` on every device.**

A naive singleton reuse (`converge_fleet_patch(name, fp, {uid}, …)` after
`supersede_fleet_operation()`) would therefore let a device pin cancel a running
fleet deploy and vice-versa, and wipe every other device's attempt state.

## The design — a second, per-device generation track

Keep **one** convergence algorithm (ratified: "do not fork the convergence
machinery"); give it a swappable liveness token.

1. **State (`__init__`):** `self.device_operations = {}` (uid → Task),
   `self.device_generations = {}` (uid → int).

2. **`converge_fleet_patch(..., generation, is_current=None)`** — add an
   `is_current` callable; default `lambda: generation == self.fleet_generation`
   preserves the fleet path byte-for-byte. Replace the 4 in-body
   `generation (!=|==) self.fleet_generation` checks with `is_current()`. The
   fleet caller is unchanged; the device caller passes
   `is_current=lambda: gen == self.device_generations.get(uid)`.

3. **`_supersede_device_operation(uid)`** — the per-device mirror of
   `supersede_fleet_operation`, but scoped to one uid: bump
   `device_generations[uid]`, cancel only `device_operations[uid]`, clear only
   *that* device's `patch_switch`. Never touches the fleet track.

4. **`converge_device_patch(uid, name, ws)`** — validate catalog + targeting
   (`uid in distribution_targets(uid)` ⇒ online **and** seat-bound; else the
   same seat-required error `retry_fleet_patch` raises), persist is done by the
   handler, then spawn `converge_fleet_patch([uid], …, is_current=device-token)`
   into `device_operations[uid]`.

## Fleet deploy must respect pins (correctness, not extra scope)

Without this, the next `set_fleet_patch` switches a pinned device away from its
pin — pinning would be a lie. Two minimal edits:

- `stage_and_converge`: `targets = [uid for uid in distribution_targets("all")
  if not self.state.device_patch_for(uid)]` — pinned devices are excluded from
  the fleet fetch/switch; their badge is measured against the pin (bite 1) so
  they read `current`, not stale.
- `supersede_fleet_operation`: clear `patch_switch` only for devices **without**
  an override, so a fleet deploy doesn't stomp a pinned device's in-flight op.

`retry_fleet_patch` is made effective-desired-aware so retrying a pinned device
retries its pin, not the fleet patch.

## Scope reality to surface (feeds the proposals + handoff)

OSC v1.5 targets content ops **by seat**, so `distribution_targets(uid)` yields a
target only for a seat-bound, online device. **Pinning a patch therefore
requires the device to be bound to a seat** — including the "standalone" Ciro
Toast (bind it to its own lone seat). This is not a new limitation (the fleet
retry guard already says it); the truly-seatless-control question belongs to the
deferred shared-surface / set-patch-hand-off design, where it is called out.

## Virtual (host-backed `simulation.active`) devices

`device_desired_patch` returns the fleet target for `virtual` devices (bite 1),
so pins don't apply to the in-process simulated fleet. `converge_device_patch`
rejects virtual devices. The Playwright/simfleet path uses **real** (non-virtual)
OSC-speaking fake Pis, so the override applies there — that is the tested path.
