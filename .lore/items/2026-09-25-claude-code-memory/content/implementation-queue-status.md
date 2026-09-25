---
name: implementation-queue-status
description: Where the bopOS implementation program stands and what's next (2026-07-30: UI unification is the live front — 02-token-promotion + 03-chrome-reclamation TIED, 04-generator-drawer-component next; Bob's 44/5-pd-adoption rig check still open)
metadata:
  node_type: memory
  type: project
  originSessionId: 491a7eb2-4168-43ea-9161-e8c6f6823bc0
  modified: 2026-07-30T03:33:04.407Z
---

**2026-07-30 — `03-chrome-reclamation` DONE & TIED (commit `e687efb`).**
Every `.eyebrow` in the app deleted; three headings that only repeated the tab
bar gone (Control, Assets, Show empty state), two kept on the same test because
they say what the tab bar doesn't (**"Fleet patch"** names one of two sections;
the Show transport h2 is the **show name**). Dead-with-their-markup rules
deleted too, incl. **`.placeholder-tab`** (outlived the Map placeholder dropped
2026-07-26). Control-tab content 149px → **85px**, Assets → 115px. **The
standalone view is now a right-aligned `Remote` link in the tab bar, OUTSIDE
`role="tablist"`** — which required `.primary-tabs` to become a wrapper div
(keeps the class, so sticky + `.primary-tabs button` still apply) with the nav
inside as `.primary-tab-list`, id and role unchanged; tab wiring is
`[data-tab]`-based so no JS moved. **Five icon buttons** (both catalog
refreshes + forget-offline `✕`, reboot `↻`, update `⇧`), `Shutdown All` keeps
its words, all four still `confirm()`. **Glyphs: `⌫ ⟳ ↥` render as TOFU in
headless Chromium** — use the set the app already draws (edit bar's `✕ ⧉ ✛ ╱`)
plus basic BMP arrows. `✕` for forget-offline and `⇧` for update are the
weakest call and are flagged for Bob. **Two toolbars declined with reasons:**
`.mode-actions` holds one conditional `Relaunch`; `.fleet-patch-actions`
belongs to `09-patches-deploy-row`. All eight `<details>` now share
design-language §9's `▸`/`▾` as an app-wide base in style.css AND
facilitator.css, with `.icon-menu` opting out the two glyph-summary menus.
**Gotcha worth keeping: `.device-sidebar footer` (0,1,1) outranks a new
`.fleet-actions` class (0,1,0)** — the toolbar stacked vertically until the
footer rule itself became the flex row. **TWO BUGS FOUND IN PASSING:** (1)
`shoot.py` wrote `localStorage['bopos.theme']` but **`theme.js` reads
`bopos-theme`** (`theme.js:4`) — nothing consumed it, the parent only looked
themed because the same evaluate set `dataset.theme` by hand, which the Control
tab's **iframe never saw**, so every dark Control-tab shot in
`02-token-promotion` has a light panel in a dark app; fixed with
`add_init_script` (runs in every frame) and the theme `<select>` now reads
`Dark` in the shots, which is the tell; (2) `theme.js` still painted retired
lavender `#f4f1f8` into `meta[theme-color]` for light. Five durable checks into
`verify_control_tab.py` (**scope tablist counts to `#primary-tabs`** — the
Seats sidebar and Monitor dock are tablists too; the first version failed on
that). Suites green: 250 fast, 17/17 browser. LIVE NEXT:
**`04-generator-drawer-component`**.

**2026-07-30 — `02-token-promotion` DONE & TIED (commit `61ff57f`, main, not
pushed). THE TWO TOKEN LAYERS ARE NOW ONE.** `--chrome-*` deleted; its 83
consumers in `style.css` read `--row-h`/`--gap`/`--radius-*` plus three new
names in the same `:root` block — `--pad-control` (`2px var(--gap)`),
`--pad-panel` (10px), `--header-h` (40px). **The block stays in
`control-panel.css` even though it is app-wide: `facilitator.html` loads
facilitator.css + control-panel.css and NOT style.css**, so that file is the
only place both hosts can read tokens from. Chrome above content **118px →
73px** (measured off the retained pair, and `.tab-stage`'s
`calc(100vh - 73px)` + the Show inspector's `top:45px` are derived from it).
Retuned app-chrome **primitives only** — header, `.primary-tabs`,
`.tab-panel`, `section`, `button`, `main`, `aside`, `#spatial-section`;
per-surface literals left to the stitches that own them (headings/toolbars →
`03`, the Control tab's still-tall target filter → `07`, its iframe → `08`).
Two flagged sweeps done: `#editor-panel`'s teal gradient → flat `--panel` +
`--group-line`, which left **`--feature`/`--feature-line` with zero consumers
→ deleted from both stylesheets**; and the light ground is one `#f8f0fc` (the
`a571b06` repaint had set it under `prefers-color-scheme` but **missed
`:root[data-theme="light"]`**, so toggle and OS preference disagreed).
**Bob then ruled the held item IN, same session (commit `51a8edb`): the
app-wide light panels are the mockup's NEUTRAL greys** — *"I'd like to try the
grey neutrals on the panels."* Both light columns of style.css AND
facilitator.css: panel `#f8f9fa`, subpanel/recessed `#e9ecef`, inputs/faces
`#ffffff`, hover/soft `#f1f3f5`, lines `#ced4da`/`#495057`, ink `#212529`;
`--bg` `#f8f0fc` still the only pink. Two non-mechanical calls: **`--deep`
was `#fff`** — the lightest value in a light theme — though it names a surface
recessed BELOW the panel (dark always had it darker), now `#e9ecef`; and
**app-wide `--dim` is `#6c757d`, NOT the panel's ratified `#868e96`**, which
lands near 3:1 on `#f8f9fa` (one deliberate token of divergence, for
contrast). **The cyan delta is CLOSED — do not re-raise it.** It was my note,
not Bob's ask: *"I don't want to change the highlights. Leave `--mod-fill` as
it is for now."* Addendum + 16 `neutral-*light.png` shots in the tied stitch
(`decisions-2-neutral-light.md`). Suites **250 fast OK, 17/17
browser** (both known-reds green this run). Evidence: **64 matched
before/after PNGs** in `.loom/tied/02-token-promotion/` (every tab, 1280 +
1680, light + dark, + expanded Monitor dock) — `shoot.py` widened to take
them, now also populates the Show tab (an empty one exercises none of the
metrics) and expands the dock. **Flatten evidence into the stitch dir with
prefixes — the loom counts any subdirectory as an unresolved child and refuses
to tie the parent.**

**2026-07-30 — UI UNIFICATION is the live front; process REVERSED to
components-first (uncommitted).** Bob's braindump → lore
`2026-07-30-ui-unification-braindump` (transcript + `rulings.md`).
`02-app-wide-rollout-design` **DROPPED** — it would have ratified a token
system top-down before each pattern's second consumer existed. Replaced by
`desktop-ui-overhaul/02-component-unification`: identify components → design
one at a time → integrate into **every** consumer → extract the language from
what shipped. Stage A done and tied:
**`.notes/component-inventory-2026-07.md`**, 8 ranked components.
**Headline finding: the app has TWO DISJOINT TOKEN LAYERS** — `--chrome-*`
(32px controls/12px gaps) in `style.css`, `--row-h`/`--gap` (24px/6px) in
`control-panel.css`, and **zero files use both** (10 vs 0, 30 vs 0 hits). The
rollout is *promotion* of the ratified layer, not a third system.
`control-panel.css` binds `--cp-*` under only `.live-card, .device-control`.
Other measured gaps: patch editor hand-rolls its own param tree
(`dashboard.js:898-927`, comment at :1362 admits it predates the shared
surface) though `editorSurface` already exists at :1365 for the preset row;
`PrecisionField` has **3** call sites vs ~47 raw `type="number"`; the
generator *fields* are already shared (`param-generator.js`) but the **drawer
chrome is not** (`control-surface.js:231` vs `show.js:786`) — cheapest big
win; two unrelated target pickers (`seat-filter.js` single/exclusive with ONE
consumer, vs `show.js:287` multi-select chips = the model Bob wants).
Children in dependency order: `02-token-promotion` → `03-chrome-reclamation`
→ `04-generator-drawer-component` → `05-value-box-component` →
`06-control-panel-reflow-and-editor` → `07-target-selector-component` →
`08-control-tab-columns` (**`.waiting`, Bob-gated**) → `09-patches-deploy-row`.
**The Excalidraw is the north star but is PARTLY SUPERSEDED** — wrote
`content/mockup-fidelity-notes.md` into the 2026-07-27 lore item listing what
NOT to copy back (per-event `sync` buttons, per-element event labels, enum as
a distinct kind, the toggle value-flash, the provisional preset row,
events-below-parameters). **The image itself is still NOT in the repo** — Bob
holds it, chat attachments can't be persisted by any tool; best durable
substitute is `.loom/tied/2-control-panel-design/mockup-control-panel.html`.
**All four questions ANSWERED same session, folded in, COMMITTED `a571b06`
(main, not pushed):** (1) standalone view = **`Remote`**, right-aligned tab-bar
link; manifest checkboxes + editor badge renamed to Remote (flag unchanged,
label only) — **shipped**; (2) **RETIRE THE CONTROL-TAB IFRAME**, host
`ControlSurface` in the parent doc, `/facilitator` = standalone Remote only
(delete CLAUDE.md Playwright gotcha 15 when that lands); (3) column layout in
**localStorage** (Bob: a chip picker makes columns cheap to re-create);
(4) app-wide light repaint YES **but the pink is a GROUND, not a panel
colour** — Bob's correction off the mockup. **Shipped**: sampled light palette
is a NEUTRAL grey scale on pale pink ground — ground `#f8f0fc`, panel
`#f8f9fa`, subpanel + manual fill `#e9ecef`, inputs/buttons `#ffffff`, ink
`#212529`/`#495057`; `--cp-bg` is the ONLY pink token (a pink panel is a
regression). Dark untouched by construction. Cyan left alone (ratified
2026-07-27, no objection) though the mockup's `#99e9f2` fill is measurably
more saturated than `--mod-fill` renders over white — noted for the design
pass. So `02-token-promotion` is now **density + `--chrome-*` retirement
only**. **The mockup PNG is now IN THE REPO** at that lore item's
`content/mockup.png` (Bob copied it to `bopOS/temp/` after macOS TCC blocked
Desktop reads — `temp/` is uncommitted and untracked). Working screenshot
harness kept at `02-token-promotion/shoot.py` + `baseline-2026-07-30-*.png`;
the archived `3-tokens-and-chrome/shoot_control_panel.py` has **rotted**
(waits on a control-tab iframe selector). Suites **fully green: 250 fast,
17/17 browser** — note **`45-device-enabled-replay-red` now PASSES** standalone
and in-suite, so that thread looks stale and should be re-checked before
anyone works it. Off-palette leftover found: `#editor-panel`'s teal
`--feature` gradient violates design-language §1.

**2026-07-28 — preset design REVIEWED then REPAIRED (commit `2b12605`).**
`2-proposal-review` (Bob ran it, commit `728a848`,
`.loom/tied/2-proposal-review/review.md`) found five defects that I
independently reproduced. **`.loom/threads/41-preset-primitive/design-addendum.md`
is now AUTHORITATIVE over the tied proposal.** Two defects were mine and both
DISSOLVED rather than needing machinery: (1) `morph` was **grammatically
ambiguous** — `_options` (`python/paramgen.py:58`) peels trailing string
options BEFORE inspecting the leading keyword, so `morph 2s lfo … c:1` had two
readings; fix = **a wrapper's arguments precede the message it wraps**
(`morph <dur> [c:<n>] <spec…>`), inner message goes verbatim to the existing
parser. (2) **"LFO→LFO morph is continuous" was FALSE** — synced phase is
`t_synced/period + phase`, so lerping period changes the denominator under a
large absolute clock and jumps; fix = **magnitudes interpolate, anything
defining time or shape (period, segment durations, shape, `f`) takes the
destination at t=0**, which leaves the generator a valid clock-anchored LFO at
every instant, needs no phase accumulator, keeps fleet alignment, and makes
catch-up-as-current-interpolated-spec actually true. Unalignable pairs **snap
and are reported** (no support matrix). Overlapping provenance also dissolved:
**store per concrete seat**, card reads mixed when seats disagree (existing
idiom), capture snapshots state not history → no ordered ledger. Accepted:
apply must resolve to concrete seats and **skip seats whose effective patch
differs** (an `/all` datagram reaches pinned devices); generator state never
replayed on rejoin (`server.py:1512` replays scalars only); `stop` leaves no
durable value (fix: dashboard computes+stores the held value); the `presets/`
exclusion **never reached `fetcher._prune`**, a generic walk that deletes
anything not in `wanted`. **Two PRE-EXISTING bugs found, unrelated to presets:**
toggle manifests don't round-trip (`manifest.py:187` rejects any min/max then
writes them itself — enum got the fix, toggle was missed), and
`DistributionStaticFiles` would serve `/patches/<n>/presets/…` over HTTP.
**Four questions RULED by Bob:** keep morph curve (leading options); preset
file carries **schema fingerprint only** (I held against the reviewer's D3 —
a preset lives inside its patch, so a self-reference warns on every unrelated
`main.pd` edit; the SHOW message does carry patch `{name,fingerprint}` per R2);
venue group names **non-empty + unique**; **iPad gets NO presets at all**
(simpler than my apply-only rec) → the row `7-preset-slot` shipped into the
facilitator host must be **removed**, superseding that stitch's decision 1.
**Eight implementation stitches specced in addendum §10, deliberately NOT
created**; stitch 1 (grammar/reference closure → contract v1.17) gates all.

**2026-07-28 — `41-preset-primitive/1` RATIFIED & TIED** (all four forks;
`.loom/tied/1-preset-architecture-design/` proposal.md + decisions.md;
uncommitted). **F4 ruled after Bob asked for context: stored provenance +
DERIVED dirtiness** — `applied_preset` holds `{patch,name}`, cleared only by
recalling another preset; equality is computed at render, never a stored dirty
bit (the hardware-synth sticky bit lies once a value is returned to its preset
position; deriving matches the entity review's ratified R5). **Bob then placed
`41/2-proposal-review` AHEAD of implementation** — another agent reviews the
proposal against the code, Bob runs it himself before any building. So the six
implementation stitches are a SKETCH in proposal §11 and are deliberately NOT
created (the review may reshape them). The review brief lists six falsifiable
load-bearing claims to verify at file:line, and explicitly permits reporting
that a *ratified* ruling is unimplementable. Core claim of the design: **a preset is not a
wire concept** — an entry IS the `/p/<identity>` argument list (`[0.75]` /
`["lfo","sine",0,1,"10s"]`), so apply is a fan-out through the existing
`osc_bridge.set_param`, which already accepts full arg lists. Storage
`patches/<patch>/presets/<slug>.json`, one file each, sparse, drift measured
against a **control-schema fingerprint** (identity/kind/range only, not the
patch dir hash) so editing `main.pd` doesn't invalidate presets. **The
load-bearing discovery: `presets/` MUST be excluded from
`identity._walk_files`** — the patch fingerprint hashes every file, so
otherwise every preset save restages the fleet patch, refetches on every node
and restarts every engine mid-sculpt. Interpolation recommendation is **`morph
<dur> <spec…>`: interpolate the generator ARGUMENT VECTOR**, not Bob's output
crossfade — preserves §3.3's one-slot/last-writer-wins (which hard takeover
rests on), costs one lerp per param per tick, and Bob's own "depth→0, swap,
depth up" falls out of a single kind-coercion rule (a constant coerces to
zero-depth LFO at its current value). Also: `text` params ARE captured
(`kind:"text"` is ratified now; only string *automation* is deferred); mixed
aggregate values ⇒ omitted, which is how save-from-an-All-card works; capture
source is dashboard durable state + automation table, never a node query (§14
rejects dump/query). Contract delta proposed as **v1.17**: `morph`, `presets/`
host-only exclusion, one §8 sentence. **Four forks for Bob (§10):** exclusion
vs restage; `morph` vs mix function; does capture-as-step include un-preset
targets (rec: no); applied-preset dirty asterisk vs clear-on-write. Six
implementation stitches sketched in §11.

**2026-07-28 — first live event test after Bob's `.pd` edits: three defects
fixed (uncommitted).** (1) **Editor fires were rejected outright** — the browser's
`fire_editor_event` payload carries only `{identity, elements}`, but
`validate_event_command` requires a selector, so every patch-edit-mode fire
died on "Event selector must be a string." The server now supplies **seat `0`**
itself (the same selector `set_editor_param` uses for the local audition
engine). `tests/test_event_plane.py` had passed a selector by hand, which is
why it never caught this — the fixture now sends the real browser payload.
(2) **Per-element `labels` RETIRED — contract v1.16** (Bob ratified: "events
carry one label for all elements"). The manifest editor always emitted
`labels: ["", ""]`, and empty strings failed the 1–32-character rule, so no
event with arity ≥ 1 could be saved. `labels` is gone from `python/manifest.py`
(stale keys **stripped on read, never rejected**), the manifest editor, the
control surface, the Show inspector, the contract (§3.2, §8) and
`patches/README.md`. Elements are numbered 0-based floats everywhere. Reported
`contract_version` bumped 1.15 → 1.16 in bopos/simfleet/audition + the pinning
tests; `test_asset_slot_context` now regex-matches the version header instead
of pinning a number (it was failing on an unrelated amendment). (3) **Manifest
rows relaid out** — a stale second `.manifest-param` rule (from before the drag
handle existed) was overriding the real one with one too few columns, which is
why number fields were text-field wide; event rows declared 10 fixed columns
regardless of arity and overflowed. Both row kinds are now **flex-wrap**, sized
by content type (numbers 86px), with event `name`/`arity` **fixed** so they
align down the list at every arity (verified 520–1280px: no overflow, no
overlap). Bob called the UI good enough — a further pass comes later.
Browser suite green on a second full run; the one red on the first
(`verify_control_surface_component`'s enum send) is the known
`47-live-param-kinds-flake` family. **Still Bob's: the Finn/Ciro rig check for
`44/5-pd-adoption`.**

**2026-07-28 — `desktop-ui-overhaul/04-event-fire-affordance` DONE & TIED
(commit `77ad89c`, main, not pushed).** Live design session with Bob off his
screenshot of the shipped panel. The Control tab's top `#event-panel` (three
event buttons + the lead field) is **deleted on both the embedded Control tab
and the standalone iPad view** — lead is desktop-only now, owned by the
Monitor dock's Globals panel; an iPad fires but does not configure. The row's
`fire` button became a **top-level panel object**: 58px × `--row-h`, `--input`
fill, `--radius-momentary` 7px, so it sits in the *same column as every
parameter's value box* (that alignment argument beat a bigger 76×28 button).
It carries the retired `/cue` buttons' lead sweep + fire flash. **Ratified ink
widening: cyan no longer means only "a generator is running" — it means
*something is driving this control*, continuously or discretely** (Bob: "the
metaphor holds"). First pass swept neutral `--value-fill` and Bob reported it
didn't read at 58px against the hover fill → sweep moved to `--mod-fill`,
border goes `--mod` while firing, and **hover is suppressed while
`.firing`/`.fired`** (the cursor is on the button by definition when it
fires). `sendEvent` now **returns** the lead it put on the wire so the sweep
runs for exactly the scheduled time; the surface holds `setInteracting` during
the animation so a heartbeat re-render can't kill it. Lead 0 = flash, no
sweep. **Events render above Parameters** in `paramTree` and in the Patch
tab's manifest editor. Also filed **`47-live-param-kinds-flake`**:
`verify_live_param_kinds.py`'s two slider assertions fail intermittently under
full-suite load only — **confirmed pre-existing by stashing and reproducing on
clean main**; same family as tied `46-control-surface-probe-race`.
`8-manifest-reorder` was already tied. **LIVE NEXT STEP: `44-event-plane/5-pd-adoption`,
which is BOB'S** (`.pd` receiver edits + Finn/Ciro rig; thread 44 can't tie
without it, and `bonks-pd`/`demo-pd` receivers stay broken until it lands).

**2026-07-28 — `desktop-ui-overhaul/03-global-controls-monitor` DONE & TIED
(commit `ae45c9e`, main, not pushed).** Master fader, MUTE ALL, and the event
lead time now share a **Globals** panel (first tab) in the Monitor dock, gone
from the app header, the Control tab, and the Show transport. Key structural
call: the controls stay authored in `index.html` (hidden `#global-controls`)
because `dashboard.js` binds `#master`/`#mute-all` at parse time and loads
*before* `monitor.js` — the dock **adopts the live nodes** rather than
rebuilding them, so every handler, element id, and existing test selector
survives. Output safety: the always-on dock header carries a red
`MUTED — UNMUTE` flag (written solely by `renderHeader()`, which already runs
on both the optimistic toggle and the server echo) that delegates to
`#mute-all`'s handler. The Show transport lost event lead outright — no
read-only echo — which also retired its `eventLeadDraft` re-render dance.
New living journey `tests/verify_global_controls_monitor.py` (17 checks);
`verify_device_control_modes.py`'s two mute clicks go through a
`click_mute_all()` helper that opens Globals and re-collapses the dock so the
fixed dock doesn't cover later targets. Suite green (196 fast, 14/14 browser).
Bob's "**Monitor** name may want revisiting" note is carried in the tied
stitch's `decisions.md`. **LIVE NEXT STEP:
`desktop-ui-overhaul/01-control-panel/8-manifest-reorder`.**

**2026-07-28 autopilot — EVENT PLANE SHIPPED, `/cue` RETIRED. Contract 1.13 →
1.14 → 1.15.** `44/3-event-plane-wire` (`cbac939`) added targetable `/e/*`:
patch-declared identities, arity 0–3 free-form floats, framework forward
scheduling, selector-free/time-free engine fires, and the `"0"`
fire-on-arrival sentinel that makes "global lead 0 is sync-off" exact.
`44/4-cue-retirement` (`e8e998b`) deleted `/cue` + the manifest `cues` key as
a hard break — cue firing now lives on the control panel's **events section**,
targetable all/group/seat, with the per-row sync toggle removed (supersedes
`6-non-float-kinds`) and the pill renamed `CUE`→`EV` keeping the set at eight.
`tools/run-tests.sh all` green (196 fast, 13/13 browser incl. new
`verify_event_control_panel.py`). **LIVE NEXT STEP: step 4,
`desktop-ui-overhaul/03-global-controls-monitor`**, then
`01-control-panel/8-manifest-reorder`. **Two things for Bob:** (1) `4`'s
instructions said stop-and-ask if any manifest declared `cues` — three did
(`bonks-pd`, `demo-pd`, `fire-button`; the design's measurement was wrong); I
proceeded because nothing *fires* cues and the ids were already valid address
segments — reversal is `git revert e8e998b`; (2) **`bonks-pd`/`demo-pd` `.pd`
receivers break until Bob's `44/5-pd-adoption`**, and `bonks-pd`/`fire-button`
are gitignored so their manifest migration is working-copy-only. Full detail:
`.notes/handoff-2026-07-28-event-plane-autopilot.md`.

**2026-07-28 — 44 design RATIFIED & TIED; RATIFIED ORDER OF WORK (commit
`779582f`, also written into CLAUDE.md).** Bob took all six forks: kind grammar
as proposed, **`text`** = fifth kind's name, identity **in the address**, **no**
show-document migration, pill code **`EV`**, children worked **sequentially**
(Bob: "I'm mostly working sequentially"). Order, with the two couplings that
drive it — **(1)** `44/2-kind-grammar` (declaration break, zero wire change;
everything waits on it) → **(2)** `44/3-event-plane-wire` (`/e/*`, `"0"`
sentinel, v1.14; settles the `cue_lead_ms`→`event_lead_ms` rename) → **(3)**
`44/4-cue-retirement` (263-ref deletion sweep) → **(4)**
`desktop-ui-overhaul/03-global-controls-monitor` (**must follow 3** — it
relocates the cue-lead control, so doing it first means moving then renaming;
also good filler while 6 waits on Bob) → **(5)**
`01-control-panel/8-manifest-reorder` (**must follow 4** — both rewrite the
manifest editor + panel section split; one pass not two) → **(6)**
`44/5-pd-adoption` (**BOB's** `.pd` edits + Finn/Ciro rig; 44 cannot tie
without it) → **(7)** `02-app-wide-rollout-design` (unblocks when 8 ties
01-control-panel) → **(8)** `41-preset-primitive/1` (design gate; needs ONLY
child 2, so pullable earlier if a Bob session is free) → **(9)**
`44/6-text-kind-control` (after 02 so it adopts the app-wide text treatment).
**Two additions from the ratification session:** (a) **`text` UI is in 44's
scope** — Bob: strings are in the contract so they need manifest + styled
control; measured reality is there IS an unstyled string control already
(`control-surface.js:282,352` → plain `<input type="text">`, excluded from
aggregation/automation) and the tied `6-non-float-kinds` simply SKIPPED
strings; manifest half in child 2, styled control deferred to child 6.
(b) **the event row's sync toggle is SUPERSEDED** — `6-non-float-kinds`
shipped "1–3 boxes + sync toggle + send" per the mockup, but every event
forward-syncs so there's one fire button; child 4 removes it and records the
supersession by name per CLAUDE.md's interim rule.

**2026-07-27 — 44-event-plane SCOPE NARROWED by Bob (commit `4c90d4a`).** Bob corrected the intake: **toggles and integers already
existed** (toggle = `type:"i"` min 0 max 1) and **enums already shipped**
(`options` on an int param — wire unchanged, value is the index, min/max
derived). **Events are the ONLY missing kind and the only wire work.** Events
are already declared-but-inert in the manifest (`events` list: name/path/
arity 1–3/labels/defaults/dashboard; validator accepts, control panel renders
the row dead). Six rulings, DO NOT re-open: (1) **every event forward-syncs**
→ the mockup's per-row `sync` button is DROPPED, one fire button per row, and
**global cue lead time `0` IS sync-off** (the only off switch); (2) **explicit
`kind` field** replacing `type`+`options`, **hard break**, nothing in
production; (3) cues absorbed as 0-element events, `/cue` deleted no shim
(earlier ruling, still in force); (4) **event elements are free-form labeled
floats** — note/velocity/duration is convention, not enforced; (5) **presets
do NOT capture events** (momentary) — this is the answer 41 was waiting on,
recorded in 41's instructions; (6) **no event automation designed** — shape
unknown, name the door only ("there will likely be event-specific automations
in future"). Design stitch rewritten to 7 narrower questions (kind grammar +
its sweep incl. `PARAM_TYPES`/`show_model.py`/editor/fixtures; plane address
and its §3 planes-table row; arity 0–3 wire shape; forward-sync inheriting
§3.1 `cue_lead_ms`/shared-time; the `/cue` deletion sweep incl.
`dashboard/shows/*.json` migration; Show pill taxonomy when `cue` category's
subject becomes an event; parity). Contract §8's two placeholder notes updated
to state the rulings. **`46-control-surface-probe-race` TIED** (`bd7b789`) —
the 1-in-5 `verify_control_surface_component.py` flake. Remaining loose ends
after 44: `01-control-panel/8-manifest-reorder` (deliberately AFTER 44 — the
`kind` break rewrites the manifest editor it touches), `03-global-controls-
monitor` (independent), `02-app-wide-rollout-design` (blocked until 01 ties).

**2026-07-27 earlier — Bob's SECOND braindump intaken** (lore
`2026-07-27-events-cues-and-global-controls-braindump`): **a cue = an event
with zero elements**; **RULED same session: cues ABSORBED into the event
plane as a HARD BREAK** — `/cue` plane deleted in 44's contract revision, no
compat shim (no production shows use cues; keep code clean); design stitch
now specs the unified plane + migration sweep, absorption itself is settled.
Cue triggering moves onto the control panel targetable
all/group/seat; panel gets separate **parameters + events sections** (no
intermingling). Master fader + MUTE ALL (header) + cue lead time (Show
transport) = global controls → new stitch
`desktop-ui-overhaul/03-global-controls-monitor` (Monitor-dock panel, ratified
"try first"; Monitor NAME may be revisited later — note only). New stitch
`01-control-panel/8-manifest-reorder`: drag-reorder Patch-tab manifest entries
to reorder the panel (workable now, independent of 44). CLAUDE.md 2026-07-27
block updated. Loom/lore changes uncommitted.

**2026-07-27 — `01-control-panel/5-hierarchy-and-persistence` DONE & TIED (commit `a8b199e`, main, not pushed).**
Children 3, 4, 5 are all shipped and committed; next loose ends are
`6-non-float-kinds` then `7-preset-slot`, then `44-event-plane/1` → `41/1`.
Nested addresses are now `<details>` accordions (`<summary>` + a
`.live-param-branch-kids` wrapper; `data-param-branch` unchanged), collapse
persisted in `localStorage` under `bopos.control.collapsed-branches` keyed
`scope:branch/path` — **no target id**, so pruning applies to every card of a
scope; re-opening deletes the key rather than storing "open". `<details>` does
the hide/show itself so a toggle writes storage and does NOT re-render (same
idiom as the facilitator's `details[data-command-uid]`). Chrome (▸/▾ via
summary `::before`, 12px indent, no left rule) in control-panel.css §14; the
base rules in style.css/facilitator.css moved `padding-left`→`margin-left` so
the panel rule overrides instead of stacking. Verified: browser 12/12 PASS with
new section (f) in `verify_control_surface_component.py` (collapse survives
heartbeat re-render AND reload). **Watch:** the long-standing fast-suite failure
`test_device_control_routing.test_reappearing_physical_device_replays_persistent_enabled_state`
now fails **standalone too** (it used to pass alone) — pre-existing on clean
main, unrelated to the UI work, wants its own stitch.

**2026-07-27 — `01-control-panel/3-tokens-and-chrome` DONE & TIED (uncommitted at the time).**
Token layer + chrome landed with no DOM changes. Key structural call: the tokens
live in a **new third stylesheet `dashboard/static/css/control-panel.css` loaded
by both `index.html` and `facilitator.html`** — not edited into style.css and
facilitator.css separately, which is where drift comes from. Panel scope is
`.live-card, .device-control` (both ControlSurface hosts), so the light pink
repaint also reaches the STANDALONE facilitator, not just the embedded Control
tab — one judgment call flagged for Bob in the tied stitch's decisions.md. Dark
theme is a no-op by construction (design's dark values == shipping ones), so all
dark deltas come from chrome rules. Beyond the brief, three off-book inks
corrected: range track + 0/1 checkbox were cyan/amber → `--accent`; value
readout cyan only under `.automated` (Q1); facilitator text param read `--bg`
→ `--input`. `--auto` rebound to `--mod` inside the panel, which moves ALL
existing automation machinery to the ratified cyan for free. `.live-param-mod`
(∿ 18px circle) rule ships ahead of its markup for `4-row-regrind`. Verified:
browser suite 12/12 PASS; fast suite 1 failure
(`test_device_control_routing.test_reappearing_physical_device_replays_persistent_enabled_state`)
that is **pre-existing on clean main**. Reusable screenshot harness kept at
`.loom/tied/3-tokens-and-chrome/shoot_control_panel.py` (before/after PNGs
alongside). Next: `4-row-regrind`.

**2026-07-27 — control-panel design RATIFIED & TIED (live session).**
`2-control-panel-design` done same day: living prototype
(`mockup-control-panel.html`, animated LFO/toggle/hatching) + two docs in the
tied stitch — `design-language.md` (tokens/rules for 02-app-wide-rollout) and
`control-panel-design.md` (mapping onto ControlSurface: keep the native range
input, restyle; evolve don't fork). Bob's rulings: pink/purple + cyan ARE the
palette (no off-book colors — UA orange focus ring called out; purple
focus/accent-color); electric cyan #4DEEE3 dark / #0798BC light (light ceiling
accepted); light bg = saturated pink pastel #f4d7eb; one slash-hatch pattern,
two inks (gray mixed / cyan mixed+gen, hatched value boxes with dots); marker
line on every slider both inks; name INSIDE sliders, sub-element labels LEFT;
58px standard number-box width; ints right-align, floats left-align; momentary
= 7px rounded (PD bang), latching = sharp 1px keyed off button[aria-pressed]
(PD toggle), ∿ icon circular exempt; free below curve above duration unit;
cyan on value boxes only under generators; enums automate like ints; takeover
status line stays. Implementation children laid out as loose ends 3–7 under
01-control-panel: 3-tokens-and-chrome → 4-row-regrind →
5-hierarchy-and-persistence → 6-non-float-kinds → 7-preset-slot. Events UI
specced but wire plane stays 44's contract question. Loom changes uncommitted.

**2026-07-27 later — entity-architecture-review COMPLETE & TIED (live session).**
System map in `.notes/entity-map-2026-07.md` (DAG, no cycles; smell =
unversioned couplings C1–C3 + duals D1–D4). Bob supplied workflow facts and
ratified the model + all three forks (tied stitch's proposal.md/decisions.md):
four layers hardware→site→content→composition; content refs carry
{name,fingerprint}, drift derived/warned/never-blocking; portable shows target
groups **by name** (F1); venue presets **retire** at 41 (F2, store empty);
drift warning in Show tab + on load (F3); collections start as show steps
("meta preset" = a step); patch switch between sections first,
multi-simultaneous-patches a noted later door; scatter/density →
scene-sequencing; pin/fleet clunk = UI input to desktop-ui-overhaul. 41/1
un-gated (waits only on UI-first queue order). Small-changes list in proposal
§4 (preset/show fingerprint fields, C3 seat-reindex show-target flag, group
name resolution). Commits: 10d7853 restructure, 2f36516 map, + review tie.

**2026-07-27 — Bob's control-panel-UI + architecture-review restructure (loom uncommitted).**
Bob attached a compact grayscale/cyan control-panel mockup + braindump → lore
`2026-07-27-control-panel-ui-and-architecture-braindump` (verbatim transcription
+ panel descriptions + session directives). New order (in CLAUDE.md's 2026-07-27
update block): **(1) `desktop-ui-overhaul/01-control-panel`** —
`1-full-manifest-visibility` first (RATIFIED behavior change: Control tab shows
ALL manifest params; `dashboard:` flag now gates only the facilitator/iPad view)
then `2-control-panel-design` (mockup-driven, Bob ratifies; events likely a new
`<target>/e/*` plane = future contract amendment; provisional preset row is a
placeholder for 41). Old `01-density-and-layout-design` renamed
`02-app-wide-rollout-design` (extracts the ratified language app-wide). **(2)
`entity-architecture-review`** (parallel/following): `1-system-map` (as-is
entities/storage/couplings for device/seat/group/patch/preset/show) then
`2-workflows-and-simplification` (Bob reviews). That thread now **GATES
`41-preset-primitive/1`** — no preset design until the review lands. Constraint:
system works today, must keep working — small ordered changes, no rewrite.
Loom/CLAUDE.md/lore changes NOT committed (dashboard/shows/test.json also dirty).

**2026-07-25 (second autopilot session) — THREAD 37 COMPLETE & TIED (11 stitches). The loom has NO loose ends.**
Bob confirmed the Finn+Ciro hardware test PASSED (bite 2 adopted), ratified all
four designs with feedback, and asked for the whole implementation sequence in
one session. Shipped, one commit per stitch on main (not pushed): `448b5dc`
ratifications+corrected artifact, `a53ff0d` **07** extract `control-surface.js`,
`5efbd7c` **08** generator drawer + `param-generator.js` + `set_live_automation`,
`213092d` **09** Device-tab control panel + per-device schema, `491f8e8` **10**
Control rename + `seat-filter.js` + scoped presets, `1f44883` **11** Set patch…
hand-off. **Two of Bob's rulings CORRECTED the proposals:** (1) patch deployment
stays on the **Patch tab** — only the Dashboard tab becomes **Control**, which
hosts no picker; (2) **"pinned" stays patch-only** — a seat-bound standalone
device gets an ordinary Seat, no new vocabulary. Architecture: the live surface
was inside `facilitator.js`, which Control embeds by **iframe**; now
`control-surface.js` used by both pages, and the component never touches the
wire (host `send` callback = the seam). A **pinned device** carries its own
`live_controls` on the device payload from `public_device` (NOT `public_state` —
`device_update` carries one device). Cross-document state = shared
`localStorage` + `storage` event (that's what "global selected seat" means).
Five new `tests/` suites (11+38+12+15+14 checks), whole suite green.
Full detail: `.notes/handoff-2026-07-25b-control-surface-autopilot.md`.
**Next Bob gates:** `41-preset-primitive` (its blocker — the generator
affordance — now exists) and `27-tied-guard-rot`. Nothing in the five stitches
has run on real hardware yet.

**2026-07-25 autopilot — 37/2 bite 2 SHIPPED & TIED + four thread-37 design proposals `.waiting` on Bob.**
Full state of play + hardware-verification step-by-step in
`.notes/handoff-2026-07-25-device-patch-autopilot.md`. Budget rule this session:
5-hour session window only, disregard weekly. Commits on main (not pushed):
`9c3f6e1` bite 2, `f502b79` reparent+scaffold, `5156eef` proposals, plus a
CLAUDE.md/handoff/memory commit. **Bite 2 (`2-device-patch-targeting`) tied:**
`set_device_patch`/`clear_device_patch` on a **per-device generation track**
(`device_operations`/`device_generations`/`_supersede_device_operation`);
`converge_fleet_patch` got a swappable `is_current` token so device pins and
fleet deploys never cross-cancel; **fleet deploy now excludes pinned devices**
(`stage_and_converge`) and `supersede_fleet_operation` spares pinned
`patch_switch`; target picker + roster 📌 marker + follow-fleet clear.
**simfleet needed NO change** (protocol-reactive, per-device patch state).
Verified `tests/verify_device_patch_targeting.py` 14/14 incl. the crucial
"fleet deploy leaves a pin intact". Real-Pi/PD = the one remaining check (Finn
Jet + Ciro Toast recipe in the handoff). **Reparented** `feature-backlog/38`
→ `37/3-generator-affordance-design` (Bob wants generator affordance ahead of
41). **Four proposals** = one artifact
`https://claude.ai/code/artifact/6f9c395e-f7b0-43f3-b132-dbe1ebc2f780`
(source `.loom/threads/37-.../control-surface-proposals.html`), stitches 3–6
`.waiting`: generator affordance, set-patch hand-off, live-control placement
(one reusable ControlSurface component), Control-tab rename. **Scope reality:**
pinning requires the device be seat-bound (OSC v1.5 targets content by seat) —
the set-patch hand-off proposal offers humane bind-to-seat for standalone nodes.
Meter 401'd (token expired) at wind-down — re-auth next session.

**2026-07-24 — 37/2 IMPLEMENTATION bite 1 DONE (uncommitted): per-device desired-patch foundation.**
Data model + effective-desired resolution + roster fields, unit-tested; NOT
wired to convergence/UI yet (deliberate — no half-feature). Changed:
`device_aliases.clean_desired_patch` + `clean_registry`/`set_custom` preserve a
`desired_patch` pin; `state.device_patch_for`/`set_device_patch_override`/
`clear_device_patch_override` (durable UID registry, save-with-rollback, mirrors
`set_device_enabled`); `server.device_desired_patch` + `public_device` now badges
against EFFECTIVE desired and publishes `patch_pinned`/`pinned_patch`/`desired_patch`.
`tests/test_device_patch_override.py` (7, green); device_enabled suite green;
server imports. Stitch `2-device-patch-targeting` stays `.stitching` with
`progress.md`. **Bite 2 NEXT:** `set_device_patch`/`clear_device_patch` (`follow
fleet`) WS cmds + per-device convergence — the trap is `fleet_generation`/
`supersede_fleet_operation` are GLOBAL and reset every `patch_switch`, so a
per-device op needs its own generation/task tracking (design first); then Patches-
tab target picker, roster pinned marker, simfleet parity + Playwright.

**2026-07-24 — 37/1 design first-bite RATIFIED & TIED; impl loose end `2-device-patch-targeting` ready.**
Bob scoped thread 37 down to a first clean bite and ratified it. Key finding:
**no per-node desired patch exists today** — `fleet_patch` is one global and
every device's `patch_badge` measures against it (`server.py:1439`). So the bite
introduces a **per-node desired-patch override** (durable UID registry, mirrors
`device_enabled_for`), effective-desired = override else fleet; `set_device_patch
{uid,patch,confirmed}` reuses `converge_fleet_patch` with a **singleton target
set**; Patches-tab target picker (fleet OR one device); roster **"pinned"** marker
as a SEPARATE axis from current/stale (Bob chose "pinned" over "drifted"); fleet-
patch drift/rollup **data** here but the menu-bar **chip deferred to
`feature-backlog/34`**. **Generator editing PARKED** →
`feature-backlog/38-generator-editing-on-surface`. Deferred to parent (NOT the
bite): shared control-surface component, Control-tab rename, per-device live panel,
Device-tab "Set patch…". Deliverables: `.loom/tied/1-device-patch-control-design/`
(decisions.md + proposal-first-bite.md). `loom.sh next` = `37/2`. Nothing coded/
committed yet. 41/1 preset design still the other Bob-gated loose end.

**2026-07-24 — 42's two loose ends CLOSED on Ciro (post-reboot).** Bob confirmed
`LOG_DESTINATION=usb` persists in `bopos.config` across reboot (Dashboard Logging
block comes back up on USB, not internal → the `read_node_config` allowlist
load-back works end to end) and logging lands from the dash to the USB stick
under `/media/bopos-usb/bopos-logs/`. Stray SD-card fallback logs (`~/bopos-logs/`)
cleared. Hot insert/remove confirmed working (pull → fallback to internal,
reinsert → resumes to stick on next entry, no restart — per-entry
`os.path.ismount`). Recorded in `.loom/tied/4-log-destination-config/verification.md`.
Thread 42 hardware adoption check COMPLETE, nothing outstanding.

**2026-07-24 — thread 43 DONE & TIED (commit `cdda229`, main, not pushed).**
The "paradox" dissolved by capturing the real browser frame: thread 40's
`send(override)` refactor (`a978cd9`) left handlers bound as
`input.onchange = send`, so the DOM **Event object** went to the wire as
`value` (`{"isTrusted":true}`) → `clean_editor_value` None → rejection.
Checkboxes fully broken since a978cd9; sliders masked by zero-arg throttled
`oninput` (their change/pointerup commits were silently rejected too). Fix:
wrap the three bindings `() => send()`. Kept both inherited fixes
(interacting-guard matcher + facilitator `ws.on("error")` alert). Durable
`tests/verify_live_param_checkbox.py` (simfleet 0.2s heartbeat, asserts wire
`p/gate=…`, installation.json persistence, no revert, no alert; fails 5
checks with fix reverted). Verified live on Bob's running dash (:8080) —
green-button toggles cleanly, left at 0. 42's two loose ends still open:
confirm `LOG_DESTINATION=usb` persisted on Ciro, stranded old SD logs.

**2026-07-24 — 42 committed+pushed (`d1ba842`) + HARDWARE-VERIFIED on Ciro;
NEW thread 43 handed off.** Bob updated Ciro via the dash and tested live
(tmux `0:0.0` ssh into `pi@ciro-toast`, seat 1, patch `fire-button`, USB at
`/media/bopos-usb`). Logging works end-to-end: `nodelog` appends, `/log` on
7770, USB destination, PD `to-bopos-log`→`/log`, and `/all|/1/p/*` routing all
proven with direct injects. The long "not appending" chase was NEVER logging —
it was, in order: (1) Patch Edit mode blocking fleet sends (`set_editor_param`
→ selector 0, edit instance; `set_param`/`set_live_param` in
`edit_blocked_mutations`), (2) seat addressing, (3) a **`set_live_param`
server rejection** = new thread **`43-live-param-checkbox-nosend`** (loose end,
comprehensive handoff written). 43: facilitator "Dashboard" All-Seats live
checkboxes rejected with "That live parameter or target is unavailable." while
"Send all" (`replay_live_params`) + sliders work; disk code says an All toggle
of green-button=1 CAN'T hit that guard (identity/value/seats all valid) →
PARADOX, next session must **instrument** `set_live_param` (name which of
decl/clean/seats is None) not reason. **Uncommitted `facilitator.js` fixes
(keep):** interacting-guard now covers plain live-param checkboxes; added a
`ws.on("error")` handler (view was silently swallowing ALL server errors — that
surfaced the rejection). `server.py` untouched. Running dash = PID `server.py
--host 0.0.0.0`, localhost:8080. Two small 42 loose ends: confirm
`LOG_DESTINATION=usb` persisted (grep was empty though logs on USB), stranded
old SD logs.

**2026-07-24 — 42-node-logging FULLY TIED (all 4 children + thread parent).**
Bob reviewed `logging-block.png`, approved the Device-tab "Logging" block as-is,
confirmed PD `to-bopos-log` bus in place → re-claimed `4-log-destination-config`,
recorded the gate clearance in its verification.md, tied it, then tied the
`42-node-logging` parent. Remaining: **Ciro Toast hardware adoption check** (real
USB write to `/media/bopos-usb/bopos-logs/`, FAT perms, hot insert/remove) — Bob
has hardware ready to run live. Nothing committed yet. `loom.sh next` now serves
nothing (all remaining loose ends `.waiting`: 37/1, 41/1 design gates, etc.).

**2026-07-24 later session — 42-node-logging IMPLEMENTATION: 2 & 3 TIED, 4 `.waiting` on Bob's UI gate.**
Worked the three implementation children (NOT committed). **2-nodelog-facility
TIED:** `python/nodelog.py` (append-only TSV, per-stream daily files, 50MB `-N`
roll, `destination_dir()` seam), `/log` handler on 7770 in bopos.py, contract
**v1.12** (§4.2 term + §15), simfleet `log_request` parity, `tests/test_nodelog.py`
(12). **3-usb-automount-install TIED:** `systemd/99-bopos-usb.rules` +
`systemd/bopos-usb@.service` + `bash/bopos-usb-mount` (one-stick, FAT uid/gid+flush,
yank-safe) + idempotent `bash/install-usb-automount.sh`, wired into `provision.sh`,
INSTALL.md updated, `tests/test_usb_automount.py` (8, lint/syntax). **4-log-destination-config
IMPLEMENTED + software-verified, PARKED `.waiting`** for Bob's Device-tab "Logging"
block UI gate (screenshot in stitch dir `logging-block.png`): `python/log_config.py`
(bounded internal/usb, effective fallback, LOG_DESTINATION persistence), bopos.py
apply/receipt on `/all/os/to <uid> log-config <json>` → `/os/log-config`, `log`
in `/os/report`, nodelog destination hook = `log_config.effective_dir` (per-entry
resolution, hot USB, visible fallback), **fixed read_node_config to allowlist
LOG_DESTINATION**, dashboard block (`logSection`/`bindLogControls` +
`logDestinationDrafts` survives heartbeat re-render), osc_bridge/server wiring,
simfleet parity, contract **v1.13** (§6 envelope + report `log` object).
`tests/test_log_config.py` (12) + `tests/verify_log_destination.py` (Playwright, 5).
Reported contract_version bumped 1.11→1.12→1.13 in lockstep (bopos/simfleet/audition
+ 3 pinning tests). **Full non-browser suite 83 pass.** **Bob's `to-bopos-log` PD
edit is ALREADY in the working tree** (`pd/bopos~.pd` + template — he did it this
session; leave those `.pd` changes alone). NEXT: Bob reviews the Logging block →
re-claim `4-log-destination-config` → tie → thread 42 done. Then Ciro Toast
hardware adoption checks (real USB write, FAT perms, hot insert).

**2026-07-24 later session — 42-node-logging design RATIFIED & TIED.**
Bob supplied the anchor use case live (Ciro Toast standalone: i2c buttons,
headphones, log interval between two presses; third party retrieves logs by
pulling the USB stick — SSH stays install-only) and ratified the proposal in
full (`.loom/tied/1-logging-seed-design/` proposal.md + decisions.md): plain
TSV `timestamp<TAB>stream<TAB>values`, per-stream daily files, usb-absent
fallback stays on SD (no catch-up v1), `to-bopos-log` bus (Bob's PD edit,
noted in `.notes/pd-edits-for-bob.md`), mount at `/media/bopos-usb`,
interval-vs-raw-events is patch author's choice. Three implementation
children laid out and workable: `2-nodelog-facility` (nodelog.py + `/log` on
7770 + §4.2 amendment v1.12 + simfleet + tests/), `3-usb-automount-install`
(udev+systemd unit, net-new install-device.sh step), `4-log-destination-config`
(LOG_DESTINATION in bopos.config, log-config envelope mirroring audio-config,
heartbeat log object, Device-tab block — UI Bob gate). Not committed yet.

**2026-07-24 autopilot (earlier session):** `39-remove-installed-pack-from-device`
and `40-precision-param-input` **both DONE & TIED** (commits `057ab80`, `a978cd9`
on main — not pushed). **39** extended device-side asset "Remove" to installed
catalog rows (reused `drop_distribution`→`dropassets`; warn-not-block on active
slots) and **uncovered+fixed a real server bug**: `handle_ws`'s `set_param`
branch bound a local `identity`, shadowing the module import so `drop_distribution`'s
`identity.valid_asset_slot()` raised `UnboundLocalError` — **every** asset drop
(catalog AND the older extra-row Remove) silently no-op'd; regressed after 11b
tied, uncaught because the tied guard never re-ran (a live thread-27 example).
Renamed local → `param_identity`. **39 hardware-verified on Ciro Toast
(Bob, 2026-07-24):** added+removed two catalog packs and removed a device-only
pack from the Asset tab, file add/remove confirmed over SSH — adoption check
closed. **40** added
click-to-type precision entry (shared `dashboard/static/js/precision-field.js` →
`window.PrecisionField`) on facilitator live controls + patch-editor param rows +
master (whole-percent); clamps to min/max, rounds to 6 sig figs / integers; Show
inspector unchanged (already `type=number step=any`). Durable test homed in
`tests/verify_precision_param_input.py` (shared surface → tests/, per thread 27),
Phase A captures the real OSC wire via simfleet fleet log. Next workable per the
fixed order: **37/1 design** (Bob-gated) → **41/1 design** (Bob-gated) →
**42-node-logging/1** (Bob-independent fill-in).

**2026-07-24 patching-session braindump — intaken** (lore
`2026-07-24-patching-session-braindump`): after the first full
editor→sim→device patching session Bob wants (a) precision float entry on every
param control → thread **`40-precision-param-input`** (workable, ungated, after
39); (b) ONE reusable control-surface component across patch editor / Device
tab / a **Control tab** (renamed Dashboard; target filter all/groups/seat;
cues+master+presets; cue section shrinks/moves aside; per-seat grid rethought)
→ **folded into 37's design gate** (Bob confirmed; scope-widened section in
37/1's instructions; rename coordinates with dashboard-terminology-review);
(c) **presets as a manifest-scoped primitive** → thread
**`41-preset-primitive/1-preset-architecture-design.waiting`** (Bob-gated):
save from editor panel, load per seat/group/all, collections, plus Bob's
same-day extensions — **Show-tab preset triggering with interpolation
(duration+curve)**, **generator editing on the control surface** (LFO/rate/
depth per param; reuse the automation-2 builder GUI), and **presets capture
generator specs, not just values**. Generator-involved interpolation is OPEN:
Bob first said "mix function" (output crossfade, two sources/param — big §3.2
+ engine change) then "if there is a more elegant approach I might prefer it"
— design stitch must compare mix vs generator-arg interpolation (morph
rate/depth/center in-slot; kind-change via depth-ramp handoff) and recommend.
**Ruled (Bob 2026-07-24): params stay individually targetable from anywhere;
hard takeover is the global model** — preset apply = fan-out of ordinary
per-param messages, no layer/lock/ownership; direct set mid-morph wins on
that param; weighs against the two-source mix engine.
Sequence 41 after or alongside 37's design. **Order fixed in
`.notes/handoff-2026-07-24-control-surface-presets.md`** (committed to main):
39 → 40 → 37/1 design → 41/1 design → **42-node-logging/1** (ex-35, Bob
activated 2026-07-24 'medium priority', un-waited, Bob-independent until
ratification — fill-in work when design sessions block on Bob) →
implementations → backlog. `bopos.devices` edit confirmed intentional and
committed. **Storage ruled (Bob 2026-07-24): presets live IN the patch folder
(1:1 with manifest, ride patch distribution, die with the patch; editor
save-preset writes there); shows stay composition-level in `dashboard/shows/`
(now committed/canonical) with patch-name+fingerprint references for drift
warnings; a patch may bundle a demo show as an import source only.** 41's
remaining storage question is just the manifest-drift policy.

**2026-07-24 update:** 31/32/33 all tied since the note below. Bob brought the
**device-scoped patch workflow** intake → new threads (all in CLAUDE.md's "Next
sweep" block + `.notes/handoff-2026-07-24-device-workflow.md`):
- `36-engine-startup-delivery-race` — **DONE & TIED**, then **Finn cold-boot
  check surfaced a residual bug, now fixed (commit `7986382`, on main).** The
  original fix had `send_to_engine` swallow `except OSError`, but pyOSC3's
  `OSCClient.send` re-wraps the socket error in `OSCClientError` (descends from
  Exception, NOT OSError), so the refusal escaped on a real Pi. `engine_alive()`
  flips true on pid+JACK a beat before PD binds 6661, so `deliver_engine_context`
  (run on the 0→1 edge, outside heartbeat_loop's send try/except) hit the
  not-yet-open port and the wrapped error **killed the heartbeat thread** — node
  stayed SSH/OSC-responsive with engine running, but stopped heartbeating →
  Dashboard showed it Offline / engine frozen "stopped" / no points. Fix:
  `send_to_engine` catches `(OSError, OSCError)`; `deliver_engine_context`
  returns delivered-bool and `heartbeat_loop` retries until accepted (never drops
  durable context on the racing first attempt). The replay unit test's fake
  client now raises pyOSC3's `OSCClientError` like the real lib. Verified on real
  hardware 2026-07-24 across **both** rig units (Finn Jet + Ciro Toast): update
  worked, reboot → 0 tracebacks, engine alive, `id`/`groups` redelivered on a
  later beat, heartbeats flowing, points working on both. (A transient "no
  points" scare was a false alarm — only one speaker plugged in, point 0 → element
  0 only; node code fine.) `tests/test_engine_ready_replay.py` 7 tests, suite 51
  OK. Aside: `bopos.devices` seed file is stale (old MACs, current rig UIDs
  absent) — harmless while stores hold assignments, but a cleanup candidate.
- `38-patch-edit-chrome` — **DONE & TIED.** Menu-bar Patch Edit launches/closes
  the editor; button cleanup + Launch editor⇄Stop Editor. Delegated to Sonnet.
- `37-device-scoped-patch-control` — **Bob-gated design (`.waiting`).** Target a
  patch to one device (Finn Jet fleet-node / Ciro Toast standalone; see
  [[finn-ciro-test-rig]]). Ratified: fleet patch = bulk-set over per-node desired
  patch; switch from the Patch tab + Device-tab "Set patch…" shortcut + live-
  control panel; engine stop/start shelved. **Define "the fleet patch" jointly
  with `feature-backlog/34`.**
- `39-remove-installed-pack-from-device` — device-side asset "Remove"; next
  unblocked workable loose end.
- `35-node-logging` seed annotated (→ renumbered `42-node-logging`, activated 2026-07-24) (USB automount is net-new install work; 31 is
  tied). Usage meter was blind this session (OAuth 401 — re-auth via `/usage`).

As of **2026-07-23**: Bob's intake added seven threads and reset the sweep
priority to **bugs + node-enablement first, Show polish deferred.** The
loose-end thread numbers were renumbered so `./.loom/loom.sh next` serves the
order **literally** (authoritative program also written into CLAUDE.md's new
"Next sweep" block). Order:

1. `29-fleet-patch-sync-hang` — **BUG — DONE & TIED (2026-07-23 autopilot).** Not
   a hang and not the fetch/patch code: it was the **software-mute path**. On the
   DigiAMP+, `enforce_mute` ran `amixer` against the wrong ALSA card (default HDMI,
   no controls) with generic control names, every call failed, and mute **fell
   back to `stop-engine.sh`** → node online + heartbeating but "Engine Stopped",
   no recovery. Fix (Bob's ruling): card-aware `amixer` + real `Digital` control
   (auto-detect non-HDMI card), and **removed the engine-kill fallback +
   `muted_via_stop`**. Hardware-verified on new-bop. Committed (NOT pushed —
   Bob's deploy call). Guard `verify_mute_targeting.py` green; repaired superseded
   `hb-identity` tied assertions.
2. `30-gdown-retirement` — **DONE & TIED.** Removed `gdown` (was the only trace);
   bash staleness sweep found **no** removable scripts (all live); `start-engine.sh`
   `LEGACY_SAMPLEPACKS` residue-cleanup retained deliberately.
3. `31-install-oneliner` — **NEXT (start of next session; not started).** Scope
   GREW this session: besides `install.sh` + README one-liner, it must (a) **land
   `bopos.config` at install with sensible defaults** — Bob 2026-07-23, "important
   for later stitches"; fresh Pis have none, which is why the mute bug bit — incl.
   the sound-card/MIXER hint the mute path + stitch 33 read; (b) create a
   **`bopos.service`/proper boot** mechanism (today: `/etc/rc.local → su pi -c
   start.sh`, no systemd unit); (c) address a **cold-boot engine race** (engine
   sometimes doesn't come up before the DigiAMP is ready). Breadcrumbs already in
   31's and 33's instructions. Still Bob-gated on the hosting URL. Depends on 30 (done).
4. `32-multi-asset-packs` — multiple packs; engine context = **list of absolute
   asset-folder paths** (today one `bopos-context assets <root>`). Design gate +
   Bob PD edit.
5. `33-device-audio-config` — sound card + JACK rate/buffer from Device tab.
   Design gate.
6. `34-fleet-patch-global-state` — "the fleet patch" as global state in the
   Dashboard menu bar. Design gate; coordinate its definition with 29.
Then tier 2 (after the node work): **`27-tied-guard-rot`** — the 39/71 failing
tied guards — elevated ABOVE the deferred polish per Bob's 2026-07-23 "failing
tests matter" emphasis, but still gated on his fresh briefed session
(`.notes/handoff-guard-rot-briefing.md`); then `20-console-dock` and
`25-message-pill-encoding` (deferred Show polish). Pill ruling (Bob 2026-07-23):
flat 7-category colour set — cue, point, raw, param-value, param-fade,
param-lfo, param-stop (confirm `loop`).

**Assessed 2026-07-23 (Bob asked which feeds which):** the patch-path guard
failures (`dist-2-node-side`, `fp-2-fleet-state`, `patch-switch-lifecycle`,
`fp-1-identity-module`) are all **stale-guard rot** (pinned contract_version
'1.3'→1.7, retired samplepacks link, pinned message lists, fake-`state` API
drift); behavioral patch-sync assertions still pass in sim. So guard-rot does
**not** feed the node bug → node bug (29) first, guard-rot after. 29's diagnosis
cross-checks those guards as a hedge.

Parked (tier 3-5): `18` chrome leftovers (lanes/scenes-paused), `asset-fleet-distribution` (after 32), scene-sequencing / version-mgmt /
zero-2 / dashboard-terminology (co-design/Bob-gated), and hardware-gated
sync-4 / spatial-3 / zero-1. `21-theme-cyan-tint` **dropped** (Bob 2026-07-23;
never was a stitch). Design gates are Bob-ratify: proposal → `.waiting`. dev Pi
[[bop000-dev-pi-access]] (confirm live in-session). Related:
[[patch-editor-and-ui-tabs-decisions]].
