# Working notes for agents

bopOS is a Raspberry Pi + Pure Data framework for networked multi-device sound
installations. This file is the orientation for any agent working here.

## Start here

1. `README.md` — system overview, OSC port map, patch system.
2. `docs/OSC-CONTRACT.md` — the **ratified** OSC contract (v1.8: 2026-07-07 base +
   the 2026-07-11 seam amendment, 2026-07-12 engine-boundary revision,
   2026-07-13 patch/asset distribution amendment, and the 2026-07-14
   fleet-patch fingerprint/cues amendments, the 2026-07-15 UID-admin and
   unassignment revision, the device asset-inventory amendment, the
   2026-07-17 patch-admin-surface amendment (engine-sent `/admin` requests,
   version/patch-fingerprint in the run context), plus the 2026-07-19
   parameter-automation grammar (§3.2 generator slots on numeric `/p/*`)):
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
`contract_version '1.3'` (now 1.7), the retired legacy-samplepacks link, pinned
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
3. **`31-install-oneliner`** — condense Pi setup into a `curl`-able `install.sh`
   + README one-liner. After 30. (USB auto-mount install step wires into 35.)
4. **`32-multi-asset-packs`** — multiple asset packs; engine context carries a
   **list of absolute asset-folder paths**. Design gate (`1-context-list-design`,
   touches the engine-boundary context surface + a Bob PD edit).
5. **`33-device-audio-config`** — set sound card + JACK sample-rate/buffer from
   the Device tab. Design gate.
6. **`34-fleet-patch-global-state`** — "the fleet patch" as global state shown
   in the Dashboard menu bar. Design gate; coordinate the fleet-patch
   *definition* with 29 and `asset-fleet-distribution`.

### Tier 2 — failing-test cleanup, then deferred Show polish

7. **`27-tied-guard-rot`** (`.waiting`) — **reframed by Bob 2026-07-23:** "we want
   durable, maintainable tests for appropriate surfaces; running tests of tied
   stitches was the wrong pattern." So this is **not** "repair the 39/71 reds + a
   sweep script." It is a **two-tier split**: promote the guards that assert
   *durable contracts* (OSC contract/wire, manifest schema, identity/fingerprint,
   mute safety, fetch convergence) into a **living `tests/` suite organized by code
   surface**, run in CI/pre-tie; **retire the rest** as authoring artifacts
   (recorded, never silent-deleted, never maintained-in-place). Evidence: 6
   diagnoses = 0 real defects — the tied archive catches nothing as a persisted
   net, and its per-stitch (not per-code-surface) layout is *why* it rots. The
   39/71 figure is now triage input, not a to-do list; no `tools/guard-sweep.sh`
   over the archive. Full framing at the top of the thread's `instructions.md` and
   `.notes/handoff-guard-rot-briefing.md`; still gated on Bob's fresh session, runs
   after the node work. **Cheap thing to do now regardless (not gated):** a stitch
   touching a genuinely shared surface writes its check into a `tests/` file, not a
   new tied guard.
8. **`20-console-dock`** (`.waiting`) — deferred Show polish (Bob's 2026-07-21
   fix-pass item). Resume after the guard-rot cleanup.
9. **`25-message-pill-encoding`** (`.waiting`) — deferred. Bob ruled 2026-07-23
   the pill colours are a **single flat 7-category set** (cue, point, raw,
   param-value, param-fade, param-lfo, param-stop — confirm whether `loop`
   folds/omits/adds an 8th), not two dimensions.

### Tier 3 — paused pending other design (not workable solo)

- **`18-show-chrome-density`** — `01`/`03` paused on the lanes/scenes design
  (collapse may not survive a multi-lane grid); `06-chrome-app-wide-assessment`
  waits on Bob living with the Show chrome, then ruling app-wide vs staged.

### Tier 4 — Bob-gated decisions / co-design / seeds (parked)

