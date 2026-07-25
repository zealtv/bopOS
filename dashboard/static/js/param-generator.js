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
  const SHAPES = ["sine", "tri", "saw", "square", "sh", "drift"];
  const UNITS = ["ms", "s", "m", "h"];

  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const typedArg = (kind, value) => window.OscMessage.typedArg(kind, value);

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
    return `step="${declaration.type === "i" ? "1" : "any"}" ${declaration.min != null ? `min="${esc(declaration.min)}"` : ""} ${declaration.max != null ? `max="${esc(declaration.max)}"` : ""}`;
  }

  function segmentRow(segment, index, declaration, count) {
    return `<div class="show-param-segment" data-param-segment="${index}">
      <label>destination <input data-param-segment-value type="number" ${valueAttrs(declaration)} value="${esc(segment.value)}"></label>
      <label>duration <span class="show-param-duration"><input data-param-segment-duration type="number" min="0" step="any" value="${esc(segment.duration.amount)}"><select data-param-segment-unit>${unitOptions(segment.duration.unit)}</select></span></label>
      <button type="button" class="danger" data-remove-param-segment aria-label="Remove segment" ${count <= 1 ? "disabled" : ""}>Remove</button>
    </div>`;
  }

  function fields(declaration, parsed) {
    if (declaration.type === "s") {
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

  function preview(parsed, declaration) {
    if (!["fade", "loop", "lfo"].includes(parsed.mode)) return "";
    if (parsed.mode === "lfo" && ["sh", "drift"].includes(parsed.shape)) {
      return '<p class="show-param-preview-random" data-param-preview-random>random — not previewable</p>';
    }
    const points = [];
    if (parsed.mode === "lfo") {
      const count = 64;
      for (let index = 0; index <= count; index += 1) {
        const time = index / count * 2;
        points.push([time, window.ParamSpec.shapeFraction(parsed.shape, time + parsed.phase, parsed.curve)]);
      }
    } else {
      const cycles = parsed.mode === "loop" ? 2 : 1;
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
    if (!points.length) return "";
    const values = points.map(point => point[1]);
    let low = parsed.mode === "lfo" ? 0 : Number(declaration.min ?? Math.min(...values));
    let high = parsed.mode === "lfo" ? 1 : Number(declaration.max ?? Math.max(...values));
    if (!Number.isFinite(low)) low = Math.min(...values);
    if (!Number.isFinite(high)) high = Math.max(...values);
    if (high === low) high = low + 1;
    const maxTime = Math.max(...points.map(point => point[0]), 1);
    const path = points.map(([time, value], index) => {
      const x = 8 + time / maxTime * 224;
      const y = 64 - (value - low) / (high - low) * 56;
      return `${index ? "L" : "M"}${x.toFixed(2)} ${Math.min(64, Math.max(8, y)).toFixed(2)}`;
    }).join(" ");
    const label = parsed.mode === "lfo" ? `${parsed.shape} LFO preview` : `${parsed.mode} preview`;
    return `<figure class="show-param-preview" data-param-preview><figcaption>${esc(label)} · value / time</figcaption><svg viewBox="0 0 240 72" role="img" aria-label="${esc(label)}"><path class="show-param-preview-axis" d="M8 8V64H232"></path><path class="show-param-preview-line" d="${path}"></path></svg></figure>`;
  }

  // Reads the fields under `root` back into §3.2 wire args. `mode` is passed in
  // rather than scraped from a fixed element id, because the Show inspector and
  // the control-surface drawer keep their own mode control.
  function compile(root, declaration, mode) {
    const type = declaration.type || "f";
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
      const from = root.querySelector("[data-param-from]")?.value.trim();
      if (from) args.push(typedArg(type, from));
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
  };
})();
