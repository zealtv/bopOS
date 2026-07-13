const ws = new BopSocket("/ws");
let installation = {devices: {}};
let selected = null;
let muted = false;
let master = 1.0;
const heartbeats = new Map();
const assignmentDrafts = new Map();
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

function mergeDevice(device) {
  if (device && device.uid) {
    installation.devices[device.uid] = device;
    if (Number(device.id) >= 0) assignmentDrafts.delete(device.uid);
  }
  render();
}
ws.on("connection", connected => { $("#ws-status").textContent = connected ? "connected" : "disconnected"; $("#ws-status").className = connected ? "online" : "offline"; });
ws.on("state", data => { installation = data; muted = !!data.muted; master = Number(data.master ?? 1); presetNames = Object.keys(data.presets || {}).sort(); renderPresets(); render(); });
ws.on("device_update", data => { if (data && data.devices) installation = data; else mergeDevice(data); });
ws.on("heartbeat", data => {
  if (!data?.uid) return;
  const heartbeatAt = String(data.timestamp ?? Date.now() / 1000);
  heartbeats.set(data.uid, heartbeatAt);
  const row = Array.from(document.querySelectorAll(".device-row"))
    .find(element => element.dataset.uid === data.uid);
  const blip = row?.querySelector(".heartbeat-blip");
  if (!blip) return;
  blip.classList.remove("pulse");
  void blip.offsetWidth;
  blip.classList.add("pulse");
  blip.dataset.heartbeatAt = heartbeatAt;
});
ws.on("params_declaration", mergeDevice); ws.on("report", mergeDevice); ws.on("rev", mergeDevice);
ws.on("device_offline", data => { if (installation.devices[data.uid]) installation.devices[data.uid].online = false; render(); });
ws.on("mute_all", data => { muted = !!data.value; renderHeader(); });
ws.on("master", data => { master = Number(data.value); renderHeader(); });
ws.on("room", data => { installation.room = data; render(); });
ws.on("listener", data => { installation.listener = data; render(); });
ws.on("points", data => { installation.points = data.points || {}; render(); });
ws.on("point_frame", data => Spatial.frame(data.points || {}));
ws.on("cue_scheduled", data => {
  const status = $("#cue-status"); if (!status) return;
  status.value = `${data.cue_id} fires in ${data.lead_ms} ms`;
});
ws.on("error", data => alert(data.message));
let venues = {venues: [], current: null};
ws.on("venues", data => { venues = data; renderVenues(); });
function renderVenues() {
  const select = $("#venue-select"); if (!select) return;
  const options = venues.venues.map(name => `<option ${name===venues.current?'selected':''}>${esc(name)}</option>`).join("");
  select.innerHTML = options || '<option disabled>none saved</option>';
}
(function bindVenues() {
  const save = $("#venue-save"), load = $("#venue-load");
  if (save) save.onclick = () => { const name = prompt("Save current installation as:", venues.current || ""); if (name) ws.send("save_venue", {name}); };
  if (load) load.onclick = () => { const name = $("#venue-select").value; if (name && confirm(`Load venue "${name}"? Replaces the current device map.`)) ws.send("load_venue", {name}); };
})();
let presetNames = [];
ws.on("presets", data => { presetNames = data.names || []; renderPresets(); });
function renderPresets() {
  const select = $("#preset-select"); if (!select) return;
  select.innerHTML = presetNames.map(name => `<option>${esc(name)}</option>`).join("") || '<option disabled>none saved</option>';
}
(function bindPresets() {
  const save = $("#preset-save"), load = $("#preset-load");
  if (save) save.onclick = () => {
    const name = prompt("Save current params + master as preset:", "");
    if (name && (!presetNames.includes(name) || confirm(`Overwrite preset "${name}"?`))) ws.send("save_preset", {name});
  };
  if (load) load.onclick = () => { const name = $("#preset-select").value; if (name) ws.send("load_preset", {name}); };
})();

