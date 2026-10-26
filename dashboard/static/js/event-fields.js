// Typed event fields on the fire side (contract v1.22, proposal §5). An event
// declares `fields`, each a param declaration without path/dashboard, and every
// place that fires an event — the control surface and the Show message
// editor — offers one control per field. This module owns that control so the
// two hosts cannot drift: the kind picks the control (a number box, the PD
// toggle box, an enum select, a text box), the field name labels it, and the
// declared default prefills it.
(function () {
  "use strict";

  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const MAX_TEXT = 255;
  const OSC_TAG = {float: "f", int: "i", toggle: "i", enum: "i", text: "s"};

  const fieldsOf = declaration => Array.isArray(declaration?.fields) ? declaration.fields : [];
  const tag = field => OSC_TAG[field?.kind] || "f";

  // What a field shows before anyone edits it: its default, else the lowest
  // value it accepts, else empty text (which a required text field makes the
  // operator replace before firing).
  function initialValue(field) {
    if (field.default != null) return field.default;
    if (field.kind === "text") return "";
    return Number.isFinite(Number(field.min)) ? Number(field.min) : 0;
  }

  // Wire limits for text: printable ASCII, no whitespace, 1–255 characters.
  const textValid = value => typeof value === "string" && value.length >= 1 && value.length <= MAX_TEXT
    && /^[\x21-\x7e]+$/.test(value);

  // One field's value from its raw control reading; null when the wire would
  // refuse it (so the caller can mark the control and hold the fire).
  function parse(field, raw) {
    if (field.kind === "text") return textValid(raw) ? raw : null;
    if (raw === "" || raw == null) return null;
    const number = Number(raw);
    if (!Number.isFinite(number)) return null;
    if (field.kind !== "float" && !Number.isInteger(number)) return null;
    if (Number.isFinite(Number(field.min)) && number < Number(field.min)) return null;
    if (Number.isFinite(Number(field.max)) && number > Number(field.max)) return null;
    return number;
  }

  // The control for field `index`. `value` overrides the default (a Show
  // message keeps what its author typed); `attr` is the host's marker
  // attribute, which also carries the index; `off` is " disabled" or "".
  function controlHtml(field, index, value, {attr, off = "", inputClass = "", invalid = false}) {
    const shown = value == null ? initialValue(field) : value;
    const label = esc(field.name);
    const mark = `${attr}="${index}" data-field-kind="${esc(field.kind)}" aria-label="${label}"${invalid ? ' aria-invalid="true"' : ""}`;
    const klass = inputClass ? ` class="${inputClass}"` : "";
    let control;
    if (field.kind === "toggle") {
      const on = Number(shown) === 1;
      control = `<button type="button" class="live-toggle" ${mark} aria-pressed="${on}"${off}><span aria-hidden="true">${on ? "✕" : ""}</span></button>`;
    } else if (field.kind === "enum") {
      const options = (field.options || []).map((name, at) =>
        `<option value="${at}"${Number(shown) === at ? " selected" : ""}>${esc(name)}</option>`).join("");
      control = `<select class="live-enum" ${mark}${off}>${options}</select>`;
    } else if (field.kind === "text") {
      control = `<input${klass} type="text" ${mark} maxlength="${MAX_TEXT}" autocomplete="off" spellcheck="false" value="${esc(shown)}"${off}>`;
    } else {
      const bounds = (Number.isFinite(Number(field.min)) ? ` min="${esc(field.min)}"` : "")
        + (Number.isFinite(Number(field.max)) ? ` max="${esc(field.max)}"` : "");
      control = `<input${klass} type="number" ${mark} step="${field.kind === "int" ? 1 : "any"}"${bounds} value="${esc(shown)}"${off}>`;
    }
    return control;
  }

  // The raw reading of a control built by controlHtml.
  function read(control) {
    if (control.tagName === "BUTTON") return control.getAttribute("aria-pressed") === "true" ? 1 : 0;
    return control.value;
  }

  // Flip a toggle button the way a click should; true when `control` was one.
  function flip(control) {
    if (control.tagName !== "BUTTON" || control.dataset.fieldKind !== "toggle") return false;
    const on = control.getAttribute("aria-pressed") !== "true";
    control.setAttribute("aria-pressed", String(on));
    control.firstElementChild.textContent = on ? "✕" : "";
    return true;
  }

  // Every field's value from `controls` (in field order), or null with the
  // offending controls marked aria-invalid when any would be refused.
  function collect(fields, controls) {
    const values = [];
    let ok = true;
    fields.forEach((field, index) => {
      const control = controls[index];
      const value = control ? parse(field, read(control)) : null;
      if (control) control.setAttribute("aria-invalid", String(value === null));
      if (value === null) ok = false;
      values.push(value);
    });
    return ok ? values : null;
  }

  window.EventFields = {fieldsOf, tag, initialValue, parse, controlHtml, read, flip, collect, textValid};
})();
