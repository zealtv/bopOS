// The parameter generator builder, extracted from show.js (thread 37, stitch
// 08) so the live control surface can host the same fields the Show inspector
// uses. There is exactly one builder: the ratified automation-2 GUI, compiling
// to the OSC contract §3.2 wire grammar. Two copies of it was the failure mode
// this extraction exists to prevent.
//
// The markup, class names and data-attributes are carried over unchanged so
// the existing Show inspector CSS keeps applying to both hosts.
(function () {
  "use strict";

  const KINDS = ["value", "fade", "loop", "lfo", "stop"];
  const DRAWER_KINDS = ["lfo", "loop", "fade"];
  const DRAWER_LABELS = {lfo: "LFO", loop: "loop", fade: "fade"};
  const SHAPES = ["sine", "tri", "saw", "square", "sh", "drift"];
  const UNITS = ["ms", "s", "m", "h"];

  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const typedArg = (kind, value) => window.OscMessage.typedArg(kind, value);
  const wireType = declaration => declaration?.kind === "float" ? "f"
    : declaration?.kind === "text" ? "s" : "i";

  function inputNumber(root, selector) {
    const value = Number(root.querySelector(selector)?.value);
    return Number.isFinite(value) ? value : null;
  }

  function durationString(root, amountSelector, unitSelector) {
    const amount = inputNumber(root, amountSelector);
    const unit = root.querySelector(unitSelector)?.value || "ms";
    if (amount == null || amount < 0) return null;
    return `${String(Number(amount))}${unit}`;
  }

  function unitOptions(selected) {
    return UNITS.map(unit => `<option value="${unit}" ${unit === selected ? "selected" : ""}>${unit}</option>`).join("");
  }

  function valueAttrs(declaration) {
    const integer = ["int", "toggle", "enum"].includes(declaration.kind);
    return `step="${integer ? "1" : "any"}" ${integer ? 'data-integer="true"' : ""} ${declaration.min != null ? `min="${esc(declaration.min)}"` : ""} ${declaration.max != null ? `max="${esc(declaration.max)}"` : ""}`;
  }

  function segmentRow(segment, index, declaration, count) {
    return `<div class="show-param-segment" data-param-segment="${index}">
      <label>destination <input data-param-segment-value type="number" ${valueAttrs(declaration)} value="${esc(segment.value)}"></label>
      <label>duration <span class="show-param-duration"><input data-param-segment-duration type="number" min="0" step="any" value="${esc(segment.duration.amount)}"><select data-param-segment-unit>${unitOptions(segment.duration.unit)}</select></span></label>
      <button type="button" class="danger" data-remove-param-segment aria-label="Remove segment" ${count <= 1 ? "disabled" : ""}>Remove</button>
    </div>`;
  }

  function fields(declaration, parsed) {
    if (declaration.kind === "text") {
      return `<label>value <input id="show-param-value" type="text" value="${esc(parsed.value ?? declaration.default ?? "")}"></label>`;
    }
    if (parsed.mode === "value") {
      return `<label>value <input id="show-param-value" type="number" ${valueAttrs(declaration)} value="${esc(parsed.value)}"></label>`;
    }
    if (parsed.mode === "stop") return '<p class="dim show-param-stop">Stops automation and holds its current output.</p>';
    if (parsed.mode === "lfo") {
      return `<div class="show-param-lfo">
        <label>shape <select data-param-lfo="shape">${SHAPES.map(shape => `<option value="${shape}" ${parsed.shape === shape ? "selected" : ""}>${shape}</option>`).join("")}</select></label>
        <label>min <input data-param-lfo="min" type="number" ${valueAttrs(declaration)} value="${esc(parsed.min)}"></label>
        <label>max <input data-param-lfo="max" type="number" ${valueAttrs(declaration)} value="${esc(parsed.max)}"></label>
        <label>period <span class="show-param-duration"><input data-param-lfo="period" type="number" min="0" step="any" value="${esc(parsed.period.amount)}"><select data-param-lfo="period-unit">${unitOptions(parsed.period.unit)}</select></span></label>
        <label>phase <input data-param-lfo="phase" type="number" min="0" max="1" step="0.01" value="${esc(parsed.phase)}"></label>
        <label class="show-check">free <input data-param-lfo="free" type="checkbox" ${parsed.free ? "checked" : ""}></label>
        <label>curve <input data-param-lfo="curve" type="number" step="any" value="${esc(parsed.curve || "")}"></label>
      </div>`;
    }
    const from = parsed.mode === "fade" && parsed.segments.length === 1
      ? `<label>from · optional <input data-param-from type="number" ${valueAttrs(declaration)} value="${esc(parsed.from ?? "")}"></label>` : "";
    return `<div class="show-param-segments" data-param-segments>
      ${parsed.segments.map((segment, index) => segmentRow(segment, index, declaration, parsed.segments.length)).join("")}
    </div>
    <button type="button" data-add-param-segment>Add segment</button>
    ${from}
    <label>curve <input data-param-curve type="number" step="any" value="${esc(parsed.curve || "")}"></label>
    <p class="show-field-error show-param-loop-hint" ${parsed.mode === "loop" && parsed.segments.length < 2 ? "" : "hidden"}>loop needs at least two segments</p>`;
  }

  // The sampled trace behind every preview: the Show inspector's captioned
  // figure and the control panel's waveform display are two framings of the
  // same geometry, so the sampling lives here once. Returns null for the
  // shapes there is nothing honest to draw (sample+hold, drift).
  // `repeats` is how many cycles of a periodic generator the frame shows. The
  // Show inspector draws two — it is reading matter, and the repetition is
  // what says "periodic". The control panel's display draws ONE (Bob,
  // 2026-07-27): it is a live instrument face, where the shape has to be
  // legible at a glance and the playhead has to mean one period.
  //
  // `normalise` frames a fade or loop by the values it actually visits rather
  // than by the parameter's declared range (Bob, 2026-07-27). A fade from .34
  // to 1 on a 0..1 param drew as a shallow line across the top third; the
  // panel's display is there to show the SHAPE, so it fills the box. The Show
  // inspector keeps declaration framing — there the range is the point.
  function previewGeometry(parsed, declaration, repeats = 2, normalise = false) {
    if (!["fade", "loop", "lfo"].includes(parsed.mode)) return null;
    if (parsed.mode === "lfo" && ["sh", "drift"].includes(parsed.shape)) return null;
    const points = [];
    if (parsed.mode === "lfo") {
      const count = 64 * repeats;
      for (let index = 0; index <= count; index += 1) {
        const time = index / count * repeats;
        points.push([time, window.ParamSpec.shapeFraction(parsed.shape, time + parsed.phase, parsed.curve)]);
      }
    } else {
      const cycles = parsed.mode === "loop" ? repeats : 1;
      const duration = Math.max(1, window.ParamSpec.totalDuration(parsed));
      let time = 0;
      let start = Number(parsed.from ?? declaration.default ?? parsed.segments[0]?.value ?? 0);
      points.push([0, start]);
      for (let cycle = 0; cycle < cycles; cycle += 1) {
        for (const segment of parsed.segments) {
          const steps = Math.max(2, Math.min(16, Math.ceil(segment.duration.ms / 100)));
          for (let index = 1; index <= steps; index += 1) {
            const fraction = index / steps;
            // saw wraps at phase 1 (periodic); a one-shot ramp must end at 1.
            const bent = fraction >= 1 ? 1 : window.ParamSpec.shapeFraction("saw", fraction, parsed.curve);
            points.push([(time + segment.duration.ms * fraction) / duration,
              start + (segment.value - start) * bent]);
          }
          time += segment.duration.ms;
          start = segment.value;
        }
        if (parsed.mode === "loop" && cycle + 1 < cycles) {
          start = Number(declaration.default ?? parsed.segments[0]?.value ?? 0);
          points.push([time / duration, start]);
        }
      }
    }
    if (!points.length) return null;
    const values = points.map(point => point[1]);
    const framed = normalise && parsed.mode !== "lfo";
    let low = parsed.mode === "lfo" ? 0
      : framed ? Math.min(...values)
      : Number(declaration.min ?? Math.min(...values));
    let high = parsed.mode === "lfo" ? 1
      : framed ? Math.max(...values)
      : Number(declaration.max ?? Math.max(...values));
    if (!Number.isFinite(low)) low = Math.min(...values);
    if (!Number.isFinite(high)) high = Math.max(...values);
    // A flat ramp has no span to normalise against; centre it rather than
    // pinning it to the floor, which would read as "at minimum".
    if (high === low) { low -= .5; high += .5; }
    const maxTime = Math.max(...points.map(point => point[0]), 1);
    const path = points.map(([time, value], index) => {
      const x = 8 + time / maxTime * 224;
      const y = 64 - (value - low) / (high - low) * 56;
      return `${index ? "L" : "M"}${x.toFixed(2)} ${Math.min(64, Math.max(8, y)).toFixed(2)}`;
    }).join(" ");
    const label = parsed.mode === "lfo" ? `${parsed.shape} LFO preview` : `${parsed.mode} preview`;
    return {path, label};
  }

  function preview(parsed, declaration) {
    if (!["fade", "loop", "lfo"].includes(parsed.mode)) return "";
    if (parsed.mode === "lfo" && ["sh", "drift"].includes(parsed.shape)) {
      return '<p class="show-param-preview-random" data-param-preview-random>random — not previewable</p>';
    }
    const geometry = previewGeometry(parsed, declaration);
    if (!geometry) return "";
    const {path, label} = geometry;
    return `<figure class="show-param-preview" data-param-preview><figcaption>${esc(label)} · value / time</figcaption><svg viewBox="0 0 240 72" role="img" aria-label="${esc(label)}"><path class="show-param-preview-axis" d="M8 8V64H232"></path><path class="show-param-preview-line" d="${path}"></path></svg></figure>`;
  }

  // ---- the control-panel drawer body (01-control-panel/9) ------------------
  // The ratified panel language (design-language §7, mockup panels 1 and 2) is
  // a different LAYOUT of the same fields: a waveform display the drawer is
  // built around, mini-sliders for the shaping args, one line per fade
  // segment. `fields()` above stays exactly as it is — it is the Show
  // inspector's, and that surface is not in this thread.
  //
  // Every `data-param-*` hook is identical, so `compile()`, the drawer
  // binding and the wire do not know which renderer drew the drawer.

  const SHAPE_LABELS = {sh: "s+h"};
  // Curve is a signed exponent and unbounded in the grammar; a slider has to
  // choose a range. ±4 is 2^±4 — a 16× bend in either direction, past which
  // the shape is indistinguishable from a step. Typed precision beyond that
  // stays available in the Show inspector's number field.
  const CURVE_LIMIT = 4;
  // Which LFO shapes curve actually bends. The engine is the authority
  // (`python/paramgen.py` `_lfo_value`): tri and saw run their ramp through
  // `_shape`, and drift shapes its interpolation between random targets.
  // sine, square and sample+hold ignore the option entirely — so the panel
  // does not offer it there (Bob, 2026-07-27: "if curve has no effect on lfo
  // it should be removed"). The Show inspector's number field is unchanged;
  // this is the live face, where a control that does nothing is a lie.
  const CURVED_SHAPES = ["tri", "saw", "drift"];

  function miniSlider(attrs, name, value, min, max, step) {
    const span = max - min;
    const position = span ? (Number(value) - min) / span : 0;
    return `<span class="live-gen-mini" style="--v:${Math.min(1, Math.max(0, position))}">
      <span class="live-gen-mini-fill" aria-hidden="true"></span>
      <span class="live-gen-mini-name" aria-hidden="true">${esc(name)} <b data-mini-readout>${esc(Number(value).toFixed(2))}</b></span>
      <input ${attrs} class="live-gen-mini-input" type="range" min="${min}" max="${max}" step="${step}" value="${esc(value)}" aria-label="${esc(name)}">
    </span>`;
  }

  // The display the drawer is built around. `motion` is present only when a
  // generator is actually running and the drawer is showing it rather than an
  // edited draft — the playhead is never invented (the `8-kind-feedback-pass`
  // ruling: a control must not animate a substitute for a value it cannot
  // know).
  // The trace alone, so the live redraw on every keystroke can replace it
  // without touching the shape picker sitting inside the same display.
  function waveTrace(parsed, declaration) {
    const geometry = previewGeometry(parsed, declaration, 1, true);
    if (!geometry) return '<span class="live-gen-wave-empty">random — not previewable</span>';
    return `<svg viewBox="0 0 240 72" preserveAspectRatio="none" role="img" aria-label="${esc(geometry.label)}"><path class="live-gen-wave-line" d="${geometry.path}" vector-effect="non-scaling-stroke"></path></svg>`;
  }

  function waveDisplay(parsed, declaration, inside, motion) {
    const geometry = previewGeometry(parsed, declaration, 1, true);
    const trace = waveTrace(parsed, declaration);
    const playhead = motion && geometry
      ? `<span class="live-gen-playhead" aria-hidden="true" style="--gen-window:${motion.windowMs}ms;--gen-elapsed:${motion.elapsedMs}ms"></span>`
      : "";
    return `<div class="live-gen-wave" data-param-preview>${trace}${playhead}${inside}</div>`;
  }

  function panelSegmentRow(segment, index, declaration, count) {
    return `<div class="live-gen-seg" data-param-segment="${index}">
      <span class="live-gen-seg-label">to</span>
      <input data-param-segment-value class="live-gen-num" type="number" ${valueAttrs(declaration)} value="${esc(segment.value)}" aria-label="destination value">
      <span class="live-gen-seg-label">in</span>
      <input data-param-segment-duration class="live-gen-num" type="number" min="0" step="any" value="${esc(segment.duration.amount)}" aria-label="duration">
      <select data-param-segment-unit class="live-gen-unit" aria-label="duration unit">${unitOptions(segment.duration.unit)}</select>
      <button type="button" class="live-gen-remove" data-remove-param-segment aria-label="Remove segment" ${count <= 1 ? "disabled" : ""}>remove</button>
    </div>`;
  }

  // `actions` is the host's commit pair (Apply / Stop). It is rendered by the
  // caller but placed by the layout: Bob moved it out of the head row and into
  // the column beside the display (2026-07-27), which is what lets the drawer
  // stop stretching to the panel's full width.
  function panelFields(declaration, parsed, motion, actions = "") {
    if (declaration.kind === "text" || parsed.mode === "value") return actions + fields(declaration, parsed);
    if (parsed.mode === "stop") return actions + fields(declaration, parsed);
    if (parsed.mode === "lfo") {
      // The shape select lives INSIDE the display, bottom-right: it names what
      // the display is showing, so it belongs to it (mockup panel 1).
      const shapes = SHAPES.map(shape =>
        `<option value="${shape}" ${parsed.shape === shape ? "selected" : ""}>${esc(SHAPE_LABELS[shape] || shape)}</option>`).join("");
      const picker = `<span class="live-gen-shape"><select data-param-lfo="shape" aria-label="shape">${shapes}</select></span>`;
      const bends = CURVED_SHAPES.includes(parsed.shape);
      const curve = miniSlider('data-param-lfo="curve"', "curve",
        bends ? (parsed.curve || 0) : 0, -CURVE_LIMIT, CURVE_LIMIT, .05);
      return `<div class="live-gen-body">
        ${waveDisplay(parsed, declaration, picker, motion)}
        <div class="live-gen-side">
          ${actions}
          ${miniSlider('data-param-lfo="phase"', "phase", parsed.phase ?? 0, 0, 1, .01)}
          <span class="live-gen-curve-slot" data-curve-shapes="${CURVED_SHAPES.join(" ")}" ${bends ? "" : "hidden"}>${curve}</span>
          <label class="live-gen-pill"><input data-param-lfo="free" type="checkbox" ${parsed.free ? "checked" : ""}><span>free</span></label>
        </div>
      </div>
      <div class="live-gen-args">
        <label class="live-gen-field">min<input data-param-lfo="min" class="live-gen-num" type="number" ${valueAttrs(declaration)} value="${esc(parsed.min)}"></label>
        <label class="live-gen-field">max<input data-param-lfo="max" class="live-gen-num" type="number" ${valueAttrs(declaration)} value="${esc(parsed.max)}"></label>
        <label class="live-gen-field">period<input data-param-lfo="period" class="live-gen-num" type="number" min="0" step="any" value="${esc(parsed.period.amount)}"></label>
        <select data-param-lfo="period-unit" class="live-gen-unit" aria-label="period unit">${unitOptions(parsed.period.unit)}</select>
      </div>`;
    }
    // `from` is the fade's one optional argument, and "absent" is a real,
    // meaningful state — it means "start from wherever the parameter is". An
    // empty box could not say that out loud, so a latching box says it
    // (Bob, 2026-07-27): off = no from value, and the box goes inert.
    const fromEnabled = parsed.mode === "fade" && parsed.from != null;
    const from = parsed.mode === "fade" && parsed.segments.length === 1
      ? `<div class="live-gen-from">
          <label class="live-gen-field live-gen-field-inline">from<input data-param-from class="live-gen-num" type="number" ${valueAttrs(declaration)} value="${esc(parsed.from ?? "")}" ${fromEnabled ? "" : "disabled"}></label>
          <input type="checkbox" class="live-gen-check" data-param-from-enabled ${fromEnabled ? "checked" : ""} aria-label="start from an explicit value">
        </div>` : "";
    return `<div class="live-gen-body">
      ${waveDisplay(parsed, declaration, "", motion)}
      <div class="live-gen-side">
        ${actions}
        ${from}
        ${miniSlider("data-param-curve", "curve", parsed.curve || 0, -CURVE_LIMIT, CURVE_LIMIT, .05)}
      </div>
    </div>
    <div class="live-gen-segments" data-param-segments>
      ${parsed.segments.map((segment, index) => panelSegmentRow(segment, index, declaration, parsed.segments.length)).join("")}
    </div>
    <div class="live-gen-add-row"><button type="button" class="live-gen-add" data-add-param-segment>add segment</button></div>
    <p class="show-field-error show-param-loop-hint" ${parsed.mode === "loop" && parsed.segments.length < 2 ? "" : "hidden"}>loop needs at least two segments</p>`;
  }

  // The complete drawer face is shared. Hosts provide only routing attributes
  // and their momentary actions; tabs, shell and fields cannot drift apart.
  function drawer(declaration, parsed, {
    attributes = "",
    actions = "",
    motion = null,
    activeMode = parsed?.mode,
  } = {}) {
    const kind = DRAWER_KINDS.includes(parsed?.mode) ? parsed.mode : "lfo";
    const tabs = DRAWER_KINDS.map(item =>
      `<button type="button" data-gen-kind-tab="${item}" aria-pressed="${item === activeMode}">${DRAWER_LABELS[item]}</button>`).join("");
    return `<div class="live-param-gen" data-gen-kind="${esc(kind)}"${attributes ? ` ${attributes}` : ""}>
      <div class="live-param-gen-head">
        <span class="live-param-gen-tabs" role="group" aria-label="generator kind">${tabs}</span>
      </div>
      <div class="live-param-gen-fields">${panelFields(declaration, parsed, motion, actions)}</div>
      <output class="live-param-gen-error" aria-live="polite"></output>
    </div>`;
  }

  // Reads the fields under `root` back into §3.2 wire args. `mode` is passed in
  // rather than scraped from a fixed element id, because the Show inspector and
  // the control-surface drawer keep their own mode control.
  function compile(root, declaration, mode) {
    const type = wireType(declaration);
    if (mode === "value") {
      const input = root.querySelector("#show-param-value");
      return input ? [typedArg(type, input.value)] : null;
    }
    if (mode === "stop") return [typedArg("s", "stop")];
    if (mode === "lfo") {
      const minimum = inputNumber(root, '[data-param-lfo="min"]');
      const maximum = inputNumber(root, '[data-param-lfo="max"]');
      const periodAmount = inputNumber(root, '[data-param-lfo="period"]');
      const period = durationString(root, '[data-param-lfo="period"]', '[data-param-lfo="period-unit"]');
      const phase = inputNumber(root, '[data-param-lfo="phase"]');
      const curve = inputNumber(root, '[data-param-lfo="curve"]');
      if (minimum == null || maximum == null || periodAmount == null || periodAmount <= 0 || period == null
          || phase == null || phase < 0 || phase > 1 || curve == null) return null;
      const args = [
        typedArg("s", "lfo"), typedArg("s", root.querySelector('[data-param-lfo="shape"]')?.value || "sine"),
        typedArg(type, minimum), typedArg(type, maximum), typedArg("s", period),
      ];
      if (phase !== 0) args.push(typedArg("s", `p:${String(Number(phase))}`));
      if (root.querySelector('[data-param-lfo="free"]')?.checked) args.push(typedArg("s", "f"));
      if (curve !== 0) args.push(typedArg("s", `c:${String(Number(curve))}`));
      return args;
    }
    const rows = [...root.querySelectorAll("[data-param-segment]")];
    const hint = root.querySelector(".show-param-loop-hint");
    if (hint) hint.hidden = !(mode === "loop" && rows.length < 2);
    if (!rows.length || (mode === "loop" && rows.length < 2)) return null;
    const args = mode === "loop" ? [typedArg("s", "loop")] : [];
    if (mode === "fade" && rows.length === 1) {
      // The panel drawer states "no from value" with a latching box; the Show
      // inspector has no such box, and there an empty field still means absent.
      const enabled = root.querySelector("[data-param-from-enabled]");
      const from = root.querySelector("[data-param-from]")?.value.trim();
      if (from && (!enabled || enabled.checked)) args.push(typedArg(type, from));
    }
    for (const row of rows) {
      const value = row.querySelector("[data-param-segment-value]")?.value;
      const duration = durationString(row, "[data-param-segment-duration]", "[data-param-segment-unit]");
      if (value == null || duration == null) return null;
      args.push(typedArg(type, value), typedArg("s", duration));
    }
    const curve = inputNumber(root, "[data-param-curve]");
    if (curve == null) return null;
    if (curve !== 0) args.push(typedArg("s", `c:${String(Number(curve))}`));
    return args;
  }

  // A starting `parsed` shape for a kind the operator has just switched to, so
  // the drawer opens on usable fields instead of empty ones.
  function blank(declaration, mode) {
    const base = Number(declaration.default ?? declaration.min ?? 0);
    const span = Number(declaration.max ?? 1);
    const duration = {ms: 1000, amount: "1", unit: "s"};
    if (mode === "lfo") {
      return {mode, shape: "sine", min: Number(declaration.min ?? 0), max: span,
              period: {ms: 1000, amount: "1", unit: "s"}, phase: 0, free: false, curve: 0};
    }
    if (mode === "loop") {
      return {mode, curve: 0, segments: [
        {value: span, duration: {...duration}},
        {value: base, duration: {...duration}},
      ]};
    }
    if (mode === "fade") {
      return {mode, curve: 0, segments: [{value: span, duration: {...duration}}]};
    }
    if (mode === "stop") return {mode: "stop"};
    return {mode: "value", value: base};
  }

  window.ParamGenerator = {
    KINDS, SHAPES, fields, preview, compile, blank,
    segmentRow, unitOptions, valueAttrs, inputNumber, durationString,
    panelFields, panelSegmentRow, previewGeometry, waveTrace, drawer,
  };
})();
