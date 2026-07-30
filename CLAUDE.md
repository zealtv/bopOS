# Working notes for agents

bopOS is a Raspberry Pi + Pure Data framework for networked multi-device sound
installations. This file is the orientation for any agent working here.

## Start here

1. `README.md` — system overview, OSC port map, patch system.
2. `docs/OSC-CONTRACT.md` — the **ratified** OSC contract (**now v1.17**; the
   version list below is historical through v1.11 — read §15 Revision history
   in the contract itself for the authoritative record, including the v1.14
   additive `/e/*` event plane, the v1.15 hard-break `/cue` retirement, the
   v1.16 event-element `labels` retirement, and the v1.17 host-side preset
   foundations (§8.1 + the `presets/` distribution exclusion, no new wire
   form).
   v1.11: 2026-07-07 base +
   the 2026-07-11 seam amendment, 2026-07-12 engine-boundary revision,
   2026-07-13 patch/asset distribution amendment, and the 2026-07-14
   fleet-patch fingerprint/cues amendments, the 2026-07-15 UID-admin and
   unassignment revision, the device asset-inventory amendment, the
   2026-07-17 patch-admin-surface amendment (engine-sent `/admin` requests,
   version/patch-fingerprint in the run context), the 2026-07-19
   parameter-automation grammar (§3.2 generator slots on numeric `/p/*`),
   the 2026-07-23 multi-asset-slot run-context revision, and the 2026-07-23
   physical-device enabled/execution-routing revision, and the 2026-07-23
   physical-device audio-configuration revision):
   grammar, planes, provided terms (§4.1), the engine surface (§4.2),
   identity/persistence, ports, constraints. Don't re-litigate it; the reasoning
   lives in lore items `2026-07-07-osc-schema-council`,
   `2026-07-10-patch-seam-council`, and tied `engine-boundary-ratification`.
3. `.notes/architecture-review-2026-07-05.md` — the current architectural review and
   forward plan; the shared context every loom thread points back to.
4. `./.loom/loom.sh status` — live task state. The loom (`.loom/`) is the task tracker;
   read `.loom/README.md` for the protocol (claim → work → tie; split when too big).
5. `.notes/dashboard-development-context.md` — full dashboard design (stack, protocol,
   UI) if working on dashboard threads.

Verification levels and representative commands are collected in
`docs/VERIFICATION.md`. Stitch-local instructions and verification artifacts
remain the authority for a particular piece of work.

## House rules

- **NEVER edit Pure Data patches (`.pd` files).** PD programming is Bob's domain.
  Agents work on Python, Bash, JS/HTML, architecture, and docs.
- **PD float precision:** PD's OSC floats are 32-bit. Never send a value needing >6
  significant figures (epoch timestamps, fine clocks) through PD as a float — encode
  64-bit values as strings or int pairs, and keep absolute time out of PD entirely.
- **0-indexing is the default** for elements, points, and any new index on the wire
  or in code (Bob, 2026-07-11). Human-facing labels may render however the UI likes,
  but the wire and the data model count from 0.
- **Decision gates:** some choices are Bob's to ratify — the OSC port/namespace
  redesign, scene-language syntax, engine strategy calls, anything user-facing in the
  facilitator view. Produce a written proposal (see Lore below), mark the stitch
  `.waiting`, and surface it to Bob. Don't implement past an unratified design.
- Commit style: plain prose subject line (match `git log`), body explaining why.

## Next sweep — holistic ordered program of work (2026-07-23)

