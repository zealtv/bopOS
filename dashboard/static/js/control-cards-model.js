// Pure Control-card persistence and ordering helpers. Kept DOM-free so the
// migration and R3 order are durable browser-free tests rather than only a UI
// journey.
(function () {
  "use strict";

  function strings(value) {
    return Array.isArray(value)
      ? value.filter(item => typeof item === "string")
      : [];
  }

  function unique(values) {
    return [...new Set(values)];
  }

  function readTargets(storage, cardsKey, columnsKey, targetKey) {
    try {
      const stored = JSON.parse(storage.getItem(cardsKey));
      if (stored?.version === 1 && Array.isArray(stored.targets)) {
        return unique(strings(stored.targets));
      }
    } catch (_error) { /* try the migrations below */ }
    try {
      const columns = JSON.parse(storage.getItem(columnsKey));
      if (Array.isArray(columns) && columns.length) {
        return unique(columns.flatMap(column => strings(column?.target)));
      }
    } catch (_error) { /* try the older single-target key */ }
    try {
      const target = JSON.parse(storage.getItem(targetKey));
      if (Array.isArray(target)) return unique(strings(target));
    } catch (_error) { /* use the first-run default */ }
    return ["all"];
  }

  function rank(selector) {
    if (selector === "all") return [0, 0];
    if (/^g\d+$/.test(selector)) return [1, Number(selector.slice(1))];
    if (/^\d+$/.test(selector)) return [2, Number(selector)];
    return [3, String(selector)];
  }

  function compareSelectors(left, right) {
    const a = rank(left);
    const b = rank(right);
    return a[0] - b[0] || (typeof a[1] === "number"
      ? a[1] - b[1]
      : String(a[1]).localeCompare(String(b[1])));
  }

  window.ControlCardsModel = {strings, unique, readTargets, compareSelectors};
})();
