const ws = new BopSocket("/ws");
let installation = {devices: {}};
let selected = null;
let selectedSeat = null;
let venueRebind = null;
let muted = false;
let master = 1.0;
const heartbeats = new Map();
const seatBindingDrafts = new Map();
let fleetPatchChoice = null;
let renderedFleetDesired = null;
let distribution = {assets: [], patches: []};
let distributionAll = false;
let deviceFilter = "all";
let editorPatchChoice = null;
let manifestDraft = null;
let manifestBaseline = null;
let manifestDirty = false;
let manifestFeedback = "";
let pendingCreatedPatch = null;
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
const TAB_NAMES = ["dashboard", "seats", "devices", "patches", "assets", "sequencer"];
let activeTab = TAB_NAMES.includes(location.hash.slice(1)) ? location.hash.slice(1) : "dashboard";

function activateTab(name, updateHash=true) {
  if (!TAB_NAMES.includes(name)) name="dashboard";
  activeTab=name;
  document.querySelectorAll("[data-tab]").forEach(button=>{
    const active=button.dataset.tab===name;
    button.setAttribute("aria-selected", active ? "true" : "false");
    button.tabIndex=active ? 0 : -1;
  });
  document.querySelectorAll("[data-tab-panel]").forEach(panel=>{
    panel.hidden=panel.dataset.tabPanel!==name;
  });
  if (updateHash) history.replaceState(null,"",`#${name}`);
  window.scrollTo(0,0);
  if (name==="seats" && installation.room) requestAnimationFrame(()=>Spatial.render(installation,selectedSeat,selectSeat,ws));
}
document.querySelectorAll("[data-tab]").forEach(button=>{
  button.onclick=()=>activateTab(button.dataset.tab);
  button.onkeydown=event=>{
    if (!["ArrowLeft","ArrowRight","Home","End"].includes(event.key)) return;
    event.preventDefault();
    let index=TAB_NAMES.indexOf(activeTab);
    if (event.key==="ArrowLeft") index=(index-1+TAB_NAMES.length)%TAB_NAMES.length;
    if (event.key==="ArrowRight") index=(index+1)%TAB_NAMES.length;
    if (event.key==="Home") index=0;
    if (event.key==="End") index=TAB_NAMES.length-1;
    activateTab(TAB_NAMES[index]);
    $(`[data-tab="${TAB_NAMES[index]}"]`)?.focus();
  };
});
window.addEventListener("hashchange",()=>activateTab(location.hash.slice(1),false));
activateTab(activeTab,false);

function mergeDevice(device) {
  if (device && device.uid) {
    installation.devices[device.uid] = device;
    if (device.editor && installation.editor) {
      installation.editor.engine_alive = Number(device.engine_alive || 0);
      installation.editor.status = device.engine_alive ? "running" : "engine closed";
    }
  }
  render();
}
ws.on("connection", connected => { $("#ws-status").textContent = connected ? "connected" : "disconnected"; $("#ws-status").className = connected ? "online" : "offline"; });
ws.on("state", data => { installation = data; muted = !!data.muted; master = Number(data.master ?? 1); presetNames = Object.keys(data.presets || {}).sort(); reconcileSelection(); renderPresets(); render(); });
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
ws.on("editor_points", data => {
  if (!installation.editor) return;
  installation.editor.points=data.points||{};
  Spatial.renderEditor(installation.editor,ws);
});
ws.on("editor_point_element", data => {
  if (!installation.editor) return;
  installation.editor.point_element=Number(data.element)||0;
  Spatial.renderEditor(installation.editor,ws);
});
ws.on("point_frame", data => Spatial.frame(data.points || {}));
ws.on("cue_scheduled", data => {
  const status = $("#cue-status"); if (!status) return;
  status.value = `${data.cue_id} fires in ${data.lead_ms} ms`;
});
ws.on("editor_cue_fired", data => {
  const status = $("#editor-cue-status"); if (!status) return;
  status.value = `${data.cue_id} fired`;
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
ws.on("seat_reindexed", data => {
  selectedSeat=Number(data.new_id); selected=occupant(installation.seats?.[String(selectedSeat)])?.uid||null; render();
});
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
    const name = prompt("Save current seat params + master as preset:", "");
    if (name && (!presetNames.includes(name) || confirm(`Overwrite preset "${name}"?`))) ws.send("save_preset", {name});
  };
  if (load) load.onclick = () => { const name = $("#preset-select").value; if (name) ws.send("load_preset", {name}); };
})();