> **Update 2026-07-27 (control-panel UI + architecture review):** Bob's
> braindump (lore `2026-07-27-control-panel-ui-and-architecture-braindump`,
> which holds the transcribed mockup annotations and session directives)
> reordered the front of the queue. Priority now: **(1)
> `desktop-ui-overhaul/01-control-panel`** — first the small ratified
> behavior change `1-full-manifest-visibility` (the Control tab shows **all**
> manifest params; the manifest's `dashboard:` flag now gates only the
> facilitator/iPad view — this supersedes the "Dashboard live controls come
> only from `dashboard: true`" line below once shipped), then
> `2-control-panel-design`, the compact grayscale/cyan mockup-driven design
> pass (Bob ratifies). The old app-wide density stitch was renamed
> `02-app-wide-rollout-design` and then **dropped on 2026-07-30** in favour of
> `02-component-unification` (components first — see Tier 3).
> **(2) `entity-architecture-review`** — in parallel with
> or after the UI work: `1-system-map` (as-is entity/storage/coupling map for
> devices, seats, groups, patches, presets, shows) then
> `2-workflows-and-simplification` (workflow walkthroughs + a
> simplicity-first proposal, Bob reviews). **Done same day — the whole
> review thread is TIED (2026-07-27, live session with Bob).** The as-is map
> is `.notes/entity-map-2026-07.md`; the ratified model and forks are in
> `.loom/tied/2-workflows-and-simplification/` (proposal.md + decisions.md):
> four layers (hardware → site → content → composition), fingerprinted
> content references with derived non-blocking drift warnings, portable
> shows target groups **by name**, venue presets retire when 41 lands,
> collections start as show steps, one application path with hard takeover.
> **Same-day resequencing (Bob):** the mockup's new parameter kinds may need
> to exist before the preset design, so **`44-event-plane`** (Bob-gated
> contract design, `.waiting` on queue order) now sits **between the
> control-panel work and `41-preset-primitive`**. **Scope narrowed
> 2026-07-27 (Bob):** toggles and integers already exist (a toggle is
> `type: "i"`, `min: 0`, `max: 1`) and enums shipped as `options` on an
> integer param, so **events are the only missing kind and the only wire
> work.** Further rulings the same session: **every event forward-syncs**
> (the mockup's per-row `sync` button is dropped; global lead time `0` *is*
> sync-off), the manifest moves to an explicit **`kind`** field as a hard
> break, event elements are **free-form labeled floats** (arity 1–3;
> note/velocity/duration is convention, not enforced), **presets do not
> capture events**, and **no event automation is designed** (door named
> only). Events are already declared-but-inert in the manifest today. Bob also added the
> **capture-as-step** workflow (Control tab → one click stores the current
> target→preset arrangement as a show step) as design input for 41's Q6.
> **Second 2026-07-27 braindump** (lore
> `2026-07-27-events-cues-and-global-controls-braindump`): **a cue is an
> event with zero elements**, and Bob ruled same-session that cues are
> **absorbed into the event plane as a hard break** — the `/cue` plane goes
> away in `44-event-plane`'s contract revision, no compatibility shim (no
> production shows rely on cues; keep the code clean). Cue triggering moves
> onto the control panel targetable at all/group/seat. The control panel
> gets separate parameters and events sections. Master fader, MUTE ALL, and
> cue lead time relocate to a Monitor-dock panel
> (`desktop-ui-overhaul/03-global-controls-monitor`, ratified direction);
> the Monitor name itself may be revisited later. Patch-tab manifest entries
> become drag-reorderable to reorder the control panel
> (`desktop-ui-overhaul/01-control-panel/8-manifest-reorder`).
> **Order — ratified by Bob 2026-07-28, supersedes the 2026-07-27 line.**
> `27-tied-guard-rot`, `46-control-surface-probe-race`, the control-panel
> implementation slices, and **`44-event-plane/1` (design, ratified & tied)**
> are all complete. The live order is:
>
> **Steps 1–3 are COMPLETE and tied (2026-07-28).** `2-kind-grammar` shipped
> the explicit `kind` field; `3-event-plane-wire` shipped `/e/*` and the `"0"`
> fire-on-arrival sentinel as **contract v1.14** (commit `cbac939`); and
> `4-cue-retirement` deleted `/cue` and the manifest `cues` key outright as
> **contract v1.15** (commit `e8e998b`), which is where the contract stood
> at the end of that step —
> `/cue` no longer exists anywhere in `python/`, `dashboard/`, `tools/` or the
> patch manifests, and cue firing lives on the control panel's events section,
> targetable at all / a group / one seat. **Step 4 is also complete and tied
> (2026-07-28): master, MUTE ALL, and event lead now share a Globals panel in
> the Monitor dock, and a muted fleet stays visible on the collapsed dock
> header. Step 5 (`8-manifest-reorder`) is tied too, and Bob's 2026-07-28
> review of the shipped panel added and tied
> **`desktop-ui-overhaul/04-event-fire-affordance`**: the top `#event-panel`
> (buttons *and* the lead field) is deleted from both the Control tab and the
> standalone iPad view, the row's `fire` button became a 58 × `--row-h`
> panel object carrying the retired cue's lead sweep + fire flash (cyan —
> `decisions.md` widens `cyan = modulation` to "something is driving this,
> continuously or discretely"), and Events now render above Parameters on the
> panel and in the manifest editor. Lead time is desktop-only from here: an
> iPad fires, it does not configure. **The live next step is 6.**
>
> 1. ~~`44-event-plane/2-kind-grammar`~~ — done.
> 2. ~~`44-event-plane/3-event-plane-wire`~~ — done, contract v1.14.
> 3. ~~`44-event-plane/4-cue-retirement`~~ — done, contract v1.15.
> 4. ~~`desktop-ui-overhaul/03-global-controls-monitor`~~ — done. The three
>    global controls left the app header, the Control tab, and the Show
>    transport for one `Globals` Monitor panel. Bob's "Monitor may want
>    renaming" note is carried in the tied stitch's `decisions.md`.
> 5. ~~`desktop-ui-overhaul/01-control-panel/8-manifest-reorder`~~ — done, and
>    `04-event-fire-affordance` re-passed the same surface (section order).
> 6. `44-event-plane/5-pd-adoption` — **next**, **Bob's**: the `.pd` receiver edits plus
>    the Finn Jet / Ciro Toast rig check. Thread 44 cannot tie without it.
> 7. `desktop-ui-overhaul/02-component-unification` — **live, and the active
>    front of the queue as of 2026-07-30.** `02-app-wide-rollout-design` is
>    dropped: Bob reversed the order to components-first (lore
>    `2026-07-30-ui-unification-braindump`). Inventory is complete
>    (`.notes/component-inventory-2026-07.md`); children run
>    ~~`02-token-promotion`~~ (tied 2026-07-30 — one metric layer, see Tier 3)
>    → **`03-chrome-reclamation` (next)** →
>    `04-generator-drawer-component` → `05-value-box-component` →
>    `06-control-panel-reflow-and-editor` → `07-target-selector-component` →
>    `08-control-tab-columns` (`.waiting`, Bob-gated) →
>    `09-patches-deploy-row`.
> 8. ~~`41-preset-primitive/1`~~ — **design gate CLEARED and TIED 2026-07-28**;
>    Bob ratified all four forks (`.loom/tied/1-preset-architecture-design/`
>    proposal.md + decisions.md). A preset is **not a wire concept**: an entry
>    is the `/p/<identity>` argument list, stored sparsely in
>    `patches/<patch>/presets/<slug>.json`, applied as an ordinary fan-out.
>    `presets/` is excluded from the distribution fingerprint (otherwise every
>    save restages the fleet patch); capture-as-step omits targets with no
>    preset applied; the applied-preset marker stores provenance with
>    **derived** dirtiness (R5). Two reviews followed
>    (`.loom/tied/2-proposal-review/`, `.loom/tied/3-addendum-review/`); the
>    addendum plus `review-2.md` are authoritative over the proposal where
>    they differ. **Bob dropped `morph` from v1 (2026-07-29)** — a timed apply
>    fades `float`/`int` entries with the existing §3.3 form and sets every
>    other kind at t=0; the settled argument-vector design is parked in
>    `feature-backlog/48-morph-interpolation`. The implementation stitches
>    `04-contract-and-schema` … `10-venue-preset-retirement` are **all tied**.
>    The contract is at v1.17 (§8.1 + the §9 `presets/` exclusion, no new wire
>    form); patch presets now span the store, shared application path,
>    Control/Device/editor surfaces, and Shows; and the old installation-scoped
>    venue-preset store and shelves are gone. The only remaining child is
>    **`11-browser-test-failures`**, the final pre-existing guard cleanup before
>    thread 41 itself ties.
> 9. `44-event-plane/6-text-kind-control` — after 7, so it adopts the app-wide
>    text treatment rather than competing with it.
>
> Standing constraint: the system works today and must keep working; prefer
> small ordered changes over rewrites.
>
> **Update 2026-07-26 (loom tidy):** Bob dropped the old
> `18-show-chrome-density` goal and replaced its remaining intent with
> `desktop-ui-overhaul/01-density-and-layout-design`: an app-wide desktop pass
> for smaller controls, tighter spacing, clearer hierarchy, and less wasted
> space. `dashboard-terminology-review` is dropped because the Control rename
> shipped in thread 37. The deferred Monitor Map placeholder is dropped and
> `20-console-dock` is tied. `asset-fleet-distribution`, `clock-sync`, and
> `spatial-audio` now sit under the `fleet-testing` umbrella.
> `framework-version-management` was audited and retained: update mechanics
> have shipped, but desired-version comparison and honest
> current/stale/unknown/diverged classification remain unbuilt. Read
> `.notes/handoff-2026-07-26-loom-tidy.md`; the desktop design is the new loose
> end.
>
> **Update 2026-07-25 (second autopilot session):** the Tier-1 framing below is
> a 2026-07-23 snapshot and is stale — `29`, `30`, `31`, `39`, `40` are tied,
> and **thread 37 (device-scoped patch control) is now complete and tied in
> full** (eleven stitches). Bite 2 passed hardware verification on the Finn Jet
> + Ciro Toast rig. Bob ratified all four widened-scope designs and the five
> implementation stitches shipped: shared `ControlSurface`, the `value ▸ gen`
> generator drawer, the Device-tab control panel, the **Dashboard → Control**
> rename with a reusable target filter, and the "Set patch…" hand-off.
>
> At that point the loom had no loose ends. The obvious gates were
> `41-preset-primitive` (the generator affordance it depended on now exists)
> and `27-tied-guard-rot`. Read
> `.notes/handoff-2026-07-25b-control-surface-autopilot.md` for that session;
> the newer 2026-07-26 update above governs current live state.
>
> **User-facing rename:** the Dashboard tab is **Control**. `#dashboard` still
> resolves via a tab alias, but new docs and prose should say Control.

