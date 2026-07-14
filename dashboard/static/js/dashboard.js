const ws = new BopSocket("/ws");
let installation = {devices: {}};
let selected = null;
let selectedSeat = null;
let venueRebind = null;
let muted = false;
let master = 1.0;
const heartbeats = new Map();
const assignmentDrafts = new Map();
const bindingSeatDrafts = new Map();
const patchChoices = new Map();
let distribution = {assets: [], patches: []};
let distributionAll = false;
let patchAll = false;
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
ws.on("patches", mergeDevice);
ws.on("distribution", data => { distribution = data || {assets: [], patches: []}; render(); });
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
ws.on("venue_rebind", data => { venueRebind = data; render(); });
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
  const seats = Object.values(installation.seats || {}).sort((a,b) => a.id-b.id);
  const bound = new Set(seats.map(s => s.bound).filter(Boolean));
  const unassigned = devices.filter(d => !d.virtual && !bound.has(d.uid));
  $("#assigned").innerHTML = seats.map(seatRow).join("") || '<p class="dim">No seats</p>';
  $("#unassigned").innerHTML = (unassigned.map(row).join("") || '<p class="dim">None</p>') + '<button id="forget-offline">Forget all offline unbound</button>';
  document.querySelectorAll(".seat-row").forEach(el => {
    el.onclick = event => { if (!event.target.closest("input")) selectSeat(Number(el.dataset.seatId)); };
    const input = el.querySelector("[data-seat-name]");
    input.onchange = () => ws.send("update_seat", {id:Number(el.dataset.seatId), name:input.value});
  });
  document.querySelectorAll(".device-row:not(.seat-row)").forEach(el => el.onclick = () => select(el.dataset.uid));
  $("#forget-offline").onclick=()=>ws.send("forget_offline_unbound",{});
  const rebind=$("#venue-rebind");
  if (rebind) {
    rebind.hidden=!venueRebind;
    const labels=entries=>(entries||[]).map(entry=>{
      const seat=installation.seats?.[String(entry.id)];
      return `${seat?.name||`Seat ${entry.id}`} (${entry.uid})`;
    }).join(', ')||'none';
    rebind.textContent=venueRebind ? `Rebound: ${labels(venueRebind.rebound)} · Waiting: ${labels(venueRebind.waiting)}` : '';
  }
  renderSimulation(devices);
  Spatial.render(installation, selectedSeat, selectSeat, ws); renderRoom();
  renderHeader(); renderDetail();
}
function occupant(seat) {
  const devices=Object.values(installation.devices||{});
  return devices.find(d=>d.virtual&&Number(d.seat_id)===Number(seat.id)) || installation.devices?.[seat.bound];
}
function seatRow(seat) {
  const d=occupant(seat), state=d?.virtual?'sim':(d?.online?'live':'empty');
  const uid=d?.uid||"";
  const heartbeatAt=heartbeats.get(uid);
  return `<div class="device-row seat-row ${Number(seat.id)===Number(selectedSeat)?'selected':''}" data-uid="${esc(uid)}" data-seat-id="${seat.id}" role="button" tabindex="0"><i class="dot ${state==='live'?'online':state==='sim'?'sim':'offline'}"></i>${uid?`<i class="heartbeat-blip${heartbeatAt?' pulse':''}" ${heartbeatAt?`data-heartbeat-at="${esc(heartbeatAt)}"`:''} aria-hidden="true"></i>`:''}<span><input data-seat-name aria-label="Seat ${seat.id} name" value="${esc(seat.name||`Seat ${seat.id}`)}"><small>ID ${seat.id} · ${state}</small></span></div>`;
}
function renderSimulation(devices) {
  const sim=installation.simulation||{active:false,status:'off'}, button=$("#simulate-toggle");
  if (!button) return;
  button.textContent=sim.active?'Stop simulation':'Start simulation';
  button.onclick=()=>ws.send("set_simulation",{active:!sim.active});
  $("#simulate-status").textContent=sim.active&&sim.patch?`${sim.status||'running'} · ${sim.patch}`:(sim.status||'off');
  const real=devices.filter(d=>!d.virtual&&d.online).length;
  $("#simulate-real-note").textContent=sim.active&&real?`${real} real device${real===1?'':'s'} online (not driven)`:'';
}
function row(d) {
  const status = d.online ? (Number(d.engine_alive) === 0 ? "crashed" : "online") : "offline";
  const heartbeatAt = heartbeats.get(d.uid);
  return `<button class="device-row ${d.uid===selected?'selected':''}" data-uid="${esc(d.uid)}"><i class="dot ${status}"></i><i class="heartbeat-blip${heartbeatAt?' pulse':''}" ${heartbeatAt?`data-heartbeat-at="${esc(heartbeatAt)}"`:''} aria-hidden="true"></i><span><strong>${esc(d.hostname || d.uid)}</strong><small>${esc(d.uid)} · ${esc(d.version)}${d.rssi != null ? ` · ${d.rssi} dBm` : ''}</small></span></button>`;
}
function renderRoom() {
  const room = installation.room || {}; const listener = installation.listener || {};
  const w = $("#room-w"), d = $("#room-d"), ox = $("#origin-x"), oy = $("#origin-y");
  if (!w) return;
  if (![w, d, ox, oy].includes(document.activeElement)) {
    w.value = room.width ?? 10; d.value = room.depth ?? 8;
    ox.value = room.origin?.[0] ?? 0; oy.value = room.origin?.[1] ?? 0;
    ox.max = room.width ?? 10; oy.max = room.depth ?? 8;
  }
}
["room-w", "room-d", "origin-x", "origin-y"].forEach(id => {
  const input = document.getElementById(id);
  if (input) input.onchange = () => ws.send("set_room", {
    width: Number($("#room-w").value), depth: Number($("#room-d").value),
    origin: [Number($("#origin-x").value), Number($("#origin-y").value)],
  });
});
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
function select(uid) {
  selected = uid; const d=installation.devices[uid];
  selectedSeat = Object.values(installation.seats||{}).find(s=>s.bound===uid)?.id ?? d?.seat_id ?? null;
  if (!d.declared) ws.send("request_params", {uid});
  ws.send("request_patches", {uid});
  render();
}
function selectSeat(id) {
  selectedSeat=id; const seat=installation.seats?.[String(id)]||installation.seats?.[id];
  const d=seat&&occupant(seat); selected=d?.uid||null;
  if(d&&!d.declared) ws.send("request_params",{uid:d.uid});
  if(d) ws.send("request_patches",{uid:d.uid});
  render();
}
let interacting = false;
document.addEventListener("pointerdown", e => { if (e.target.closest("#detail input, #detail select")) interacting = true; });
document.addEventListener("pointerup", () => { interacting = false; });

