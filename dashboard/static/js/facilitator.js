// The standalone Remote view: one ControlColumn, plus the page furniture that
// only this document has (venue name, master, mute).
//
// Until `3-iframe-retirement` this file was BOTH hosts — the Control tab
// embedded this same page as an iframe with `?embedded=1`, and four behaviours
// forked on that URL parameter. The Control tab now mounts the column directly
// in `index.html` (`js/control-host.js`), so the fork is gone: what the two
// hosts differ about is stated by what each passes in.
//
// Remote derives All, every group and every Seat. It shares the card renderer
// with Control but has no target picker or presets; dashboard:true still gates
// its manifest subset, and it retains the device commands needed away from the
// desktop rack view.
const ws = new BopSocket("/ws");
const $ = selector => document.querySelector(selector);
let installation = {devices: {}, seats: {}, groups: {}};
let muted = false;
let master = 1.0;
let interacting = false;

const column = window.ControlColumn.create({
  host: $("#control-column-host"),
  id: "remote",
  storageKey: null,
  capabilities: {
    fullManifest: false,
    presetMenu: false,
    targetPicker: false,
    deriveAllTargets: true,
    deviceCommands: true,
    deviceHandoff: false,
    groupSlot: groupId => window.GroupSlots.forGroup(
      groupId, Object.values(installation.groups || {})),
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
  sendCommand: payload => ws.send("action", payload),
});

ws.on("connection", connected => {
  $("#ws-status").textContent = connected ? "" : "reconnecting…";
  $("#ws-status").className = connected ? "online" : "offline";
});
ws.on("error", data => {
  alert(data?.message || "The dashboard rejected that action.");
});
ws.on("state", data => {
  installation = data;
  muted = !!data.muted;
  master = Number(data.master ?? 1);
  column.refresh(data);
  renderPageFurniture();
  const loading = $("#initial-loading");
  if (loading) loading.hidden = true;
});
ws.on("device_update", data => {
  if (data?.devices) installation = data;
  else if (data?.uid) installation.devices[data.uid] = data;
  render();
});
ws.on("params_declaration", data => {
  if (data?.uid) installation.devices[data.uid] = data;
  render();
});
ws.on("device_offline", data => {
  if (installation.devices[data.uid]) {
    installation.devices[data.uid].online = false;
    render();
  }
});
ws.on("mute_all", data => {
  muted = !!data.value;
  renderControls();
});
ws.on("master", data => {
  master = Number(data.value);
  renderControls();
});
ws.on("event_scheduled", data => column.reportEventScheduled(data));
document.addEventListener("pointerdown", event => {
  if (event.target.matches(
    'input[type="range"], button.live-toggle[data-live-param], select.live-enum[data-live-param]',
  )) interacting = true;
});
document.addEventListener("pointerup", () => {
  if (!interacting) return;
  // Click/change follows pointerup. Keep every column frozen through that event
  // so a heartbeat cannot replace the control before its handler fires.
  setTimeout(() => {
    interacting = false;
    render();
  }, 0);
});

function render() {
  column.render();
  renderPageFurniture();
}

function renderPageFurniture() {
  $("#venue-name").textContent = installation.name || "bopOS";
  renderControls();
}

function renderControls() {
  if (!interacting) $("#master").value = master;
  $("#master-out").value = Math.round(master * 100) + "%";
  const silence = $("#silence");
  silence.textContent = muted ? "UNMUTE" : "MUTE";
  silence.classList.toggle("active", muted);
}

{
  const masterInput = $("#master");
  let last = 0;
  let timer;
  const sendMaster = () => {
    master = Number(masterInput.value);
    ws.send("set_master", {value: master});
    renderControls();
  };
  masterInput.oninput = () => {
    const now = performance.now();
    if (now - last >= 33) {
      last = now;
      sendMaster();
    } else {
      clearTimeout(timer);
      timer = setTimeout(sendMaster, 33 - (now - last));
    }
  };
  masterInput.onchange = sendMaster;
  masterInput.onpointerup = sendMaster;
}

$("#silence").onclick = () => {
  muted = !muted;
  ws.send("mute_all", {value: muted ? 1 : 0});
  renderControls();
};