This is the whole-loom order, not just the 2026-07-23 intake. Bob set the
priority: **the node-installation bug first, then the node-enablement cluster,
then the failing-test / guard-rot cleanup, then deferred Show polish** —
everything else stays gated for the reason in its stitch. Work one stitch at a
time (claim → work → verify → tie); design-gate stitches end in a Bob-ratified
proposal and go `.waiting`.

The loose-end thread numbers of the *active* tier were renumbered so
`./.loom/loom.sh next` serves tier 1 **literally**. Gated/paused threads stay
`.waiting` (excluded from `next`) and are ranked here in prose.

**Guard-rot vs the node bug — assessed 2026-07-23 (Bob asked which feeds which).**
Of the 39/71 red browser-free tied guards, the ones on the patch/fleet path
(`dist-2-node-side`, `fp-2-fleet-state`, `patch-switch-lifecycle`,
`fp-1-identity-module`) fail on the **known rot signatures** — a pinned
`contract_version '1.3'` (now 1.11), the retired legacy-samplepacks link, pinned
exact refresh-message lists / UI copy, and fake-`state` API drift. The
*behavioral* patch-sync assertions still **pass** in the sim (fetch progress,
"converges bytes then switches responsive nodes", per-device fetch
serialization). So **no guard-rot failure is feeding the node bug** — the node
bug is fresh-Pi-specific (cold cache / first real fetch / timeout), which
simfleet doesn't model. Hence node bug first, guard-rot after. (Diagnosis in
`29/1` should still cross-check those three patch-path guards, cheaply, in case
a real regression hides among the drift.)

### Tier 1 — active linear sweep (`loom.sh next` serves in this order)

1. **`29-fleet-patch-sync-hang`** — BUG. A freshly-flashed Pi goes unresponsive
   in the Dashboard when sent the fleet patch (SSH still works). Diagnose
   (`1-reproduce-diagnose`) then fix. The node-installation error; jumps the queue.
2. **`30-gdown-retirement`** — remove the stale `gdown` dep + bash-script
   staleness pass. Quick; unblocks 31.
3. **`31-install-oneliner`** — condense Pi setup into a `curl`-able `install-device.sh`
   + README one-liner. After 30. (USB auto-mount install step wires into 35.)
4. **Complete — `32-multi-asset-packs`.** Multiple asset slots; engine context
   carries a **list of absolute asset-folder paths**. Bob ratified the v1.9
   list boundary and completed the direct `bopos-context` PD/template edits;
   zero/one/two-slot local-editor checks passed 2026-07-23.
5. **Complete — `33-device-audio-config`.** Detected ALSA playback-card plus
   bounded JACK rate/buffer/period controls now live in the Device tab. Mixer
   selection remains node-side hardware policy, not an operator control. Apply
   is an exact-physical, unprivileged, transactional engine restart with config
   rollback and output-safety reapplication. Software/browser gates pass; real
   Pi/JACK and audible behavior remain a hardware adoption check.
6. **Moved to feature backlog — `34-fleet-patch-global-state`.** "The fleet
   patch" as global state shown in the Dashboard menu bar remains wanted, but
   Bob deferred it on 2026-07-23. Its waiting design gate stays intact.

### Tier 2 — failing-test cleanup, then desktop overhaul

8. **Complete — `27-tied-guard-rot` (2026-07-27).** Durable contracts now live
   in the code-surface-organized `tests/` suite, with
   `tools/run-tests.sh fast|browser|all` as the canonical local/pre-tie entry
   point. The preserved `.loom/tied/` guards are historical evidence, not a
   regression suite or maintenance backlog. The assertion-level disposition
   and named hardware follow-ups are recorded in
   `.loom/tied/08-archive-retirement-ledger/retirement-ledger.md`.