function renderDetail() {
  const seat = installation.seats?.[String(selectedSeat)] || installation.seats?.[selectedSeat];
  const runtime = installation.devices[selected] || (seat && occupant(seat));
  if (!seat) {
    if(!runtime) { $("#detail").innerHTML='<section><p class="dim">Select a seat or device.</p></section>'; return; }
    const empty=Object.values(installation.seats||{}).filter(s=>!s.bound);
    const draft=bindingSeatDrafts.get(runtime.uid);
    $("#detail").innerHTML=`<section><h2>Unbound device</h2><dl><dt>UID</dt><dd>${esc(runtime.uid)}</dd><dt>Hostname</dt><dd>${esc(runtime.hostname||runtime.uid)}</dd><dt>Status</dt><dd>${runtime.online?'online':'offline'}</dd></dl><div class="assign"><label>empty seat <select id="device-seat">${empty.map(s=>`<option value="${s.id}" ${Number(s.id)===Number(draft)?'selected':''}>${esc(s.name||`Seat ${s.id}`)}</option>`).join('')}</select></label><button id="device-bind" ${empty.length?'':'disabled'}>Bind</button><button id="device-forget">Forget</button><button data-identify>Identify</button></div></section>`;
    $("#device-seat").onchange=()=>bindingSeatDrafts.set(runtime.uid,Number($("#device-seat").value));
    $("#device-bind").onclick=()=>{const id=Number($("#device-seat").value);bindingSeatDrafts.delete(runtime.uid);bindDeviceToSeat(id,runtime);};
    $("#device-forget").onclick=()=>{const recent=Date.now()/1000-Number(runtime.last_seen||0)<30;if(!recent||confirm(`Forget recently seen ${runtime.hostname||runtime.uid}?`))ws.send("forget_device",{uid:runtime.uid});};
    document.querySelectorAll("[data-identify]").forEach(b=>b.onclick=()=>ws.send("identify",{uid:runtime.uid}));
    return;
  }
  const d = runtime ? {...runtime, id:seat?.id, name:seat?.name,
    pos1:seat?.positions?.[0], pos2:seat?.positions?.[1],
    params:seat?.params||runtime.params} : {uid:"",id:seat.id,name:seat.name,
    pos1:seat.positions?.[0],pos2:seat.positions?.[1],params:seat.params,
    online:false,patches:[],declared:[]};
  // never rebuild the panel out from under a drag or mid-typing
  const active = document.activeElement;
  if (interacting || ($("#detail").contains(active) && active.matches('input[type="text"],input[type="number"],select'))) return;
  const declarations = d.declared || [];
  let previousGroup = null;
  const controls = declarations.map(p => {
    const group = p.group || "parameters", label = group !== previousGroup ? `<h3>${esc(group)}</h3>` : ""; previousGroup=group;
    const value = d.params?.[p.name] ?? p.default ?? "";
    if (p.type === "s") return `${label}<label>${esc(p.name)}<input data-param="${esc(p.name)}" type="text" value="${esc(value)}"></label>`;
    if (p.type === "i" && p.min===0 && p.max===1) return `${label}<label class="toggle">${esc(p.name)}<input data-param="${esc(p.name)}" type="checkbox" ${value?'checked':''}></label>`;
    return `${label}<label>${esc(p.name)} <output>${esc(value)}</output><input data-param="${esc(p.name)}" type="range" min="${p.min??0}" max="${p.max??1}" step="${p.type==='i'?1:0.01}" value="${esc(value)}"></label>`;
  }).join("");
  const assigned = !!runtime;
  const assignmentDraft = assignmentDrafts.get(d.uid) || {};
  const positionKeys = ["pos1", "pos2"].filter(key => Array.isArray(d[key]));
  if (!positionKeys.length) positionKeys.push("pos1");
  const room = installation.room || {}; const origin = room.origin || [0, 0];
  const positions = positionKeys.map((key, index) => {
    const position = d[key];
    const x = Array.isArray(position) ? Math.round((position[0] - origin[0]) * 100) / 100 : "";
    const y = Array.isArray(position) ? Math.round((position[1] - origin[1]) * 100) / 100 : "";
    return `<div class="position-row" data-position-key="${key}"><strong>element ${index}</strong><label>x <input class="position-coordinate" data-axis="x" type="number" step="0.01" min="${-origin[0]}" max="${(room.width??10)-origin[0]}" value="${x}"></label><label>y <input class="position-coordinate" data-axis="y" type="number" step="0.01" min="${-origin[1]}" max="${(room.depth??8)-origin[1]}" value="${y}"></label><span class="dim">m from origin</span></div>`;
  }).join("");
  const installed = Array.isArray(d.patches) ? d.patches : [];
  const activePatch = installed.find(p => p.active) || installed.find(p => p.name === d.report?.patch);
  const rememberedPatch = patchChoices.get(d.uid);
  const chosenName = (installed.some(p => p.name === rememberedPatch) ? rememberedPatch : null)
    || activePatch?.name || installed[0]?.name || "";
  if (chosenName) patchChoices.set(d.uid, chosenName); else patchChoices.delete(d.uid);
  const chosenPatch = installed.find(p => p.name === chosenName);
  const patchOptions = installed.map(p => `<option value="${esc(p.name)}" ${p.name===chosenName?'selected':''}>${p.git?'◆ ':''}${esc(p.name)}${p.manifest?'':' (invalid manifest)'}</option>`).join("");
  const simulating = !!installation.simulation?.active && !!d.virtual;
  const patchRows = distribution.patches.map(item => distributionRow(d, item)).join("");
  const assetRows = distribution.assets.map(item => distributionRow(d, item)).join("");
  $("#detail").innerHTML = `<section><h2>${esc(d.name || d.uid)} ${d.undeclared?'<b class="badge">UNDECLARED</b>':''}</h2><dl><dt>UID</dt><dd>${esc(d.uid)}</dd><dt>ID</dt><dd>${esc(d.id)}</dd><dt>Status</dt><dd>${d.online?'online':'offline'}</dd><dt>Version</dt><dd>${esc(d.version)}</dd><dt>Engine</dt><dd>${d.engine_alive?'alive':'stopped'}</dd><dt>RSSI</dt><dd>${esc(d.rssi)}</dd><dt>IP</dt><dd>${esc(d.ip)}</dd><dt>Converged</dt><dd>${d.rev?`${esc(d.rev.sha)} (${esc(d.rev.model)}, ${ago(d.rev.at)})`:'—'}</dd></dl></section>
    <section><h2>Seat</h2><div class="assign"><label>name <input id="seat-name" type="text" value="${esc(seat?.name||'')}"></label><label>ID <input type="number" value="${seat?.id}" disabled></label><button id="seat-rename">Apply</button><button id="seat-remove">Remove seat</button></div><div class="assign"><label>device <select id="seat-device"><option value="">unbound</option>${Object.values(installation.devices||{}).filter(x=>!x.virtual).map(x=>`<option value="${esc(x.uid)}" ${seat?.bound===x.uid?'selected':''}>${esc(x.hostname||x.uid)}</option>`).join('')}</select></label><button id="seat-bind">${seat?.bound?'Rebind':'Bind'}</button>${seat?.bound?'<button id="seat-unbind">Unbind</button>':''}</div></section>
    <section><h2>Position</h2><div class="position-grid">${positions}</div></section>
    ${assigned?`<section><div class="section-head"><h2>Params</h2><label><input id="broadcast" type="checkbox"> broadcast to all</label></div><div class="params">${controls || '<p class="dim">Loading declaration…</p>'}</div></section>
    <section><div class="section-head"><h2>Patch</h2>${simulating?'<span class="dim">Host-backed simulated fleet</span>':'<span class="dim">◆ Git-managed</span>'}</div><p class="dim">current: <b>${esc(activePatch?.name ?? d.report?.patch ?? '—')}</b></p><div class="assign"><label>${simulating?'host patches':'installed'} <select id="patch-select">${patchOptions || `<option disabled>${d.patches===null?'loading…':'No patches installed'}</option>`}</select></label><button id="patch-switch" ${!chosenPatch||!chosenPatch.manifest?'disabled':''}>Switch</button>${!simulating&&activePatch?.git?'<button id="patch-pull">Pull latest</button>':''}${simulating?'':`<button id="patch-drop" ${!chosenPatch||chosenPatch.active?'disabled':''}>Delete from device</button><label><input id="patch-all" type="checkbox" ${patchAll?'checked':''}> target all compatible devices</label>`}</div>${simulating?'<p class="dim">All simulated devices use this patch. Switching restarts the managed engine fleet; host patches need no Send step.</p>':'<div class="assign git-add"><label>add Git patch <input id="patch-user" type="text" placeholder="GitHub user"></label><label>&nbsp;<input id="patch-repo" type="text" placeholder="repository"></label><button id="patch-add">Add</button></div>'}</section>
    ${simulating?'':`<section id="distribution"><div class="section-head"><h2>Send &amp; sync</h2><label><input id="distribution-all" type="checkbox" ${distributionAll?'checked':''}> target all online devices</label></div><p class="dim">Host folders mirror onto ${distributionAll?'all online devices':esc(d.name||d.uid)}. The installed dropdown lists only patches acknowledged by this device; a successful Send adds a new patch there.</p><div class="distribution-actions"><button id="sync-all">Sync all</button><button id="refresh-distribution">Refresh host folders</button></div><h3>Patches</h3><div class="distribution-grid">${patchRows || '<p class="dim">No host patches.</p>'}</div><h3>Assets</h3><div class="distribution-grid">${assetRows || '<p class="dim">No host assets.</p>'}</div></section>`}
    <section><h2>Actions</h2><div class="actions">${["reboot","shutdown","restart-engine","updatebopos"].map(v=>`<button data-action="${v}">${actionLabel(v)}</button>`).join('')}<button data-identify>Identify</button></div></section>`:''}
    <section><div class="section-head"><h2>Report</h2><button id="refresh-report">Refresh report</button></div>${report(d.report)}</section>`;
  bindControls(d, seat);
}
function actionLabel(verb) { return verb === "updatebopos" ? "Update bopOS" : verb.replaceAll("-", " "); }
function bindDeviceToSeat(id, device) {
  const seat=installation.seats?.[String(id)]||installation.seats?.[id];
  if (seat && device?.hostname && (!seat.name || seat.name===`Seat ${seat.id}`)) {
    ws.send("update_seat", {id:seat.id, name:device.hostname});
  }
  ws.send("bind_seat", {id, uid:device.uid});
}
function itemSlot(item) { return item.kind === "patch" ? `patch:${item.name}` : item.name; }
function deviceDistributionStatus(d, item) {
  const slot = itemSlot(item), phase = d.fetch?.[slot], sent = d.distribution?.[slot];
  if (!d.online) return "offline";
  if (item.kind === "patch" && (d.patches || []).some(p=>p.name===item.name&&p.git)) return "Git-managed";
  if (phase === "queued" || phase === "fetching" || phase === "sent") return phase === "sent" ? "queued" : phase;
  if (phase === "err" || phase === "timeout") return phase === "timeout" ? "timed out" : "failed";
  if (sent && sent !== item.fingerprint) return "stale";
  if (sent === item.fingerprint) return "in sync";
  return "unknown";
}
function distributionTargets(d) { return distributionAll ? Object.values(installation.devices||{}).filter(device=>Number(device.id)>=0) : [d]; }
function distributionStatus(d, item) {
  const targets=distributionTargets(d), statuses=targets.map(device=>({device,status:deviceDistributionStatus(device,item)}));
  if (!distributionAll) return {label:statuses[0]?.status||"unknown", details:""};
  const eligible=statuses.filter(entry=>!["offline","Git-managed"].includes(entry.status));
  const synced=eligible.filter(entry=>entry.status==="in sync").length;
  const pending=eligible.find(entry=>["queued","fetching"].includes(entry.status));
  const failed=eligible.find(entry=>["failed","timed out","stale"].includes(entry.status));
  const label=pending?.status || failed?.status || `${synced}/${eligible.length} in sync`;
  const details=statuses.map(entry=>`${entry.device.name||entry.device.uid}: ${entry.status}`).join(" · ");
  return {label,details};
}
function formatBytes(value) {
  const bytes = Number(value) || 0;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024*1024) return `${(bytes/1024).toFixed(1)} KB`;
  return `${(bytes/1024/1024).toFixed(1)} MB`;
}
function distributionRow(d, item) {
  const status = distributionStatus(d, item), targets=distributionTargets(d);
  const gitTargets = item.kind === "patch" ? targets.filter(device=>(device.patches||[]).some(p=>p.name===item.name&&p.git)) : [];
  const pending=targets.some(device=>["sent","queued","fetching"].includes(device.fetch?.[itemSlot(item)]));
  const timedOut=targets.some(device=>device.fetch?.[itemSlot(item)]==="timeout");
  const selectedGit=!distributionAll&&gitTargets.length>0;
  const invalid=item.kind==="patch"&&!item.valid;
  const noOnline=targets.every(device=>!device.online);
  const disabled=selectedGit||invalid||pending||timedOut||noOnline;
  const reason=selectedGit?'Git-managed patches use Pull latest':invalid?(item.error||'Invalid patch manifest'):pending?'Send already in progress':timedOut?'Receipt timed out; restart the dashboard before retrying so a late receipt cannot be misread':noOnline?'No online target devices':'';
  return `<article class="distribution-item" data-kind="${item.kind}" data-name="${esc(item.name)}"><div><strong>${esc(item.name)}</strong>${gitTargets.length?`<span class="git-badge">◆ Git on ${gitTargets.length} device${gitTargets.length===1?'':'s'}</span>`:''}${invalid?'<span class="invalid-badge">invalid manifest</span>':''}<small>${item.files} files · ${formatBytes(item.bytes)} · <time datetime="${new Date(item.modified*1000).toISOString()}">${new Date(item.modified*1000).toLocaleString()}</time></small>${status.details?`<small class="device-sync">${esc(status.details)}</small>`:''}</div><span role="status" aria-live="polite" class="sync-status ${status.label.replace(/[^a-z0-9]+/gi,'-')}">${status.label}</span><button data-send ${disabled?`disabled title="${esc(reason)}"`:''}>${item.kind==='asset'?'Send assets':'Send patch'}</button>${item.kind==='asset'?'<button data-drop-asset>Remove from device</button>':''}</article>`;
}
function nextFreeId() { const used = new Set(Object.values(installation.seats||{}).map(s=>Number(s.id))); let id=0; while (used.has(id)) id++; return id; }
function report(r) { if (!r) return '<p class="dim">No report loaded.</p>'; const keys=["hostname","engine","patch","git_rev","uptime","has_i2c","has_wifi","audio_channels","screen","update_model","contract_version"]; return `<dl>${keys.map(k=>`<dt>${k}</dt><dd>${k==='uptime'?human(r[k]):esc(r[k])}</dd>`).join('')}</dl>`; }
function human(seconds) { seconds=Number(seconds)||0; return `${Math.floor(seconds/3600)}h ${Math.floor(seconds%3600/60)}m ${seconds%60}s`; }
function ago(epoch) { const s=Math.max(0,Math.round(Date.now()/1000-Number(epoch))); return s<60?`${s}s ago`:s<3600?`${Math.floor(s/60)}m ago`:`${Math.floor(s/3600)}h ago`; }
function bindControls(d, seat) {
  const simulating=!!installation.simulation?.active&&!!d.virtual;
  let last=0, timer;
  document.querySelectorAll("[data-param]").forEach(input => {
    const send = () => {
      let value=input.type==='checkbox'?(input.checked?1:0):input.value; if(input.type==='range') value=Number(value);
      ws.send("set_param", {uid:d.uid,name:input.dataset.param,value,broadcast:!!$("#broadcast")?.checked});
      // optimistic local update so the post-drag re-render shows the sent value,
      // not the last server echo; re-sends are safe (idempotent full-state)
      const local = installation.devices[d.uid]; if (local) local.params[input.dataset.param] = value;
      if (seat) seat.params[input.dataset.param] = value;
    };
    input.oninput = () => { input.previousElementSibling?.tagName==='OUTPUT' && (input.previousElementSibling.value=input.value); const now=performance.now(); if(now-last>=33){last=now;send();} else {clearTimeout(timer);timer=setTimeout(send,33-(now-last));} };
    input.onchange=send;
    // fires target-phase, before the document pointerup re-render can detach
    // the input and strand the final change event on a dead node
    input.onpointerup=send;
  });
  document.querySelectorAll("[data-action]").forEach(button => button.onclick=()=>{ const verb=button.dataset.action; if(["reboot","shutdown","updatebopos"].includes(verb)&&!confirm(`${actionLabel(verb)} ${d.name||d.uid}?`))return; ws.send("action",{uid:d.uid,verb}); });
  document.querySelectorAll("[data-identify]").forEach(button => button.onclick=()=>ws.send("identify",{uid:d.uid}));
  document.querySelectorAll(".position-coordinate").forEach(input => input.onchange = () => {
    const row = input.closest("[data-position-key]");
    const x = Number(row.querySelector('[data-axis="x"]').value);
    const y = Number(row.querySelector('[data-axis="y"]').value);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    const origin = installation.room?.origin || [0, 0];
    const position = [Math.round((x + origin[0]) * 100) / 100,
                      Math.round((y + origin[1]) * 100) / 100];
    const index = Number(row.dataset.positionKey === "pos2");
    seat.positions[index] = position;
    ws.send("update_seat", {id:seat.id, positions:seat.positions});
    Spatial.render(installation, selectedSeat, selectSeat, ws);
  });
  const rename=$("#seat-rename"); if(rename) rename.onclick=()=>ws.send("update_seat",{id:seat.id,name:$("#seat-name").value});
  const remove=$("#seat-remove"); if(remove) remove.onclick=()=>{if(confirm(`Remove seat ${seat.id}?`))ws.send("remove_seat",{id:seat.id});};
  const bind=$("#seat-bind"); if(bind) bind.onclick=()=>{const uid=$("#seat-device").value;if(uid)bindDeviceToSeat(seat.id,installation.devices[uid]);};
  const unbind=$("#seat-unbind"); if(unbind) unbind.onclick=()=>ws.send("unbind_seat",{id:seat.id});
  const patchSwitch=$("#patch-switch"); if(patchSwitch){
    const patchTarget=()=>patchAll?"all":d.uid;
    const patchAllInput=$("#patch-all"); if(patchAllInput) patchAllInput.onchange=()=>{patchAll=patchAllInput.checked;renderDetail();};
    const patchSelect=$("#patch-select");
    patchSelect.onchange=()=>{ patchChoices.set(d.uid, patchSelect.value); renderDetail(); };
    patchSwitch.onclick=()=>{const p=patchSelect.value,target=simulating?'the simulated fleet':(patchAll?'all compatible devices':d.name||d.uid),effect=simulating?'The managed engines restart.':'The device reboots.'; if(p&&confirm(`Switch ${target} to patch "${p}"? ${effect}`))ws.send("switch_patch",{uid:simulating?'all':patchTarget(),patch:p});};
    const pull=$("#patch-pull"); if(pull) pull.onclick=()=>{if(confirm(`Pull latest active Git patch on ${patchAll?'all Git-managed devices':d.name||d.uid}? It reboots.`))ws.send("pull_patch",{uid:patchTarget()});};
    const patchDrop=$("#patch-drop"); if(patchDrop) patchDrop.onclick=()=>{const p=patchSelect.value;if(p&&confirm(`Delete patch "${p}" from ${patchAll?'all devices where it is inactive':d.name||d.uid}?`))ws.send("drop_distribution",{uid:patchTarget(),kind:"patch",name:p});};
    const patchAdd=$("#patch-add"); if(patchAdd) patchAdd.onclick=()=>{const u=$("#patch-user").value.trim(),r=$("#patch-repo").value.trim(); if(u&&r)ws.send("add_patch",{uid:patchTarget(),user:u,repo:r});};
  }
  const distributionTarget=$("#distribution-all");
  if(distributionTarget) distributionTarget.onchange=()=>{ distributionAll=distributionTarget.checked; renderDetail(); };
  const distributionTargetUid=()=>distributionAll?"all":d.uid;
  const needsRestartConfirmation = item => {
    if (item.kind !== "patch") return false;
    const targets = distributionAll ? Object.values(installation.devices || {}).filter(device=>Number(device.id)>=0) : [d];
    return targets.some(device => !Array.isArray(device.patches) || !device.patches.length || device.patches.some(p=>p.active&&p.name===item.name));
  };
  const sendItem = item => {
    let confirmedActive = false;
    if (needsRestartConfirmation(item)) {
      confirmedActive = confirm(`Sending active patch "${item.name}" will stop and restart the engine on the target device(s). Continue?`);
      if (!confirmedActive) return;
    }
    ws.send("send_distribution", {uid:distributionTargetUid(),kind:item.kind,name:item.name,confirmed_active:confirmedActive});
  };
  document.querySelectorAll(".distribution-item").forEach(row => {
    const item = [...distribution.patches, ...distribution.assets].find(entry=>entry.kind===row.dataset.kind&&entry.name===row.dataset.name);
    const send=row.querySelector("[data-send]"); if(send&&!send.disabled) send.onclick=()=>sendItem(item);
    const drop=row.querySelector("[data-drop-asset]"); if(drop) drop.onclick=()=>{if(confirm(`Remove asset slot "${item.name}" from ${distributionAll?'all devices':d.name||d.uid}?`))ws.send("drop_distribution",{uid:distributionTargetUid(),kind:"asset",name:item.name});};
  });
  const syncAll=$("#sync-all"); if(syncAll) syncAll.onclick=()=>{
    const patchItems=distribution.patches || [];
    const restart=patchItems.some(needsRestartConfirmation);
    let confirmedActive=false;
    if(restart){confirmedActive=confirm("Sync all includes active patches. Their engines will stop and restart on the target device(s). Continue?");if(!confirmedActive)return;}
    ws.send("sync_distribution",{uid:distributionTargetUid(),confirmed_active:confirmedActive});
  };
  const refreshDistribution=$("#refresh-distribution"); if(refreshDistribution) refreshDistribution.onclick=()=>ws.send("refresh_distribution",{});
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
document.querySelectorAll("[data-all]").forEach(b=>b.onclick=()=>{const verb=b.dataset.all;if(["reboot","updatebopos"].includes(verb)&&!confirm(`${actionLabel(verb)} all devices?`))return;ws.send("action",{uid:"all",verb});});
