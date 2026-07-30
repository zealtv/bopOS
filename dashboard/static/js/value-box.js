(function () {
  "use strict";

  // The app-wide numeric-entry primitive. Native number inputs keep their
  // existing handlers and accessibility, while this layer gives them one face
  // and makes the value observed by those handlers safe for the PD float wire.
  function round(value, integer) {
    if (integer) return Math.round(value);
    return Number(value.toPrecision(6));
  }

  function integerSpec(element, spec = {}) {
    if (spec.integer != null) return Boolean(spec.integer);
    if (element.dataset.integer != null) return element.dataset.integer !== "false";
    return element.step === "1";
  }

  function decorate(element, spec = {}) {
    if (!element) return element;
    element.classList.add("value-box");
    if (integerSpec(element, spec)) element.dataset.integer = "true";
    else delete element.dataset.integer;
    return element;
  }

  function normalize(input, spec = {}) {
    if (!input || input.value.trim() === "") return null;
    const previous = input.value;
    let value = Number(input.value);
    if (!Number.isFinite(value)) return null;
    const min = spec.min != null ? Number(spec.min)
      : input.min === "" ? null : Number(input.min);
    const max = spec.max != null ? Number(spec.max)
      : input.max === "" ? null : Number(input.max);
    if (min != null && Number.isFinite(min)) value = Math.max(min, value);
    if (max != null && Number.isFinite(max)) value = Math.min(max, value);
    value = round(value, integerSpec(input, spec));
    input.value = String(value);
    // Draft editors commonly mirror native `input` events into an in-memory
    // model. Re-emit only when normalization changed the spelling so that
    // model receives the same safe value later read by `change` handlers.
    if (input.value !== previous) {
      input.dispatchEvent(new Event("input", {bubbles: true}));
    }
    return value;
  }

  function decorateTree(root) {
    if (root?.matches?.('input[type="number"]')) decorate(root);
    root?.querySelectorAll?.('input[type="number"]').forEach(input => decorate(input));
  }

  // Capture runs before the call sites' existing `onchange` handlers, so they
  // read the clamped/rounded value without becoming coupled to this component.
  document.addEventListener("change", event => {
    const input = event.target;
    if (input?.matches?.('input[type="number"]')) normalize(input);
  }, true);

  const start = () => {
    decorateTree(document);
    new MutationObserver(records => records.forEach(record =>
      record.addedNodes.forEach(node => {
        if (node.nodeType === Node.ELEMENT_NODE) decorateTree(node);
      })
    )).observe(document.documentElement, {childList: true, subtree: true});
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, {once: true});
  } else start();

  window.ValueBox = Object.freeze({decorate, normalize, round});
}());