function render() {
  const devices = Object.values(installation.devices || {});
  const assigned = devices.filter(d => Number(d.id) >= 0).sort((a,b) => a.id-b.id);
  const unassigned = devices.filter(d => Number(d.id) < 0);
  $("#assigned").innerHTML = assigned.map(row).join("");
  $("#unassigned").innerHTML = unassigned.map(row).join("") || '<p class="dim">None</p>';
  document.querySelectorAll(".device-row").forEach(el => el.onclick = () => select(el.dataset.uid));
  Spatial.render(installation, selected, select, ws); renderRoom();
  renderHeader(); renderDetail();
}
function row(d) {
  const status = d.online ? (Number(d.engine_alive) === 0 ? "crashed" : "online") : "offline";
  const heartbeatAt = heartbeats.get(d.uid);
  return `<button class="device-row ${d.uid===selected?'selected':''}" data-uid="${esc(d.uid)}"><i class="dot ${status}"></i><i class="heartbeat-blip${heartbeatAt?' pulse':''}" ${heartbeatAt?`data-heartbeat-at="${esc(heartbeatAt)}"`:''} aria-hidden="true"></i><span><strong>${esc(d.name || d.uid)}</strong><small>ID ${esc(d.id)} · ${esc(d.version)}${d.rssi != null ? ` · ${d.rssi} dBm` : ''}</small></span></button>`;
}
function renderRoom() {
  const room = installation.room || {}; const listener = installation.listener || {};
  const w = $("#room-w"), d = $("#room-d");
  if (!w) return;
  if (document.activeElement !== w && document.activeElement !== d) {
    w.value = room.width ?? 10; d.value = room.depth ?? 8;
  }
}
["room-w", "room-d"].forEach(id => { const input = document.getElementById(id); if (input) input.onchange = () => ws.send("set_room", {width: Number($("#room-w").value), depth: Number($("#room-d").value)}); });
(function bindCue() {
  const button = $("#cue-fire"); if (!button) return;
  button.onclick = () => {
    const cueId = $("#cue-id").value.trim();
    const leadMs = Math.min(10000, Math.max(100, Number($("#cue-lead").value) || 500));
    if (!cueId) return;
    ws.send("fire_cue", {cue_id: cueId, lead_ms: leadMs});
    button.disabled = true;
    setTimeout(() => { button.disabled = false; }, leadMs + 250);
  };
})();
function renderHeader() {
  const ds = Object.values(installation.devices || {}), online = ds.filter(d => d.online).length;
  $("#online-count").textContent = `${online} / ${ds.length} online`;
  $("#mute-all").classList.toggle("active", muted); $("#mute-all").textContent = muted ? "MUTED — UNMUTE" : "MUTE ALL";
  if (document.activeElement !== $("#master")) $("#master").value = master;
  $("#master-out").value = Math.round(master * 100) + "%";
}
function select(uid) { selected = uid; const d=installation.devices[uid]; if (!d.declared) ws.send("request_params", {uid}); render(); }
let interacting = false;
document.addEventListener("pointerdown", e => { if (e.target.closest("#detail input")) interacting = true; });
document.addEventListener("pointerup", () => { interacting = false; });

