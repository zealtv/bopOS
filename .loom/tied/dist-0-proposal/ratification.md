# Ratification — Bob, 2026-07-13 (verbatim feedback + rulings)

Bob's feedback on `proposal.md`, verbatim:

> here's my feedback: ok re patches being either git or host managed.  this
> needs to be clear in the ui.  patches that are git patches should have an
> icon or similar.
>
> might want to be able to hot update running patches (triggering an engine
> stop and start) in the future.  ok to hold off for now.
>
> 3.2 ok
>
> 5 - drop the gdrive fetch scheme now.  this is a hard break.
>
> same for get samples.  hard break.
>
> same with the fallback. hard break.
>
> i think we need to explicitly make update updatebopos to indicate it is not
> updating the patch (or assets)
>
> 7 friction docs -
> git can be an it's own section "advanced workflow with git"
>
> Q1 one sync all is good
>
> Q2 hard break, kill now
>
> q3 yes, drop is useful
>
> q4 let's go with violence - maybe confirmation gated
>
> q5 - ok for now
>
> q6 - yes

## Rulings as applied

- **Ratified as proposed:** the mirror model, `patch:` slot on `/os/fetch`,
  git-XOR-host-mirrored rule, `/os/patches` + `/os/droppatch` (3.2 ok),
  Send assets / Send patch / one **Sync all** (Q1), `demo-pd`/`demo-sc`
  (Q5, "ok for now"), `templates/` dissolves (Q6).
- **Amendment — git visibility in UI:** git-managed patches get an icon (or
  similar) in the dashboard so the git/host-mirrored split is legible.
  → dist-3.
- **Amendment — hard breaks, no legacy windows** (supersedes the proposal's
  one-release windows): `gdrive:` fetch scheme dies now; `getsamples`
  (verb, script, button) dies now (Q2); the no-manifest `main.pd` legacy
  fallback dies now — a patch requires a valid `bopos.patch.json`.
- **Amendment — verb rename:** `/os/update` → **`/os/updatebopos`**, so the
  wire itself says it does not update the patch or assets. Hard break
  consistent with the above (no alias). Dashboard label "Update bopOS".
- **Q3:** yes — `droppatch`, and asset-slot drop (`dropassets <slot>`) since
  the question bundled them and "drop is useful".
- **Q4 — send-to-active:** *violence, confirmation gated*: sending the active
  patch stops the engine, converges, restarts; the dashboard confirm-gates
  it. Note: Bob's earlier remark ("hot update … ok to hold off for now")
  reads as the same flow deferred; Q4's explicit answer is taken as the
  ruling. Node side does not refuse; the confirm gate is dashboard-side.
- **friction-0-docs:** unblocked; git is not in the main flow — it becomes
  its own section, "advanced workflow with git".

Consequences executed at tie time: `dist-1..4` children created (with the
amendments folded in), `samples-0..2` and the `sample-distribution` goal
dropped as superseded, `friction-0-docs` un-waited.
