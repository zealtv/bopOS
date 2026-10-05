// Start the socket after the area scripts have initialized their components.
// A state snapshot may render immediately, including on a fast local connection.
const ws = new BopSocket("/ws");

ws.on("connection", (connected) => {
  $("#ws-status").textContent = connected ? "connected" : "disconnected";
  $("#ws-status").className = connected ? "online" : "offline";
});
ws.on("state", (data) => {
  if (installation.project && installation.project !== data.project) {
    selected = null;
    selectedSeat = null;
    selectedGroup = null;
    focusedGroup = null;
    visibleGroups = [null, null, null, null];
    seatBindingDrafts.clear();
    logDestinationDrafts.clear();
    editorPatchChoice = null;
    manifestDraft = null;
    manifestBaseline = null;
    manifestDirty = false;
    manifestFeedback = "";
    remoteCommandDraft = null;
    remoteCommandSaving = false;
    remoteCommandFeedback = "";
    pendingCreatedPatch = null;
  }
  installation = data;
  muted = !!data.muted;
  master = Number(data.master ?? 1);
  reconcileSelection();
  reconcileGroupView();
  render();
  const loading = $("#initial-loading");
  if (loading) loading.hidden = true;
});
ws.on("device_update", (data) => {
  if (data && data.devices) installation = data;
  else mergeDevice(data);
});
ws.on("heartbeat", (data) => {
  if (!data?.uid) return;
  const heartbeatAt = String(data.timestamp ?? Date.now() / 1000);
  heartbeats.set(data.uid, heartbeatAt);
  const row = Array.from(document.querySelectorAll(".device-row")).find((element) => element.dataset.uid === data.uid);
  const blip = row?.querySelector(".heartbeat-blip");
  if (!blip) return;
  blip.classList.remove("pulse");
  void blip.offsetWidth;
  blip.classList.add("pulse");
  blip.dataset.heartbeatAt = heartbeatAt;
});
ws.on("params_declaration", mergeDevice);
ws.on("report", mergeDevice);
ws.on("rev", mergeDevice);
ws.on("patches", mergeDevice);
ws.on("assets", mergeDevice);
ws.on("distribution", (data) => {
  distribution = data || { assets: [], patches: [] };
  render();
});
ws.on("manifest_saved", (data) => {
  const patch = data?.patch || editorPatchChoice;
  const declarations = data?.declarations || data?.params || [];
  if (patch && patch === editorPatchChoice) {
    manifestDraft = {
      patch,
      params: structuredClone(declarations),
      events: structuredClone(data.events || []),
      io_modules: structuredClone(data.io_modules || []),
    };
    manifestBaseline = structuredClone(manifestDraft);
    manifestDirty = false;
  }
  if (installation.editor && installation.editor.patch === patch) {
    installation.editor.declarations = structuredClone(declarations);
    installation.editor.events = structuredClone(data.events || []);
    installation.editor.io_modules = structuredClone(data.io_modules || []);
  }
  const warnings = (data?.warnings || [data?.pd_receive_warning]).filter(Boolean);
  manifestFeedback = warnings.length
    ? `Saved with warning: ${warnings.join(" ")}`
    : "Manifest saved. Live controls refreshed; the engine was not restarted.";
  render();
});
ws.on("patch_created", (data) => {
  if (data?.patch) pendingCreatedPatch = data.patch;
  manifestDraft = null;
  manifestBaseline = null;
  manifestDirty = false;
  manifestFeedback = data?.template_copied
    ? `Created ${data.patch} with a manifest and a verbatim copy of Bob's patch template.`
    : data?.status || `Created ${data?.patch || "patch"} manifest-only; no template was copied.`;
  ws.send("refresh_distribution", {});
  render();
});
ws.on("notification", (data) => {
  if (data?.scope === "patch_editor" || data?.patch) {
    manifestFeedback = String(data.message || data.status || "");
    render();
  }
});
ws.on("status", (data) => {
  if (data?.scope === "patch_editor") {
    manifestFeedback = String(data.message || data.status || "");
    render();
  }
});
ws.on("device_offline", (data) => {
  if (installation.devices[data.uid]) installation.devices[data.uid].online = false;
  render();
});
ws.on("mute_all", (data) => {
  muted = !!data.value;
  installation.muted = muted;
  render();
});
ws.on("master", (data) => {
  master = Number(data.value);
  renderHeader();
});
ws.on("room", (data) => {
  installation.room = data;
  render();
});
ws.on("listener", (data) => {
  installation.listener = data;
  render();
});
ws.on("points", (data) => {
  installation.points = data.points || {};
  render();
});
ws.on("editor_points", (data) => {
  if (!installation.editor) return;
  installation.editor.points = data.points || {};
  Spatial.renderEditor(installation.editor, ws);
});
ws.on("editor_point_element", (data) => {
  if (!installation.editor) return;
  installation.editor.point_element = Number(data.element) || 0;
  Spatial.renderEditor(installation.editor, ws);
});
ws.on("point_frame", (data) => Spatial.frame(data.points || {}));
ws.on("editor_event_fired", (data) => {
  const status = $("#editor-event-status");
  if (!status) return;
  status.value = `${data.identity} fired`;
});
ws.on("error", (data) => {
  if (remoteCommandSaving) {
    remoteCommandSaving = false;
    remoteCommandFeedback = `Not saved: ${data.message}`;
    renderRemoteCommandEditor();
    return;
  }
  if (manifestFeedback.endsWith("…")) {
    manifestFeedback = `Not saved: ${data.message}`;
    const feedback = $("#manifest-feedback");
    if (feedback) feedback.textContent = manifestFeedback;
  }
  if (activeTab === "show" && typeof window.ShowInspectorError === "function") {
    window.ShowInspectorError(data.message);
    return;
  }
  alert(data.message);
});
ws.on("seat_reindexed", (data) => {
  selectedSeat = Number(data.new_id);
  selected = occupant(installation.seats?.[String(selectedSeat)])?.uid || null;
  render();
});
