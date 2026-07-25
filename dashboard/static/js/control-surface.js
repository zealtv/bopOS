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

  function create(context) {
    // context: {getState, deviceForSeat, send, sendAutomation, setInteracting, requestRender}
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
      if (!seat || declaration.type === "s") return null;
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
          if (!declaration || declaration.type === "s") continue;
          let parsed;
          try { parsed = window.ParamSpec.parse(entry.args || [], declaration.type); }
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
      try { parsed = window.ParamSpec.parse(entry.args || [], declaration.type); }
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

    // ---- generator drawer (37/08) -----------------------------------------
    // A numeric row authors either a value or a generator against the same
    // param address. The mode switch says which one the operator is editing;
    // whether a generator is *running* is a separate axis, which is why stop
    // is a control inside the drawer and not a third switch state.
    const GEN_KINDS = ["fade", "loop", "lfo"];
    const numericDeclaration = declaration => declaration.type === "f" || declaration.type === "i";
    const drawerKey = (scope, id, declaration) => `${scope}:${id ?? "all"}:${declaration.identity}`;

    function generatorAvailable(declaration) {
      return !!window.ParamGenerator && !!window.ParamSpec && numericDeclaration(declaration);
    }

    function draftSpec(key, declaration, running) {
      const args = drafts.get(key);
      if (args) {
        try { return window.ParamSpec.parse(args, declaration.type); }
        catch (_error) { /* fall through to the running/blank default */ }
      }
      if (running?.args) {
        try { return window.ParamSpec.parse(running.args, declaration.type); }
        catch (_error) { /* not authorable — start blank */ }
      }
      return window.ParamGenerator.blank(declaration, "lfo");
    }

    function modeSwitch(key, declaration, open, disabled) {
      const label = `${declaration.name} authoring mode`;
      const button = (mode, text, pressed) =>
        `<button type="button" class="live-param-mode-button" data-gen-mode="${mode}" data-gen-key="${esc(key)}" aria-pressed="${pressed}" ${disabled ? "disabled" : ""}>${text}</button>`;
      return `<span class="live-param-mode" role="group" aria-label="${esc(label)}">${button("value", "value", !open)}${button("gen", "gen", open)}</span>`;
    }

    function generatorDrawer(scope, id, key, declaration, running, disabled) {
      const spec = draftSpec(key, declaration, running);
      const kind = GEN_KINDS.includes(spec.mode) ? spec.mode : "lfo";
      const options = GEN_KINDS.map(item =>
        `<option value="${item}" ${item === kind ? "selected" : ""}>${item}</option>`).join("");
      const off = disabled ? "disabled" : "";
      return `<div class="live-param-gen" data-gen-drawer="${esc(key)}" data-live-scope="${esc(scope)}"${id == null ? "" : ` data-live-id="${esc(id)}"`} data-param-path="${esc(declaration.identity)}">
        <div class="live-param-gen-head">
          <label>generator <select data-gen-kind ${off}>${options}</select></label>
          <span class="live-param-gen-actions">
            <button type="button" data-gen-apply class="primary" ${off}>Apply</button>
            <button type="button" data-gen-stop ${off}>Stop</button>
          </span>
        </div>
        <div class="live-param-gen-fields">${window.ParamGenerator.fields(declaration, spec)}</div>
        <div class="live-param-gen-preview">${window.ParamGenerator.preview(spec, declaration)}</div>
        <output class="live-param-gen-error" aria-live="polite"></output>
      </div>`;
    }

    function scopeAttrs(scope, id, declaration) {
      return `data-live-param data-live-scope="${scope}"${id == null ? "" : ` data-live-id="${esc(id)}"`} data-param-path="${esc(declaration.identity)}"`;
    }

    function paramControl(scope, id, members, declaration, disabled) {
      const state = scope === "seat" || scope === "device"
        ? {value: valueForSeat(members[0], declaration), mixed: false,
           automation: automationForSeat(members[0], declaration), automationMixed: false}
        : aggregateValue(members, declaration);
      const mixed = state.mixed || state.automationMixed;
      const value = state.value;
      const sourceSeat = members[0];
      const model = state.automationMixed ? null : automationModel(state.automation, declaration, sourceSeat, value);
      const automation = automationPresentation(model ? state.automation : null, state.automationMixed);
      const attrs = scopeAttrs(scope, id, declaration);
      const valueLabel = state.mixed ? `${declaration.name}, mixed values` : declaration.name;
      const label = automation ? `${valueLabel}, automated, ${automation.label}` : valueLabel;
      const common = `${attrs} data-param-name="${esc(declaration.name)}" aria-label="${esc(label)}" ${automation ? 'data-automated="true"' : ""} ${disabled ? "disabled" : ""}`;
      const mixedText = state.automationMixed ? '<span class="live-param-auto-mixed">auto·mixed</span>' : "";
      let input;
      if (declaration.type === "s") {
        input = `<input ${common} type="text" value="${mixed ? "" : esc(value)}" ${mixed ? 'placeholder="mixed" data-mixed="true"' : ""}>`;
      } else if (declaration.type === "i" && Number(declaration.min) === 0 && Number(declaration.max) === 1) {
        input = `<input ${common} type="checkbox" ${!mixed && Number(value) ? "checked" : ""} ${mixed ? 'data-mixed="true"' : ""}>`;
      } else {
        const kind = model?.parsed.mode === "lfo" ? model.parsed.shape : model?.parsed.mode;
        const display = state.automationMixed ? "auto·mixed" : state.mixed ? "mixed"
          : model?.parsed.mode === "fade" ? `→ ${model.target}`
          : model ? `${value} · ${kind}` : value;
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
        input = `<output${preciseReadout ? ' data-precise="true"' : ""}>${esc(display)}</output><span class="live-param-range-wrap">${motion}<input ${common} type="range" min="${esc(declaration.min ?? 0)}" max="${esc(declaration.max ?? 1)}" step="${declaration.type === "i" ? 1 : 0.01}" value="${esc(rangeValue)}" ${mixed ? 'data-mixed="true"' : ""} ${fadeAttrs}></span>`;
      }
      const glyph = automation ? `<span class="live-param-glyph" aria-hidden="true">${automation.glyph}</span>` : "";
      const device = scope === "device" ? context.deviceForScope?.(id) : deviceForSeat(sourceSeat);
      const seatScoped = scope === "seat" || scope === "device";
      const online = !seatScoped || (!!device?.online && Number(device?.engine_alive) !== 0);
      const deviceOutputDisabled = seatScoped && !!(device?.device_enabled === false || device?.output_enabled === false);
      // Every numeric row carries the value/gen switch; the drawer is a sibling
      // of the label rather than a child, because a <label> must not wrap a
      // form region of its own. `.promoted-controls` is a grid, so the drawer
      // lands directly beneath its row.
      const generator = generatorAvailable(declaration);
      const key = drawerKey(scope, id, declaration);
      const open = generator && openDrawers.has(key);
      const switcher = generator ? modeSwitch(key, declaration, open, disabled) : "";
      const drawer = open ? generatorDrawer(scope, id, key, declaration, state.automation, disabled) : "";
      return `<label class="live-param${mixed ? " mixed" : ""}${automation ? " automated" : ""}${!online ? " automation-offline" : ""}${deviceOutputDisabled ? " automation-muted" : ""}${open ? " gen-open" : ""}" data-param-path="${esc(declaration.identity)}"><span class="live-param-name">${esc(declaration.name)}${glyph}</span>${declaration.type === "i" && Number(declaration.min) === 0 && Number(declaration.max) === 1 ? mixedText : ""}${switcher}${input}</label>${drawer}`;
    }

    function paramTree(scope, id, members, declarations, disabled) {
      const roots = {branches: new Map(), leaves: []};
      for (const declaration of declarations) {
        let node = roots;
        for (const segment of declaration.path || []) {
          if (!node.branches.has(segment)) node.branches.set(segment, {branches: new Map(), leaves: []});
          node = node.branches.get(segment);
        }
        node.leaves.push(declaration);
      }
      const renderNode = (node, trail = []) => {
        const leaves = node.leaves.map(declaration => paramControl(scope, id, members, declaration, disabled)).join("");
        const branches = [...node.branches.entries()].map(([name, child]) => {
          const path = [...trail, name];
          return `<section class="live-param-branch" data-param-branch="${esc(path.join("/"))}"><h3>${esc(name)}</h3>${renderNode(child, path)}</section>`;
        }).join("");
        return leaves + branches;
      };
      return renderNode(roots);
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

    function bindParams(root = document) {
      root.querySelectorAll("[data-live-param]").forEach(input => {
        if (input.type === "checkbox" && input.dataset.mixed === "true") input.indeterminate = true;
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
          input.indeterminate = false;
          input.dataset.mixed = "false";
          input.closest(".live-param")?.classList.remove("mixed");
          // `override` carries the exact typed value from the precision field, which
          // bypasses the range's coarse step so full precision reaches the wire.
          const value = override !== undefined ? override
            : input.type === "checkbox" ? (input.checked ? 1 : 0) : input.type === "range" ? Number(input.value) : input.value;
          const scope = input.dataset.liveScope;
          const id = input.dataset.liveId == null ? null : input.dataset.liveId;
          context.send({scope, id, name: input.dataset.paramPath, value});
          if (takingOver) {
            takeoverSent = true;
            announceTakeover(value);
          }
        };
        input.onpointerdown = beginTakeover;
        if (input.type === "range") {
          input.oninput = () => {
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
          }, value => { input.value = value; send(value); },
             editing => {
               context.setInteracting?.(editing);
               if (!editing) context.requestRender?.();
             });
        } else input.onchange = () => send();
      });
      bindGenerators(root);
      startFadeAnimator();
    }

    function bindGenerators(root = document) {
      root.querySelectorAll("[data-gen-mode]").forEach(button => {
        button.onclick = event => {
          // The switch lives inside the row's <label>, so a plain click would
          // also activate the labelled control — toggling the very checkbox
          // the operator was trying to open a drawer for.
          event.preventDefault();
          const key = button.dataset.genKey;
          if (button.dataset.genMode === "gen") openDrawers.add(key);
          else openDrawers.delete(key);
          context.requestRender?.();
        };
      });

      root.querySelectorAll("[data-gen-drawer]").forEach(drawer => {
        const key = drawer.dataset.genDrawer;
        const identity = drawer.dataset.paramPath;
        const scope = drawer.dataset.liveScope;
        const id = drawer.dataset.liveId ?? null;
        const declaration = (state().live_controls?.declarations || [])
          .find(item => item.identity === identity) || {type: "f", identity};
        const kindSelect = drawer.querySelector("[data-gen-kind]");
        const error = drawer.querySelector(".live-param-gen-error");

        // Editing inside a drawer must survive the heartbeat: the host's
        // render guard is the same one the precision field uses.
        drawer.onfocusin = () => context.setInteracting?.(true);
        drawer.onfocusout = () => context.setInteracting?.(false);

        const compile = () => window.ParamGenerator.compile(drawer, declaration, kindSelect?.value || "lfo");
        const refresh = () => {
          const args = compile();
          if (!args) return null;
          drafts.set(key, args);
          const preview = drawer.querySelector(".live-param-gen-preview");
          if (preview) {
            try {
              preview.innerHTML = window.ParamGenerator.preview(
                window.ParamSpec.parse(args, declaration.type), declaration);
            } catch (_error) { preview.innerHTML = ""; }
          }
          return args;
        };

        if (kindSelect) kindSelect.onchange = () => {
          // Switching kind starts that kind's own defaults rather than trying
          // to reinterpret the previous kind's fields.
          drafts.delete(key);
          const blank = window.ParamGenerator.blank(declaration, kindSelect.value);
          drawer.querySelector(".live-param-gen-fields").innerHTML =
            window.ParamGenerator.fields(declaration, blank);
          bindGenerators(drawer.parentElement || root);
          refresh();
        };

        drawer.querySelectorAll("input, select").forEach(field => {
          if (field === kindSelect) return;
          field.oninput = refresh;
          field.onchange = refresh;
        });

        const addSegment = drawer.querySelector("[data-add-param-segment]");
        if (addSegment) addSegment.onclick = () => {
          const list = drawer.querySelector("[data-param-segments]");
          const count = list.querySelectorAll("[data-param-segment]").length;
          list.insertAdjacentHTML("beforeend", window.ParamGenerator.segmentRow(
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
      bind: bindParams,
      refreshAnchors: refreshAutomationAnchors,
      announcement: key => takeoverAnnouncements.get(key) || "",
      startFadeAnimator,
    };
  }

  window.ControlSurface = {create};
})();
