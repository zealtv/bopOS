# dist-2-node-side

**.waiting — deferred by Bob (2026-07-13): ratified, implement later. Resume
only on his explicit green light; do not claim autonomously.**

Node/framework side of the ratified model (authority:
`.loom/tied/dist-0-proposal/`; contract text from dist-1). Surveys with
file:line for everything touched are in the tied stitch dir.

- [ ] **`patch:` landing**: extend `python/fetcher.py` slot handling + the
      bopos.py fetch worker (`bopos.py:288-331,659-667`) — `patch:<name>`
      lands in `patches/<name>/`, refuse err if `.git` present. If `<name>`
      is the active patch: stop engine, converge, restart engine, then reply
      (Q4 — node never refuses on active; no reboot, engine restart only).
- [ ] **Hard removals**: `gdrive:` scheme from fetcher.py; `/os/getsamples`
      verb from bopos.py (PROVISION_VERBS, `bopos.py:841-847,1017-1024`);
      `bash/getsamples.sh`; patch-level `bopos.config` reading
      (`getsamples.sh` was its only consumer); the no-manifest fallback in
      `python/manifest.py` (exit-3 path, 100-118) and
      `bash/start-engine.sh:12-19` defaults — invalid/missing manifest now
      fails the launch loudly (`/os/patch` validation in `bopos.py:876-909`
      already requires manifest-or-main.pd; tighten to manifest-only).
      Check `bash/clearsamples.sh` and the legacy samplepacks symlink
      adoption (`start-engine.sh:40-61`) — decide with the contract text
      whether the symlink dies in the same break; record the call here.
- [ ] **Verb changes**: `/os/update` → `/os/updatebopos` (rename in
      bopos.py + `bash/update.sh` invocation path; no alias);
      add `/os/patches` (JSON list `{name, active, git, manifest}`),
      `/os/droppatch <name>` (refuse active), `/os/dropassets <slot>`;
      all reply `/os/rev`.
- [ ] **Fetch progress observability** (inherited from dropped samples-1):
      progress visible while a fetch runs — contract-cleanest option, shaped
      additively and flagged (delegated wire-shaping rule).
- [ ] **`hostname` in `/os/report`** (additive; ratified via
      `dashboard-8-identity-sim-design` Q6): bopos.py adds the node's
      hostname to the report JSON — the dashboard seats work (d8-1/d8-3)
      consumes it for name suggestions.
- [ ] **simfleet parity in the same stitch**: fetch `patch:` simulation,
      patches/droppatch/dropassets members, updatebopos rename, getsamples
      member removed.
- [ ] **gitignore**: `patches/*` and `assets/*` ignored except the demos
      (coordinate with dist-4 naming).
- [ ] verify_*.py (browser-free): sim + real fetch into temp dirs — patch
      send converges + prunes, `.git` target refused, active-patch send
      restarts engine (observable via run context change), dropped verbs
      gone, new verbs reply.
