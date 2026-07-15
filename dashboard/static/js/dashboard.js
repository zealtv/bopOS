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
let fleetPatchChoice = null;
let renderedFleetDesired = null;
let distribution = {assets: [], patches: []};
let distributionAll = false;
let editorPatchChoice = null;
let manifestDraft = null;
let manifestBaseline = null;
let manifestDirty = false;
let manifestFeedback = "";
let pendingCreatedPatch = null;
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

function mergeDevice(device) {
  if (device && device.uid) {
    installation.devices[device.uid] = device;
    if (device.editor && installation.editor) {
      installation.editor.engine_alive = Number(device.engine_alive || 0);
      installation.editor.status = device.engine_alive ? "running" : "engine closed";
    }
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
ws.on("distribution", data => {
  distribution=data||{assets:[],patches:[]};
  if (pendingCreatedPatch && (distribution.patches||[]).some(item=>item.valid&&item.name===pendingCreatedPatch)) {
    editorPatchChoice=pendingCreatedPatch; pendingCreatedPatch=null;
  }
  render();
});
ws.on("manifest_saved", data => {
  const patch=data?.patch||editorPatchChoice;
  const declarations=data?.declarations||data?.params||[];
  if (patch && patch===editorPatchChoice) {
    manifestDraft={patch,params:structuredClone(declarations),cues:structuredClone(data.cues||[])};
    manifestBaseline=structuredClone(manifestDraft);
    manifestDirty=false;
  }
  if (installation.editor && installation.editor.patch===patch) {
    installation.editor.declarations=structuredClone(declarations);
    installation.editor.cues=structuredClone(data.cues||[]);
  }
  const warnings=(data?.warnings||[data?.pd_receive_warning]).filter(Boolean);
  manifestFeedback=warnings.length?`Saved with warning: ${warnings.join(" ")}`:"Manifest saved. Live controls refreshed; the engine was not restarted.";
  render();
});
ws.on("patch_created", data => {
  if (data?.patch) pendingCreatedPatch=data.patch;
  manifestDraft=null; manifestBaseline=null; manifestDirty=false;
  manifestFeedback=data?.template_copied
    ? `Created ${data.patch} with a manifest and a verbatim copy of Bob's patch template.`
    : (data?.status||`Created ${data?.patch||"patch"} manifest-only; no template was copied.`);
  ws.send("refresh_distribution",{});
  render();
});
ws.on("notification", data => {
  if (data?.scope==="patch_editor" || data?.patch) {
    manifestFeedback=String(data.message||data.status||""); render();
  }
});
ws.on("status", data => {
  if (data?.scope==="patch_editor") {
    manifestFeedback=String(data.message||data.status||""); render();
  }
});
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
ws.on("error", data => {
  if (manifestFeedback.endsWith("…")) {
    manifestFeedback=`Not saved: ${data.message}`;
    const feedback=$("#manifest-feedback"); if (feedback) feedback.textContent=manifestFeedback;
  }
  alert(data.message);
});
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
  renderEditor();
  renderFleetPatch();
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
  return `<div class="device-row seat-row ${Number(seat.id)===Number(selectedSeat)?'selected':''} ${badgeTone(d?.patch_badge)}" data-uid="${esc(uid)}" data-seat-id="${seat.id}" role="button" tabindex="0"><i class="dot ${state==='live'?'online':state==='sim'?'sim':'offline'}"></i>${uid?`<i class="heartbeat-blip${heartbeatAt?' pulse':''}" ${heartbeatAt?`data-heartbeat-at="${esc(heartbeatAt)}"`:''} aria-hidden="true"></i>`:''}<span><input data-seat-name aria-label="Seat ${seat.id} name" value="${esc(seat.name||`Seat ${seat.id}`)}"><small>ID ${seat.id} · ${state}</small></span>${d?patchBadge(d.patch_badge):''}</div>`;
}
const PATCH_BADGE_LABELS = {unset:"not set",unknown:"unknown / last seen",switching:"switching",missing:"missing",mismatch:"mismatch",stale:"stale",stale_unverified:"stale (unverified)",current:"current"};
const PATCH_BADGE_ORDER = ["current","switching","missing","mismatch","stale","stale_unverified","unknown","unset"];
function patchBadge(value) {
  const badge=value||"unknown", label=PATCH_BADGE_LABELS[badge]||badge.replaceAll("_"," ");
  return `<span class="patch-badge patch-badge-${esc(badge)}" title="Fleet patch: ${esc(label)}">${esc(label)}</span>`;
}
function badgeTone(value) { return value && !["current","unset"].includes(value) ? "patch-exception" : ""; }
function renderFleetPatch() {
  const select=$("#patch-select"), set=$("#patch-switch"), revert=$("#fleet-patch-revert");
  if (!select || !set || !revert) return;
  const patches=(distribution.patches||[]).filter(item=>item.valid);
  const desired=installation.fleet_patch?.name||"";
  if (desired!==renderedFleetDesired) {
    fleetPatchChoice=patches.some(item=>item.name===desired)?desired:(patches[0]?.name||null);
    renderedFleetDesired=desired;
  } else if (!patches.some(item=>item.name===fleetPatchChoice)) {
    fleetPatchChoice=patches.some(item=>item.name===desired)?desired:(patches[0]?.name||null);
  }
  select.innerHTML=patches.map(item=>`<option value="${esc(item.name)}" ${item.name===fleetPatchChoice?'selected':''}>${esc(item.name)}</option>`).join("")||'<option value="" disabled>No valid host patches</option>';
  const editing=installation.supervisor?.mode==="edit";
  select.disabled=!patches.length||editing;
  set.disabled=!fleetPatchChoice||editing;
  revert.disabled=!installation.fleet_patch?.previous?.name||editing;
  select.onchange=()=>{fleetPatchChoice=select.value;};
  set.onclick=()=>{const name=select.value;if(name&&confirm(`Set "${name}" as the fleet patch? The dashboard will converge patch bytes, then restart audio engines across online assigned devices.`))ws.send("set_fleet_patch",{patch:name,confirmed:true});};
  revert.onclick=()=>{const name=installation.fleet_patch?.previous?.name;if(name&&confirm(`Revert the fleet to patch "${name}"? The dashboard will use the same convergence and engine restart flow.`))ws.send("revert_fleet_patch",{confirmed:true});};
  $("#refresh-distribution").onclick=()=>ws.send("refresh_distribution",{});
  const assigned=Object.values(installation.seats||{}).map(occupant).filter(Boolean);
  const counts=new Map(); assigned.forEach(device=>counts.set(device.patch_badge||"unknown",(counts.get(device.patch_badge||"unknown")||0)+1));
  const summary=PATCH_BADGE_ORDER.filter(badge=>counts.has(badge)).map(badge=>`${counts.get(badge)} ${PATCH_BADGE_LABELS[badge]}`).join(" · ");
  $("#fleet-patch-summary").textContent=summary||(desired?"No assigned devices":"No fleet patch set");
}
function renderSimulation(devices) {
  const sim=installation.simulation||{active:false,status:'off'}, button=$("#simulate-toggle");
  if (!button) return;
  button.textContent=sim.active?'Stop simulation':'Start simulation';
  button.onclick=()=>{
    if (sim.active && !confirm("Stop the running simulation?")) return;
    ws.send("set_simulation",{active:!sim.active,confirmed:sim.active});
  };
  $("#simulate-status").textContent=sim.active&&sim.patch?`${sim.status||'running'} · ${sim.patch}`:(sim.status||'off');
  const real=devices.filter(d=>!d.virtual&&d.online).length;
  $("#simulate-real-note").textContent=sim.active&&real?`${real} real device${real===1?'':'s'} online (not driven)`:'';
  const edit=$("#edit-sim-patch");
  edit.hidden=!sim.active;
  edit.onclick=()=>{
    const patch=sim.patch;
    if (patch && confirm(`Stop the running simulation and edit "${patch}"?`)) {
      ws.send("set_edit",{active:true,patch,confirmed:true});
    }
  };
}

function manifestSource(editor, patches, patch) {
  const item=patches.find(candidate=>candidate.name===patch)||{};
  const embedded=item.manifest && typeof item.manifest==="object" ? item.manifest : {};
  const current=editor.patch===patch ? editor : {};
  const params=current.declarations||embedded.params||item.params||item.declarations;
  const cues=current.cues||embedded.cues||item.cues;
  return {
    engine:current.engine??embedded.engine??item.engine,
    entrypoint:current.entrypoint??embedded.entrypoint??item.entrypoint,
    caps:current.caps??embedded.caps??item.caps??[],
    slots:current.slots??embedded.slots??item.slots??[],
    params:Array.isArray(params)?params:[],
    cues:Array.isArray(cues)?cues:[],
    available:Array.isArray(params)||Array.isArray(cues)||Boolean(current.engine||embedded.engine||item.engine),
    editable:Boolean(editor.active&&editor.patch===patch),
  };
}
function resetManifestDraft(patch, source) {
  manifestDraft={patch,params:structuredClone(source.params),cues:structuredClone(source.cues)};
  manifestBaseline=structuredClone(manifestDraft);
  manifestDirty=false;
}
function manifestValue(value) {
  if (Array.isArray(value)) return value.length?value.map(item=>typeof item==="string"?item:JSON.stringify(item)).join(", "):"none";
  return value??"—";
}
function paramManifestRow(param, index) {
  const legacy=param.type==="s", disabled=legacy?"disabled":"";
  return `<div class="manifest-row manifest-param" data-param-index="${index}">
    <label>name<input data-manifest-field="name" type="text" value="${esc(param.name||"")}" autocomplete="off" ${disabled}></label>
    <label>type<select data-manifest-field="type" ${disabled}><option value="f" ${param.type==="f"?"selected":""}>float</option><option value="i" ${param.type==="i"?"selected":""}>integer</option>${legacy?'<option value="s" selected>string (legacy, read-only)</option>':''}</select></label>
    <label>min<input data-manifest-field="min" type="number" step="any" value="${esc(param.min??"")}" ${disabled}></label>
    <label>max<input data-manifest-field="max" type="number" step="any" value="${esc(param.max??"")}" ${disabled}></label>
    <label>default<input data-manifest-field="default" type="number" step="any" value="${esc(param.default??"")}" ${disabled}></label>
    <label>group<input data-manifest-field="group" type="text" value="${esc(param.group||"")}" autocomplete="off" ${disabled}></label>
    <label class="manifest-check"><input data-manifest-field="facilitator" type="checkbox" ${param.facilitator===true?"checked":""} ${disabled}> facilitator</label>
    <button data-remove-param="${index}" class="danger" title="${legacy?'Legacy string declarations are read-only':'Remove parameter'}" ${disabled}>${legacy?'Read-only':'Remove'}</button>
  </div>`;
}
function cueManifestRow(cue, index) {
  return `<div class="manifest-row manifest-cue" data-cue-index="${index}">
    <label>ID<input data-manifest-field="id" type="text" value="${esc(cue.id||"")}" autocomplete="off"></label>
    <label>label<input data-manifest-field="label" type="text" value="${esc(cue.label||"")}" autocomplete="off"></label>
    <label>description<input data-manifest-field="description" type="text" value="${esc(cue.description||"")}" autocomplete="off"></label>
    <button data-remove-cue="${index}" class="danger">Remove</button>
  </div>`;
}
function bindManifestEditor(source) {
  document.querySelectorAll(".manifest-param").forEach(row=>{
    const index=Number(row.dataset.paramIndex);
    row.querySelectorAll("[data-manifest-field]").forEach(input=>{
      input.oninput=input.onchange=()=>{
        const field=input.dataset.manifestField;
        manifestDraft.params[index][field]=input.type==="checkbox"?input.checked:(input.type==="number"?(input.value===""?"":Number(input.value)):input.value);
        manifestDirty=true;
      };
    });
  });
  document.querySelectorAll(".manifest-cue").forEach(row=>{
    const index=Number(row.dataset.cueIndex);
    row.querySelectorAll("[data-manifest-field]").forEach(input=>input.oninput=input.onchange=()=>{
      manifestDraft.cues[index][input.dataset.manifestField]=input.value; manifestDirty=true;
    });
  });
  document.querySelectorAll("[data-remove-param]").forEach(button=>button.onclick=()=>{
    const param=manifestDraft.params[Number(button.dataset.removeParam)];
    if (!confirm(`Remove parameter "${param?.name||"unnamed"}"? Pure Data receives do not change automatically; update the corresponding [receive] in the patch.`)) return;
    manifestDraft.params.splice(Number(button.dataset.removeParam),1); manifestDirty=true; renderManifestEditor(source);
  });
  document.querySelectorAll("[data-remove-cue]").forEach(button=>button.onclick=()=>{
    manifestDraft.cues.splice(Number(button.dataset.removeCue),1); manifestDirty=true; renderManifestEditor(source);
  });
}
function renderManifestEditor(source) {
  const panel=$("#manifest-editor"); if (!panel) return;
  const patch=editorPatchChoice;
  panel.hidden=!patch;
  if (!patch) return;
  if (!manifestDraft || manifestDraft.patch!==patch || (!manifestDirty && JSON.stringify({params:source.params,cues:source.cues})!==JSON.stringify({params:manifestDraft.params,cues:manifestDraft.cues}))) {
    resetManifestDraft(patch,source);
  }
  $("#manifest-readonly").innerHTML=`<dl><dt>Engine</dt><dd>${esc(manifestValue(source.engine))}</dd><dt>Entrypoint</dt><dd>${esc(manifestValue(source.entrypoint))}</dd><dt>Capabilities</dt><dd>${esc(manifestValue(source.caps))}</dd><dt>Asset slots</dt><dd>${esc(manifestValue(source.slots))}</dd></dl>`;
  $("#manifest-params").innerHTML=manifestDraft.params.map(paramManifestRow).join("")||'<p class="dim">No parameters declared.</p>';
  $("#manifest-cues").innerHTML=manifestDraft.cues.map(cueManifestRow).join("")||'<p class="dim">No cues declared.</p>';
  $("#manifest-feedback").textContent=manifestFeedback||(source.editable
    ? "Renaming or removing a parameter does not update Pure Data: its [receive] name must be changed in the patch too."
    : "Launch this patch in edit mode to change its manifest.");
  const addParam=$("#manifest-add-param"), addCue=$("#manifest-add-cue");
  addParam.disabled=!source.editable; addCue.disabled=!source.editable;
  addParam.onclick=()=>{manifestDraft.params.push({name:"",type:"f",min:0,max:1,default:0,group:"parameters",facilitator:false});manifestDirty=true;renderManifestEditor(source);};
  addCue.onclick=()=>{manifestDraft.cues.push({id:"",label:"",description:""});manifestDirty=true;renderManifestEditor(source);};
  const save=$("#manifest-save"); save.disabled=!source.available||!source.editable;
  save.title=!source.available?"Manifest data is not available for this patch.":(!source.editable?"Launch this patch in the editor before saving.":"");
  save.onclick=()=>{
    const before=(manifestBaseline?.params||[]).map(param=>param.name);
    const after=manifestDraft.params.map(param=>param.name);
    const changed=before.filter((name,index)=>name && (after[index]!==name || !after.includes(name)));
    if (changed.length && !confirm(`Save parameter rename/removal (${changed.join(", ")})? Pure Data receives do not follow manifest changes; update each corresponding [receive] in the patch.`)) return;
    manifestFeedback="Saving manifest…";
    ws.send("save_patch_manifest",{patch,params:structuredClone(manifestDraft.params),cues:structuredClone(manifestDraft.cues)});
    save.blur();
    $("#manifest-feedback").textContent=manifestFeedback;
  };
  bindManifestEditor(source);
  if (!source.editable) document.querySelectorAll("#manifest-params input, #manifest-params select, #manifest-params button, #manifest-cues input, #manifest-cues button").forEach(control=>{control.disabled=true;});
}

function editorControl(declaration, value) {
  const badge=declaration.facilitator?'<b class="badge facilitator-badge">facilitator</b>':'';
  const name=`${esc(declaration.name)} ${badge}`;
  if (declaration.type === "s") return `<label><span>${name}</span><input data-editor-param="${esc(declaration.name)}" type="text" value="${esc(value)}"></label>`;
  if (declaration.type === "i" && declaration.min===0 && declaration.max===1) return `<label class="toggle"><span>${name}</span><input data-editor-param="${esc(declaration.name)}" type="checkbox" ${value?'checked':''}></label>`;
  return `<label><span>${name}</span><output>${esc(value)}</output><input data-editor-param="${esc(declaration.name)}" type="range" min="${declaration.min??0}" max="${declaration.max??1}" step="${declaration.type==='i'?1:0.01}" value="${esc(value)}"></label>`;
}
function renderEditor() {
  const editor=installation.editor||{active:false,status:"off",declarations:[],params:{}}, mode=installation.supervisor?.mode||"off";
  const patches=(distribution.patches||[]).filter(item=>item.valid);
  const select=$("#editor-patch"), launch=$("#editor-launch");
  if (!select || !launch) return;
  if (!editorPatchChoice || !patches.some(item=>item.name===editorPatchChoice)) {
    editorPatchChoice=editor.patch&&patches.some(item=>item.name===editor.patch)
      ? editor.patch : (installation.fleet_patch?.name&&patches.some(item=>item.name===installation.fleet_patch.name)
        ? installation.fleet_patch.name : patches[0]?.name);
  }
  if (document.activeElement!==select) {
    select.innerHTML=patches.map(item=>`<option value="${esc(item.name)}" ${item.name===editorPatchChoice?'selected':''}>${esc(item.name)}</option>`).join("")||'<option value="" disabled>No valid host patches</option>';
  }
  select.disabled=!patches.length;
  select.onchange=()=>{
    editorPatchChoice=select.value; manifestDraft=null; manifestBaseline=null; manifestDirty=false; manifestFeedback="";
    select.blur(); renderEditor();
  };
  const newPatch=$("#editor-new-patch");
  newPatch.onclick=()=>{
    const name=prompt("New patch name (letters, numbers, . _ or -):","")?.trim();
    if (!name) return;
    manifestFeedback=`Creating ${name}…`;
    ws.send("create_patch",{name});
    renderEditor();
  };
  launch.disabled=!patches.length;
  launch.textContent=editor.active?'Launch selected patch':'Launch editor';
  launch.onclick=()=>{
    const patch=select.value;
    if (!patch) return;
    if (mode==="simulate" && !confirm(`Stop the running simulation and edit "${patch}"?`)) return;
    ws.send("set_edit",{active:true,patch,confirmed:mode==="simulate"});
  };
  $("#editor-status").textContent=editor.active?`${editor.status||"running"} · ${editor.patch}`:(editor.status||"off");
  const closed=editor.active&&editor.engine_alive!=null&&Number(editor.engine_alive)===0;
  $("#editor-engine-note").textContent=closed
    ? "Engine closed. It will stay closed until you explicitly relaunch it."
    : editor.active ? (editor.engine==="pd"?"PD is open for live editing.":"Runtime controls are live; GUI editing is PD-only in v1.")
      : "Launch a valid host patch through the managed audition runtime.";
  const actions=$("#editor-session-actions");
  actions.innerHTML=editor.active
    ? `${closed?'<button id="editor-relaunch">Relaunch</button>':''}<button id="editor-restart">Restart</button><button id="editor-hear-sim">Hear it in the sim</button><button id="editor-stop">Stop</button>`:"";
  $("#editor-relaunch")?.addEventListener("click",()=>ws.send("relaunch_edit",{}));
  $("#editor-restart")?.addEventListener("click",()=>ws.send("restart_edit",{}));
  $("#editor-hear-sim")?.addEventListener("click",()=>ws.send("set_simulation",{active:true,patch:editor.patch}));
  $("#editor-stop")?.addEventListener("click",()=>ws.send("set_edit",{active:false}));
  const focused=document.activeElement;
  const source=manifestSource(editor,patches,editorPatchChoice);
  if (!$("#manifest-editor").contains(focused)) renderManifestEditor(source);
  if ((interacting || focused?.matches?.('input[type="text"], input[type="number"], select'))
      && $("#editor-panel").contains(focused)) return;
  const groups=[];
  for (const declaration of editor.declarations||[]) {
    const name=declaration.group||"parameters";
    let group=groups.find(item=>item.name===name);
    if (!group) { group={name,items:[]}; groups.push(group); }
    group.items.push(declaration);
  }
  const controls=groups.map(group=>`<h3>${esc(group.name)}</h3>${group.items.map(item=>editorControl(item,editor.params?.[item.name]??item.default??"")).join("")}`).join("");
  $("#editor-params").innerHTML=editor.active
    ? `<h3>master</h3><label><span>master</span><output>${Math.round(master*100)}%</output><input id="editor-master" type="range" min="0" max="1" step="0.01" value="${master}"></label>${controls||'<p class="dim">No manifest parameters.</p>'}`:"";
  document.querySelectorAll("[data-editor-param]").forEach(input=>{
    const send=()=>{const value=input.type==="checkbox"?(input.checked?1:0):(input.type==="range"?Number(input.value):input.value);editor.params[input.dataset.editorParam]=value;ws.send("set_editor_param",{name:input.dataset.editorParam,value});};
    if(input.type==="range") {
      let pending=null;
      input.oninput=()=>{if(input.previousElementSibling?.tagName==="OUTPUT")input.previousElementSibling.value=input.value;if(pending===null)pending=requestAnimationFrame(()=>{pending=null;send();});};
      input.onchange=send;
    } else {
      input.onchange=send;
    }
  });
  const editorMaster=$("#editor-master");
  if(editorMaster) editorMaster.oninput=()=>{master=Number(editorMaster.value);editorMaster.previousElementSibling.value=Math.round(master*100)+"%";ws.send("set_master",{value:master});};
}
function row(d) {
  const status = d.online ? (Number(d.engine_alive) === 0 ? "crashed" : "online") : "offline";
  const heartbeatAt = heartbeats.get(d.uid);
  return `<button class="device-row ${d.uid===selected?'selected':''} ${badgeTone(d.patch_badge)}" data-uid="${esc(d.uid)}"><i class="dot ${status}"></i><i class="heartbeat-blip${heartbeatAt?' pulse':''}" ${heartbeatAt?`data-heartbeat-at="${esc(heartbeatAt)}"`:''} aria-hidden="true"></i><span><strong>${esc(d.hostname || d.uid)}</strong><small>${esc(d.uid)} · ${esc(d.version)}${d.rssi != null ? ` · ${d.rssi} dBm` : ''}</small></span>${patchBadge(d.patch_badge)}</button>`;
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
  const editorMaster=$("#editor-master");
  if(editorMaster&&document.activeElement!==editorMaster) editorMaster.value=master;
  if(editorMaster?.previousElementSibling) editorMaster.previousElementSibling.value=Math.round(master*100)+"%";
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
document.addEventListener("pointerdown", e => { if (e.target.closest("#detail input, #detail select, #editor-panel input, #editor-panel select")) interacting = true; });
document.addEventListener("pointerup", () => { interacting = false; });

function patchDiagnostics(d, allowRemediation) {
  const installed=Array.isArray(d.patches)?d.patches:[];
  const active=installed.find(patch=>patch.active)||installed.find(patch=>patch.name===d.report?.patch);
  const desired=installation.fleet_patch||{};
  const fetchPhase=desired.name?(d.fetch||{})[`patch:${desired.name}`]:null;
  const rows=installed.map(patch=>`<tr><td>${patch.git?'◆ ':''}${esc(patch.name)}</td><td>${patch.active?'active':'inactive'}</td><td>${patch.manifest?'valid':'invalid'}</td><td>${patch.git?'git-managed':'host-mirrored'}</td><td><code>${esc(patch.fingerprint||'unreported')}</code></td></tr>`).join("");
  const remediation=allowRemediation&&d.online&&["missing","stale","stale_unverified","mismatch"].includes(d.patch_badge)
    ? `<button id="fleet-patch-retry">${d.patch_badge==="mismatch"?'Re-switch':'Retry'}</button>`:"";
  const pull=d.online&&active?.git?'<button id="patch-pull">Pull latest</button>':"";
  return `<section id="patch-diagnostics"><div class="section-head"><h2>Patch diagnostics</h2>${patchBadge(d.patch_badge)}</div><p class="dim">observed current: <b>${esc(active?.name??d.report?.patch??'—')}</b></p><dl><dt>Desired fleet patch</dt><dd>${esc(desired.name||'not set')}</dd><dt>Desired fingerprint</dt><dd><code>${esc(desired.fingerprint||'—')}</code></dd><dt>Observed active patch</dt><dd>${esc(active?.name??d.report?.patch??'—')}</dd><dt>Reported content identity</dt><dd><code>${esc(active?.fingerprint||'unreported')}</code></dd><dt>Fetch phase</dt><dd>${esc(fetchPhase||'none')}</dd><dt>Manifest / framework git</dt><dd>${esc(active?.manifest?'valid manifest':'invalid or unreported manifest')} · ${active?.git?'git-managed patch':'host-mirrored patch'} · bopOS ${esc(d.report?.git_rev||'—')}</dd></dl><h3>Installed patches</h3><div class="patch-table-wrap"><table class="patch-table"><thead><tr><th>Patch</th><th>State</th><th>Manifest</th><th>Source</th><th>Fingerprint / content identity</th></tr></thead><tbody>${rows||'<tr><td colspan="5">No patch listing reported.</td></tr>'}</tbody></table></div>${remediation||pull?`<div class="actions patch-remediation">${remediation}${pull}</div>`:''}${d.virtual?'<p class="dim">Host-backed simulated fleet; patch choice is controlled globally and needs no Send step.</p>':''}</section>`;
}
function bindPatchDiagnostics(d) {
  const retry=$("#fleet-patch-retry");
  if(retry) retry.onclick=()=>ws.send("retry_fleet_patch",{uid:d.uid});
  const pull=$("#patch-pull");
  if(pull) pull.onclick=()=>{if(confirm(`Pull latest active Git patch on ${d.name||d.uid}? It reboots.`))ws.send("pull_patch",{uid:d.uid});};
}

function renderDetail() {
  const seat = installation.seats?.[String(selectedSeat)] || installation.seats?.[selectedSeat];
  const runtime = installation.devices[selected] || (seat && occupant(seat));
  if (!seat) {
    if(!runtime) { $("#detail").innerHTML='<section><p class="dim">Select a seat or device.</p></section>'; return; }
    const empty=Object.values(installation.seats||{}).filter(s=>!s.bound);
    const draft=bindingSeatDrafts.get(runtime.uid);
    $("#detail").innerHTML=`<section><h2>Unbound device</h2><dl><dt>UID</dt><dd>${esc(runtime.uid)}</dd><dt>Hostname</dt><dd>${esc(runtime.hostname||runtime.uid)}</dd><dt>Status</dt><dd>${runtime.online?'online':'offline'}</dd></dl><div class="assign"><label>empty seat <select id="device-seat">${empty.map(s=>`<option value="${s.id}" ${Number(s.id)===Number(draft)?'selected':''}>${esc(s.name||`Seat ${s.id}`)}</option>`).join('')}</select></label><button id="device-bind" ${empty.length?'':'disabled'}>Bind</button><button id="device-forget">Forget</button><button data-identify>Identify</button></div></section>${patchDiagnostics(runtime,false)}`;
    $("#device-seat").onchange=()=>bindingSeatDrafts.set(runtime.uid,Number($("#device-seat").value));
    $("#device-bind").onclick=()=>{const id=Number($("#device-seat").value);bindingSeatDrafts.delete(runtime.uid);bindDeviceToSeat(id,runtime);};
    $("#device-forget").onclick=()=>{const recent=Date.now()/1000-Number(runtime.last_seen||0)<30;if(!recent||confirm(`Forget recently seen ${runtime.hostname||runtime.uid}?`))ws.send("forget_device",{uid:runtime.uid});};
    document.querySelectorAll("[data-identify]").forEach(b=>b.onclick=()=>ws.send("identify",{uid:runtime.uid}));
    bindPatchDiagnostics(runtime);
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
  const simulating = !!installation.simulation?.active && !!d.virtual;
  const assetRows = distribution.assets.map(item => distributionRow(d, item)).join("");
  $("#detail").innerHTML = `<section><h2>${esc(d.name || d.uid)} ${d.undeclared?'<b class="badge">UNDECLARED</b>':''}</h2><dl><dt>UID</dt><dd>${esc(d.uid)}</dd><dt>ID</dt><dd>${esc(d.id)}</dd><dt>Status</dt><dd>${d.online?'online':'offline'}</dd><dt>Version</dt><dd>${esc(d.version)}</dd><dt>Engine</dt><dd>${d.engine_alive?'alive':'stopped'}</dd><dt>RSSI</dt><dd>${esc(d.rssi)}</dd><dt>IP</dt><dd>${esc(d.ip)}</dd><dt>Converged</dt><dd>${d.rev?`${esc(d.rev.sha)} (${esc(d.rev.model)}, ${ago(d.rev.at)})`:'—'}</dd></dl></section>
    <section><h2>Seat</h2><div class="assign"><label>name <input id="seat-name" type="text" value="${esc(seat?.name||'')}"></label><label>ID <input type="number" value="${seat?.id}" disabled></label><button id="seat-rename">Apply</button><button id="seat-remove">Remove seat</button></div><div class="assign"><label>device <select id="seat-device"><option value="">unbound</option>${Object.values(installation.devices||{}).filter(x=>!x.virtual).map(x=>`<option value="${esc(x.uid)}" ${seat?.bound===x.uid?'selected':''}>${esc(x.hostname||x.uid)}</option>`).join('')}</select></label><button id="seat-bind">${seat?.bound?'Rebind':'Bind'}</button>${seat?.bound?'<button id="seat-unbind">Unbind</button>':''}</div></section>
    <section><h2>Position</h2><div class="position-grid">${positions}</div></section>
    ${assigned?`<section><div class="section-head"><h2>Params</h2><label><input id="broadcast" type="checkbox"> broadcast to all</label></div><div class="params">${controls || '<p class="dim">Loading declaration…</p>'}</div></section>
    ${patchDiagnostics(d,true)}
    ${simulating?'':`<section id="distribution"><div class="section-head"><h2>Asset send &amp; sync</h2><label><input id="distribution-all" type="checkbox" ${distributionAll?'checked':''}> target all online devices</label></div><p class="dim">Host asset folders mirror onto ${distributionAll?'all online devices':esc(d.name||d.uid)}. Fleet patch distribution is controlled only by the global fleet patch panel.</p><div class="distribution-actions"><button id="sync-all">Sync all assets</button></div><div class="distribution-grid">${assetRows || '<p class="dim">No host assets.</p>'}</div></section>`}
    <section><h2>Actions</h2><div class="actions">${["reboot","shutdown","restart-engine","updatebopos"].map(v=>`<button data-action="${v}">${actionLabel(v)}</button>`).join('')}<button data-identify>Identify</button></div></section>`:''}
    <section><div class="section-head"><h2>Report</h2><button id="refresh-report">Refresh report</button></div>${report(d.report)}</section>`;
  bindControls(d, seat);
  bindPatchDiagnostics(d);
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
  const distributionTarget=$("#distribution-all");
  if(distributionTarget) distributionTarget.onchange=()=>{ distributionAll=distributionTarget.checked; renderDetail(); };
  const distributionTargetUid=()=>distributionAll?"all":d.uid;
  document.querySelectorAll(".distribution-item").forEach(row => {
    const item = distribution.assets.find(entry=>entry.kind===row.dataset.kind&&entry.name===row.dataset.name);
    const send=row.querySelector("[data-send]"); if(send&&!send.disabled) send.onclick=()=>ws.send("send_distribution",{uid:distributionTargetUid(),kind:"asset",name:item.name,confirmed_active:false});
    const drop=row.querySelector("[data-drop-asset]"); if(drop) drop.onclick=()=>{if(confirm(`Remove asset slot "${item.name}" from ${distributionAll?'all devices':d.name||d.uid}?`))ws.send("drop_distribution",{uid:distributionTargetUid(),kind:"asset",name:item.name});};
  });
  const syncAll=$("#sync-all"); if(syncAll) syncAll.onclick=()=>{
    (distribution.assets||[]).forEach(item=>ws.send("send_distribution",{uid:distributionTargetUid(),kind:"asset",name:item.name,confirmed_active:false}));
  };
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
