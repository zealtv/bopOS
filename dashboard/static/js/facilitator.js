// Facilitator view: volumes, master, silence/resume, sound check, presets.
// Everything technical stays in / (proposal Q6 scope guard).
const ws = new BopSocket("/ws");
let installation = {devices: {}};
let muted = false;
let master = 1.0;
let presetNames = [];
const requested = new Set();
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

// volume resolution (contract sec 8 / facilitator proposal Q1):
// role "volume", else the param literally named gain, else no slider
function volumeParam(device) {
  const declared = device.declared || [];
  const byRole = declared.find(p => p.role === "volume");
  if (byRole) return byRole;
  return declared.find(p => p.name === "gain" && p.role !== "meter") || null;
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
  renderCards(); renderControls(); renderPresets();
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
  const volume = volumeParam(d);
  const control = volume
    ? `<input type="range" data-uid="${esc(d.uid)}" data-param="${esc(volume.name)}"
         min="${volume.min ?? 0}" max="${volume.max ?? 1}" step="0.01"
         value="${esc(d.params?.[volume.name] ?? volume.default ?? 0)}">`
    : (d.declared ? '<span class="badge">no volume param</span>' : '<span class="badge dim">…</span>');
  return `<div class="card"><i class="dot ${ok ? 'ok' : ''}"></i><span class="name">${esc(d.name || d.uid)}</span>${control}</div>`;
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
    input.oninput = () => { const now = performance.now(); if (now - last >= 33) { last = now; send(); } else { clearTimeout(timer); timer = setTimeout(send, 33 - (now - last)); } };
    input.onchange = send;
    input.onpointerup = send;
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

{
  const master_ = $("#master");
  let last = 0, timer;
  const send = () => { master = Number(master_.value); ws.send("set_master", {value: master}); renderControls(); };
  master_.oninput = () => { const now = performance.now(); if (now - last >= 33) { last = now; send(); } else { clearTimeout(timer); timer = setTimeout(send, 33 - (now - last)); } };
  master_.onchange = send;
  master_.onpointerup = send;
}
$("#silence").onclick = () => { muted = !muted; ws.send("mute_all", {value: muted ? 1 : 0}); renderControls(); };
$("#soundcheck").onclick = () => ws.send("action", {uid: "all", verb: "aloha"});
