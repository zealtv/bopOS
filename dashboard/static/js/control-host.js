// The Control tab: N independently targeted columns
// (08-control-tab-columns/4-n-columns/1-columns-layout).
//
// It used to be an iframe of `/facilitator?embedded=1`. That cost a second
// websocket, a second copy of the fleet state, a document boundary every
// browser journey had to reach through, and — because the two documents could
// only talk via `localStorage` — a cross-document dance for the focus Seat.
// All four are gone (`3-iframe-retirement`), which is what let this file grow
// from mounting one column to mounting a row of them.
//
// This file is page wiring only: layout, persistence, the tab strip, and the
// fan-out of socket messages to every column. All column logic is
// `js/control-column.js`, which is the same component Remote mounts once.
//
// It runs AFTER `dashboard.js`, and deliberately reads that script's top-level
// `ws` and `installation` bindings rather than opening a socket of its own —
// one connection per document. Handler order follows registration order, so
// every handler here sees the state `dashboard.js` has already merged.
(function () {
  "use strict";

  const stage = document.querySelector("#control-column-host");
  if (!stage) return;

  // D9: ONE layout key, holding `{id, target, open}` per column in display
  // order. The ids are MINTED, never indices — indices renumber on remove, and
  // a stored record keyed by position silently re-points at whichever column
  // slid into the gap.
  const LAYOUT_KEY = "bopos.control.columns";
  // Migrated once into column 1, then left alone. Remote keeps its own key.
  const LEGACY_TARGET_KEY = "bopos.target.control";

  // The column's own freeze guard. `dashboard.js` has an `interacting` flag of
  // its own for the Device and Patch panels; sharing one would let a drag in
  // either surface suppress re-renders in the other. One flag covers the whole
  // row: a drag is in exactly one column, and freezing the others for the
  // duration of a pointer gesture costs nothing.
  let interacting = false;
  let minted = 0;
  const columns = [];

  function readLayout() {
    let stored = null;
    try { stored = JSON.parse(localStorage.getItem(LAYOUT_KEY)); }
    catch (_error) { stored = null; }
    const records = Array.isArray(stored)
      ? stored.filter(entry => entry && typeof entry.id === "string")
      : null;
    if (records && records.length) return records;
    // First run on this browser — or the first run after the tab became
    // N-column. An operator who had aimed the single column somewhere keeps
    // that aim as column 1 rather than being reset to All.
    let legacy = null;
    try { legacy = JSON.parse(localStorage.getItem(LEGACY_TARGET_KEY)); }
    catch (_error) { legacy = null; }
    const target = Array.isArray(legacy) &&
      legacy.every(entry => typeof entry === "string") ? legacy : ["all"];
    let open = false;
    try { open = localStorage.getItem(`${LEGACY_TARGET_KEY}.open`) === "true"; }
    catch (_error) { open = false; }
    return [{id: "c0", target, open}];
  }

  function writeLayout() {
    try {
      localStorage.setItem(LAYOUT_KEY, JSON.stringify(columns.map(column => ({
        id: column.id, target: column.target, open: column.open,
      }))));
    } catch (_error) { /* private mode: the layout just doesn't persist */ }
  }

  function mintId() {
    let id;
    do { id = `c${minted++}`; } while (columns.some(column => column.id === id));
    return id;
  }

  // At N=1 the ✕ is hidden rather than removed (see `setSole`), so adding a
  // second column does not shift the first column's picker sideways.
  function markSole() {
    columns.forEach(column => column.surface.setSole(columns.length === 1));
  }

  function mount(record, {focus = false} = {}) {
    const element = document.createElement("section");
    element.className = "control-column";
    stage.appendChild(element);
    const entry = {id: record.id, target: record.target, open: !!record.open};
    entry.surface = window.ControlColumn.create({
      host: element,
      // Minted, so two columns' pickers never share a `data-target-picker`
      // value. A target identifier is not an element identifier (gotcha 19).
      id: `control-${record.id}`,
      // No `storageKey`: the column's target and open state live in the ONE
      // layout record above, which is what D9 asks for and what stops a
      // second authority for the same fact appearing beside it.
      storageKey: null,
      initialTarget: Array.isArray(record.target) ? record.target : ["all"],
      // Closed by default (D4): an open picker costs ~180px of a 342px column,
      // times N, for a control set once. Its terse readout is the title.
      defaultOpen: !!record.open,
      onTargetChange: selection => { entry.target = selection; writeLayout(); },
      onOpenChange: open => { entry.open = open; writeLayout(); },
      onRemove: () => removeColumn(entry.id),
      // The desktop Control tab shows the WHOLE manifest; `dashboard: true`
      // gates only Remote (01-control-panel/1-full-manifest-visibility).
      full: true,
      getState: () => installation,
      isInteracting: () => interacting,
      setInteracting: editing => { interacting = editing; },
      send: ({scope, id, name, value}) => {
        const payload = {scope, name, value};
        if (id != null) payload.id = Number(id);
        ws.send("set_live_param", payload);
      },
      // Returns the lead so the row's fire button sweeps for exactly as long as
      // the event is actually scheduled for (04-event-fire-affordance).
      sendEvent: ({scope, id, identity, elements}) => {
        const selector = scope === "all"
          ? "all"
          : scope === "group" ? `g${id}` : String(id);
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
      // D8's replacement for the per-card `Device setup` disclosure: the
      // Devices tab owns device lifecycle, so the card hands off to it the way
      // `07`'s "Set patch…" hands off to Patches. `select` and `activateTab`
      // are `dashboard.js`'s own top-level functions, which this file already
      // shares a scope with.
      openDevice: uid => {
        if (!installation.devices?.[uid]) return;
        select(uid);
        activateTab("devices");
      },
    });
    columns.push(entry);
    makeDraggable(entry);
    markSole();
    if (focus) entry.surface.focus();
    return entry;
  }

  // Drag to reorder, from the grip only. The column is what drags, but it is
  // only `draggable` while the pointer is on its grip — a draggable column
  // would make every fader inside it a drag handle, and a fader that starts a
  // drag instead of moving is a control that stopped working.
  let dragging = null;
  function makeDraggable(entry) {
    const {element, grip} = entry.surface;
    if (!grip) return;
    grip.onpointerdown = () => { element.draggable = true; };
    element.ondragstart = event => {
      dragging = entry;
      event.dataTransfer.effectAllowed = "move";
      // Firefox will not start a drag without data on the transfer.
      event.dataTransfer.setData("text/plain", entry.id);
    };
    element.ondragend = () => {
      element.draggable = false;
      dragging = null;
      writeLayout();
    };
    element.ondragover = event => {
      if (!dragging || dragging === entry) return;
      event.preventDefault();
      const box = element.getBoundingClientRect();
      const before = event.clientX < box.left + box.width / 2;
      const from = columns.indexOf(dragging);
      if (from < 0 || columns.indexOf(entry) < 0) return;
      // Move in the DOM and in the ordered list together, so the stored order
      // is what the operator sees rather than a second model of it.
      stage.insertBefore(dragging.surface.element,
                         before ? element : element.nextSibling);
      columns.splice(from, 1);
      columns.splice(columns.indexOf(entry) + (before ? 0 : 1), 0, dragging);
    };
    element.ondrop = event => event.preventDefault();
  }

  function addColumn(target) {
    const entry = mount({id: mintId(), target: target || ["all"], open: !target},
                        {focus: true});
    // Rendered here and NOT in `mount`, because the columns restored on load
    // are mounted before the first `state` message arrives. Rendering then
    // would prune every stored target against an empty venue and — correctly,
    // per D5 — leave every restored column reading "no longer in this venue".
    // A column added by hand is added long after the venue is known.
    entry.surface.render();
    writeLayout();
    return entry;
  }

  function removeColumn(id) {
    // Minimum one. The ✕ is hidden at N=1 rather than removed, so this is a
    // belt-and-braces guard for a keyboard or scripted activation.
    if (columns.length <= 1) return;
    const index = columns.findIndex(column => column.id === id);
    if (index < 0) return;
    columns[index].surface.destroy();
    columns.splice(index, 1);
    markSole();
    writeLayout();
    document.querySelector("#control-add-column")?.focus();
  }

  readLayout().forEach(record => mount({
    id: typeof record.id === "string" ? record.id : mintId(),
    target: record.target,
    open: record.open,
  }));
  // Ids restored from storage may collide with what `mintId` would produce, so
  // start minting past the highest one we already hold.
  minted = columns.reduce((high, column) => {
    const number = Number(String(column.id).replace(/^c/, ""));
    return Number.isInteger(number) ? Math.max(high, number + 1) : high;
  }, minted);
  writeLayout();

  const addButton = document.querySelector("#control-add-column");
  if (addButton) addButton.onclick = () => addColumn();

  // The Seats → Control workflow, explicit at last. D7 (Bob, 2026-07-31)
  // retired the ambient focus-Seat follow at every N: one click on the Seats
  // tab used to re-aim the Control surface and PERSIST it, which with N
  // columns would destroy an arrangement durably and with no undo. This is the
  // replacement — focus a column already showing that Seat, else append one.
  window.ControlHost = {
    openSeat(seatId) {
      const selector = String(seatId);
      const existing = columns.find(column =>
        column.surface.target().includes(selector));
      if (existing) existing.surface.focus();
      else addColumn([selector]);
    },
    columnCount: () => columns.length,
  };

  // A restored column must not render before the first `state` — it would
  // prune every stored target against an empty venue, and D5 would then
  // correctly report them all lost. `1-columns-layout` knew that and kept
  // `mount` from rendering; what it missed is that a `device_update` heartbeat
  // can beat the initial `state` to the socket and render one anyway. The
  // prune PERSISTS (`target-picker.js` resolve → persist), so that race did not
  // just look wrong for a moment — it erased the operator's stored layout for
  // good. Found by this thread's own `3-chrome-demotions/shoot.py`, which could
  // not reproduce its own three columns twice running.
  let venueKnown = false;
  const renderAll = () => {
    if (!venueKnown) return;
    columns.forEach(column => column.surface.render());
  };
  ws.on("state", data => {
    venueKnown = true;
    columns.forEach(column => column.surface.refresh(data));
  });
  ws.on("device_update", renderAll);
  ws.on("params_declaration", renderAll);
  ws.on("device_offline", renderAll);
  // A capture preview belongs to whichever surface asked for it: a column
  // claims it only when its own request is outstanding, and says so, which is
  // what leaves the Device panel's and the editor's requests — and every other
  // column's — alone.
  ws.on("preset_capture_preview", data =>
    columns.some(column => column.surface.acceptCapturePreview(data)));
  ws.on("preset_saved", data =>
    columns.forEach(column => column.surface.reportPresetSaved(data)));
  ws.on("preset_applied", data =>
    columns.forEach(column => column.surface.reportPresetApplied(data)));
  ws.on("event_scheduled", data =>
    columns.forEach(column => column.surface.reportEventScheduled(data)));

  document.addEventListener("pointerdown", event => {
    if (!stage.contains(event.target)) return;
    if (event.target.matches(
      'input[type="range"], button.live-toggle[data-live-param], select.live-enum[data-live-param]',
    )) interacting = true;
  });
  document.addEventListener("pointerup", () => {
    if (!interacting) return;
    // Click/change follows pointerup. Keep the columns frozen through that
    // event so a heartbeat cannot replace the control before its handler fires.
    setTimeout(() => {
      interacting = false;
      columns.forEach(column => column.surface.render());
    }, 0);
  });
})();