function render() {
  const devices = Object.values(installation.devices || {});
  const seats = Object.values(installation.seats || {}).sort((a,b) => a.id-b.id);
  const bound = new Set(seats.map(s => s.bound).filter(Boolean));
  const physical = devices.filter(d=>!d.virtual).sort((a,b)=>Number(b.online)-Number(a.online)||(Number(b.last_seen)||0)-(Number(a.last_seen)||0));
  const visible = physical.filter(device=>{
    if (deviceFilter==="online" || deviceFilter==="offline") return !!device.online===(deviceFilter==="online");
    if (deviceFilter==="bound" || deviceFilter==="unbound") return bound.has(device.uid)===(deviceFilter==="bound");
    return true;
  });
  $("#assigned").innerHTML = seats.map(seatRow).join("") || '<p class="dim">No seats</p>';
  $("#device-roster").innerHTML = visible.map(device=>row(device,seats.find(seat=>seat.bound===device.uid))).join("") || '<p class="dim">No matching devices</p>';
  document.querySelectorAll(".seat-row").forEach(el => {
    el.onclick = event => { if (!event.target.closest("input")) selectSeat(Number(el.dataset.seatId)); };
    const input = el.querySelector("[data-seat-name]");
    input.onchange = () => ws.send("update_seat", {id:Number(el.dataset.seatId), name:input.value});
  });
  document.querySelectorAll(".device-row:not(.seat-row)").forEach(el => el.onclick = () => select(el.dataset.uid));
  $("#device-filter").value=deviceFilter;
  $("#device-filter").onchange=event=>{deviceFilter=event.target.value;render();};
  $("#forget-offline").onclick=()=>{if(confirm("Forget all offline unbound devices from this runtime roster?"))ws.send("forget_offline_unbound",{});};
  $("#seat-add").onclick=()=>{
    const id=nextFreeId(); selectedSeat=id; selected=null;
    ws.send("add_seat",{id,name:`Seat ${id}`,positions:[]});
  };
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
  renderHeader(); renderSeatDetail(); renderDeviceDetail();
}
function occupant(seat) {
  const devices=Object.values(installation.devices||{});
  return devices.find(d=>d.virtual&&Number(d.seat_id)===Number(seat.id)) || installation.devices?.[seat.bound];
}
function reconcileSelection() {
  if (selectedSeat != null) {
    const seat=installation.seats?.[String(selectedSeat)]||installation.seats?.[selectedSeat];
    if (!seat) { selectedSeat=null; selected=null; return; }
    selected=occupant(seat)?.uid||null;
    return;
  }
  if (!selected || !installation.devices?.[selected]) { selected=null; return; }
  const seat=Object.values(installation.seats||{}).find(item=>item.bound===selected);
  if (seat) selectedSeat=seat.id;
}
function seatRow(seat) {
  const d=occupant(seat), state=d?.virtual?'sim':(d?.online?'live':'empty');
  const uid=d?.uid||"";
  const heartbeatAt=heartbeats.get(uid);
  return `<div class="device-row seat-row ${Number(seat.id)===Number(selectedSeat)?'selected':''} ${badgeTone(d?.patch_badge)}" data-uid="${esc(uid)}" data-seat-id="${seat.id}" role="button" tabindex="0"><i class="dot ${state==='live'?'online':state==='sim'?'sim':'offline'}"></i>${uid?`<i class="heartbeat-blip${heartbeatAt?' pulse':''}" ${heartbeatAt?`data-heartbeat-at="${esc(heartbeatAt)}"`:''} aria-hidden="true"></i>`:''}<span><input data-seat-name aria-label="Seat ${seat.id} name" value="${esc(seat.name||`Seat ${seat.id}`)}"><small>ID ${seat.id} · ${state}</small></span>${d?patchBadge(d.patch_badge):''}</div>`;
}
const PATCH_BADGE_LABELS = {unset:"not set",unknown:"unknown / last seen",switching:"switching",timeout:"switch timed out",failed:"switch failed",missing:"missing",mismatch:"mismatch",stale:"stale",stale_unverified:"stale (unverified)",current:"current"};
const PATCH_BADGE_ORDER = ["current","switching","timeout","failed","missing","mismatch","stale","stale_unverified","unknown","unset"];
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
  set.onclick=()=>{const name=select.value;if(name&&confirm(`Deploy "${name}" as the fleet patch? The dashboard will converge patch bytes, then restart audio engines across online assigned devices.`))ws.send("set_fleet_patch",{patch:name,confirmed:true});};
  revert.onclick=()=>{const name=installation.fleet_patch?.previous?.name;if(name&&confirm(`Revert the fleet to patch "${name}"? The dashboard will use the same convergence and engine restart flow.`))ws.send("revert_fleet_patch",{confirmed:true});};
  $("#refresh-distribution").onclick=()=>ws.send("refresh_distribution",{});
  const assigned=Object.values(installation.seats||{}).map(occupant).filter(Boolean);
  const counts=new Map(); assigned.forEach(device=>counts.set(device.patch_badge||"unknown",(counts.get(device.patch_badge||"unknown")||0)+1));
  const summary=PATCH_BADGE_ORDER.filter(badge=>counts.has(badge)).map(badge=>`${counts.get(badge)} ${PATCH_BADGE_LABELS[badge]}`).join(" · ");
  $("#fleet-patch-summary").textContent=summary||(desired?"No assigned devices":"No fleet patch set");
}
function renderSimulation(devices) {
  const sim=installation.simulation||{active:false,status:'off'};
  $("#simulate-status").textContent=sim.active&&sim.patch?`${sim.status||'running'} · ${sim.patch}`:(sim.status||'off');
  const real=devices.filter(d=>!d.virtual&&d.online).length;
  $("#simulate-real-note").textContent=sim.active&&real?`${real} real device${real===1?'':'s'} online (not driven)`:'';
}

