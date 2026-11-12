// Shared group identity palette. A group's visual slot is its position in the
// numerically sorted venue roster, modulo the four Seats-map treatments. That
// is the same rule TargetPicker uses and does not depend on map visibility.
(function () {
  "use strict";

  const palette = [
    {colour: "#56B4E9", pattern: "solid"},
    {colour: "#E69F00", pattern: "dash"},
    {colour: "#00B98B", pattern: "dot"},
    {colour: "#CC79A7", pattern: "dash-dot"},
  ];
  palette.forEach((slot, index) =>
    document.documentElement.style.setProperty(
      `--group-slot-${index + 1}`, slot.colour));

  function forGroup(groupId, groups = []) {
    const wanted = Number(groupId);
    const index = Array.from(groups)
      .map(group => Number(group?.id))
      .filter(Number.isInteger)
      .sort((left, right) => left - right)
      .indexOf(wanted);
    return index < 0 ? -1 : index % palette.length;
  }

  window.GroupSlots = {palette, forGroup};
})();