9. **Complete — `20-console-dock`.** Monitor v1 shipped with
   Incoming, Outgoing, Send, Reports, System, persistence, and wide split/snap
   on 2026-07-23. Bob dropped the deferred Map placeholder on 2026-07-26, so
   the parent is tied.
10. **`25-message-pill-encoding`** — **complete, tied 2026-07-23.** Message
   pills use the ratified flat eight-category set (cue, point, raw,
   param-value, param-fade, param-loop, param-lfo, param-stop), with visible
   kind codes as a non-colour channel.
11. **Complete — `45-device-enabled-replay-red`** (tied 2026-07-27, fix
   `e9e25cc`). The replay was never missing: `OSCBridge.handle()` has replayed
   `state.device_enabled_for(uid)` on a device's return since `5eda7b4`. The
   red was a **host-dependent test fake** — `54ff063` made the bridge discover
   its source route and create a separate `bridge.lan_sender`, while the
   promoted fake stubbed only `bridge.sender`, so the frame recorder saw
   nothing on any host that could route to `192.0.2.1`. The fake now routes
   every sender the bridge creates back through the recorder; the exact
   `enabled 0` safety assertion is intact. **`fast` is fully green (250).**
   *This entry claimed the test was still red until 2026-07-30 and sent a
   later session hunting a fixed bug — the note in the tied stitch's
   `decisions.md` records why it can look red on one machine and green on
   another.*
12. **`47-live-param-kinds-flake`** — `tests/verify_live_param_kinds.py` fails
   intermittently in `tools/run-tests.sh browser` on its two slider
   assertions, and only under full-suite load (confirmed pre-existing on clean
   `main`, 2026-07-28). Same family as the tied `46-control-surface-probe-race`:
   a Playwright step racing the heartbeat re-render, suspect being gotcha (16)
   — actionability passing is not the handler being bound. Diagnose before
   fixing; if it turns out to be a real binding window in `control-surface.js`,
   it is an operator-facing defect, not a test bug.

### Tier 3 — desktop UI overhaul + architecture review (reordered to the front, 2026-07-27)

- **`desktop-ui-overhaul/01-control-panel`** — the Control-tab control panel
  as the reference surface for the new compact UI language (Bob's 2026-07-27
  mockup): `1-full-manifest-visibility` (ratified, shippable now) then
  `2-control-panel-design` (Bob-gated design pass).
- **`entity-architecture-review`** — `1-system-map` then
  `2-workflows-and-simplification`; gates `41-preset-primitive/1`. Parallel
  with or after the control-panel work.
- **`desktop-ui-overhaul/02-component-unification`** — replaces the dropped
  `02-app-wide-rollout-design` (Bob, 2026-07-30, lore
  `2026-07-30-ui-unification-braindump`). Components first: identify the
  reusable components, design them one at a time, integrate each into **every**
  consumer, and extract the design language from what shipped — not a token
  system ratified ahead of its second consumer. Evidence base is
  `.notes/component-inventory-2026-07.md`, whose headline finding is that the
  app carries **two disjoint token layers** (`--chrome-*` at 32px/12px in
  `style.css`, `--row-h`/`--gap` at 24px/6px in `control-panel.css`, zero
  files using both), so the rollout is promotion of the ratified layer rather
  than invention of a third. The mockup is on file at
  `.lore/items/2026-07-27-control-panel-ui-and-architecture-braindump/content/mockup.png`
  and is the north star, qualified by `mockup-fidelity-notes.md` beside it —
  several mockup details (per-event `sync` buttons, per-element event labels,
  the enum kind, the toggle value-flash) were superseded by Bob's own later
  rulings and must not be copied back in. The standalone facilitator retains
  its separate tablet-first constraints; mobile divergence is a metric override
  (`@media (pointer:coarse)`), not a parallel layout.
  **Four rulings from 2026-07-30, all folded into the stitches:** (1) the
  standalone view is named **Remote** — a right-aligned tab-bar link, and the
  manifest tab's `dashboard` checkboxes and editor badge now read Remote (the
  flag is unchanged, only the label; shipped); (2) **the Control-tab iframe is
  retired** — `ControlSurface` hosts in the parent document so the tab can hold
  N columns, and `/facilitator` becomes the standalone Remote view only (delete
  Playwright gotcha 15 below once that lands); (3) column layout persists in
  **localStorage**; (4) the app-wide light repaint happens, but **the pink is a
  ground, not a panel colour** — sampled from the mockup, light is a neutral
  grey scale (panel `#f8f9fa`, subpanel/manual-fill `#e9ecef`, inputs
  `#ffffff`, ink `#212529`) on a pale pink ground `#f8f0fc`, and `--cp-bg` is
  the only pink token. That repaint **shipped 2026-07-30**, so
  `02-token-promotion` was density and `--chrome-*` retirement only — and it is
  now **TIED (2026-07-30)**. There is one metric layer: `--chrome-*` is deleted
  and its 83 consumers point at `--row-h`/`--gap`/`--radius-*` plus
  `--pad-control`, `--pad-panel`, `--header-h`, all declared at `:root` in
  `control-panel.css` (the one file **both** hosts load — `facilitator.html`
  does not load `style.css`). App chrome above content went 118px → 73px; the
  teal `--feature`/`--feature-line` pair is retired as off-palette; and the
  light ground is one `#f8f0fc` (the repaint had missed
  `:root[data-theme="light"]`). **Bob then ruled the held item in (same day):
  the app-wide light panels are now the mockup's NEUTRAL grey scale** — panel
  `#f8f9fa`, subpanel/recessed `#e9ecef`, inputs/buttons `#ffffff`, hover/soft
  `#f1f3f5`, lines `#ced4da`/`#495057`, ink `#212529`, in both light blocks of
  `style.css` and `facilitator.css`; `--bg` `#f8f0fc` stays the only pink. Two
  notes travel with it: `--deep` is now `#e9ecef` (it names a *recessed*
  surface, as dark always had it, and was the lightest light value by mistake),
  and app-wide `--dim` is `#6c757d` rather than the panel's ratified `#868e96`
  for contrast on `#f8f9fa`. **The cyan delta is CLOSED, not open** — Bob:
  *"I don't want to change the highlights."* `--mod-fill` stays as ratified;
  stop carrying it as a question. Detail in the tied stitch's
  `decisions-2-neutral-light.md`. Per-surface literals
  were left to the stitches that own them — dead headings/toolbars to `03`, the
  target filter to `07`, the Control-tab iframe to `08`. Evidence is 64 matched
  before/after shots (every tab, 1280 + 1680, light + dark, plus the Monitor
  dock) in the tied stitch, whose `shoot.py` is the working harness.

