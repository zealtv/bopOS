// Facilitator view: promoted params, master, silence/resume, and presets.
// Everything technical stays in / (proposal Q6 scope guard).
const ws = new BopSocket("/ws");
let installation = {devices: {}};
let muted = false;
let master = 1.0;
let presetNames = [];
const requested = new Set();
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

// contract sec 8: every facilitator:true param gets a labelled control on
// the device card; no role concept, no anointed volume, no gain fallback
function promotedParams(device) {
  return (device.declared || []).filter(p => p.facilitator === true);
}

function paramControl(d, param) {
  const value = d.params?.[param.name] ?? param.default ?? "";
  const attrs = `data-uid="${esc(d.uid)}" data-param="${esc(param.name)}"`;
  if (param.type === "s") {
    return `<label class="promoted"><span>${esc(param.name)}</span><input ${attrs} type="text" value="${esc(value)}"></label>`;
  }
  if (param.type === "i" && param.min === 0 && param.max === 1) {
    return `<label class="promoted toggle"><span>${esc(param.name)}</span><input ${attrs} type="checkbox" ${value ? "checked" : ""}></label>`;
  }
  return `<label class="promoted"><span>${esc(param.name)}</span><output>${esc(value)}</output><input ${attrs} type="range" min="${param.min ?? 0}" max="${param.max ?? 1}" step="${param.type === "i" ? 1 : 0.01}" value="${esc(value)}"></label>`;
}

ws.on("connection", connected => { $("#ws-status").textContent = connected ? "" : "reconnecting…"; $("#ws-status").className = connected ? "online" : "offline"; });
ws.on("state", data => { installation = data; muted = !!data.muted; master = Number(data.master ?? 1); presetNames = Object.keys(data.presets || {}).sort(); render(); });
ws.on("device_update", data => { if (data && data.uid) { installation.devices[data.uid] = data; render(); } });
ws.on("params_declaration", data => { if (data && data.uid) { installation.devices[data.uid] = data; render(); } });
ws.on("device_offline", data => { if (installation.devices[data.uid]) { installation.devices[data.uid].online = false; render(); } });
ws.on("mute_all", data => { muted = !!data.value; renderControls(); });
ws.on("master", data => { master = Number(data.value); renderControls(); });
ws.on("presets", data => { presetNames = data.names || []; renderPresets(); });

let interacting = false;
document.addEventListener("pointerdown", e => { if (e.target.matches('input[type="range"]')) interacting = true; });
document.addEventListener("pointerup", () => { if (interacting) { interacting = false; render(); } });

function render() {
  $("#venue-name").textContent = installation.name || "bopOS";
  renderCards(); renderControls(); renderCommands(); renderPresets();
}

function renderCards() {
  if (interacting) return;
  const assigned = Object.values(installation.devices || {})
    .filter(d => Number(d.id) >= 0).sort((a, b) => a.id - b.id);
  for (const d of assigned) {
    if (!d.declared && !requested.has(d.uid)) { requested.add(d.uid); ws.send("request_params", {uid: d.uid}); }
  }
  $("#cards").innerHTML = assigned.map(card).join("") || '<p class="empty">Waiting for devices…</p>';
  bindCards();
}

function card(d) {
  // green = sounding-capable, gray = not; no technical detail (proposal Q1/Q6)
  const ok = d.online && Number(d.engine_alive) !== 0;
  const pending = d.declared ? "" : '<span class="badge dim">…</span>';
  const promoted = d.declared
    ? promotedParams(d).map(param => paramControl(d, param)).join("") : "";
  return `<div class="card"><div class="card-main"><i class="dot ${ok ? 'ok' : ''}"></i><span class="name">${esc(d.name || d.uid)}</span>${pending}</div>${promoted ? `<div class="promoted-controls">${promoted}</div>` : ""}</div>`;
}

function bindCards() {
  document.querySelectorAll("#cards input[type=range]").forEach(input => {
    let last = 0, timer;
    const send = () => {
      const value = Number(input.value);
      ws.send("set_param", {uid: input.dataset.uid, name: input.dataset.param, value});
      const device = installation.devices[input.dataset.uid];
      if (device) device.params[input.dataset.param] = value;
    };
    input.oninput = () => { if (input.previousElementSibling?.tagName === "OUTPUT") input.previousElementSibling.value = input.value; const now = performance.now(); if (now - last >= 33) { last = now; send(); } else { clearTimeout(timer); timer = setTimeout(send, 33 - (now - last)); } };
    input.onchange = send;
    input.onpointerup = send;
  });
  document.querySelectorAll('#cards input[type="checkbox"], #cards input[type="text"]').forEach(input => {
    const send = () => {
      const value = input.type === "checkbox" ? (input.checked ? 1 : 0) : input.value;
      ws.send("set_param", {uid: input.dataset.uid, name: input.dataset.param, value});
      const device = installation.devices[input.dataset.uid];
      if (device) device.params[input.dataset.param] = value;
    };
    input.onchange = send;
  });
}

function renderControls() {
  if (!interacting) { $("#master").value = master; }
  $("#master-out").value = Math.round(master * 100) + "%";
  const silence = $("#silence");
  silence.textContent = muted ? "RESUME" : "SILENCE ALL";
  silence.classList.toggle("active", muted);
}

function renderPresets() {
  $("#presets").innerHTML = presetNames.map(name =>
    `<button class="chip" data-preset="${esc(name)}">${esc(name)}</button>`).join("");
  document.querySelectorAll("[data-preset]").forEach(button =>
    button.onclick = () => ws.send("load_preset", {name: button.dataset.preset}));
}

const destructiveCommands = new Set(["updatebopos", "reboot", "shutdown"]);
function commandLabel(command) { return command === "updatebopos" ? "Update bopOS" : command.replaceAll("-", " ").replaceAll("_", " "); }
function renderCommands() {
  const commands = installation.facilitator_commands || [];
  $("#facilitator-commands").innerHTML = commands.map(command =>
    `<button data-command="${esc(command)}" class="${destructiveCommands.has(command) ? "hold" : ""}">${esc(commandLabel(command))}${destructiveCommands.has(command) ? " — hold" : ""}</button>`).join("");
  document.querySelectorAll("[data-command]").forEach(button => {
    const command = button.dataset.command;
    if (!destructiveCommands.has(command)) {
      button.onclick = () => {
        if (confirm(`${commandLabel(command)} all devices?`)) ws.send("action", {uid: "all", verb: command});
      };
      return;
    }
    let timer = null;
    const cancel = () => { clearTimeout(timer); timer = null; button.classList.remove("holding"); };
    button.onpointerdown = () => {
      button.classList.add("holding");
      timer = setTimeout(() => { timer = null; button.classList.remove("holding"); ws.send("action", {uid: "all", verb: command}); }, 1200);
    };
    button.onpointerup = cancel;
    button.onpointercancel = cancel;
    button.onpointerleave = cancel;
  });
}

{
  const master_ = $("#master");
  let last = 0, timer;
  const send = () => { master = Number(master_.value); ws.send("set_master", {value: master}); renderControls(); };
  master_.oninput = () => { const now = performance.now(); if (now - last >= 33) { last = now; send(); } else { clearTimeout(timer); timer = setTimeout(send, 33 - (now - last)); } };
  master_.onchange = send;
  master_.onpointerup = send;
}
$("#silence").onclick = () => { muted = !muted; ws.send("mute_all", {value: muted ? 1 : 0}); renderControls(); };