function contextualExecutionPatch() {
  const editor=installation.editor||{}, sim=installation.simulation||{};
  if (editor.active&&editor.patch) return editor.patch;
  if (activeTab==="patches"&&editorPatchChoice) return editorPatchChoice;
  return sim.patch||installation.fleet_patch?.name||editorPatchChoice||null;
}

function setExecutionTarget(target) {
  const mode=installation.supervisor?.mode||"off";
  if (target==="off") {
    if (mode==="simulate") {
      if (!confirm("Stop Simulation and return audio control to the Live fleet?")) return;
      ws.send("set_simulation",{active:false,confirmed:true});
    } else if (mode==="edit") {
      if (!confirm("Stop Patch edit and return audio control to the Live fleet?")) return;
      ws.send("set_edit",{active:false,confirmed:true});
    }
    return;
  }
  if (target==="simulate") {
    if (mode==="simulate") return;
    const patch=contextualExecutionPatch();
    const question=mode==="edit"
      ? `Stop Patch edit and hear "${patch||"the selected patch"}" in Simulation?`
      : `Run "${patch||"the selected patch"}" in Simulation? Live fleet devices will not be driven.`;
    if (!confirm(question)) return;
    ws.send("set_simulation",{active:true,patch,confirmed:true});
    return;
  }
  if (target==="edit") {
    if (mode==="simulate") {
      if (!confirm("Stop Simulation and choose a patch to edit?")) return;
      ws.send("set_simulation",{active:false,confirmed:true});
    }
    activateTab("patches");
    requestAnimationFrame(()=>$("#editor-patch")?.focus());
  }
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
function renderEditorPreview(editor) {
  Spatial.renderEditor(editor,ws);
  const cues=$("#editor-declared-cues"), free=$("#editor-cue-id"), fire=$("#editor-cue-fire");
  if (!cues || !free || !fire || !editor.active) return;
  cues.innerHTML=(editor.cues||[]).map(cue=>{
    const label=cue.label||cue.id;
    const description=cue.description?`<small>${esc(cue.description)}</small>`:"";
    return `<button data-editor-cue="${esc(cue.id)}" title="Fire ${esc(cue.id)}">${esc(label)}${description}</button>`;
  }).join("");
  const send=cueId=>{
    if (!cueId) return;
    ws.send("fire_editor_cue",{cue_id:cueId});
    $("#editor-cue-status").value=`Firing ${cueId}…`;
  };
  cues.querySelectorAll("[data-editor-cue]").forEach(button=>button.onclick=()=>send(button.dataset.editorCue));
  fire.onclick=()=>send(free.value.trim());
  free.onkeydown=event=>{if(event.key==="Enter"){event.preventDefault();fire.click();}};
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
    if (mode!=="edit") {
      const question=mode==="simulate"
        ? `Stop the running Simulation and edit "${patch}"?`
        : `Open "${patch}" in Patch edit? Live fleet devices will not be driven.`;
      if (!confirm(question)) return;
    }
    ws.send("set_edit",{active:true,patch,confirmed:mode!=="edit"});
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
  $("#editor-hear-sim")?.addEventListener("click",()=>{
    if (confirm(`Stop Patch edit and hear "${editor.patch}" in Simulation?`)) {
      ws.send("set_simulation",{active:true,patch:editor.patch,confirmed:true});
    }
  });
  $("#editor-stop")?.addEventListener("click",()=>{
    if (confirm("Stop Patch edit and return audio control to the Live fleet?")) {
      ws.send("set_edit",{active:false,confirmed:true});
    }
  });
  const focused=document.activeElement;
  const source=manifestSource(editor,patches,editorPatchChoice);
  if (!$("#manifest-editor").contains(focused)) renderManifestEditor(source);
  renderEditorPreview(editor);
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
function row(d, seat) {
  const status = d.online ? (Number(d.engine_alive) === 0 ? "crashed" : "online") : "offline";
  const heartbeatAt = heartbeats.get(d.uid);
  const assignment=d.revoking_assignment?"clearing assignment":seat?`bound · Seat ${seat.id}`:"unbound";
  return `<button class="device-row ${d.uid===selected?'selected':''} ${badgeTone(d.patch_badge)}" data-uid="${esc(d.uid)}"><i class="dot ${status}"></i><i class="heartbeat-blip${heartbeatAt?' pulse':''}" ${heartbeatAt?`data-heartbeat-at="${esc(heartbeatAt)}"`:''} aria-hidden="true"></i><span><strong>${esc(d.hostname || d.uid)}</strong><small>${esc(d.uid)} · ${esc(d.version)}${d.rssi != null ? ` · ${d.rssi} dBm` : ''}</small><small class="device-binding-badge">${esc(assignment)}</small></span>${patchBadge(d.patch_badge)}</button>`;
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
  const mode=installation.supervisor?.mode||"off";
  $("#mode-status").textContent=mode==="simulate"?"simulation":mode==="edit"?"patch edit":"live fleet";
  document.querySelectorAll("[data-execution-target]").forEach(button=>{
    const active=button.dataset.executionTarget===mode;
    button.setAttribute("aria-pressed",active?"true":"false");
  });
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
  const remediation=allowRemediation&&d.online&&["missing","stale","stale_unverified","mismatch","failed","timeout"].includes(d.patch_badge)
    ? '<button id="fleet-patch-retry">Sync to fleet patch</button>':"";
  const unboundNote=!allowRemediation&&desired.name
    ? '<p class="dim patch-target-note">Assign this device to a Seat before syncing content. OSC v1.5 does not UID-target patch distribution or switching.</p>':"";
  const pull=allowRemediation&&d.online&&active?.git?'<button id="patch-pull">Pull latest</button>':"";
  const switchAttempt=d.patch_switch||{};
  return `<section id="patch-diagnostics"><div class="section-head"><h2>Patch diagnostics</h2>${patchBadge(d.patch_badge)}</div><p class="dim">observed current: <b>${esc(active?.name??d.report?.patch??'—')}</b></p><dl><dt>Desired fleet patch</dt><dd>${esc(desired.name||'not set')}</dd><dt>Desired fingerprint</dt><dd><code>${esc(desired.fingerprint||'—')}</code></dd><dt>Observed active patch</dt><dd>${esc(active?.name??d.report?.patch??'—')}</dd><dt>Switch attempt</dt><dd>${esc(switchAttempt.status||'none')}${switchAttempt.reason?` · ${esc(switchAttempt.reason)}`:''}</dd><dt>Reported content identity</dt><dd><code>${esc(active?.fingerprint||'unreported')}</code></dd><dt>Fetch phase</dt><dd>${esc(fetchPhase||'none')}</dd><dt>Manifest / framework git</dt><dd>${esc(active?.manifest?'valid manifest':'invalid or unreported manifest')} · ${active?.git?'git-managed patch':'host-mirrored patch'} · bopOS ${esc(d.report?.git_rev||'—')}</dd></dl><h3>Installed patches</h3><div class="patch-table-wrap"><table class="patch-table"><thead><tr><th>Patch</th><th>State</th><th>Manifest</th><th>Source</th><th>Fingerprint / content identity</th></tr></thead><tbody>${rows||'<tr><td colspan="5">No patch listing reported.</td></tr>'}</tbody></table></div>${remediation||pull?`<div class="actions patch-remediation">${remediation}${pull}</div>`:''}${unboundNote}${d.virtual?'<p class="dim">Host-backed simulated fleet; patch choice is controlled globally and needs no Send step.</p>':''}</section>`;
}
function bindPatchDiagnostics(d) {
  const retry=$("#fleet-patch-retry");
  if(retry) retry.onclick=()=>ws.send("retry_fleet_patch",{uid:d.uid});
  const pull=$("#patch-pull");
  if(pull) pull.onclick=()=>{if(confirm(`Pull latest active Git patch on ${d.name||d.uid}? It reboots.`))ws.send("pull_patch",{uid:d.uid});};
}

function renderSeatDetail() {
  const panel=$("#seat-detail");
  if (!panel) return;
  const seat=installation.seats?.[String(selectedSeat)]||installation.seats?.[selectedSeat];
  if (!seat) { panel.innerHTML='<p class="dim">Select a Seat on the map or in the list.</p>'; return; }
  const active=document.activeElement;
  if (interacting || (panel.contains(active) && active.matches('input,select'))) return;
  const devices=Object.values(installation.devices||{}).filter(device=>!device.virtual);
  const boundElsewhere=new Set(Object.values(installation.seats||{})
    .filter(other=>Number(other.id)!==Number(seat.id)).map(other=>other.bound).filter(Boolean));
  const available=devices.filter(device=>!device.revoking_assignment&&(!boundElsewhere.has(device.uid)||device.uid===seat.bound));
  if (seatBindingDrafts.get(seat.id)===seat.bound) seatBindingDrafts.delete(seat.id);
  const bindingChoice=seatBindingDrafts.get(seat.id)??seat.bound??"";
  const currentKnown=devices.find(device=>device.uid===seat.bound);
  const options=[];
  if (seat.bound && !currentKnown) options.push(`<option value="${esc(seat.bound)}" ${bindingChoice===seat.bound?'selected':''}>${esc(seat.bound)} · remembered offline</option>`);
  if (currentKnown?.revoking_assignment) options.push(`<option value="${esc(currentKnown.uid)}" ${bindingChoice===currentKnown.uid?'selected':''} disabled>${esc(currentKnown.hostname||currentKnown.uid)} · clearing old assignment</option>`);
  options.push(...available.map(device=>`<option value="${esc(device.uid)}" ${device.uid===bindingChoice?'selected':''}>${esc(device.hostname||device.uid)} · ${device.online?'online':'offline'}</option>`));
  if (!seat.bound) options.unshift(`<option value="" ${bindingChoice?'':'selected'}>Choose a device</option>`);
  const room=installation.room||{}, origin=room.origin||[0,0];
  const positions=(seat.positions||[]).map((position,index)=>`<div class="position-row" data-seat-element="${index}"><strong>element ${index}</strong><label>x <input data-axis="x" type="number" step="0.01" value="${Math.round((position[0]-origin[0])*100)/100}"></label><label>y <input data-axis="y" type="number" step="0.01" value="${Math.round((position[1]-origin[1])*100)/100}"></label><button data-remove-element="${index}" class="danger">Remove</button></div>`).join('');
  const binding=seat.bound ? installation.devices?.[seat.bound] : null;
  const choiceRevoking=!!devices.find(device=>device.uid===bindingChoice)?.revoking_assignment;
  panel.innerHTML=`<h3>Seat workspace</h3>
    <div class="assign"><label>name <input id="seat-name" type="text" value="${esc(seat.name||'')}"></label><button id="seat-rename">Apply name</button></div>
    <div class="assign"><label>ID <input id="seat-id" type="number" min="0" step="1" value="${seat.id}"></label><button id="seat-reindex">Reindex</button><button id="seat-remove" class="danger">Delete Seat</button></div>
    <h3>Elements</h3><div class="position-grid">${positions||'<p class="dim">No elements positioned yet.</p>'}</div><button id="seat-element-add">Add element</button>
    <h3>Physical device</h3><small class="dim seat-binding-note">${seat.bound?`${esc(seat.bound)} · ${binding?.online?'online':binding?'offline':'waiting to be seen'}`:'No device assigned'}</small>
    <div class="assign"><label>device <select id="seat-device">${options.join('')||'<option value="">No available devices</option>'}</select></label><button id="seat-identify" ${choiceRevoking?'disabled':''}>Identify</button><button id="seat-bind" ${choiceRevoking?'disabled':''}>${seat.bound?'Assign / replace':'Assign'}</button>${seat.bound?'<button id="seat-unbind">Unassign</button>':''}</div>`;
  const savePositions=positionsValue=>{seat.positions=positionsValue;ws.send("update_seat",{id:seat.id,positions:positionsValue});Spatial.render(installation,selectedSeat,selectSeat,ws);};
  panel.querySelectorAll('[data-seat-element] input').forEach(input=>input.onchange=()=>{
    const row=input.closest('[data-seat-element]'), index=Number(row.dataset.seatElement);
    const x=Number(row.querySelector('[data-axis="x"]').value), y=Number(row.querySelector('[data-axis="y"]').value);
    if (!Number.isFinite(x)||!Number.isFinite(y)) return;
    const next=structuredClone(seat.positions||[]); next[index]=[Math.round((x+origin[0])*100)/100,Math.round((y+origin[1])*100)/100]; savePositions(next);
  });
  panel.querySelectorAll('[data-remove-element]').forEach(button=>button.onclick=()=>{const next=structuredClone(seat.positions||[]);next.splice(Number(button.dataset.removeElement),1);savePositions(next);});
  $("#seat-element-add").onclick=()=>savePositions([...(seat.positions||[]),[Number(origin[0])||0,Number(origin[1])||0]]);
  $("#seat-rename").onclick=()=>ws.send("update_seat",{id:seat.id,name:$("#seat-name").value});
  $("#seat-reindex").onclick=()=>{const next=Number($("#seat-id").value);if(Number.isInteger(next)&&next>=0&&next!==Number(seat.id)&&confirm(`Change Seat ID ${seat.id} to ${next}? Current presets follow the new ID; saved venues stay unchanged.`))ws.send("reindex_seat",{id:seat.id,new_id:next});};
  $("#seat-remove").onclick=()=>{if(confirm(`Delete Seat ${seat.id}? Its current preset entries will also be removed.`))ws.send("remove_seat",{id:seat.id});};
  const chosen=()=>$("#seat-device").value;
  $("#seat-device").onchange=()=>seatBindingDrafts.set(seat.id,chosen());
  $("#seat-identify").onclick=()=>{const uid=chosen();if(uid&&installation.devices?.[uid])ws.send("identify",{uid});};
  $("#seat-bind").onclick=()=>{const uid=chosen();if(!uid)return;const replacing=seat.bound&&seat.bound!==uid;if(!replacing||confirm(`Replace ${seat.bound} with ${uid} on Seat ${seat.id}?`))ws.send("bind_seat",{id:seat.id,uid,confirmed:!!replacing});};
  const unbind=$("#seat-unbind");if(unbind)unbind.onclick=()=>{if(confirm(`Unassign ${seat.bound} from Seat ${seat.id}?`))ws.send("unbind_seat",{id:seat.id});};
}

function renderDeviceDetail() {
  const d=installation.devices?.[selected];
  if (!d || d.virtual) { $("#detail").innerHTML='<section><p class="dim">Select a physical device.</p></section>'; return; }
  const active=document.activeElement;
  if ($("#detail").contains(active) && active.matches('input,select')) return;
  const seat=Object.values(installation.seats||{}).find(item=>item.bound===d.uid);
  const emptySeats=Object.values(installation.seats||{}).filter(item=>!item.bound).sort((a,b)=>a.id-b.id);
  const assignOptions=emptySeats.map(item=>`<option value="${item.id}">${esc(item.name||`Seat ${item.id}`)} · ID ${item.id}</option>`).join('');
  const health=!d.online?'offline':Number(d.engine_alive)===0?'engine stopped':'healthy';
  const binding=d.revoking_assignment
    ? '<section id="device-binding"><h2>Assignment</h2><p class="dim">Clearing a stale node assignment. This device cannot be rebound until it acknowledges ID -1.</p></section>'
    : seat
      ? `<section id="device-binding"><div class="section-head"><div><h2>Assignment</h2><p class="dim">Bound to ${esc(seat.name||`Seat ${seat.id}`)} · ID ${seat.id}</p></div><button id="device-open-seat">Open Seat</button></div></section>`
      : `<section id="device-binding"><h2>Assignment</h2><p class="dim">Unbound physical device. Assignment uses the same authoritative Seat transaction.</p><div class="assign"><label>empty Seat <select id="device-seat" ${assignOptions?'':'disabled'}>${assignOptions||'<option>No empty Seats</option>'}</select></label><button id="device-bind" ${assignOptions&&d.online?'':'disabled'}>Assign</button></div></section>`;
  const assetRows=distribution.assets.map(item=>distributionRow(d,item)).join("");
  $("#detail").innerHTML=`<section><h2>${esc(d.hostname||d.uid)} ${d.undeclared?'<b class="badge">UNDECLARED</b>':''}</h2><dl><dt>UID</dt><dd>${esc(d.uid)}</dd><dt>Seat</dt><dd>${seat?`${esc(seat.name||`Seat ${seat.id}`)} · ID ${seat.id}`:'unbound'}</dd><dt>Health</dt><dd class="device-health ${health==='healthy'?'online':health==='offline'?'offline':''}">${health}</dd><dt>Last seen</dt><dd>${d.last_seen?ago(d.last_seen):'—'}</dd><dt>Version</dt><dd>${esc(d.version)}</dd><dt>Engine</dt><dd>${d.engine_alive?'alive':'stopped'}</dd><dt>RSSI</dt><dd>${d.rssi==null?'wired / unavailable':esc(`${d.rssi} dBm`)}</dd><dt>IP</dt><dd>${esc(d.ip)}</dd><dt>Converged</dt><dd>${d.rev?`${esc(d.rev.sha)} (${esc(d.rev.model)}, ${ago(d.rev.at)})`:'—'}</dd></dl><p class="dim">Seat naming, IDs, positions and assignment live in the Seats workspace. Mix parameters live there too.</p></section>
    ${binding}
    ${patchDiagnostics(d,!!seat)}
    <section id="distribution"><div class="section-head"><h2>Asset send &amp; sync</h2><label><input id="distribution-all" type="checkbox" ${distributionAll?'checked':''}> target all online devices</label></div><div class="distribution-actions"><button id="sync-all">Sync all assets</button></div><div class="distribution-grid">${assetRows||'<p class="dim">No host assets.</p>'}</div></section>
    <section><h2>Actions</h2><div class="actions"><button data-identify ${d.online?'':'disabled'}>Identify</button>${["reboot","shutdown","restart-engine","updatebopos"].map(v=>`<button data-action="${v}" ${d.online?'':'disabled'}>${actionLabel(v)}</button>`).join('')}${seat?'':'<button id="device-forget">Forget</button>'}</div></section>
    <section><div class="section-head"><h2>Report</h2><button id="refresh-report" ${d.online?'':'disabled'}>Refresh report</button></div>${report(d.report)}</section>`;
  bindDeviceDetailControls(d); bindPatchDiagnostics(d);
}

function bindDeviceDetailControls(d) {
  document.querySelectorAll("#detail [data-action]").forEach(button=>button.onclick=()=>{const verb=button.dataset.action;if(!confirm(`${actionLabel(verb)} ${d.hostname||d.uid}?`))return;ws.send("action",{uid:d.uid,verb});});
  document.querySelectorAll("#detail [data-identify]").forEach(button=>button.onclick=()=>ws.send("identify",{uid:d.uid}));
  const openSeat=$("#device-open-seat");if(openSeat)openSeat.onclick=()=>{const seat=Object.values(installation.seats||{}).find(item=>item.bound===d.uid);if(seat){selectSeat(Number(seat.id));activateTab("seats");}};
  const bind=$("#device-bind");if(bind)bind.onclick=()=>{const id=Number($("#device-seat").value);if(Number.isInteger(id))ws.send("bind_seat",{id,uid:d.uid,confirmed:false});};
  const forget=$("#device-forget");if(forget)forget.onclick=()=>{if(confirm(`Forget ${d.hostname||d.uid}?`))ws.send("forget_device",{uid:d.uid});};
  $("#refresh-report").onclick=()=>ws.send("request_report",{uid:d.uid});
  const target=$("#distribution-all");if(target)target.onchange=()=>{distributionAll=target.checked;renderDeviceDetail();};
  const targetUid=()=>distributionAll?"all":d.uid;
  document.querySelectorAll("#detail .distribution-item").forEach(row=>{
    const item=distribution.assets.find(entry=>entry.kind===row.dataset.kind&&entry.name===row.dataset.name);
    const send=row.querySelector("[data-send]");if(send&&!send.disabled)send.onclick=()=>ws.send("send_distribution",{uid:targetUid(),kind:"asset",name:item.name,confirmed_active:false});
    const drop=row.querySelector("[data-drop-asset]");if(drop)drop.onclick=()=>{if(confirm(`Remove asset slot "${item.name}"?`))ws.send("drop_distribution",{uid:targetUid(),kind:"asset",name:item.name});};
  });
  const sync=$("#sync-all");if(sync)sync.onclick=()=>distribution.assets.forEach(item=>ws.send("send_distribution",{uid:targetUid(),kind:"asset",name:item.name,confirmed_active:false}));
}

function actionLabel(verb) { return verb === "updatebopos" ? "Update bopOS" : verb.replaceAll("-", " "); }
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
$("#mute-all").onclick=()=>{muted=!muted;ws.send("mute_all",{value:muted?1:0});renderHeader();};
{
  const input = $("#master");
  let last = 0, timer;
  const send = () => { master = Number(input.value); ws.send("set_master", {value: master}); renderHeader(); };
  input.oninput = () => { const now = performance.now(); if (now-last >= 33) { last=now; send(); } else { clearTimeout(timer); timer=setTimeout(send, 33-(now-last)); } };
  input.onchange = send;
  input.onpointerup = send;
}
document.querySelectorAll("[data-all]").forEach(b=>b.onclick=()=>{const verb=b.dataset.all;if(!confirm(`${actionLabel(verb)} all physical devices?`))return;ws.send("action",{uid:"all",verb});});
document.querySelectorAll("[data-execution-target]").forEach(button=>button.onclick=()=>setExecutionTarget(button.dataset.executionTarget));