### Tier 4 — Bob-gated decisions / co-design / seeds (parked)

- **`feature-backlog/33b-device-network-config`** — saved Wi-Fi profiles and
  write-only credentials from the Device tab. Bob deferred it 2026-07-23;
  secret handling, privileged storage, safe switching, reconnect, and recovery
  remain an unratified design gate.
- **`feature-backlog/34-fleet-patch-global-state`** — fleet-patch global state
  and a persistent menu-bar convergence indicator. Bob deferred it 2026-07-23;
  its definition and menu-bar design remain unratified.
- **`42-node-logging`** (ex-`35`, renumbered + **activated 2026-07-24**: Bob
  set it medium priority — no longer parked) — the append-only-log seed
  (destination in Device tab + USB auto-mount). Design stitch is un-waited and
  queued after `40-precision-param-input`; proposal still ends in Bob
  ratification. See `.notes/handoff-2026-07-24-control-surface-presets.md`.
- **`scene-sequencing`** (whole thread paused 2026-07-08; language is co-design),
  **`framework-version-management/version-0`** (desired-state comparison and
  currentness UX; existing update mechanics are already shipped), and
  **`pi-zero-performance/zero-2-engine-verdict`** (SC strategy co-design).

### Tier 5 — hardware / rig-gated (need Bob or a live rig)

- **`fleet-testing`** — umbrella for `asset-fleet-distribution`,
  `clock-sync/sync-4-hw-measurement`, and
  `spatial-audio/spatial-3-rig-sweep`.
- **`pi-zero-performance/zero-1-tuning-matrix`** (claimable in any session that
  confirms `bop000` reachable).

Then, after the sweep: the host-loom patch-workflow documentation/starter-kit
close-out (`~/repos/.loom/threads/patch-workflow-friction/`).

**`21-theme-cyan-tint` is dropped** (Bob, 2026-07-23). It was named in the
2026-07-21 fix-pass text below but never became a stitch; it's off the program.

## Thread ordering (reconciled 2026-07-16)

**Foundation status (all complete, software-side):** the OSC contract is at
**v1.11** (2026-07-07 base + seam amendment + engine-boundary revision +
distribution amendment + fleet-patch fingerprint/cues amendments + UID-admin
and unassignment revision + additive unattended-update outcome receipts +
2026-07-17 patch-admin-surface amendment + 2026-07-19 parameter-automation
grammar §3.2 + 2026-07-23 multi-asset-slot run-context revision +
physical-device enabled/execution-routing revision + physical-device
audio-configuration revision);
`engine-boundary-design`, `patch-seam`, `clock-sync`
(sync-0..3), spatial software (spatial-1/2), the dashboard's four phases + UI
review, the audition preview stack (Stage 0 + preview-0..3), and
`patch-asset-sync` (dist-0..4), fleet-patch (fp-0..4), and patch-editor
(pe-0..4 plus the PE-4b delivery/element-target follow-up), and the nested
parameter-address foundation are **all tied**. `bopos.py`
(ex-helper.py) alone owns LAN 6660/5550; engines consume the localhost 6661
surface; run context is launch-delivered; `role`/meter are dead;
Desktop Control and Device control panels show every manifest parameter;
`dashboard: true` gates only the standalone facilitator/iPad surface.

The dashboard review sweep is complete through Devices and Patches (01, 02,
03, 05, 06, 08, 07, 09, and 10). Bob expanded the accepted implementation
sweep to the following **nine-stage program of work**. This order takes precedence
over `./.loom/loom.sh next`'s alphabetical listing; still claim, work, verify,
and tie one concrete stitch at a time:

1. **Complete — parameter-address foundation.** Contract/model/relay and
   dashboard state/editor are tied. True nested OSC, flat compatibility,
   canonical persistence/presets, and editor path CRUD are verified; promoted
   live controls remain reserved for stage 7.
2. **Complete — Seat-group spatial UX gate.** Bob ratified focus plus bounded
   four-group rail comparison, view-local styles, checklist authoring,
   eye/eye-off visibility, and the subordinate collapsible Groups placement
   after Seat detail and before Simulation/Venue.
3. **Complete — Seat-group core.** Canonical selectors, node persistence and
   matching, simulator/audition parity, dashboard group state, safe assignment
   transitions, and acknowledged membership synchronization are tied.
4. **Complete — Seat-group delivery.** Group catalog/membership authoring,
   eye/eye-off comparison controls, stable four-slot spatial rails, responsive
   touch layout, and dense-layout verification are tied.
5. **Complete — Single-device Assets workflow.** Device asset inventory
   (`11a`) and the operational one-assigned-physical-device Assets workspace
   (`11b`) are tied. The first real `bop000` transfer gate also repaired
   canonical cache ordering across restart and retired the temporary
   `samplepacks` compatibility path. Durable observations drive
   absent/current/stale/unknown/extra state; fleet-wide bulk rollout remains
   deferred to `asset-fleet-distribution`.
6. **Complete — unattended Update bopOS.** Runtime convergence is split
   from privileged provisioning, fails without prompting, reports outcome
   phases and reboots only after success. Niko Cloud passed the real
   receipt-before-reboot/return gate at `7d8a671` with `bonks-pd` preserved.
