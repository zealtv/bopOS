// The Control tab hosts ControlColumn in the dashboard document
// (08-control-tab-columns/3-iframe-retirement).
//
// It used to be an iframe of `/facilitator?embedded=1`. That cost a second
// websocket, a second copy of the fleet state, a document boundary every
// browser journey had to reach through, and — because the two documents could
// only talk via `localStorage` — a cross-document dance for the focus Seat.
// All four are gone. This file is the dashboard's half of what
// `js/facilitator.js` is for Remote: page wiring, no column logic.
//
// It runs AFTER `dashboard.js`, and deliberately reads that script's top-level
// `ws` and `installation` bindings rather than opening a socket of its own —
// one connection per document. Handler order follows registration order, so
// every handler here sees the state `dashboard.js` has already merged.
(function () {
  "use strict";

  const host = document.querySelector("#control-column-host");
  if (!host) return;

  // The column's own freeze guard. `dashboard.js` has an `interacting` flag of
  // its own for the Device and Patch panels; sharing one would let a drag in
  // either surface suppress re-renders in the other.
  let interacting = false;

  const column = window.ControlColumn.create({
    host,
    id: "control",
    storageKey: "bopos.target.control",
    // The desktop Control tab shows the WHOLE manifest; `dashboard: true` gates
    // only Remote (01-control-panel/1-full-manifest-visibility). Presets and
    // capture-as-Show-step are desktop affordances for the same reason.
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
    requestShowCapturePreview: payload =>
      ws.send("preview_show_preset_capture", payload),
    captureShowStep: ({scope, id}) =>
      ws.send("capture_show_preset_step", {scope, id}),
    sendCommand: payload => ws.send("action", payload),
  });

  // `ws.on` appends, so these sit beside `dashboard.js`'s handlers for the same
  // messages rather than replacing them — the same arrangement the two
  // documents had, minus the second socket.
  ws.on("state", data => column.refresh(data));
  ws.on("device_update", () => column.render());
  ws.on("params_declaration", () => column.render());
  ws.on("device_offline", () => column.render());
  // A capture preview belongs to whichever surface asked for it: the column
  // claims it only when its own request is outstanding, and says so, which is
  // what leaves the Device panel's and the editor's requests alone.
  ws.on("preset_capture_preview", data => column.acceptCapturePreview(data));
  ws.on("preset_saved", data => column.reportPresetSaved(data));
  ws.on("preset_applied", data => column.reportPresetApplied(data));
  ws.on("show_preset_capture_preview", data =>
    column.handleShowCapturePreview(data));
  ws.on("event_scheduled", data => column.reportEventScheduled(data));

  document.addEventListener("pointerdown", event => {
    if (!host.contains(event.target)) return;
    if (event.target.matches(
      'input[type="range"], button.live-toggle[data-live-param], select.live-enum[data-live-param]',
    )) interacting = true;
  });
  document.addEventListener("pointerup", () => {
    if (!interacting) return;
    // Click/change follows pointerup. Keep the column frozen through that event
    // so a heartbeat cannot replace the control before its handler fires.
    setTimeout(() => {
      interacting = false;
      column.render();
    }, 0);
  });
})();