- **`35-node-logging`** — the append-only-log seed (destination in Device tab +
  USB auto-mount); grow the design when Bob wants it.
- **`asset-fleet-distribution`** — bulk asset rollout; sequence its model after
  `32-multi-asset-packs` settles the pack shape.
- **`scene-sequencing`** (whole thread paused 2026-07-08; language is co-design),
  **`framework-version-management/version-0`** (parked on the UI-tabs-runway
  basis), **`pi-zero-performance/zero-2-engine-verdict`** (SC strategy co-design),
  **`dashboard-terminology-review`**.

### Tier 5 — hardware / rig-gated (need Bob or a live rig)

- **`clock-sync/sync-4-hw-measurement`**, **`spatial-audio/spatial-3-rig-sweep`**,
  **`pi-zero-performance/zero-1-tuning-matrix`** (claimable in any session that
  confirms `bop000` reachable).

Then, after the sweep: the host-loom patch-workflow documentation/starter-kit
close-out (`~/repos/.loom/threads/patch-workflow-friction/`).

**`21-theme-cyan-tint` is dropped** (Bob, 2026-07-23). It was named in the
2026-07-21 fix-pass text below but never became a stitch; it's off the program.

## Thread ordering (reconciled 2026-07-16)

**Foundation status (all complete, software-side):** the OSC contract is at
**v1.8** (2026-07-07 base + seam amendment + engine-boundary revision +
distribution amendment + fleet-patch fingerprint/cues amendments + UID-admin
and unassignment revision + additive unattended-update outcome receipts +
2026-07-17 patch-admin-surface amendment + 2026-07-19 parameter-automation
grammar §3.2);
`engine-boundary-design`, `patch-seam`, `clock-sync`
(sync-0..3), spatial software (spatial-1/2), the dashboard's four phases + UI
review, the audition preview stack (Stage 0 + preview-0..3), and
`patch-asset-sync` (dist-0..4), fleet-patch (fp-0..4), and patch-editor
(pe-0..4 plus the PE-4b delivery/element-target follow-up), and the nested
parameter-address foundation are **all tied**. `bopos.py`
(ex-helper.py) alone owns LAN 6660/5550; engines consume the localhost 6661
surface; run context is launch-delivered; `role`/meter are dead;
Dashboard live controls come only from `dashboard: true`.

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
   Exact-UID persistent physical-device mute, fleet-overlay OR semantics,
   selected-detail action, roster indication, simulator/audition parity, and
   focused touch verification are tied. Seat/Group mute and solo remain
   deferred.
