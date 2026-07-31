// /facilitator hosts one ControlColumn today. The Dashboard tab embeds this
// same document; later column-count and document-boundary work can instantiate
// the component again without duplicating its state.
const embedded = new URLSearchParams(location.search).get("embedded") === "1";
if (embedded) document.body.classList.add("embedded");

const ws = new BopSocket("/ws");
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "—").replace(
  /[&<>"']/g,
  character => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"}[character]),
);
const destructiveCommands = new Set(["updatebopos", "reboot", "shutdown"]);
let installation = {devices: {}, seats: {}, groups: {}};
let muted = false;
let master = 1.0;
let interacting = false;

const column = window.ControlColumn.create({
  host: document.body,
  id: "control",
  storageKey: "bopos.target.control",
  full: embedded,
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
ws.on("preset_capture_preview", data => column.acceptCapturePreview(data));
ws.on("preset_saved", data => column.reportPresetSaved(data));
ws.on("preset_applied", data => column.reportPresetApplied(data));
ws.on("show_preset_capture_preview", data =>
  column.handleShowCapturePreview(data));
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
  renderCommands();
}

function renderControls() {
  if (!interacting) $("#master").value = master;
  $("#master-out").value = Math.round(master * 100) + "%";
  const silence = $("#silence");
  silence.textContent = muted ? "RESUME" : "SILENCE ALL";
  silence.classList.toggle("active", muted);
}

function commandLabel(command) {
  return command === "updatebopos"
    ? "Update bopOS"
    : command.replaceAll("-", " ").replaceAll("_", " ");
}

function renderCommands() {
  const commands = installation.facilitator_commands || [];
  $("#facilitator-commands").innerHTML = commands.length
    ? `<span class="command-scope-label">Fleet setup</span>${commands.map(command =>
        `<button data-command="${esc(command)}" class="${destructiveCommands.has(command) ? "hold" : ""}">${esc(commandLabel(command))}${destructiveCommands.has(command) ? " — hold" : ""}</button>`,
      ).join("")}`
    : "";
  $("#facilitator-commands").querySelectorAll("[data-command]")
    .forEach(button => bindCommandButton(button));
}

function bindCommandButton(button) {
  const command = button.dataset.command;
  if (!destructiveCommands.has(command)) {
    button.onclick = () => {
      if (confirm(`${commandLabel(command)} all devices?`)) {
        ws.send("action", {uid: "all", verb: command});
      }
    };
    return;
  }
  let timer = null;
  const cancel = () => {
    clearTimeout(timer);
    timer = null;
    button.classList.remove("holding");
  };
  button.onpointerdown = () => {
    button.classList.add("holding");
    timer = setTimeout(() => {
      timer = null;
      button.classList.remove("holding");
      ws.send("action", {uid: "all", verb: command});
    }, 1200);
  };
  button.onpointerup = cancel;
  button.onpointercancel = cancel;
  button.onpointerleave = cancel;
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