7. **Complete — Dashboard live controls.** The staged host manifest now drives
   Seat-owned All/Group/Seat promoted controls with nested identity intact,
   mixed aggregates, durable offline/unbound values, and per-Seat/All replay.
   Exact-UID persistent physical Device enabled, execution MUTE ALL semantics,
   selected-detail action, roster indication, simulator/audition parity, and
   focused touch verification are tied. Seat/Group mute and solo remain
   deferred.
8. **Complete — Diagnostic density and polish.** The host Git shorthand,
   copyable identity tails, adjacent desired/reported identities, terse copy,
   divided Seat inspector, two-element UI guard, Seat-bound IP, empty-preset
   cleanup, UX-reviewed All & Groups / Seats live tabs, and manifest-declared
   synchronized Dashboard cue triggers, bounded Seat/Device rosters, live Seat
   name filtering, independently staged physical Device enabled state, and
   exact-device alias-derived hostname action are tied. Existing Pis need one
   manual provisioning run before the hostname action is available.
9. **Complete — Show tab first slice.** Thread `14-show-tab` is fully tied
   (2026-07-18): the Sequencer placeholder is gone, replaced by the **Show**
   tab — steps/sections/messages document model with persistence, playback
   engine with the full then-action vocabulary, compact Ableton-density
   rows, context-sensitive inspector with message builder and multi-target
   chip picker (targets are selector lists), structural editing
   (copy/cut/paste/move/delete), and always-on outgoing/incoming OSC
   consoles with client-side filtering. Deferred by design: musical time /
   global transport, decomposed curves, point motion, the animated
   visualisation view, and multi-column layout — those stay with the
   Bob-gated `scene-sequencing` co-design.
10. **Complete — Show polish sweep.** Bob's 2026-07-19 braindump (lore item
   `2026-07-19-show-tab-polish-braindump`) authorizes thread
   `15-show-polish`: Show tab bug fixes (0-values, lost transport clicks),
   exclusive one-step playback with progress/armed visualisation, a global
   transport with a settable cue lead time (per-step forward-sync retired —
   all cues forward-sync), step-list scroll box, inspector defaults,
   drag + keyboard/undo editing, and the Patch tab tidy
   (facilitator→Dashboard copy, legacy `group` removal, path-hint clarity).
   All p1→p8 stitches are tied, including final operator docs and handoff.
