// The live control surface, extracted from facilitator.js so the same rows can
// be rendered by more than one host (37/07). Bob's ruling for the placement
// design was "same component, different send": a host supplies state and a send
// callback, and everything about how a parameter row looks and behaves —
// mixed aggregates, automation glyphs and markers, fade animation, takeover,
// precision entry — lives here, once.
//
// This module deliberately holds no host state of its own beyond the animation
// bookkeeping that must survive re-renders (automation anchors, takeover
// announcements). Everything else arrives through the context object, because
// the two hosts (/facilitator and the Dashboard's Device tab) keep their own
// `installation` and their own websocket.
(function () {
  "use strict";

  const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const wireType = declaration => declaration?.kind === "float" ? "f"
    : declaration?.kind === "text" ? "s" : "i";

  // Which hierarchy accordions the operator has pruned. localStorage rather
  // than module state because the Control tab is an iframe and the Device-tab
  // panel is the parent document: storage is the only channel the two share
  // (CLAUDE.md gotcha 15), and it is also what makes pruning survive a reload.
  //
  // Keyed by scope + branch path, not by target id: collapsing `reverb` on one
  // Seat card prunes it on every Seat card, which is the point — the operator
  // is pruning the manifest, not one card. Absent means open, so a fresh
  // browser and an unreadable store both land on today's always-open panel.
  const BRANCH_STORAGE_KEY = "bopos.control.collapsed-branches";
  const branchKey = (scope, path) => `${scope}:${path.join("/")}`;

  function collapsedBranches() {
    try {
      const stored = JSON.parse(window.localStorage.getItem(BRANCH_STORAGE_KEY) || "[]");
      return new Set(Array.isArray(stored) ? stored.map(String) : []);
    } catch (_error) { return new Set(); }
  }

  function storeBranchCollapsed(key, collapsed) {
    const branches = collapsedBranches();
    if (collapsed) branches.add(key); else branches.delete(key);
    try { window.localStorage.setItem(BRANCH_STORAGE_KEY, JSON.stringify([...branches])); }
    catch (_error) { /* storage denied: the accordion still works, it just forgets */ }
  }

  function create(context) {
    // context: {getState, deviceForSeat, send, sendEvent, sendAutomation, setInteracting, requestRender}
    const automationAnchors = new Map();
    const takeoverAnnouncements = new Map();
    // Which generator drawers are open, and the argument list each one is
    // currently authoring. Both survive the heartbeat re-render, which is why
    // they live here and not in the DOM.
    const openDrawers = new Set();
    const drafts = new Map();
    let fadeAnimationFrame = null;
    let lastReducedFadeUpdate = 0;

    const state = () => context.getState() || {};
    const deviceForSeat = seat => context.deviceForSeat ? context.deviceForSeat(seat) : null;

    function valueForSeat(seat, declaration) {
      return seat.params?.[declaration.identity] ?? declaration.default ?? "";
    }

    function automationForSeat(seat, declaration) {
      if (!seat || declaration.kind === "text") return null;
      const entry = state().automation?.[String(seat.id)]?.[declaration.identity];
      return entry && ["fade", "loop", "lfo"].includes(entry.kind) ? entry : null;
    }

    function aggregateValue(members, declaration) {
      if (!members.length) return {value: declaration.default ?? "", mixed: false, automation: null, automationMixed: false};
      const values = members.map(seat => valueForSeat(seat, declaration));
      const automation = members.map(seat => automationForSeat(seat, declaration));
      const signature = entry => entry ? JSON.stringify(entry.args) : null;
      const firstSignature = signature(automation[0]);
      const automationMixed = automation.some(entry => signature(entry) !== firstSignature);
      return {value: values[0], mixed: values.some(value => !Object.is(value, values[0])),
              automation: automationMixed ? null : automation[0], automationMixed};
    }

    function automationPresentation(entry, mixed = false) {
      if (mixed) return {glyph: "∿̸", label: "mixed"};
      if (!entry) return null;
      if (entry.kind === "fade") return {glyph: "╱", label: "fade"};
      if (entry.kind === "loop") return {glyph: "⟳", label: "loop"};
      const shape = entry.shape || "unknown";
      const glyph = ["sine", "tri", "drift"].includes(shape) ? "∿" : "⌁";
      return {glyph, label: `${shape} LFO`};
    }

    function automationKey(seat, declaration) {
      return `${seat?.id ?? "none"}:${declaration.identity}`;
    }

    function refreshAutomationAnchors(nextState) {
      const declarations = new Map((nextState.live_controls?.declarations || []).map(item => [item.identity, item]));
      const now = Date.now();
      const present = new Set();
      for (const [seatId, entries] of Object.entries(nextState.automation || {})) {
        for (const [identity, entry] of Object.entries(entries || {})) {
          const declaration = declarations.get(identity);
          if (!declaration || declaration.kind === "text") continue;
          let parsed;
          try { parsed = window.ParamSpec.parse(entry.args || [], wireType(declaration)); }
          catch (_error) { continue; }
          const key = `${seatId}:${identity}`;
          const commandSignature = JSON.stringify(entry.args || []);
          const signature = JSON.stringify([entry.args, entry.sent_at]);
          const expected = window.ParamSpec.phaseAnchor(entry, parsed, now);
          const previous = automationAnchors.get(key);
          const predicted = previous ? previous.elapsedMs + now - previous.atMs : 0;
          const period = expected.periodMs;
          const rawError = period > 0 ? Math.abs(((expected.elapsedMs - predicted + period / 2) % period + period) % period - period / 2) : Math.abs(expected.elapsedMs - predicted);
          const meaningful = rawError > Math.max(40, period * .02);
          // Reapplying an identical synchronized LFO is idempotent node-side: it
          // remains on the leader's absolute-time phase. Preserve the live browser
          // anchor too, rather than restarting its CSS animation for a looping Show
          // step's new sent_at. Changed commands and free LFOs are new instances.
          const sameSynchronizedLfo = previous && parsed.mode === "lfo" && !parsed.free &&
            previous.commandSignature === commandSignature;
          if (!previous || (!sameSynchronizedLfo && (previous.signature !== signature || meaningful))) {
            automationAnchors.set(key, {...expected, atMs: now, signature, commandSignature});
          }
          present.add(key);
        }
      }
      for (const key of automationAnchors.keys()) if (!present.has(key)) automationAnchors.delete(key);
    }

    function automationModel(entry, declaration, seat, catchupValue) {
      if (!entry) return null;
      let parsed;
      try { parsed = window.ParamSpec.parse(entry.args || [], wireType(declaration)); }
      catch (_error) { return null; }
      const anchor = automationAnchors.get(automationKey(seat, declaration)) ||
        {...window.ParamSpec.phaseAnchor(entry, parsed), atMs: Date.now()};
      const elapsedMs = Math.max(0, anchor.elapsedMs + Date.now() - anchor.atMs);
      const periodMs = window.ParamSpec.totalDuration(parsed);
      if (parsed.mode === "fade" && elapsedMs >= periodMs) return null;
      const model = {parsed, elapsedMs, periodMs, target: parsed.segments?.at(-1)?.value};
      if (parsed.mode === "lfo") {
        model.minimum = window.ParamSpec.position(parsed.min, declaration);
        model.maximum = window.ParamSpec.position(parsed.max, declaration);
        model.marker = !["sh", "drift"].includes(parsed.shape);
      } else if (parsed.mode === "loop") {
        model.marker = true;
        const samples = [];
        const total = Math.max(1, periodMs);
        let start = Number(catchupValue);
        if (!Number.isFinite(start)) start = Number(declaration.default ?? parsed.segments[0].value);
        let offset = 0;
        samples.push(`${window.ParamSpec.position(start, declaration).toFixed(5)} 0%`);
        for (const segment of parsed.segments) {
          const duration = segment.duration.ms;
          const steps = Math.max(1, Math.min(12, Math.ceil(duration / 80)));
          for (let index = 1; index <= steps; index += 1) {
            const fraction = index / steps;
            // saw wraps at phase 1 (periodic); a one-shot ramp must end at 1.
            const bent = fraction >= 1 ? 1 : window.ParamSpec.shapeFraction("saw", fraction, parsed.curve);
            const value = start + (segment.value - start) * bent;
            const time = (offset + duration * fraction) / total * 100;
            samples.push(`${window.ParamSpec.position(value, declaration).toFixed(5)} ${time.toFixed(3)}%`);
          }
          offset += duration;
          start = segment.value;
        }
        samples.push(`${window.ParamSpec.position(catchupValue, declaration).toFixed(5)} 100%`);
        model.loopEasing = `linear(${samples.join(",")})`;
      }
      return model;
    }

    // ---- generator drawer (37/08, reground by 01-control-panel/4) ----------
    // A numeric row authors either a value or a generator against the same
    // param address. The ∿ icon opens the drawer; "which am I editing" is now
    // drawer-open state rather than a separate two-button switch (the ratified
    // row grammar). Whether a generator is *running* stays a separate axis,
    // which is why stop is a control inside the drawer and not an icon state.
    // How long one breath of the modulation pulse takes. Emitted onto the row
    // so the stylesheet and this module cannot disagree about it.
    const PULSE_MS = 1400;
    const GEN_KINDS = ["fade", "loop", "lfo"];
    // Tab order is the ratified reading order; GEN_KINDS stays the wire/parse
    // order so nothing downstream has to care about presentation.
    const GEN_TAB_ORDER = ["lfo", "loop", "fade"];
    const GEN_TAB_LABELS = {lfo: "LFO", loop: "loop", fade: "fade"};
    const numericDeclaration = declaration =>
      ["float", "int", "toggle", "enum"].includes(declaration.kind);
    const drawerKey = (scope, id, declaration) => `${scope}:${id ?? "all"}:${declaration.identity}`;

    function generatorAvailable(declaration) {
      return !!window.ParamGenerator && !!window.ParamSpec && numericDeclaration(declaration);
    }

    function draftSpec(key, declaration, running) {
      const args = drafts.get(key);
      if (args) {
        try { return window.ParamSpec.parse(args, wireType(declaration)); }
        catch (_error) { /* fall through to the running/blank default */ }
      }
      if (running?.args) {
        try { return window.ParamSpec.parse(running.args, wireType(declaration)); }
        catch (_error) { /* not authorable — start blank */ }
      }
      return window.ParamGenerator.blank(declaration, "lfo");
    }

    // The ∿ icon: disclosure for the drawer AND the row's modulation indicator.
    // `aria-expanded` carries the disclosure state; the automated class on the
    // row paints the active ink even when the drawer is shut.
    function modIcon(key, declaration, open, disabled) {
      const label = `${declaration.name} generator`;
      return `<button type="button" class="live-param-mod" data-gen-toggle data-gen-key="${esc(key)}" aria-expanded="${open}" aria-label="${esc(label)}" ${disabled ? "disabled" : ""}>∿</button>`;
    }

    // The drawer's playhead may only move when the surface actually knows the
    // phase. That is the case when a periodic generator is running AND the
    // drawer is showing it rather than an edited draft; the display then reads
    // two cycles wide, so one traversal is two periods.
    function drawerMotion(key, model) {
      if (!model || drafts.has(key)) return null;
      if (model.parsed.mode !== "lfo" && model.parsed.mode !== "loop") return null;
      if (!(model.periodMs > 0)) return null;
      return {windowMs: model.periodMs * 2, elapsedMs: model.elapsedMs};
    }

    function generatorDrawer(scope, id, key, declaration, running, disabled, model) {
      const spec = draftSpec(key, declaration, running);
      const kind = GEN_KINDS.includes(spec.mode) ? spec.mode : "lfo";
      const off = disabled ? "disabled" : "";
      const tabs = GEN_TAB_ORDER.map(item =>
        `<button type="button" data-gen-kind-tab="${item}" aria-pressed="${item === kind}" ${off}>${GEN_TAB_LABELS[item]}</button>`).join("");
      // Apply and Stop are rendered here but PLACED by the body's layout — they
      // sit in the column beside the display, under the tabs (Bob,
      // 2026-07-27), which is what lets the drawer stop stretching.
      // Stop then Apply (Bob, 2026-07-27): the commit sits on the right, where
      // the eye leaves the drawer.
      const actions = `<span class="live-param-gen-actions">
            <button type="button" data-gen-stop ${off}>Stop</button>
            <button type="button" data-gen-apply class="primary" ${off}>Apply</button>
          </span>`;
      return `<div class="live-param-gen" data-gen-drawer="${esc(key)}" data-gen-kind="${esc(kind)}" data-live-scope="${esc(scope)}"${id == null ? "" : ` data-live-id="${esc(id)}"`} data-param-path="${esc(declaration.identity)}">
        <div class="live-param-gen-head">
          <span class="live-param-gen-tabs" role="group" aria-label="generator kind">${tabs}</span>
        </div>
        <div class="live-param-gen-fields">${window.ParamGenerator.panelFields(declaration, spec, drawerMotion(key, model), actions)}</div>
        <output class="live-param-gen-error" aria-live="polite"></output>
      </div>`;
    }

    // ---- the provisional preset row (01-control-panel/7) -------------------
    // Panel anatomy item 2 (control-panel-design §1): patch name, preset
    // dropdown, `new`/`save`/`del`. The slot is DESIGNED, not built — presets
    // are `41-preset-primitive`, which is gated behind `44-event-plane`. It
    // renders now so 41 lands into a designed home instead of redesigning the
    // panel around itself.
    //
    // Everything but the patch name is inert. Disabled controls are not
    // focusable, so `title` alone would never be announced: the row carries a
    // visually-hidden note and every control points at it with
    // `aria-describedby`, which IS announced for a disabled control.
    const PRESET_NOTE = "Presets are not built yet — the preset system is 41-preset-primitive.";
    const PRESET_ACTIONS = ["new", "save", "del"];

    function presetRow(patch, key) {
      const noteId = `live-preset-note-${String(key).replace(/[^a-zA-Z0-9_-]/g, "-")}`;
      const described = `aria-describedby="${noteId}" title="${esc(PRESET_NOTE)}"`;
      const actions = PRESET_ACTIONS.map(action =>
        `<button type="button" class="live-preset-action" data-preset-action="${action}" ${described} disabled>${action}</button>`).join("");
      return `<div class="live-preset-row" data-preset-slot>
        <span class="live-preset-patch">${esc(patch || "no patch")}</span>
        <select class="live-preset-select" aria-label="preset" ${described} disabled><option>no presets</option></select>
        ${actions}
        <span id="${noteId}" class="live-preset-note">${esc(PRESET_NOTE)}</span>
      </div>`;
    }

    // ---- parameter kinds (01-control-panel/6) ------------------------------
    // One dispatch for the whole surface. Enum is checked before toggle
    // because a two-option enum also spans 0..1, and it is the `options` list —
    // not the range — that says "this integer names its values".
    function paramKind(declaration) {
      if (declaration.kind === "event") return "event";
      if (declaration.kind === "text") return "string";
      if (declaration.kind === "enum") return "enum";
      if (declaration.kind === "toggle") return "toggle";
      return "numeric";
    }

    function scopeAttrs(scope, id, declaration) {
      return `data-live-param data-live-scope="${scope}"${id == null ? "" : ` data-live-id="${esc(id)}"`} data-param-path="${esc(declaration.identity)}"`;
    }

    // An event declaration renders its ratified row: fire, 0–3 editable float
    // elements, then the name. Every event uses the global forward-sync lead;
    // there is deliberately no per-row synchronization choice.
    function eventRow(scope, id, declaration, disabled) {
      const arity = Math.min(3, Math.max(0, Number(declaration.arity) || 0));
      const off = disabled ? " disabled" : "";
      const labels = Array.isArray(declaration.labels) ? declaration.labels : [];
      const defaults = Array.isArray(declaration.defaults) ? declaration.defaults : [];
      // Exactly `arity` boxes, no held-open slots: the name hugs the last box
      // (Bob, 2026-07-27), so a one-element event's name sits where its one
      // box ends rather than where a triplet's third box would have.
      const boxes = Array.from({length: arity}, (_unused, index) => {
        const shown = Number.isFinite(Number(defaults[index])) ? Number(defaults[index]) : 0;
        const name = labels[index] || `element ${index}`;
        return `<input class="live-event-box" type="number" step="any" value="${esc(shown)}" aria-label="${esc(`${declaration.name} ${name}`)}"${off}>`;
      }).join("");
      // Reading order is the sending order (Bob, 2026-07-27): the trigger, the
      // elements it will send, then the name.
      return `<div class="live-param live-param-event" data-live-scope="${esc(scope)}"${id == null ? "" : ` data-live-id="${esc(id)}"`} data-param-path="${esc(declaration.identity)}" data-event-arity="${arity}">
        <button type="button" class="live-event-send" aria-label="${esc(`fire ${declaration.name}`)}"${off}><span class="live-event-label">fire</span><i class="live-event-sweep" aria-hidden="true"></i></button>
        ${boxes}<span class="live-param-name">${esc(declaration.name)}</span>
      </div>`;
    }

    function paramControl(scope, id, members, declaration, disabled) {
      if (paramKind(declaration) === "event") {
        const eventId = scope === "device" ? members[0]?.id : id;
        // An event row honours the same disabled gate as a param row: an
        // offline or unbound target must not offer a fire button that would
        // put a datagram on the wire for nobody.
        return eventRow(scope, eventId, declaration, disabled);
      }
      const state = aggregateValue(members, declaration);
      const mixed = state.mixed || state.automationMixed;
      const value = state.value;
      const sourceSeat = members[0];
      const model = state.automationMixed ? null : automationModel(state.automation, declaration, sourceSeat, value);
      const automation = automationPresentation(model ? state.automation : null, state.automationMixed);
      const attrs = scopeAttrs(scope, id, declaration);
      const valueLabel = state.mixed ? `${declaration.name}, mixed values` : declaration.name;
      const label = automation ? `${valueLabel}, automated, ${automation.label}` : valueLabel;
      const common = `${attrs} data-param-name="${esc(declaration.name)}" aria-label="${esc(label)}" ${automation ? 'data-automated="true"' : ""} ${disabled ? "disabled" : ""}`;
      const glyph = automation ? `<span class="live-param-glyph" aria-hidden="true">${automation.glyph}</span>` : "";
      const nameSpan = `<span class="live-param-name">${esc(declaration.name)}${glyph}</span>`;
      const kind = paramKind(declaration);
      // Which controls can actually show the value their generator is
      // producing (Bob, 2026-07-27). A fade is sampled per frame by the rAF
      // animator, and a marker-bearing LFO/loop paints its exact position on
      // the slider. Everything else — toggles, enums, and the shapes whose
      // value the runtime cannot know (sample+hold, drift) — would have to
      // invent a value, so those pulse instead (design-language §6/§10; the
      // 50%-duty toggle flash from stitch 6 is retired).
      // Only the numeric row has a channel for a live generator value at all:
      // the rAF-sampled fade, or the CSS marker that paints an LFO's/loop's
      // exact position. A toggle box and an enum select have neither, whatever
      // the shape.
      const tracksValue = kind === "numeric" && !!model &&
        (model.parsed.mode === "fade" || !!model.marker);
      const pulsing = !!model && !tracksValue &&
        (kind === "toggle" || kind === "enum" || kind === "numeric");
      let input;
      if (kind === "string") {
        input = `${nameSpan}<input ${common} type="text" value="${mixed ? "" : esc(value)}" ${mixed ? 'placeholder="mixed" data-mixed="true"' : ""}>`;
      } else if (kind === "toggle") {
        // A PD toggle box with its label beside it: a latching `aria-pressed`
        // button in the value-box column, marked ✕ when on, so it reads as a
        // box you click rather than a full-width bar (Bob, 2026-07-27).
        const on = !mixed && !!Number(value);
        input = `<button type="button" class="live-toggle" ${common} aria-pressed="${on}" ${mixed ? 'data-mixed="true"' : ""}><span aria-hidden="true">${on ? "✕" : ""}</span></button>${nameSpan}`;
      } else if (kind === "enum") {
        // Enums automate like ints (Q2): the value on the wire is the index,
        // so the select is a labelled view of the same integer a generator
        // drives. `mixed` has no option to select, hence the dotted placeholder.
        const options = declaration.options.map((label, index) =>
          `<option value="${index}"${!mixed && Number(value) === index ? " selected" : ""}>${esc(label)}</option>`).join("");
        const mixedOption = mixed ? '<option value="" selected disabled>·····</option>' : "";
        input = `<select class="live-enum" ${common} ${mixed ? 'data-mixed="true"' : ""}>${mixedOption}${options}</select>${nameSpan}`;
      } else {
        // The value box is a number box, not a state legend: states it cannot
        // state numerically show the ratified dots and carry the words in the
        // accessible name.
        //
        // Under a periodic generator that is *architectural*, not a gap: an
        // LFO's and a loop's position are painted by a CSS animation (the
        // ratified mechanism, design-language §10), so no JavaScript knows the
        // value between heartbeats and the box would otherwise show a stale
        // number beside a moving marker. It shows dots in the modulation ink
        // instead (Bob, 2026-07-27). A fade is different — the rAF animator
        // samples it every frame and writes the box — so it keeps its number.
        const display = mixed || (model && model.parsed.mode !== "fade") ? "·····"
          : model?.parsed.mode === "fade" ? model.target
          : value;
        const boxLabel = state.automationMixed ? `${declaration.name}, mixed automation`
          : state.mixed ? `${declaration.name}, mixed values`
          : `${declaration.name} value`;
        const rangeValue = mixed ? (declaration.default ?? declaration.min ?? 0) : value;
        let motion = "";
        if (model) {
          const shape = model.parsed.mode === "lfo" ? model.parsed.shape : model.parsed.mode;
          const styles = [`--auto-period:${model.periodMs}ms`, `--auto-elapsed:${model.elapsedMs}ms`];
          if (model.minimum != null) {
            const span = model.maximum - model.minimum;
            styles.push(`--auto-min-pos:${model.minimum * 100}%`, `--auto-max-pos:${model.maximum * 100}%`);
            for (const fraction of [.03806, .14645, .30866, .5, .69134, .85355, .96194]) {
              // slice(2): "0.03806" -> "03806" must match var(--auto-p03806);
              // a leading dot would make the custom-property name invalid CSS.
              styles.push(`--auto-p${String(fraction).slice(2)}:${(model.minimum + span * fraction) * 100}%`);
            }
          }
          if (model.loopEasing) styles.push(`--auto-loop-easing:${model.loopEasing}`);
          const marker = model.marker ? `<span class="live-param-marker auto-shape-${esc(shape)}${model.parsed.free ? " free" : ""}" style="${esc(styles.join(";"))}" aria-hidden="true"></span>` : "";
          motion = marker;
        }
        const fadeAttrs = model?.parsed.mode === "fade"
          ? `data-fade-anchor="${esc(Date.now() - model.elapsedMs)}" data-fade-duration="${esc(model.periodMs)}" data-fade-from="${esc(model.parsed.from ?? state.automation?.from ?? value)}" data-fade-curve="${esc(model.parsed.curve ?? 0)}" data-fade-segments="${esc(JSON.stringify(model.parsed.segments.map(segment => ({value: segment.value, ms: segment.duration.ms}))))}"`
          : "";
        // A plain numeric readout (not mixed/automated) doubles as a click-to-type
        // precision field (40-precision-param-input); mixed/automation states keep a
        // static readout so takeover semantics are unchanged.
        const preciseReadout = !state.automationMixed && !state.mixed && !model;
        // `--v` is the fill/marker position for a *manual* row. Under a
        // periodic generator the animated marker element carries the fill
        // instead (it is the only thing that knows where the value is between
        // heartbeats), and the CSS hides the static fill behind it.
        const fillPosition = mixed ? 1 : window.ParamSpec.position(rangeValue, declaration);
        input = `<output${preciseReadout ? ' data-precise="true"' : ""} class="live-param-value" aria-label="${esc(boxLabel)}"${declaration.kind === "int" ? ' data-integer="true"' : ""}${display === "·····" ? ' data-dots="true"' : ""}>${esc(display)}</output><span class="live-param-range-wrap" style="--v:${fillPosition}"><span class="live-param-fill" aria-hidden="true"></span>${motion}${nameSpan}<input ${common} type="range" min="${esc(declaration.min ?? 0)}" max="${esc(declaration.max ?? 1)}" step="${declaration.kind === "int" ? 1 : 0.01}" value="${esc(rangeValue)}" ${mixed ? 'data-mixed="true"' : ""} ${fadeAttrs}></span>`;
      }
      const device = scope === "device" ? context.deviceForScope?.(id) : deviceForSeat(sourceSeat);
      const seatScoped = scope === "seat" || scope === "device";
      const online = !seatScoped || (!!device?.online && Number(device?.engine_alive) !== 0);
      const deviceOutputDisabled = seatScoped && !!(device?.device_enabled === false || device?.output_enabled === false);
      // Every numeric row carries the ∿ icon; the drawer is a sibling of the
      // label rather than a child, because a <label> must not wrap a form
      // region of its own. `.promoted-controls` is a grid, so the drawer lands
      // directly beneath its row.
      const generator = generatorAvailable(declaration);
      const key = drawerKey(scope, id, declaration);
      const open = generator && openDrawers.has(key);
      const modButton = generator ? modIcon(key, declaration, open, disabled) : "";
      const drawer = open ? generatorDrawer(scope, id, key, declaration, state.automation, disabled, model) : "";
      // A mixed row hatches in the modulation ink as soon as a generator is
      // anywhere in the aggregate — one pattern, two inks (design §6).
      const mixedMod = mixed && (state.automationMixed || !!state.automation);
      // The toggle's control is a <button>, and a <label> whose labelled
      // control is a button forwards its own clicks to it — so that row is a
      // plain container instead.
      const tag = kind === "toggle" ? "div" : "label";
      const classes = `live-param live-param-${kind}${mixed ? " mixed" : ""}${mixedMod ? " mixed-mod" : ""}${automation ? " automated" : ""}${pulsing ? " auto-pulse" : ""}${!online ? " automation-offline" : ""}${deviceOutputDisabled ? " automation-muted" : ""}${open ? " gen-open" : ""}`;
      // The pulse is a CSS animation on a node the heartbeat re-render
      // replaces, so it would restart — and never reach its own peak — a few
      // times a second. A negative delay anchors it, the same mechanism the
      // slider marker uses. The anchor is the wall clock rather than each
      // generator's elapsed time, so every pulsing row on the panel breathes
      // together instead of beating against its neighbours; the pulse says
      // "a generator owns this", not "here is its phase".
      const pulseAnchor = pulsing
        ? ` style="--pulse-period:${PULSE_MS}ms;--pulse-elapsed:${Date.now() % PULSE_MS}ms"` : "";
      return `<${tag} class="${classes}" data-param-path="${esc(declaration.identity)}"${pulseAnchor}>${input}${modButton}</${tag}>${drawer}`;
    }

    function declarationTree(scope, id, members, declarations, disabled) {
      const roots = {branches: new Map(), leaves: []};
      for (const declaration of declarations) {
        let node = roots;
        for (const segment of declaration.path || []) {
          if (!node.branches.has(segment)) node.branches.set(segment, {branches: new Map(), leaves: []});
          node = node.branches.get(segment);
        }
        node.leaves.push(declaration);
      }
      // Collapsed state is read once per render: a branch is open unless the
      // operator has pruned it (design-language §9). `<details>` does the
      // showing and hiding natively, so a toggle needs no re-render — only a
      // write to the store, which is what makes it survive the heartbeat.
      const collapsed = collapsedBranches();
      const renderNode = (node, trail = []) => {
        const leaves = node.leaves.map(declaration => paramControl(scope, id, members, declaration, disabled)).join("");
        const branches = [...node.branches.entries()].map(([name, child]) => {
          const path = [...trail, name];
          const key = branchKey(scope, path);
          const open = collapsed.has(key) ? "" : " open";
          return `<details class="live-param-branch" data-param-branch="${esc(path.join("/"))}" data-branch-key="${esc(key)}"${open}><summary>${esc(name)}</summary><div class="live-param-branch-kids">${renderNode(child, path)}</div></details>`;
        }).join("");
        return leaves + branches;
      };
      return renderNode(roots);
    }

    function paramTree(scope, id, members, declarations, disabled) {
      const parameters = declarations.filter(declaration => paramKind(declaration) !== "event");
      const events = declarations.filter(declaration => paramKind(declaration) === "event");
      const section = (kind, label, items) => items.length
        ? `<section class="live-control-section live-control-section-${kind}"><h3>${label}</h3>${declarationTree(scope, id, members, items, disabled)}</section>`
        : "";
      // Events first (Bob, 2026-07-28): they are the panel's performative
      // controls, and the Patch tab's manifest editor lists them in the same
      // order, so authoring and playing read top-to-bottom the same way.
      return section("events", "Events", events) + section("parameters", "Parameters", parameters);
    }

    // The slider's fill and marker are painted by the wrapper from `--v`, so
    // any code that moves the native range's value has to move `--v` with it:
    // dragging, precision entry, and the fade animator all land here.
    function syncFill(input) {
      const wrap = input.closest(".live-param-range-wrap");
      if (!wrap) return;
      const minimum = Number(input.min);
      const maximum = Number(input.max);
      const span = maximum - minimum;
      const position = Number.isFinite(span) && span !== 0
        ? (Number(input.value) - minimum) / span : 0;
      wrap.style.setProperty("--v", String(Math.min(1, Math.max(0, position))));
    }

    function fadeValueAt(input, elapsedMs) {
      const segments = JSON.parse(input.dataset.fadeSegments || "[]");
      const curve = Number(input.dataset.fadeCurve);
      let value = Number(input.dataset.fadeFrom);
      let offset = 0;
      for (const segment of segments) {
        const duration = Number(segment.ms);
        const target = Number(segment.value);
        if (elapsedMs >= offset + duration) {
          value = target;
          offset += duration;
          continue;
        }
        const fraction = duration > 0 ? Math.max(0, (elapsedMs - offset) / duration) : 1;
        const bent = fraction >= 1 ? 1 : window.ParamSpec.shapeFraction("saw", fraction, curve);
        return value + (target - value) * bent;
      }
      return value;
    }

    function finishFade(input, value) {
      input.value = value;
      syncFill(input);
      const control = input.closest(".live-param");
      const output = control?.querySelector("output");
      if (output) output.value = input.value;
      control?.classList.remove("automated");
      control?.querySelector(".live-param-glyph")?.remove();
      control?.querySelector(".live-param-marker")?.remove();
      input.removeAttribute("data-automated");
      input.setAttribute("aria-label", input.dataset.paramName || "parameter");
      for (const name of ["data-fade-anchor", "data-fade-duration", "data-fade-from", "data-fade-curve", "data-fade-segments"]) input.removeAttribute(name);
    }

    function animateFades() {
      fadeAnimationFrame = null;
      const inputs = [...document.querySelectorAll('[data-fade-anchor][data-automated="true"]')];
      if (!inputs.length) return;
      const now = Date.now();
      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      const reducedUpdateDue = now - lastReducedFadeUpdate >= 1000;
      let updated = false;
      for (const input of inputs) {
        const control = input.closest(".live-param");
        if (control?.classList.contains("taking-over") || input.matches(":active")) continue;
        const elapsed = Math.max(0, now - Number(input.dataset.fadeAnchor));
        const duration = Number(input.dataset.fadeDuration);
        const complete = elapsed >= duration;
        if (reducedMotion && !reducedUpdateDue && !complete) continue;
        const value = fadeValueAt(input, Math.min(elapsed, duration));
        if (complete) finishFade(input, value);
        else {
          input.value = value;
          syncFill(input);
          const output = control?.querySelector("output");
          if (output) output.value = input.value;
        }
        updated = true;
      }
      if (reducedMotion && updated) lastReducedFadeUpdate = now;
      if (document.querySelector('[data-fade-anchor][data-automated="true"]')) fadeAnimationFrame = requestAnimationFrame(animateFades);
    }

    function startFadeAnimator() {
      if (fadeAnimationFrame == null && document.querySelector('[data-fade-anchor][data-automated="true"]')) {
        fadeAnimationFrame = requestAnimationFrame(animateFades);
      }
    }

    // The fire button carries the whole schedule: a sweep across the button for
    // the lead the host actually sent, then a cyan flash at the moment the
    // event lands. This is the feedback the retired `/cue` buttons had, moved
    // onto the row where firing now lives (04-event-fire-affordance).
    // Lead 0 is sync-off, so it flashes with no sweep.
    const FLASH_MS = 260;
    function fireFeedback(button, leadMs) {
      if (button.dataset.firing) return;
      button.dataset.firing = "1";
      button.setAttribute("aria-busy", "true");
      // A heartbeat re-render mid-sweep would replace the button and drop the
      // animation, so hold renders off the same way a dragged slider does.
      context.setInteracting?.(true);
      const flash = () => {
        button.classList.remove("firing");
        button.classList.add("fired");
        button.style.removeProperty("--event-lead-duration");
        setTimeout(() => {
          button.classList.remove("fired");
          delete button.dataset.firing;
          button.removeAttribute("aria-busy");
          context.setInteracting?.(false);
          context.requestRender?.();
        }, FLASH_MS);
      };
      if (leadMs <= 0) { flash(); return; }
      button.style.setProperty("--event-lead-duration", `${leadMs}ms`);
      button.classList.add("firing");
      setTimeout(flash, leadMs);
    }

    function bindParams(root = document) {
      root.querySelectorAll(".live-param-event").forEach(row => {
        const button = row.querySelector(".live-event-send");
        if (!button) return;
        row.querySelectorAll(".live-event-box").forEach(input => {
          input.onfocus = () => context.setInteracting?.(true);
          input.onblur = () => context.setInteracting?.(false);
        });
        button.onclick = () => {
          const elements = [...row.querySelectorAll(".live-event-box")].map(input => Number(input.value));
          const scope = row.dataset.liveScope;
          const id = row.dataset.liveId == null ? null : row.dataset.liveId;
          const lead = context.sendEvent?.({scope, id, identity: row.dataset.paramPath, elements});
          fireFeedback(button, Number.isFinite(Number(lead)) ? Math.max(0, Number(lead)) : 0);
        };
      });
      root.querySelectorAll("[data-live-param]").forEach(input => {
        const toggle = input.tagName === "BUTTON";
        const select = input.tagName === "SELECT";
        let last = 0, timer = null, takingOver = false, takeoverSent = false;
        const beginTakeover = () => {
          if (input.dataset.automated !== "true") return;
          takingOver = true;
          input.closest(".live-param")?.classList.add("taking-over");
        };
        const announceTakeover = value => {
          if (!takingOver) return;
          const card = input.closest(".live-card");
          const cardId = card?.dataset.liveId ?? "all";
          const key = `${card?.dataset.liveScope}:${cardId}`;
          const message = `${input.dataset.paramName} automation stopped, set to ${value}`;
          takeoverAnnouncements.set(key, message);
          const status = card?.querySelector(".live-param-status");
          if (status) status.value = message;
          setTimeout(() => takeoverAnnouncements.delete(key), 2000);
        };
        const send = (override) => {
          if (takingOver && takeoverSent) return;
          input.dataset.mixed = "false";
          input.closest(".live-param")?.classList.remove("mixed", "mixed-mod");
          // `override` carries the exact typed value from the precision field, which
          // bypasses the range's coarse step so full precision reaches the wire.
          // A toggle and an enum both put an integer on the same `/p/*` wire —
          // the toggle its pressed state, the enum its option index.
          const value = override !== undefined ? override
            : toggle ? (input.getAttribute("aria-pressed") === "true" ? 1 : 0)
            : select ? Number(input.value)
            : input.type === "range" ? Number(input.value) : input.value;
          const scope = input.dataset.liveScope;
          const id = input.dataset.liveId == null ? null : input.dataset.liveId;
          context.send({scope, id, name: input.dataset.paramPath, value});
          if (takingOver) {
            takeoverSent = true;
            announceTakeover(value);
          }
        };
        // Pointer interactions are guarded by each host, but keyboard users
        // can focus a control without a pointerdown. Hold the same render
        // guard while keyboard-focused so a heartbeat cannot replace the node
        // between focus and key activation (47-live-param-kinds-flake).
        //
        // Keep the two sources distinct: a pointerup deliberately releases
        // the host guard even though a clicked control remains focused. The
        // deferred reassertion also wins over a preceding pointerup's queued
        // release when focus moves immediately under a loaded browser.
        let pointerFocusing = false, keyboardFocused = false;
        input.onfocus = () => {
          keyboardFocused = !pointerFocusing;
          if (!keyboardFocused) return;
          context.setInteracting?.(true);
          setTimeout(() => {
            if (document.activeElement === input) context.setInteracting?.(true);
          }, 0);
        };
        input.onblur = () => {
          if (keyboardFocused) context.setInteracting?.(false);
          keyboardFocused = false;
        };
        input.onpointerdown = () => {
          pointerFocusing = true;
          beginTakeover();
        };
        input.addEventListener("pointerup", () => { pointerFocusing = false; });
        input.addEventListener("pointercancel", () => { pointerFocusing = false; });
        if (toggle) {
          // The button IS the state: flip `aria-pressed` first, then send what
          // it now reads, so semantics and the wire cannot disagree. A mixed
          // aggregate resolves to "on" — the same "editing unifies" rule the
          // slider follows.
          input.onclick = () => {
            const wasMixed = input.dataset.mixed === "true";
            const on = wasMixed || input.getAttribute("aria-pressed") !== "true";
            input.setAttribute("aria-pressed", String(on));
            input.firstElementChild.textContent = on ? "✕" : "";
            // Takeover stops the generator, so the pulse stops with it.
            input.closest(".live-param")?.classList.remove("auto-pulse");
            send();
          };
        } else if (select) {
          input.onchange = () => send();
        } else if (input.type === "range") {
          input.oninput = () => {
            syncFill(input);
            const output = input.closest(".live-param")?.querySelector("output");
            if (output?.tagName === "OUTPUT") output.value = input.value;
            const now = performance.now();
            if (takingOver) return;
            if (now - last >= 33) { last = now; send(); }
            else { clearTimeout(timer); timer = setTimeout(send, 33 - (now - last)); }
          };
          // Wrapped: DOM handlers pass the Event, which would land in `override`
          // and go to the wire as {isTrusted:true} (thread 43).
          input.onchange = () => send();
          input.onpointerup = () => send();
          const output = input.closest(".live-param")?.querySelector('output[data-precise="true"]');
          if (output) window.PrecisionField.attach(output, {
            min: input.min === "" ? null : Number(input.min),
            max: input.max === "" ? null : Number(input.max),
            integer: input.step === "1",
            value: Number(input.value),
            label: input.dataset.paramName,
            disabled: input.disabled,
          }, value => { input.value = value; syncFill(input); send(value); },
             editing => {
               context.setInteracting?.(editing);
               if (!editing) context.requestRender?.();
             });
        } else input.onchange = () => send();
      });
      bindBranches(root);
      bindGenerators(root);
      startFadeAnimator();
    }

    // `<details>` opens and closes itself; all we do is record the outcome, so
    // the next heartbeat re-render (and the next page load) reproduces it.
    function bindBranches(root = document) {
      root.querySelectorAll("[data-branch-key]").forEach(branch => {
        branch.ontoggle = () => storeBranchCollapsed(branch.dataset.branchKey, !branch.open);
      });
    }

    function bindGenerators(root = document) {
      root.querySelectorAll("[data-gen-toggle]").forEach(button => {
        button.onclick = event => {
          // The icon lives inside the row's <label>, so a plain click would
          // also activate the labelled control — nudging the very slider the
          // operator was trying to open a drawer for.
          event.preventDefault();
          const key = button.dataset.genKey;
          if (openDrawers.has(key)) openDrawers.delete(key);
          else openDrawers.add(key);
          context.requestRender?.();
        };
      });

      root.querySelectorAll("[data-gen-drawer]").forEach(drawer => {
        const key = drawer.dataset.genDrawer;
        const identity = drawer.dataset.paramPath;
        const scope = drawer.dataset.liveScope;
        const id = drawer.dataset.liveId ?? null;
        const declaration = (state().live_controls?.declarations || [])
          .find(item => item.identity === identity) || {kind: "float", identity};
        const error = drawer.querySelector(".live-param-gen-error");
        // The kind used to live in a <select>; it is now the drawer's own
        // dataset, written by the tab row, so the compile path has one source
        // of truth whatever the chrome looks like.
        const currentKind = () => drawer.dataset.genKind || "lfo";

        // Editing inside a drawer must survive the heartbeat: the host's
        // render guard is the same one the precision field uses.
        drawer.onfocusin = () => context.setInteracting?.(true);
        drawer.onfocusout = () => context.setInteracting?.(false);

        const compile = () => window.ParamGenerator.compile(drawer, declaration, currentKind());
        const refresh = () => {
          const args = compile();
          if (!args) return null;
          drafts.set(key, args);
          // The display IS the preview now, so an edit redraws its trace. Only
          // the trace: the shape picker lives inside the same box, and
          // replacing it under the operator's pointer would drop the focus
          // they are editing with. The playhead goes, because an edited draft
          // is no longer the generator that is running (drawerMotion's rule
          // made visible).
          const wave = drawer.querySelector(".live-gen-wave");
          if (wave) {
            wave.querySelector(".live-gen-playhead")?.remove();
            const trace = wave.querySelector("svg, .live-gen-wave-empty");
            try {
              const drawn = window.ParamGenerator.waveTrace(
                window.ParamSpec.parse(args, wireType(declaration)), declaration);
              if (trace) trace.outerHTML = drawn;
              else wave.insertAdjacentHTML("afterbegin", drawn);
            } catch (_error) { /* keep the last good trace */ }
          }
          return args;
        };

        // A mini-slider paints itself from `--v`, like the parameter row's
        // slider, and states its value in its own inside label.
        const syncMini = input => {
          const wrap = input.closest(".live-gen-mini");
          if (!wrap) return;
          const span = Number(input.max) - Number(input.min);
          const position = span ? (Number(input.value) - Number(input.min)) / span : 0;
          wrap.style.setProperty("--v", String(Math.min(1, Math.max(0, position))));
          const readout = wrap.querySelector("[data-mini-readout]");
          if (readout) readout.textContent = Number(input.value).toFixed(2);
        };
        drawer.querySelectorAll(".live-gen-mini-input").forEach(input => {
          input.addEventListener("input", () => syncMini(input));
        });

        // Curve only bends tri, saw and drift; on the other shapes the option
        // reaches the node and does nothing. Changing shape therefore takes
        // the control away and zeroes it, so a stale bend cannot ride out on
        // the next Apply.
        const shape = drawer.querySelector('[data-param-lfo="shape"]');
        const curveSlot = drawer.querySelector(".live-gen-curve-slot");
        if (shape && curveSlot) shape.addEventListener("change", () => {
          const bends = (curveSlot.dataset.curveShapes || "").split(" ")
            .includes(shape.value);
          curveSlot.hidden = !bends;
          if (bends) return;
          const input = curveSlot.querySelector(".live-gen-mini-input");
          if (input) { input.value = "0"; syncMini(input); }
        });

        // The fade's `from` box is inert until its latching box says there is
        // a start value to state (Bob, 2026-07-27).
        const fromEnabled = drawer.querySelector("[data-param-from-enabled]");
        if (fromEnabled) fromEnabled.addEventListener("change", () => {
          const field = drawer.querySelector("[data-param-from]");
          if (!field) return;
          field.disabled = !fromEnabled.checked;
          if (fromEnabled.checked && !field.value) field.value = declaration.default ?? declaration.min ?? 0;
          if (fromEnabled.checked) field.focus();
        });

        drawer.querySelectorAll("[data-gen-kind-tab]").forEach(tab => {
          tab.onclick = () => {
            const kind = tab.dataset.genKindTab;
            if (kind === currentKind()) return;
            // Switching kind starts that kind's own defaults rather than trying
            // to reinterpret the previous kind's fields.
            drawer.dataset.genKind = kind;
            drafts.delete(key);
            for (const other of drawer.querySelectorAll("[data-gen-kind-tab]")) {
              other.setAttribute("aria-pressed", String(other === tab));
            }
            const blank = window.ParamGenerator.blank(declaration, kind);
            // The commit pair lives inside the body, so a kind switch has to
            // carry it across rather than let the re-render drop it.
            const actions = drawer.querySelector(".live-param-gen-actions")?.outerHTML || "";
            drawer.querySelector(".live-param-gen-fields").innerHTML =
              window.ParamGenerator.panelFields(declaration, blank, null, actions);
            bindGenerators(drawer.parentElement || root);
            refresh();
          };
        });

        drawer.querySelectorAll("input, select").forEach(field => {
          field.oninput = refresh;
          field.onchange = refresh;
        });

        const addSegment = drawer.querySelector("[data-add-param-segment]");
        if (addSegment) addSegment.onclick = () => {
          const list = drawer.querySelector("[data-param-segments]");
          const count = list.querySelectorAll("[data-param-segment]").length;
          list.insertAdjacentHTML("beforeend", window.ParamGenerator.panelSegmentRow(
            {value: declaration.max ?? 1, duration: {ms: 1000, amount: "1", unit: "s"}},
            count, declaration, count + 1));
          bindGenerators(drawer.parentElement || root);
          refresh();
        };
        drawer.querySelectorAll("[data-remove-param-segment]").forEach(button => {
          button.onclick = () => {
            button.closest("[data-param-segment]")?.remove();
            bindGenerators(drawer.parentElement || root);
            refresh();
          };
        });

        const apply = drawer.querySelector("[data-gen-apply]");
        if (apply) apply.onclick = () => {
          const args = refresh();
          if (!args) {
            if (error) error.value = "Those generator fields are incomplete.";
            return;
          }
          if (error) error.value = "";
          context.sendAutomation?.({scope, id, name: identity, args});
        };
        const stop = drawer.querySelector("[data-gen-stop]");
        if (stop) stop.onclick = () => {
          if (error) error.value = "";
          context.sendAutomation?.({
            scope, id, name: identity,
            args: [window.OscMessage.typedArg("s", "stop")],
          });
        };
      });
    }

    return {
      tree: paramTree,
      control: paramControl,
      presetRow,
      bind: bindParams,
      refreshAnchors: refreshAutomationAnchors,
      announcement: key => takeoverAnnouncements.get(key) || "",
      startFadeAnimator,
    };
  }

  window.ControlSurface = {create};
})();