8. **Complete — Diagnostic density and polish.** The host Git shorthand,
   copyable identity tails, adjacent desired/reported identities, terse copy,
   divided Seat inspector, two-element UI guard, Seat-bound IP, empty-preset
   cleanup, UX-reviewed All & Groups / Seats live tabs, and manifest-declared
   synchronized Dashboard cue triggers, bounded Seat/Device rosters, live Seat
   name filtering, independently staged device mute beneath fleet safety, and
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
   healed). Then `20-console-dock` (the two OSC terminals become one VS Code-style
   bottom dock — design gate first, then the unified frame, with an OSC
   send terminal, a system tab, wide-view drag-to-split, and a
   deliberately deferred map tab); `21-theme-cyan-tint` (light-theme
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

Everything else is `.waiting` for a reason stated in its stitch:

- **Bob + hardware gates:** `sync-4` (rig jitter measurement),
  `spatial-3-rig-sweep`, and `zero-1` (claimable in any session that confirms
  bop000 reachable).
- **Bob-gated decisions/pauses:** `scene-sequencing` (whole thread paused
  2026-07-08; language is co-design, never solo), `zero-2-engine-verdict`
  (SC strategy is co-design), and `framework-version-management` (device
  framework-currentness/update design, parked on the UI-tabs-runway basis).
  `parameter-addresses`, `seat-groups`, the single-device Assets workflow, and
  Dashboard live controls, diagnostic density, Show polish, and parameter
  automation are complete, and Bob's 2026-07-20 feedback pass landed
  `17-automation-polish` (fully tied) plus `theme-0-bop-palette-repass`.
  The theme/spinner/catchup run and the 2026-07-20 autopilot session's
  `show-layout-polish` thread (edit bar + inline step name + responsive
  OSC terminals, per the tied `01-layout-review` ratified decisions) and
  `engine-group-context` (groups on the engine-context surface; Bob still
  owes the `bopos~.pd` receiver edit in `.notes/pd-edits-for-bob.md`) are
  all tied. The `18-show-chrome-density` workable stitches are also
  **tied** (2026-07-21 autopilot): the collapsible inspector sidebar
  (`02`), named section dividers + the unified click-to-edit title
  pattern (`04`), and the Show-tab-only compact chrome pass (`05`,
  `--chrome-*` variables). Still waiting on that thread: `01`/`03`
  (paused pending the lanes/scenes design — collapse may not survive a
  multi-lane grid) and `06-chrome-app-wide-assessment` (Bob lives with
  the Show chrome, then rules app-wide vs staged adoption). Next
  software work is the rest of Bob's 2026-07-21 fix pass — `20` and `21`
  remain (`19`, `22`, `23`, `24` and `26` are tied) — then the host-loom
  patch-workflow documentation/starter-kit close-out (stage 14). Bob
  gates outstanding: `20-console-dock/01-dock-design` (dock scope —
  Show-tab-only vs app-wide, which also bears on `18/06`),
  `25-message-pill-encoding/01-pill-encoding-design`, and the three
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
- **Dashboard browser tests:** every dashboard stitch ships a `verify_*.py` that
  launches the real `dashboard/server.py` + `tools/simfleet.py` on non-default
  ports and drives headless Chromium (Playwright). Copy the newest tied one
  (`.loom/tied/*/verify_*.py`) as the template — repo-by-marker root, sim ports,
  teardown. **Verifies run from the `~/.venvs/bopos` venv** (the path
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
  `bounding_box()` instead; (7) fixture manifests: the validator only
  allows *numeric* `min`/`max`/`default`, so a string param declaration
  must omit `default` or the whole manifest silently fails to load;
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
  "differ", so the check passes vacuously).

**Re-running a tied guard:** the harness declines to execute scripts living
under `.loom/tied/`. Copy the guard into your own stitch directory and run
the copy — the repo-by-marker root lookup survives the move, and it also
spares the tied screenshots from being regenerated (no
`git checkout -- .loom/tied/` needed afterwards). Two traps: **run it with
the repo root as cwd** (some guards use cwd-relative paths, and running
from the copy's directory silently changes the answer), and if it opens a
sibling file from its own tied directory — a fixture, a word list — copy
the **whole directory**, or the `FileNotFoundError` looks like a failure
that is really the copy rule's fault. Delete the copy and its
screenshots when done. A tied guard that pins something Bob has since ruled
away is **superseded, not authoritative**: invert or repair the assertion in
place with an inline comment naming the superseding stitch, and record the
ruling in that stitch's `decisions.md` — don't leave a guard permanently red
(`.loom/tied/03-divider-rule-styling/decisions.md` is the worked example;
`.loom/tied/hb-identity/test_hb_identity.py` is another, superseded by
`29-fleet-patch-sync-hang/2-fix`). This repair-in-place is the **interim** rule
for a guard you break during other work. The **durable** direction (Bob,
2026-07-23) is thread `27-tied-guard-rot`'s two-tier split: durable-contract
assertions move into a living `tests/` suite organized by code surface; the rest
retire as authoring artifacts. Running the tied archive as a regression suite was
the wrong pattern — don't invest in maintaining it. New checks for genuinely
shared surfaces go straight into `tests/`, not a new tied guard.

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