11. **Complete — Parameter automation.** Bob ratified the generator-slot
   design 2026-07-19 (lore `2026-07-19-param-automation-design-ratified`);
   the full thread is tied (2026-07-20): grammar as contract §3.2 (v1.8),
   engine + simfleet parity (`automation-1`), the Show-tab generator
   builder GUI compiling to the wire grammar (`automation-2`, which also
   fixed `/p/*` playback truncating automation args), the waveform UX
   council + ratified design (`automation-4`, pre-ratified by Bob —
   authority is the tied stitch's `judgment.md`), runtime generator
   tracking with the Slice-1 static treatment and take-over
   (`automation-3`), and the CSS value-axis markers + Show-inspector
   preview (`automation-5-waveform-marker`). Dashboard restart forgets
   runtime automation state by design. Strings/mixed-arrays as a
   non-param manifest kind stay deferred (name and plane undecided);
   muted-device markers keep moving (Bob may veto — see the tied
   ratification note).
12. **In progress — Bob's 2026-07-21 fix pass.** Lore item
   `2026-07-21-show-console-dock-and-fixes-braindump` authorizes four
   threads, in this order: `19-show-chrome-fixes` — **complete, tied
   2026-07-21** (all four Show-tab defects: the collapse toggle now
   anchors to its panel at narrow widths instead of landing on the edit
   bar's delete button; add-step/add-divider became one "+ shape" SVG
   family instead of a `+`/`—` opposed pair; named divider rules are a
   fixed 28px and the unnamed row is a flat line, no gradient; the
   generator duration field's unit box shrank to 56px *and* a dead
   `@container` ordering bug that kept the LFO fields two-up was
   healed). `20-console-dock` is now **Monitor v1 complete** (the two OSC
   terminals became one app-wide bottom dock with Incoming, Outgoing, Send,
   Reports, System, persistence, and wide-view split/snap; only the deliberately
   deferred Map tab remains); `21-theme-cyan-tint` (light-theme
   green → cyan at the token layer); and `22-listener-range-ux` (the
   Seats listener range is only settable by dragging a handle that clips
   off the map — UX design gate, Bob ratifies, then implementation),
   whose live review produced the now-complete `26-listener-range-fixes`
   (item 13).
   Bob then reviewed it live and `24-show-divider-and-glyph-repass`
   (tied same day) reversed two of its calls: the unnamed divider is now
   a short 28px rule centred in the alias slot, not a full-width span,
   and the drawn SVG glyphs are gone in favour of `✛` / `╱`, chosen to
   match the edit bar's existing `⧉` / `✕`.
13. **Complete — `23-waveform-marker-guard-regression`** (tied
   2026-07-22). All four collected red guards were **stale guards, not
   runtime defects**, each traceable to a deliberate later change:
   `fbea2b0` retired the fade progress bar by design, `d23bba0` made
   every non-virtual heartbeat a mute-convergence edge (so the guard's
   exact `uid_command` list gained a `mute`), and `149c794` cut a
   scraped sentence in the terse-copy pass. All three repaired in
   place. Three of the four broke because **the guard pinned more than
   its subject** — worth carrying into how guards get written.
   The stitch also measured the rest: **39 of the 71 browser-free tied
   guards fail on clean `main`**. That finding is a written proposal for
   Bob (`proposal-guard-sweep.md` in the tied stitch) and a `.waiting`
   thread, `27-tied-guard-rot`, holding the evidence.
   **Also complete — thread `26-listener-range-fixes`** (tied
   2026-07-22): Bob's four listener defects. Defects 1 and 2 were one
   bug — `clipPathUnits` is `userSpaceOnUse`, so the room clip resolved
   in the *referencing* element's space and a `translate(listener)`
   wrapper slid the clip window by the listener position. The clip moved
   to an untranslated wrapper; the radial gradient needed no change. The
   dashed out-of-room arc is retired per Bob's ruling, and the Listener
   toolbar is gone — all control graphical, with the puck's `aria-label`
   now the only textual statement of the values plus a small
   gesture-only on-canvas label.
14. **Then — Docs close-out.** The in-repo `patch-workflow-friction`
   thread was **dropped** 2026-07-17 (subsumed by ongoing documentation
   improvements; only `friction-0a-readme-refresh` tied). The surviving
   pointer is a host-loom loose end
   (`~/repos/.loom/threads/patch-workflow-friction/`) — lay any final
   documentation/starter-kit stitches out from there, after
   `16-param-automation` so the docs describe the finished system.

The latest sequencer brainstorm is input to the separately Bob-gated
`scene-sequencing` co-design. It does not itself authorize implementation;
the 2026-07-18 braindump authorized the `14-show-tab` slice and the
2026-07-19 braindump authorizes exactly the `15-show-polish` sweep.

Everything else is `.waiting` for a reason stated in its stitch, apart from the
new desktop-overhaul design loose end:

- **Bob + hardware gates:** the `fleet-testing` clock and spatial acceptance
  children, and `zero-1` (claimable in any session that confirms bop000
  reachable).
- **Bob-gated decisions/pauses:** `scene-sequencing` (whole thread paused
  2026-07-08; language is co-design, never solo), `zero-2-engine-verdict`
  (SC strategy is co-design), and `framework-version-management` (device
  desired-state comparison/currentness design; the updater itself is already
  shipped).
  `parameter-addresses`, `seat-groups`, the single-device Assets workflow, and
  Dashboard live controls, diagnostic density, Show polish, and parameter
  automation are complete, and Bob's 2026-07-20 feedback pass landed
  `17-automation-polish` (fully tied) plus `theme-0-bop-palette-repass`.
  The theme/spinner/catchup run and the 2026-07-20 autopilot session's
  `show-layout-polish` thread (edit bar + inline step name + responsive
  OSC terminals, per the tied `01-layout-review` ratified decisions) and
  `engine-group-context` (groups on the engine-context surface; Bob still
  owes the `bopos~.pd` receiver edit in `.notes/pd-edits-for-bob.md`) are
  all tied. The completed Show-density slices are also **tied** (2026-07-21
  autopilot): the inspector sidebar
  (`02`), named section dividers + the unified click-to-edit title
  pattern (`04`), and the Show-tab-only compact chrome pass (`05`,
  `--chrome-*` variables). The remaining thread was dropped on 2026-07-26;
  broader density work now lives in `desktop-ui-overhaul`. Next software work
  in this historical sequence was the rest of Bob's 2026-07-21 fix pass — `21`
  remains (`19`, Monitor v1 from `20`, `22`, `23`, `24` and `26` are tied) —
  then the host-loom
  patch-workflow documentation/starter-kit close-out (stage 14). Bob
  design gates for `20-console-dock/01-dock-design` and
  `25-message-pill-encoding/01-pill-encoding-design` were ratified by Bob on
  2026-07-23 and both v1 implementations are complete; outstanding gates are the three
  rulings in `27-tied-guard-rot`, of which Bob settled the ordering
  (after `20`/`21`) and the pulled-out defect on 2026-07-22 — the sweep
  question itself he will take in a fresh session, briefed by
  `.notes/handoff-guard-rot-briefing.md`. `28-fleet-mute-semantics` is
  tied: the suspected fleet-mute defect was **not** a defect, just
  another guard pinning a ruling Bob had superseded. See
  `.notes/handoff-2026-07-22-autopilot.md`.

Standing rulings still in force: `/sync/*` wire shaping delegated (record
additively, flag it); a dev Pi is ssh-reachable for hardware stitches
(confirm in-session; don't bake gremlin-ask steps into instructions);
the audition software stack is retained, but the combined Mac/Linux audible
gate—particularly Linux auditioning—is no longer actively tracked; the
2026-07-08 "template lives in `templates/`" ruling is
**superseded** (Q6, 2026-07-13 — demos live in `patches/`).
Cross-repo: spool-scoped siblings live in `kite-choir-brains/.loom`
(`bopos-uptodate`) — coordinate, don't duplicate.

## Testing without hardware

- **Simulated fleet:** `dashboard-0-sim-fleet` builds `tools/simfleet.py` — N fake Pis
  speaking the real OSC protocol (heartbeats on 5550, commands on 6660). Once it
  exists, use it for all dashboard/clock-sync/scene development; treat it as part of
  the deliverable (new protocol features land in the simulator in the same stitch).
- **Laptop rig:** `bash/start-laptop.sh` runs PD + the io bridge on a laptop
  (MCP2221A USB-I2C adapter) for peripheral work.
- **Audible fleet:** `audition-rig` builds the composition monitor — N real engine
  instances on the laptop, spatially mixed. Protocol-only (`simfleet`) and audible
  instances should stay config-compatible so they can mix in one session.
- **Real Pi loop:** the edit→push→pull-on-Pi dance and the stop-stack/restart test
  sequence are documented in `kite-choir-brains/.claude/skills/bopos-dev/SKILL.md`.
  Hardware verification ultimately needs Bob or a live rig — say so in the stitch
  rather than claiming it verified.
- **Dashboard browser tests:** living `tests/verify_*.py` journeys launch the
  real `dashboard/server.py` + `tools/simfleet.py` on non-default ports and
  drive headless Chromium (Playwright). Extend the nearest living journey or
  use it as the template — repo-by-marker root, sim ports, teardown.
  **Patch-edit / execution-mode flows verify headlessly:** launching
  simfleet with `--sim-no-engine` (and `--sim-audio-backend none`) lets
  `set_edit`/`set_simulation` reach real `edit`/`simulate` `supervisor.mode`
  without spawning Pure Data — so the editor GUI and mode switch are testable in
  CI (see `tests/verify_device_control_modes.py` and the tied
  `38-patch-edit-chrome/1/verify_editor_toggle.py`). Only real PD/GUI behaviour
  then remains a hardware adoption check. **Verifies run from the `~/.venvs/bopos` venv** (the path
  `dashboard/README.md` uses); system `pip` is PEP-668 externally-managed, so if
  that venv is missing, create it: `python3 -m venv ~/.venvs/bopos && ~/.venvs/
  bopos/bin/pip install -r dashboard/requirements.txt pyOSC3`. Browser-free
  verifies (sync/spatial planes — LAN/engine only) need just those deps; the
  Playwright dashboard suites add: `~/.venvs/bopos/bin/pip install playwright &&
  ~/.venvs/bopos/bin/playwright install chromium --only-shell`. Guards that
  sample screenshot pixels also need `~/.venvs/bopos/bin/pip install Pillow`.
  Three Playwright gotchas these scripts learned the hard way: (1) `inner_text`
  applies CSS `text-transform`, so lowercase before matching a `capitalize`d
  row; (2) clicking a button auto-scrolls the page — `window.scrollTo(0,0)` and
  re-read bounding boxes before a spatial drag, and clamp drag targets on-screen
  (the room can extend above the viewport); (3) one type-aware `page.on("dialog")`
  handler (prompt→text, else accept) — two handlers race and one eats the other's
  prompt; (4) `page.wait_for_function(expr, value)` fails — pass the argument
  as `arg=value` (keyword-only in the sync API); (5) the facilitator page's
  `#ws-status` is an *empty* span when online — wait with
  `state="attached"`, the default visible-wait never fires; (6)
  `scroll_into_view_if_needed`/auto-scrolling actions wait for element
  *stability*, and CSS-animated controls (automation markers) plus
  heartbeat re-renders keep nodes perpetually unstable or detach them
  mid-wait — use a one-shot `page.evaluate` `scrollIntoView` and a fresh
  `bounding_box()` instead; (7) fixture manifests use explicit `kind`; a
  `text` default, when present, must be a string, and invalid defaults fail
  with a named manifest error;
  (8) any element inside a non-active tab panel resolves but never goes
  *visible* — wait with `state="attached"`, like `#ws-status`; (9)
  compare bounding rects only from ONE scroll state — per-element
  `scrollIntoView` between measurements makes y-coordinates
  incomparable; gather all rects in a single `page.evaluate`; (10)
  changing the Show inspector's generator `<select>` write-through
  persists new args onto the focused message — use one fixture message
  per generator kind instead of switching kinds in-test; (11) an SVG
  element's `getBoundingClientRect()` reports its *geometry* box and
  ignores clipping, so no DOM assertion can tell you whether a clipped
  shape painted outside its clip — sample screenshot pixels (Pillow) for
  that, and take the reference pixel from *inside* the same surface you
  are probing (an outside-the-room reference makes every in-room probe
  "differ", so the check passes vacuously); (12) a device row's
  `data-uid` is **not** unique — the Seats-tab seat rows carry it too
  (`.device-row.seat-row`), so `page.click('.device-row[data-uid="…"]')`
  resolves two elements and clicks the hidden one from the inactive tab.
  Scope roster clicks to the container (`#device-roster .device-row[data-uid=…]`);
  (13) a **Seats-roster** row's centre is its name `<input>`, and the row's
  click handler deliberately ignores clicks inside inputs — `page.click()` on
  the row selects nothing. Aim at the `small` (ID label) instead; (14) the
  offline sweep marks a device down **30 s** after its last heartbeat, so a
  test that kills simfleet and waits for `online === false` needs a timeout
  longer than that; (15) the Control surface is an **iframe**
  (`#dashboard-live-view`) — reach its filter and cards through
  `page.frame_locator("#dashboard-live-view")`, and note that `localStorage` is
  the only state the two documents share. (16) waiting for an *element*
  is not waiting for its *handler*: `bindParams` reassigns `onchange`/`onclick`
  after every heartbeat re-render, so a dispatch aimed at a freshly rendered
  control lands on an unbound node and silently sends nothing. Wait on the
  binding (`page.wait_for_function("() => !!document.querySelector(…)?.onchange")`)
  before dispatching, and match a recorded send by param name rather than by
  position in the log.

**Historical tied guards:** `.loom/tied/` is preserved authoring and decision
evidence, not a regression suite. Routine and pre-tie checks use
`tools/run-tests.sh` and the living modules under `tests/`; do not sweep, copy,
or repair archived guards merely to make the archive green. New durable checks
go into the appropriate code-surface-owned `tests/` module.

The narrow interim supersession rule remains for unrelated work that explicitly
encounters and relies on a tied guard: if an assertion pins something Bob has
since ruled away, it is **superseded, not authoritative**. Update only the
encountered assertion, add an inline comment naming the superseding stitch, and
record the ruling in the current stitch's `decisions.md`
(`.loom/tied/03-divider-rule-styling/decisions.md` is the worked example).
Do not expand that exception into neighbour or archive maintenance. The final
archive disposition is
`.loom/tied/08-archive-retirement-ledger/retirement-ledger.md`.

## Records

- `.lore/` holds complete dated artifacts — design proposals, decision records,
  session transcripts. `./lore.sh keep <prepared-dir> <slug>`; read `.lore/INDEX.md`
  deliberately, don't auto-load it. Design drafts awaiting ratification live here.
- `.notes/` holds current working reference (revisable); `docs/` (once created) holds
  durable specs like `OSC-CONTRACT.md`.
- Put working artifacts (measurements, logs, decision notes) inside the stitch
  directory — they travel with it into `tied/`. Because tie **moves** the
  directory (different depth), stitch test scripts must locate the repo by
  marker (walk up until `tools/simfleet.py` exists) or via an imported
  module's path — never by a fixed number of `..` hops.
