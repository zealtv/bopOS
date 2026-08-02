// The desktop Control tab: one independently targetable card per persisted
// selector. Card membership is authored; card order is always derived from the
// venue (All, groups, Seats) and is never persisted.
(function () {
  "use strict";

  const stage = document.querySelector("#control-column-host");
  if (!stage) return;

  const CARDS_KEY = "bopos.control.cards";
  const LEGACY_LAYOUT_KEY = "bopos.control.columns";
  const LEGACY_TARGET_KEY = "bopos.target.control";
  const cards = [];
  let interacting = false;
  let venueKnown = false;
  let runtimeId = 0;

  function strings(value) {
    return Array.isArray(value)
      ? value.filter(item => typeof item === "string")
      : [];
  }

  function unique(values) {
    return [...new Set(values)];
  }

  function readTargets() {
    try {
      const stored = JSON.parse(localStorage.getItem(CARDS_KEY));
      if (stored?.version === 1 && Array.isArray(stored.targets)) {
        return unique(strings(stored.targets));
      }
    } catch (_error) { /* try the migrations below */ }

    try {
      const columns = JSON.parse(localStorage.getItem(LEGACY_LAYOUT_KEY));
      if (Array.isArray(columns) && columns.length) {
        return unique(columns.flatMap(column => strings(column?.target)));
      }
    } catch (_error) { /* try the older single-target key */ }

    try {
      const target = JSON.parse(localStorage.getItem(LEGACY_TARGET_KEY));
      if (Array.isArray(target)) return unique(strings(target));
    } catch (_error) { /* use the first-run default */ }
    return ["all"];
  }

  function committedTargets() {
    return cards.flatMap(card => card.draft ? [] : card.target.slice(0, 1));
  }

  function writeTargets() {
    try {
      localStorage.setItem(CARDS_KEY, JSON.stringify({
        version: 1,
        targets: committedTargets(),
      }));
      localStorage.removeItem(LEGACY_LAYOUT_KEY);
    } catch (_error) { /* private mode: membership remains session-only */ }
  }

  function rank(selector) {
    if (selector === "all") return [0, 0];
    if (/^g\d+$/.test(selector)) return [1, Number(selector.slice(1))];
    if (/^\d+$/.test(selector)) return [2, Number(selector)];
    return [3, String(selector)];
  }

  function compare(left, right) {
    if (left.draft !== right.draft) return left.draft ? 1 : -1;
    const a = rank(left.target[0]);
    const b = rank(right.target[0]);
    return a[0] - b[0] || (typeof a[1] === "number"
      ? a[1] - b[1]
      : String(a[1]).localeCompare(String(b[1])));
  }

  function sortCards() {
    cards.sort(compare);
    cards.forEach(card => stage.appendChild(card.surface.element));
  }

  function targetsExcept(entry) {
    return new Set(cards.flatMap(card =>
      card === entry || card.draft ? [] : card.target.slice(0, 1)));
  }

  function mount(target, {draft = false, focus = false} = {}) {
    const element = document.createElement("section");
    element.className = "control-column";
    stage.appendChild(element);
    const entry = {
      id: `card-${runtimeId++}`,
      target: strings(target).slice(0, 1),
      draft,
      surface: null,
    };
    entry.surface = window.ControlColumn.create({
      host: element,
      id: `control-${entry.id}`,
      storageKey: null,
      initialTarget: entry.target,
      defaultOpen: draft,
      singleTarget: true,
      unavailableTargets: () => targetsExcept(entry),
      onTargetChange: selection => {
        const next = strings(selection).slice(0, 1);
        if (next[0] && targetsExcept(entry).has(next[0])) {
          entry.surface.setTarget(entry.target);
          return;
        }
        entry.target = next;
        if (next.length) entry.draft = false;
        sortCards();
        writeTargets();
        if (venueKnown) cards.forEach(card => card.surface.render());
      },
      onRemove: () => removeCard(entry),
      capabilities: {
        fullManifest: true,
        presetMenu: true,
        targetPicker: true,
        deriveAllTargets: false,
        deviceCommands: false,
        deviceHandoff: true,
        groupSlot: groupId => visibleGroups.indexOf(Number(groupId)),
      },
      getState: () => installation,
      isInteracting: () => interacting,
      setInteracting: editing => { interacting = editing; },
      send: ({scope, id, name, value}) => {
        const payload = {scope, name, value};
        if (id != null) payload.id = Number(id);
        ws.send("set_live_param", payload);
      },
      sendEvent: ({scope, id, identity, elements}) => {
        const selector = scope === "all"
          ? "all" : scope === "group" ? `g${id}` : String(id);
        const leadMs = Math.min(
          10000,
          Math.max(0, Number(installation.event_lead_ms ?? 500) || 0),
        );
        ws.send("fire_event", {selector, identity, elements, lead_ms: leadMs});
        return leadMs;
      },
      sendAutomation: ({scope, id, name, args}) => {
        const payload = {scope, name, args};
        if (id != null) payload.id = Number(id);
        ws.send("set_live_automation", payload);
      },
      replay: payload => ws.send("replay_live_params", payload),
      applyPreset: ({scope, id, patch, name}) => {
        const payload = {scope, patch, name};
        if (id != null) payload.id = Number(id);
        ws.send("apply_preset", payload);
      },
      savePreset: ({scope, id, patch, name, include, revision}) => {
        const payload = {scope, patch, name, include};
        if (id != null) payload.id = Number(id);
        if (revision) payload.revision = revision;
        ws.send("save_patch_preset", payload);
      },
      deletePreset: ({patch, slug, revision}) =>
        ws.send("delete_patch_preset", {patch, slug, revision}),
      requestCapturePreview: ({scope, id, patch}) => {
        const payload = {scope, patch};
        if (id != null) payload.id = Number(id);
        ws.send("preview_preset_capture", payload);
      },
      sendCommand: payload => ws.send("action", payload),
      openDevice: uid => {
        if (!installation.devices?.[uid]) return;
        select(uid);
        activateTab("devices");
      },
    });
    cards.push(entry);
    sortCards();
    if (venueKnown) cards.forEach(card => card.surface.render());
    if (focus) entry.surface.focus();
    return entry;
  }

  function removeCard(entry) {
    const index = cards.indexOf(entry);
    if (index < 0) return;
    entry.surface.destroy();
    cards.splice(index, 1);
    writeTargets();
    if (venueKnown) cards.forEach(card => card.surface.render());
    document.querySelector("#control-add-column")?.focus();
  }

  function addDraft() {
    const existing = cards.find(card => card.draft);
    if (existing) {
      existing.surface.focus();
      existing.surface.revealTarget();
      return existing;
    }
    return mount([], {draft: true, focus: true});
  }

  function validTargets() {
    const valid = new Set(["all"]);
    Object.values(installation.groups || {}).forEach(group =>
      valid.add(`g${group.id}`));
    Object.values(installation.seats || {}).forEach(seat =>
      valid.add(String(seat.id)));
    return valid;
  }

  function pruneAndRefresh(data) {
    venueKnown = true;
    const valid = validTargets();
    for (const entry of cards.slice()) {
      if (!entry.draft && !valid.has(entry.target[0])) removeCard(entry);
    }
    cards.forEach(card => card.surface.refresh(data));
    sortCards();
    writeTargets();
  }

  readTargets().forEach(target => mount([target]));
  writeTargets();
  const addButton = document.querySelector("#control-add-column");
  if (addButton) addButton.onclick = addDraft;

  window.ControlHost = {
    openSeat(seatId) {
      const selector = String(seatId);
      const existing = cards.find(card => card.target[0] === selector);
      if (existing) existing.surface.focus();
      else mount([selector], {focus: true});
    },
    columnCount: () => cards.length,
  };

  const renderAll = () => {
    if (!venueKnown) return;
    cards.forEach(card => card.surface.render());
  };
  ws.on("state", pruneAndRefresh);
  ws.on("device_update", renderAll);
  ws.on("params_declaration", renderAll);
  ws.on("device_offline", renderAll);
  ws.on("preset_capture_preview", data =>
    cards.some(card => card.surface.acceptCapturePreview(data)));
  ws.on("preset_saved", data =>
    cards.forEach(card => card.surface.reportPresetSaved(data)));
  ws.on("preset_applied", data =>
    cards.forEach(card => card.surface.reportPresetApplied(data)));
  ws.on("event_scheduled", data =>
    cards.forEach(card => card.surface.reportEventScheduled(data)));
  window.addEventListener("group-slots-change", renderAll);

  document.addEventListener("pointerdown", event => {
    if (!stage.contains(event.target)) return;
    if (event.target.matches(
      'input[type="range"], button.live-toggle[data-live-param], select.live-enum[data-live-param]',
    )) interacting = true;
  });
  document.addEventListener("pointerup", () => {
    if (!interacting) return;
    setTimeout(() => {
      interacting = false;
      cards.forEach(card => card.surface.render());
    }, 0);
  });
})();
