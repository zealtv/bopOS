// Shared identity palette and the desktop Seats map's current four slot
// assignments. The assignment is presentation state, not venue/group data;
// localStorage only lets the sibling Remote document observe the same view.
(function () {
  "use strict";

  const key = "bopos.group.slots";
  const palette = [
    {colour: "#56B4E9", pattern: "solid"},
    {colour: "#E69F00", pattern: "dash"},
    {colour: "#00B98B", pattern: "dot"},
    {colour: "#CC79A7", pattern: "dash-dot"},
  ];
  palette.forEach((slot, index) =>
    document.documentElement.style.setProperty(
      `--group-slot-${index + 1}`, slot.colour));

  function normalise(value) {
    return Array.from({length: 4}, (_item, index) => {
      const id = value?.[index];
      return id == null || !Number.isInteger(Number(id)) ? null : Number(id);
    });
  }

  function read() {
    try { return normalise(JSON.parse(localStorage.getItem(key))); }
    catch (_error) { return normalise([]); }
  }

  function write(value) {
    const next = normalise(value);
    if (JSON.stringify(read()) === JSON.stringify(next)) return;
    try { localStorage.setItem(key, JSON.stringify(next)); }
    catch (_error) { /* identity falls back to neutral in private mode */ }
    window.dispatchEvent(new CustomEvent("group-slots-change", {detail: next}));
  }

  function indexOf(groupId, value = read()) {
    return normalise(value).indexOf(Number(groupId));
  }

  window.GroupSlots = {key, palette, read, write, indexOf};
})();
