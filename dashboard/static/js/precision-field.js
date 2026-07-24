(function () {
  "use strict";

  // Click-to-type exact numeric entry layered onto a slider's <output> readout
  // (40-precision-param-input). Sliders are a gesture tool; sequencing and
  // deliberate composition need exact numbers. The <output> shows the value;
  // clicking it (or focusing and pressing Enter/Space) swaps in a <number>
  // field. On commit the typed value is clamped to the control's min/max and
  // rounded to the precision the wire actually carries — integers for an
  // integer control, otherwise 6 significant figures (PD OSC floats are 32-bit;
  // the house =<6-significant-figures rule forbids implying more). The rounded
  // value is handed to commit(value); the caller sends it and syncs the slider.
  //
  // The helper is deliberately decoupled from the <input type="range"> element:
  // callers pass a plain spec, so a control shown in different units than it
  // sends (the master %, say) can drive the field in display units and convert
  // inside commit.

  function round(value, integer) {
    if (integer) return Math.round(value);
    // toPrecision(6) then back through Number drops trailing zeros and keeps at
    // most six significant figures.
    return Number(value.toPrecision(6));
  }

  // output: the <output> readout to make editable.
  // spec:   {min, max, integer, value, label, disabled}. min/max may be null.
  // commit: (roundedValue) => void. Called only on a committing keypress/blur.
  // guard:  optional (editing:boolean) => void. Lets the caller suppress a
  //         re-render while the field is live so a heartbeat cannot clobber it.
  function attach(output, spec, commit, guard) {
    if (!output || output.dataset.preciseBound === "true") return;
    output.dataset.preciseBound = "true";
    output.tabIndex = 0;
    output.setAttribute("role", "button");
    output.title = "Click to type an exact value";
    output.classList.add("precise-output");

    const open = () => {
      if (spec.disabled || output.dataset.editing === "true") return;
      output.dataset.editing = "true";
      if (guard) guard(true);
      const field = document.createElement("input");
      field.type = "number";
      field.className = "precise-input";
      if (spec.min != null) field.min = String(spec.min);
      if (spec.max != null) field.max = String(spec.max);
      field.step = spec.integer ? "1" : "any";
      field.value = String(spec.value);
      field.setAttribute("aria-label", `${spec.label || "value"}, exact value`);
      output.replaceWith(field);
      field.focus();
      field.select();

      let settled = false;
      const close = (save) => {
        if (settled) return;
        settled = true;
        if (save && field.value.trim() !== "") {
          let value = Number(field.value);
          if (Number.isFinite(value)) {
            if (spec.min != null) value = Math.max(spec.min, value);
            if (spec.max != null) value = Math.min(spec.max, value);
            value = round(value, spec.integer);
            output.value = value;
            commit(value);
          }
        }
        output.dataset.editing = "false";
        if (field.isConnected) field.replaceWith(output);
        if (guard) guard(false);
      };

      field.onkeydown = (event) => {
        if (event.key === "Enter") { event.preventDefault(); close(true); }
        else if (event.key === "Escape") { event.preventDefault(); close(false); }
      };
      field.onblur = () => close(true);
    };

    output.onclick = open;
    output.onkeydown = (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); open(); }
    };
  }

  window.PrecisionField = Object.freeze({attach, round});
}());
