# dist-1-contract-amendment

Write the ratified distribution model into `docs/OSC-CONTRACT.md` (v1.3).
Authority: `.loom/tied/dist-0-proposal/` (proposal.md + ratification.md —
Bob's rulings 2026-07-13, all hard breaks, no legacy windows). Work this
before dist-2/3/4 so implementation cites settled text.

- [ ] §9: `patch:<name>` slot prefix on `/os/fetch` — lands in
      `patches/<name>/`, same convergence semantics; refuse (err) if the
      target contains `.git` (a device patch is git-managed XOR
      host-mirrored). Sending the *active* patch is allowed and means
      stop-engine → converge → restart (Q4 "violence"; the confirm gate is
      dashboard-side, the node does not refuse).
- [ ] §9: **`gdrive:` scheme removed** (hard break). `http:`/`file:` remain.
- [ ] §7: `/os/update` → **`/os/updatebopos`** (rename, no alias — it never
      updated the patch or assets and now says so); `getsamples` verb
      **removed**; add `/os/patches` → `/os/patches <json>` (unicast; list of
      `{name, active, git, manifest}`), `/os/droppatch <name>` (refuses the
      active patch), `/os/dropassets <slot>` (Q3). Drops reply `/os/rev` like
      other provisioning verbs.
- [ ] §8: a patch **requires** a valid `bopos.patch.json` — the no-manifest
      `main.pd` fallback is removed (hard break). Patch-level `bopos.config`
      is retired entirely (its only key served getsamples).
- [ ] §13 migration: record the hard breaks for the deployed fleets (Kite
      Choir, The Plants) — they move in lockstep, no compatibility shims.
      Cross-repo: note it for `kite-choir-brains/.loom` (`bopos-uptodate`
      sibling) — coordinate, don't duplicate.
- [ ] §14 if apt: gdrive ingest and undeclared-patch launch join "rejected by
      design".
- [ ] §6: **`hostname` joins the `/os/report` JSON fields** (additive) —
      ratified via `dashboard-8-identity-sim-design` Q6 (Bob 2026-07-13);
      heartbeat stays lean. One contract touch for both threads.
- [ ] Rewrite the stale `patches/README.md` ("entry point is always main.pd"
      is wrong) against the new model; note the host layout (`patches/`,
      `assets/`, demos, composer dirs gitignored).
- [ ] Contract-only stitch: no code changes here.