function renderDetail() {
  const d = installation.devices[selected]; if (!d) return;
  // never rebuild the panel out from under a drag or mid-typing
  const active = document.activeElement;
  if (interacting || ($("#detail").contains(active) && active.matches('input[type="text"],input[type="number"]'))) return;
  const declarations = d.declared || [];
  let previousGroup = null;
  const controls = declarations.map(p => {
    const group = p.group || "parameters", label = group !== previousGroup ? `<h3>${esc(group)}</h3>` : ""; previousGroup=group;
    const value = d.params?.[p.name] ?? p.default ?? "";
    if (p.type === "s") return `${label}<label>${esc(p.name)}<input data-param="${esc(p.name)}" type="text" value="${esc(value)}"></label>`;
    if (p.type === "i" && p.min===0 && p.max===1) return `${label}<label class="toggle">${esc(p.name)}<input data-param="${esc(p.name)}" type="checkbox" ${value?'checked':''}></label>`;
    return `${label}<label>${esc(p.name)} <output>${esc(value)}</output><input data-param="${esc(p.name)}" type="range" min="${p.min??0}" max="${p.max??1}" step="${p.type==='i'?1:0.01}" value="${esc(value)}"></label>`;
  }).join("");
  const assigned = Number(d.id) >= 0;
  const assignmentDraft = assignmentDrafts.get(d.uid) || {};
  $("#detail").innerHTML = `<section><h2>${esc(d.name || d.uid)} ${d.undeclared?'<b class="badge">UNDECLARED</b>':''}</h2><dl><dt>UID</dt><dd>${esc(d.uid)}</dd><dt>ID</dt><dd>${esc(d.id)}</dd><dt>Status</dt><dd>${d.online?'online':'offline'}</dd><dt>Version</dt><dd>${esc(d.version)}</dd><dt>Engine</dt><dd>${d.engine_alive?'alive':'stopped'}</dd><dt>RSSI</dt><dd>${esc(d.rssi)}</dd><dt>IP</dt><dd>${esc(d.ip)}</dd><dt>Converged</dt><dd>${d.rev?`${esc(d.rev.sha)} (${esc(d.rev.model)}, ${ago(d.rev.at)})`:'—'}</dd></dl></section>
    <section><h2>${assigned?'Identity':'Assign'}</h2><div class="assign"><label>name <input id="assign-name" type="text" value="${esc(assigned?(d.name||''):(assignmentDraft.name??''))}" placeholder="planter-nw"></label><label>ID <input id="assign-id" type="number" min="0" step="1" value="${assigned?d.id:(assignmentDraft.id??nextFreeId())}"></label><button id="assign-send">${assigned?'Apply':'Assign'}</button>${assigned?'':'<button data-identify>Identify</button>'}</div>${assigned?'':'<p class="dim">New device: identify to flash the box, name it, assign, then drag it onto the map.</p>'}</section>
    ${assigned?`<section><div class="section-head"><h2>Params</h2><label><input id="broadcast" type="checkbox"> broadcast to all</label></div><div class="params">${controls || '<p class="dim">Loading declaration…</p>'}</div></section>
    <section><h2>Patch</h2><p class="dim">current: <b>${esc(d.report?.patch ?? '—')}</b></p><div class="assign"><label>switch to <input id="patch-name" type="text" placeholder="wind_chimes"></label><button id="patch-switch">Switch</button><button id="patch-pull">Pull latest</button><button data-action="get_samples">Get samples</button></div><div class="assign"><label>add from GitHub <input id="patch-user" type="text" placeholder="user"></label><label>&nbsp;<input id="patch-repo" type="text" placeholder="repo"></label><button id="patch-add">Add</button></div></section>
    <section><h2>Actions</h2><div class="actions">${["reboot","shutdown","restart-engine","update","get_samples"].map(v=>`<button data-action="${v}">${v.replace('_',' ')}</button>`).join('')}<button data-identify>Identify</button></div></section>`:''}
    <section><div class="section-head"><h2>Report</h2><button id="refresh-report">Refresh report</button></div>${report(d.report)}</section>`;
  bindControls(d);
}
function nextFreeId() { const used = new Set(Object.values(installation.devices||{}).map(d=>Number(d.id)).filter(id=>id>=0)); let id=1; while (used.has(id)) id++; return id; }
function report(r) { if (!r) return '<p class="dim">No report loaded.</p>'; const keys=["engine","patch","git_rev","uptime","has_i2c","has_wifi","audio_channels","screen","update_model","contract_version"]; return `<dl>${keys.map(k=>`<dt>${k}</dt><dd>${k==='uptime'?human(r[k]):esc(r[k])}</dd>`).join('')}</dl>`; }
function human(seconds) { seconds=Number(seconds)||0; return `${Math.floor(seconds/3600)}h ${Math.floor(seconds%3600/60)}m ${seconds%60}s`; }
function ago(epoch) { const s=Math.max(0,Math.round(Date.now()/1000-Number(epoch))); return s<60?`${s}s ago`:s<3600?`${Math.floor(s/60)}m ago`:`${Math.floor(s/3600)}h ago`; }
function bindControls(d) {
  let last=0, timer;
  document.querySelectorAll("[data-param]").forEach(input => {
    const send = () => {
      let value=input.type==='checkbox'?(input.checked?1:0):input.value; if(input.type==='range') value=Number(value);
      ws.send("set_param", {uid:d.uid,name:input.dataset.param,value,broadcast:!!$("#broadcast")?.checked});
      // optimistic local update so the post-drag re-render shows the sent value,
      // not the last server echo; re-sends are safe (idempotent full-state)
      const local = installation.devices[d.uid]; if (local) local.params[input.dataset.param] = value;
    };
    input.oninput = () => { input.previousElementSibling?.tagName==='OUTPUT' && (input.previousElementSibling.value=input.value); const now=performance.now(); if(now-last>=33){last=now;send();} else {clearTimeout(timer);timer=setTimeout(send,33-(now-last));} };
    input.onchange=send;
    // fires target-phase, before the document pointerup re-render can detach
    // the input and strand the final change event on a dead node
    input.onpointerup=send;
  });
  document.querySelectorAll("[data-action]").forEach(button => button.onclick=()=>{ const verb=button.dataset.action; if(["reboot","shutdown"].includes(verb)&&!confirm(`${verb} ${d.name||d.uid}?`))return; ws.send("action",{uid:d.uid,verb}); });
  document.querySelectorAll("[data-identify]").forEach(button => button.onclick=()=>ws.send("identify",{uid:d.uid}));
  if (Number(d.id) < 0) {
    const rememberAssignment = () => assignmentDrafts.set(d.uid, {
      name: $("#assign-name").value,
      id: Number($("#assign-id").value),
    });
    $("#assign-name").oninput = rememberAssignment;
    $("#assign-id").oninput = rememberAssignment;
  }
  const assign=$("#assign-send"); if(assign) assign.onclick=()=>ws.send("assign_device",{uid:d.uid,name:$("#assign-name").value,id:Number($("#assign-id").value)});
  const bcast=()=>$("#broadcast")?.checked; const target=()=>bcast()?"all":d.uid;
  const patchSwitch=$("#patch-switch"); if(patchSwitch){
    patchSwitch.onclick=()=>{const p=$("#patch-name").value.trim(); if(p&&confirm(`Switch ${bcast()?'ALL devices':d.name||d.uid} to patch "${p}"? The device reboots.`))ws.send("switch_patch",{uid:target(),patch:p});};
    $("#patch-pull").onclick=()=>{if(confirm(`Pull latest patch on ${bcast()?'ALL devices':d.name||d.uid}? It reboots.`))ws.send("pull_patch",{uid:target()});};
    $("#patch-add").onclick=()=>{const u=$("#patch-user").value.trim(),r=$("#patch-repo").value.trim(); if(u&&r)ws.send("add_patch",{uid:target(),user:u,repo:r});};
  }
  $("#refresh-report").onclick=()=>ws.send("request_report",{uid:d.uid});
}
$("#mute-all").onclick=()=>{muted=!muted;ws.send("mute_all",{value:muted?1:0});renderHeader();};
{
  const input = $("#master");
  let last = 0, timer;
  const send = () => { master = Number(input.value); ws.send("set_master", {value: master}); renderHeader(); };
  input.oninput = () => { const now = performance.now(); if (now-last >= 33) { last=now; send(); } else { clearTimeout(timer); timer=setTimeout(send, 33-(now-last)); } };
  input.onchange = send;
  input.onpointerup = send;
}
document.querySelectorAll("[data-all]").forEach(b=>b.onclick=()=>{const verb=b.dataset.all;if(["reboot","update"].includes(verb)&&!confirm(`${verb} all devices?`))return;ws.send("action",{uid:"all",verb});});
