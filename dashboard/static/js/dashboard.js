const ws = new BopSocket("/ws");
let installation = {devices: {}};
let selected = null;
let selectedSeat = null;
let selectedGroup = null;
let focusedGroup = null;
let visibleGroups = [null, null, null, null];
let groupMemberFilter = "";
let seatRosterFilter = "";
let seatSidebarMode = "seats";
let groupMessage = "";
let venueRebind = null;
let muted = false;
let master = 1.0;
const heartbeats = new Map();
const seatBindingDrafts = new Map();
const logDestinationDrafts = new Map();  // uid -> unsaved log destination choice
let presetNames = [];
let fleetPatchChoice = null;
let fleetPatchTarget = "all";
let patchHandoffDevice = null;
let renderedFleetDesired = null;
let distribution = {assets: [], patches: []};
let assetTarget = null;
let assetFeedback = "";
let assetFeedbackPending = null;
let deviceFilter = "all";
let editorPatchChoice = null;
let manifestDraft = null;
let manifestBaseline = null;
let manifestDirty = false;
let manifestFeedback = "";
let pendingCreatedPatch = null;
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
const Identity = window.DeviceIdentity;

async function copyFullIdentity(button) {
  const value=button.dataset.copyIdentity;
  let copied=false;
  try {
    if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(value);copied=true;}
  } catch(_error) {}
  if(!copied){
    const input=document.createElement("textarea");
    input.value=value;input.setAttribute("readonly","");input.style.position="fixed";input.style.opacity="0";
    document.body.append(input);input.select();
    try{copied=document.execCommand("copy");}catch(_error){}
    input.remove();
  }
  const feedback=button.querySelector(".copy-feedback");
  if(feedback){feedback.textContent=copied?"Copied":"Copy failed";setTimeout(()=>{if(feedback.isConnected)feedback.textContent="";},1400);}
}
document.addEventListener("click",event=>{const button=event.target.closest("[data-copy-identity]");if(button)copyFullIdentity(button);});
const GROUP_SLOTS = [
  {colour:"#56B4E9", pattern:"solid"},
  {colour:"#E69F00", pattern:"dash"},
  {colour:"#00B98B", pattern:"dot"},
  {colour:"#CC79A7", pattern:"dash-dot"},
];
const TAB_NAMES = ["show", "control", "seats", "devices", "patches", "assets"];
// The Control tab was called Dashboard until 2026-07-25 (37/10). Existing
// bookmarks and links still say #dashboard, so keep resolving it.
const TAB_ALIASES = {dashboard: "control"};
function tabFromHash(hash) {
  const name = TAB_ALIASES[hash] || hash;
  return TAB_NAMES.includes(name) ? name : null;
}
let activeTab = tabFromHash(location.hash.slice(1)) || "show";

function activateTab(name, updateHash=true) {
  if (!TAB_NAMES.includes(name)) name="show";
  activeTab=name;
  document.querySelectorAll("[data-tab]").forEach(button=>{
    const active=button.dataset.tab===name;
    button.setAttribute("aria-selected", active ? "true" : "false");
    button.tabIndex=active ? 0 : -1;
  });
  document.querySelectorAll("[data-tab-panel]").forEach(panel=>{
    panel.hidden=panel.dataset.tabPanel!==name;
  });
  // The preset shelf is scoped by the target filter, which lives in the
  // embedded surface; re-read it whenever the tab comes forward.
  if (name==="control") renderPresets();
  if (updateHash) history.replaceState(null,"",`#${name}`);
  window.scrollTo(0,0);
  if (name==="seats" && installation.room) requestAnimationFrame(()=>Spatial.render(installation,selectedSeat,selectSeat,ws,groupView()));
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
window.addEventListener("hashchange",()=>activateTab(tabFromHash(location.hash.slice(1))||"show",false));
document.addEventListener("keydown",event=>{
  if (event.key!=="Escape" || activeTab!=="seats" || event.target.matches("input,select,textarea")) return;
  if (focusedGroup!==null) {
    focusedGroup=null; renderGroups(); renderGroupMap(); Spatial.render(installation,selectedSeat,selectSeat,ws,groupView());
  } else if (visibleGroupIds().length) clearGroupView();
});
activateTab(activeTab,false);

function activateSeatSidebar(mode, moveFocus=false) {
  seatSidebarMode=mode==="groups"?"groups":"seats";
  const seats=seatSidebarMode==="seats";
  $("#seat-sidebar-tab").setAttribute("aria-selected",seats?"true":"false");
  $("#group-sidebar-tab").setAttribute("aria-selected",seats?"false":"true");
  $("#seat-sidebar-tab").tabIndex=seats?0:-1;
  $("#group-sidebar-tab").tabIndex=seats?-1:0;
  $("#seat-sidebar-panel").hidden=!seats;
  $("#group-sidebar-panel").hidden=seats;
  if(moveFocus)$(seats?"#seat-sidebar-tab":"#group-sidebar-tab").focus();
}
$("#seat-sidebar-tab").onclick=()=>activateSeatSidebar("seats");
$("#group-sidebar-tab").onclick=()=>activateSeatSidebar("groups");
$("#seat-sidebar-tabs").onkeydown=event=>{
  if(!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;
  event.preventDefault();
  const groups=event.key==="ArrowRight"||event.key==="End";
  activateSeatSidebar(groups?"groups":"seats",true);
};
activateSeatSidebar(seatSidebarMode);

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
ws.on("state", data => { installation = data; muted = !!data.muted; master = Number(data.master ?? 1); presetNames = Object.keys(data.presets || {}).sort(); reconcileSelection(); reconcileGroupView(); resumePatchHandoff(); renderPresets(); render(); const loading = $("#initial-loading"); if (loading) loading.hidden = true; });
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
ws.on("patches", mergeDevice); ws.on("assets", mergeDevice);
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
ws.on("mute_all", data => { muted = !!data.value; installation.muted=muted; render(); });
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
ws.on("editor_cue_fired", data => {
  const status = $("#editor-cue-status"); if (!status) return;
  status.value = `${data.cue_id} fired`;
});
ws.on("error", data => {
  if (manifestFeedback.endsWith("…")) {
    manifestFeedback=`Not saved: ${data.message}`;
    const feedback=$("#manifest-feedback"); if (feedback) feedback.textContent=manifestFeedback;
  }
  if (activeTab==="show" && typeof window.ShowInspectorError==="function") {
    window.ShowInspectorError(data.message);
    return;
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
ws.on("presets", data => { presetNames = data.names || []; renderPresets(); });
// Presets follow the target filter (Bob, 2026-07-25). The filter itself lives
// in the embedded Control surface, but its choice is in shared storage, so the
// shelf here reads the same target the operator is looking at.
function presetTarget() {
  const filter = window.SeatFilter;
  if (!filter) return {scope: "all", id: null, label: "All Seats"};
  const mode = localStorage.getItem("bopos.target-filter-mode") || "all";
  if (mode === "seat") {
    const id = filter.selectedSeat();
    const seat = id == null ? null : installation.seats?.[String(id)];
    if (seat) return {scope: "seat", id: Number(seat.id), label: seat.name || `Seat ${seat.id}`};
  }
  if (mode === "groups") return {scope: "groups", id: null, label: "Groups"};
  return {scope: "all", id: null, label: "All Seats"};
}

function renderPresets() {
  const select = $("#preset-select"); if (!select) return;
  select.innerHTML = presetNames.map(name => `<option>${esc(name)}</option>`).join("") || '<option disabled>none saved</option>';
  const scope = $("#preset-scope");
  if (scope) scope.value = presetTarget().label;
}
// The target filter lives in the embedded surface, which writes its choice to
// shared storage; a storage event is how this document hears about it.
window.addEventListener("storage", event => {
  if (event.key === "bopos.target-filter-mode"
      || event.key === window.SeatFilter?.SELECTED_SEAT_KEY) renderPresets();
});
(function bindPresets() {
  const save = $("#preset-save"), load = $("#preset-load");
  if (save) save.onclick = () => {
    const target = presetTarget();
    const name = prompt(`Save ${target.label} params + master as preset:`, "");
    if (name && (!presetNames.includes(name) || confirm(`Overwrite preset "${name}"?`))) {
      ws.send("save_preset", {name, scope: target.scope, id: target.id});
    }
  };
  if (load) load.onclick = () => {
    const name = $("#preset-select").value;
    if (!name) return;
    const target = presetTarget();
    ws.send("load_preset", {name, scope: target.scope, id: target.id});
  };
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
  const rosterFilter=$("#seat-roster-filter");
  if (rosterFilter && document.activeElement!==rosterFilter) rosterFilter.value=seatRosterFilter;
  const applyRosterFilter=()=>{
    seatRosterFilter=rosterFilter?.value||"";
    const value=seatRosterFilter.trim().toLowerCase();let matches=0;
    document.querySelectorAll("#assigned [data-seat-filter]").forEach(row=>{
      row.hidden=!!value&&!row.dataset.seatFilter.startsWith(value);
      if(!row.hidden)matches++;
    });
    const empty=$("#seat-roster-filter-empty");if(empty)empty.hidden=!value||matches>0;
  };
  if (rosterFilter) rosterFilter.oninput=applyRosterFilter;
  applyRosterFilter();
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
  renderEditor();
  renderFleetPatch();
  renderAssets();
  renderGroups();
  renderGroupMap();
  Spatial.render(installation, selectedSeat, selectSeat, ws, groupView()); renderRoom();
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

function groupCatalog() {
  return Object.values(installation.groups || {}).sort((a,b)=>Number(a.id)-Number(b.id));
}
function groupById(id) {
  return installation.groups?.[String(id)] || installation.groups?.[id] || null;
}
function groupMembers(id) {
  return Object.values(installation.seats || {}).filter(seat=>(seat.groups||[]).includes(Number(id))).sort((a,b)=>Number(a.id)-Number(b.id));
}
function visibleGroupIds() {
  return visibleGroups.filter(id=>id!==null);
}
function reconcileGroupView() {
  const valid=new Set(groupCatalog().map(group=>Number(group.id)));
  visibleGroups=Array.from({length:4},(_item,index)=>{
    const id=visibleGroups[index]; return id!==null&&valid.has(Number(id))?Number(id):null;
  });
  if (!valid.has(Number(focusedGroup))) focusedGroup=null;
  if (!valid.has(Number(selectedGroup))) selectedGroup=null;
}
function groupView() {
  return {visible:visibleGroupIds(),visibleSlots:[...visibleGroups],focused:focusedGroup,slots:GROUP_SLOTS};
}
// Adapted Lucide eye/eye-off geometry; see THIRD_PARTY_NOTICES.md.
function eyeIcon(shown) {
  const slash=shown?'':'<path d="M2 2l20 20"></path>';
  return `<svg class="visibility-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"></path><circle cx="12" cy="12" r="3"></circle>${slash}</svg>`;
}
function ensureGroupVisible(id) {
  id=Number(id);
  if (visibleGroups.includes(id)) return true;
  const slot=visibleGroups.findIndex(item=>item===null);
  if (slot<0) {
    groupMessage="Four groups are already shown; hide one to compare another.";
    return false;
  }
  visibleGroups[slot]=id; groupMessage=""; return true;
}
function focusGroup(id) {
  id=Number(id); selectedGroup=id; groupMemberFilter=""; activateSeatSidebar("groups");
  if (focusedGroup===id) focusedGroup=null;
  else if (ensureGroupVisible(id)) focusedGroup=id;
  renderGroups(); renderGroupMap();
  Spatial.render(installation,selectedSeat,selectSeat,ws,groupView());
}
function toggleGroupVisible(id) {
  id=Number(id);
  if (visibleGroups.includes(id)) {
    visibleGroups=visibleGroups.map(item=>item===id?null:item);
    if (focusedGroup===id) focusedGroup=null;
    groupMessage="";
  } else ensureGroupVisible(id);
  renderGroups(); renderGroupMap();
  Spatial.render(installation,selectedSeat,selectSeat,ws,groupView());
}
function clearGroupView() {
  focusedGroup=null; visibleGroups=[null,null,null,null]; groupMessage="";
  renderGroups(); renderGroupMap();
  Spatial.render(installation,selectedSeat,selectSeat,ws,groupView());
}
function groupMarker(id) {
  const index=visibleGroups.indexOf(Number(id));
  if (index<0) return '<i class="group-slot hidden" aria-hidden="true">–</i>';
  const slot=GROUP_SLOTS[index];
  return `<i class="group-slot slot-${index+1}" style="--group-colour:${slot.colour}" aria-hidden="true">${index+1}</i>`;
}
function renderGroups() {
  const panel=$("#group-sidebar-panel"), content=$("#groups-content"), summary=$("#groups-summary");
  if (!panel || !content || !summary) return;
  const previousFilter=$("#group-member-filter");
  const restoreFilterFocus=document.activeElement===previousFilter;
  const filterSelection=restoreFilterFocus
    ? [previousFilter.selectionStart,previousFilter.selectionEnd] : null;
  reconcileGroupView();
  const groups=groupCatalog();
  summary.textContent=`${visibleGroupIds().length} shown · ${groups.length} total`;
  const rows=groups.map(group=>{
    const id=Number(group.id), visible=visibleGroups.includes(id), count=groupMembers(id).length;
    const action=`${visible?'Hide':'Show'} ${group.name} ${visible?'from':'on'} map`;
    return `<div class="group-row${focusedGroup===id?' focused':''}${selectedGroup===id?' selected':''}" data-group-row="${id}">
      <button class="group-focus" data-group-focus="${id}" aria-pressed="${focusedGroup===id}">${groupMarker(id)}<span><strong>${esc(group.name)}</strong><small>g${id} · ${count} ${count===1?'Seat':'Seats'}</small></span></button>
      <button class="group-eye" data-group-eye="${id}" aria-pressed="${visible}" aria-label="${esc(action)}" title="${esc(action)}">${eyeIcon(visible)}</button>
      <details class="group-overflow"><summary aria-label="Actions for ${esc(group.name)}" title="Group actions">…</summary><div><button data-group-rename="${id}">Rename</button><button data-group-delete="${id}" class="danger">Delete</button></div></details>
    </div>`;
  }).join("");
  const active=groupById(selectedGroup);
  const members=active ? groupMembers(active.id) : [];
  const seatQuery=groupMemberFilter.trim().toLowerCase();
  const memberRows=active ? Object.values(installation.seats||{}).sort((a,b)=>Number(a.id)-Number(b.id)).map(seat=>{
    const checked=(seat.groups||[]).includes(Number(active.id));
    const search=String(seat.name||`Seat ${seat.id}`).trim().toLowerCase();
    const device=seat.bound?installation.devices?.[seat.bound]:null;
    const sync=!seat.bound?'unbound':device?.group_sync?.status||(device?.online?'waiting':'offline');
    return `<label class="membership-check" data-group-member-filter="${esc(search)}" ${seatQuery&&!search.startsWith(seatQuery)?'hidden':''}><input type="checkbox" data-group-member="${seat.id}" ${checked?'checked':''}><span><strong>${esc(seat.name||`Seat ${seat.id}`)}</strong><small>Seat ${seat.id} · ${esc(sync)}</small></span></label>`;
  }).join("") : "";
  const detail=active ? `<section class="group-detail"><div class="group-detail-head"><div><strong>${esc(active.name)}</strong><small>g${active.id} · ${members.length} ${members.length===1?'Seat':'Seats'}</small></div><button id="group-show-map">Show on map</button></div><label class="group-filter">Filter Seats <input id="group-member-filter" type="text" placeholder="Names beginning with…" value="${esc(groupMemberFilter)}"></label><div class="membership-list">${memberRows||'<p class="dim">No Seats to add yet.</p>'}</div><p id="group-filter-empty" class="dim" ${seatQuery&&memberRows&&!Object.values(installation.seats||{}).some(seat=>String(seat.name||`Seat ${seat.id}`).trim().toLowerCase().startsWith(seatQuery))?'':'hidden'}>No Seat names begin with this filter.</p></section>` : "";
  content.innerHTML=`<div class="group-rows">${rows||'<p class="dim">No groups yet</p>'}</div><p id="group-limit" class="group-limit" role="status" ${groupMessage?'':'hidden'}>${esc(groupMessage)}</p>${detail}`;
  $("#group-create").onclick=()=>{const name=prompt("Group name:","");if(name?.trim())ws.send("create_group",{name:name.trim()});};
  content.querySelectorAll("[data-group-focus]").forEach(button=>button.onclick=()=>focusGroup(button.dataset.groupFocus));
  content.querySelectorAll("[data-group-eye]").forEach(button=>button.onclick=()=>toggleGroupVisible(button.dataset.groupEye));
  content.querySelectorAll("[data-group-rename]").forEach(button=>button.onclick=()=>{const group=groupById(button.dataset.groupRename);const name=group&&prompt("Rename group:",group.name);if(name?.trim())ws.send("rename_group",{id:Number(group.id),name:name.trim()});});
  content.querySelectorAll("[data-group-delete]").forEach(button=>button.onclick=()=>{const group=groupById(button.dataset.groupDelete);if(group&&confirm(`Delete ${group.name} (g${group.id})? Seat memberships will be removed.`)){visibleGroups=visibleGroups.map(id=>id===Number(group.id)?null:id);if(focusedGroup===Number(group.id))focusedGroup=null;if(selectedGroup===Number(group.id))selectedGroup=null;ws.send("delete_group",{id:Number(group.id)});}});
  const show=$("#group-show-map"); if(show)show.onclick=()=>{if(focusedGroup!==Number(active.id))focusGroup(active.id);};
  const memberFilter=$("#group-member-filter"); if(memberFilter){
    const applyFilter=()=>{groupMemberFilter=memberFilter.value;const value=groupMemberFilter.trim().toLowerCase();let matches=0;content.querySelectorAll("[data-group-member-filter]").forEach(row=>{row.hidden=!!value&&!row.dataset.groupMemberFilter.startsWith(value);if(!row.hidden)matches++;});const empty=$("#group-filter-empty");if(empty)empty.hidden=!value||matches>0;};
    memberFilter.oninput=applyFilter;
    memberFilter.onchange=applyFilter;
    memberFilter.onkeydown=event=>{if(event.key==="Enter"){event.preventDefault();applyFilter();}};
    if(restoreFilterFocus){memberFilter.focus();if(filterSelection.every(value=>value!==null))memberFilter.setSelectionRange(...filterSelection);}
  }
  content.querySelectorAll("[data-group-member]").forEach(input=>input.onchange=()=>{
    const seat=installation.seats?.[String(input.dataset.groupMember)]; if(!seat||!active)return;
    const next=new Set((seat.groups||[]).map(Number)); input.checked?next.add(Number(active.id)):next.delete(Number(active.id));
    seat.groups=[...next].sort((a,b)=>a-b); ws.send("set_seat_groups",{id:Number(seat.id),groups:seat.groups});
    renderGroupMap(); Spatial.render(installation,selectedSeat,selectSeat,ws,groupView());
  });
}
function renderGroupMap() {
  const bar=$("#group-map-bar"), legend=$("#group-map-legend"), message=$("#group-map-message");
  if (!bar || !legend || !message) return;
  bar.hidden=!visibleGroupIds().length;
  legend.innerHTML=visibleGroups.map((id,index)=>{if(id===null)return"";const group=groupById(id);if(!group)return"";return `<button class="group-legend-chip${focusedGroup===id?' focused':''}" data-group-legend="${id}">${groupMarker(id)}<span>${esc(group.name)} <small>g${id}</small></span></button>`;}).join("");
  legend.querySelectorAll("[data-group-legend]").forEach(button=>button.onclick=()=>focusGroup(button.dataset.groupLegend));
  $("#group-view-clear").onclick=clearGroupView;
  const focused=groupById(focusedGroup), empty=focused&&groupMembers(focused.id).length===0;
  message.hidden=!empty; message.textContent=empty?`No Seats in ${focused.name} (g${focused.id})`:"";
}
function seatRow(seat) {
  const d=occupant(seat), state=d?.virtual?'sim':(d?.online?'live':'empty');
  const uid=d?.uid||"";
  const heartbeatAt=heartbeats.get(uid);
  const name=seat.name||`Seat ${seat.id}`;
  return `<div class="device-row seat-row ${Number(seat.id)===Number(selectedSeat)?'selected':''} ${badgeTone(d?.patch_badge)}" data-uid="${esc(uid)}" data-seat-id="${seat.id}" data-seat-filter="${esc(String(name).trim().toLowerCase())}" role="button" tabindex="0"><i class="dot ${state==='live'?'online':state==='sim'?'sim':'offline'}"></i>${uid?`<i class="heartbeat-blip${heartbeatAt?' pulse':''}" ${heartbeatAt?`data-heartbeat-at="${esc(heartbeatAt)}"`:''} aria-hidden="true"></i>`:''}<span><input data-seat-name aria-label="Seat ${seat.id} name" value="${esc(name)}"><small>ID ${seat.id} · ${state}</small></span>${d?pinnedMarker(d)+patchBadge(d.patch_badge):''}</div>`;
}
const PATCH_BADGE_LABELS = {unset:"not set",unknown:"unknown / last seen",switching:"switching",timeout:"switch timed out",failed:"switch failed",missing:"missing",mismatch:"mismatch",stale:"stale",stale_unverified:"stale (unverified)",current:"current"};
const PATCH_BADGE_ORDER = ["current","switching","timeout","failed","missing","mismatch","stale","stale_unverified","unknown","unset"];
function patchBadge(value) {
  const badge=value||"unknown", label=PATCH_BADGE_LABELS[badge]||badge.replaceAll("_"," ");
  return `<span class="patch-badge patch-badge-${esc(badge)}" title="Fleet patch: ${esc(label)}">${esc(label)}</span>`;
}
function badgeTone(value) { return value && !["current","unset"].includes(value) ? "patch-exception" : ""; }
// The pin is a separate axis from the convergence badge (thread 37): a device
// deliberately targeted to its own patch, marked with a non-colour glyph.
function pinnedMarker(d) {
  if (!d || !d.patch_pinned) return "";
  const name=d.pinned_patch||"a patch";
  return `<span class="patch-pin" title="Pinned to ${esc(name)} — follow fleet to clear" aria-label="Pinned to ${esc(name)}">📌</span>`;
}
// Deliberately its own function: inside renderFleetPatch, `select` is the
// local <select> element, which would shadow the global select(uid) and make
// the crumb throw instead of returning to the device.
function renderPatchHandoffCrumb() {
  const crumb=$("#patch-handoff-crumb"), back=$("#patch-handoff-back");
  if (!crumb || !back) return;
  const origin=patchHandoffDevice?installation.devices?.[patchHandoffDevice]:null;
  crumb.hidden=!origin;
  if (!origin) return;
  back.textContent=`← Back to ${Identity.primary(origin,installation)}`;
  back.onclick=()=>{
    const uid=patchHandoffDevice;
    patchHandoffDevice=null;
    select(uid);
    activateTab("devices");
  };
}

function renderFleetPatch() {
  const select=$("#patch-select"), target=$("#patch-target"), set=$("#patch-switch"), revert=$("#fleet-patch-revert");
  if (!select || !target || !set || !revert) return;
  const patches=(distribution.patches||[]).filter(item=>item.valid);
  const desired=installation.fleet_patch?.name||"";
  if (desired!==renderedFleetDesired) {
    fleetPatchChoice=patches.some(item=>item.name===desired)?desired:(patches[0]?.name||null);
    renderedFleetDesired=desired;
  } else if (!patches.some(item=>item.name===fleetPatchChoice)) {
    fleetPatchChoice=patches.some(item=>item.name===desired)?desired:(patches[0]?.name||null);
  }
  select.innerHTML=patches.map(item=>`<option value="${esc(item.name)}" ${item.name===fleetPatchChoice?'selected':''}>${esc(item.name)}</option>`).join("")||'<option value="" disabled>No valid host patches</option>';
  // Deploy target (thread 37): the whole fleet, or one seat-bound online device.
  // A single-device deploy pins that device's desired patch; the rest hold.
  const deployable=Object.values(installation.seats||{}).map(occupant)
    .filter(device=>device&&device.online&&!device.virtual);
  if (fleetPatchTarget!=="all" && !deployable.some(device=>device.uid===fleetPatchTarget)) fleetPatchTarget="all";
  target.innerHTML=[`<option value="all" ${fleetPatchTarget==="all"?'selected':''}>Whole fleet</option>`]
    .concat(deployable.map(device=>`<option value="${esc(device.uid)}" ${device.uid===fleetPatchTarget?'selected':''}>${esc(Identity.primary(device,installation))}${device.patch_pinned?" · pinned":""}</option>`)).join("");
  renderPatchHandoffCrumb();
  const editing=installation.supervisor?.mode==="edit";
  const toFleet=fleetPatchTarget==="all";
  select.disabled=!patches.length||editing;
  target.disabled=!patches.length||editing;
  set.disabled=!fleetPatchChoice||editing;
  set.textContent=toFleet?"Deploy as fleet patch":"Pin to device";
  revert.disabled=!installation.fleet_patch?.previous?.name||editing;
  select.onchange=()=>{fleetPatchChoice=select.value;};
  target.onchange=()=>{fleetPatchTarget=target.value;set.textContent=fleetPatchTarget==="all"?"Deploy as fleet patch":"Pin to device";};
  set.onclick=()=>{
    const name=select.value; if(!name) return;
    if (fleetPatchTarget==="all") {
      if(confirm(`Deploy "${name}" as the fleet patch? The dashboard will converge patch bytes, then restart audio engines across online assigned devices.`))ws.send("set_fleet_patch",{patch:name,confirmed:true});
    } else {
      const device=deployable.find(item=>item.uid===fleetPatchTarget);
      const label=device?Identity.primary(device,installation):fleetPatchTarget;
      if(confirm(`Pin "${name}" to ${label}? Only this device converges and restarts; the rest of the fleet is untouched.`))ws.send("set_device_patch",{uid:fleetPatchTarget,patch:name,confirmed:true});
    }
  };
  revert.onclick=()=>{const name=installation.fleet_patch?.previous?.name;if(name&&confirm(`Revert the fleet to patch "${name}"? The dashboard will use the same convergence and engine restart flow.`))ws.send("revert_fleet_patch",{confirmed:true});};
  $("#refresh-distribution").onclick=()=>ws.send("refresh_distribution",{});
  const assigned=Object.values(installation.seats||{}).map(occupant).filter(Boolean);
  const counts=new Map(); assigned.forEach(device=>counts.set(device.patch_badge||"unknown",(counts.get(device.patch_badge||"unknown")||0)+1));
  const progress=PATCH_BADGE_ORDER.filter(badge=>counts.has(badge)).map(badge=>`${counts.get(badge)} ${PATCH_BADGE_LABELS[badge]}`).join(" · ");
  const pinned=assigned.filter(device=>device.patch_pinned).length;
  const targets=`${assigned.length} assigned target${assigned.length===1?'':'s'}`;
  const pinNote=pinned?` · ${pinned} pinned`:"";
  $("#fleet-patch-summary").textContent=desired?`${targets}${pinNote}${progress?` · ${progress}`:''}`:`No fleet patch set${pinNote}`;
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
    if (mode==="edit") {
      activateTab("patches");
      requestAnimationFrame(()=>$("#editor-patch")?.focus());
      return;
    }
    const patch=contextualExecutionPatch();
    if (mode==="simulate") {
      if (!confirm(`Stop Simulation and edit "${patch||"the selected patch"}"?`)) return;
      ws.send("set_simulation",{active:false,confirmed:true});
      if (patch) ws.send("set_edit",{active:true,patch,confirmed:true});
    } else {
      if (patch) {
        if (!confirm(`Open "${patch}" in Patch edit? Live fleet devices will not be driven.`)) return;
        ws.send("set_edit",{active:true,patch,confirmed:true});
      }
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
function paramIdentity(param) {
  const path=Array.isArray(param?.path)?param.path:[];
  return [...path,param?.name||""].join("/");
}
function manifestParamsForSave(params) {
  return structuredClone(params).map(param=>{
    if (!Array.isArray(param.path) || !param.path.length) delete param.path;
    delete param.group;
    delete param.facilitator;
    return param;
  });
}
function paramManifestRow(param, index) {
  const legacy=param.type==="s", disabled=legacy?"disabled":"";
  const path=Array.isArray(param.path)?param.path.join("/"):"";
  return `<div class="manifest-row manifest-param" data-param-index="${index}">
    <label>path<input data-manifest-field="path" type="text" value="${esc(path)}" placeholder="e.g. instrument/marimba" autocomplete="off" ${disabled}></label>
    <label>name<input data-manifest-field="name" type="text" value="${esc(param.name||"")}" autocomplete="off" ${disabled}></label>
    <label>type<select data-manifest-field="type" ${disabled}><option value="f" ${param.type==="f"?"selected":""}>float</option><option value="i" ${param.type==="i"?"selected":""}>integer</option>${legacy?'<option value="s" selected>string (legacy, read-only)</option>':''}</select></label>
    <label>min<input data-manifest-field="min" type="number" step="any" value="${esc(param.min??"")}" ${disabled}></label>
    <label>max<input data-manifest-field="max" type="number" step="any" value="${esc(param.max??"")}" ${disabled}></label>
    <label>default<input data-manifest-field="default" type="number" step="any" value="${esc(param.default??"")}" ${disabled}></label>
    <label class="manifest-check"><input data-manifest-field="dashboard" type="checkbox" ${param.dashboard===true?"checked":""} ${disabled}> Facilitator</label>
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
      const update=()=>{
        const field=input.dataset.manifestField;
        manifestDraft.params[index][field]=field==="path"
          ? (input.value===""?[]:input.value.split("/"))
          : (input.type==="checkbox"?input.checked:(input.type==="number"?(input.value===""?"":Number(input.value)):input.value));
        manifestDirty=true;
      };
      input.oninput=update;
      input.onchange=update;
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
    if (!confirm(`Remove parameter "${paramIdentity(param)||"unnamed"}"? Engine routes do not change automatically; update the corresponding route in the patch.`)) return;
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
    ? "Path/name changes create a new OSC identity; engine routes never change automatically."
    : "Launch this patch in edit mode to change its manifest.");
  const addParam=$("#manifest-add-param"), addCue=$("#manifest-add-cue");
  addParam.disabled=!source.editable; addCue.disabled=!source.editable;
  addParam.onclick=()=>{manifestDraft.params.push({path:[],name:"",type:"f",min:0,max:1,default:0,dashboard:false});manifestDirty=true;renderManifestEditor(source);};
  addCue.onclick=()=>{manifestDraft.cues.push({id:"",label:"",description:""});manifestDirty=true;renderManifestEditor(source);};
  const save=$("#manifest-save"); save.disabled=!source.available||!source.editable;
  save.title=!source.available?"Manifest data is not available for this patch.":(!source.editable?"Launch this patch in the editor before saving.":"");
  save.onclick=()=>{
    const before=(manifestBaseline?.params||[]).map(paramIdentity);
    const after=manifestDraft.params.map(paramIdentity);
    const changed=before.filter(identity=>identity&&!after.includes(identity));
    if (changed.length && !confirm(`Save parameter move/rename/removal (${changed.map(item=>`/p/${item}`).join(", ")})? Engine routes do not follow manifest changes.`)) return;
    manifestFeedback="Saving manifest…";
    ws.send("save_patch_manifest",{patch,params:manifestParamsForSave(manifestDraft.params),cues:structuredClone(manifestDraft.cues)});
    save.blur();
    $("#manifest-feedback").textContent=manifestFeedback;
  };
  bindManifestEditor(source);
  if (!source.editable) document.querySelectorAll("#manifest-params input, #manifest-params select, #manifest-params button, #manifest-cues input, #manifest-cues button").forEach(control=>{control.disabled=true;});
}

function editorControl(declaration, value) {
  const badge=declaration.dashboard?'<b class="badge dashboard-badge">Dashboard</b>':'';
  const name=`${esc(declaration.name)} ${badge}`;
  const identity=paramIdentity(declaration);
  if (declaration.type === "s") return `<label><span>${name}</span><input data-editor-param="${esc(identity)}" type="text" value="${esc(value)}"></label>`;
  if (declaration.type === "i" && declaration.min===0 && declaration.max===1) return `<label class="toggle"><span>${name}</span><input data-editor-param="${esc(identity)}" type="checkbox" ${value?'checked':''}></label>`;
  return `<label><span>${name}</span><output data-precise="true">${esc(value)}</output><input data-editor-param="${esc(identity)}" type="range" min="${declaration.min??0}" max="${declaration.max??1}" step="${declaration.type==='i'?1:0.01}" value="${esc(value)}"></label>`;
}
function editorParamTree(declarations, values) {
  const roots=[];
  const branch=(siblings,name)=>{
    let node=siblings.find(item=>item.name===name);
    if (!node) { node={name,children:[],leaves:[]}; siblings.push(node); }
    return node;
  };
  for (const declaration of declarations) {
    const parents=Array.isArray(declaration.path)&&declaration.path.length
      ? declaration.path : ["parameters"];
    let siblings=roots, node=null;
    for (const name of parents) { node=branch(siblings,name); siblings=node.children; }
    node.leaves.push(declaration);
  }
  const render=(node,trail=[])=>{
    const path=[...trail,node.name];
    const leaves=node.leaves.map(item=>editorControl(
      item,values?.[paramIdentity(item)]??item.default??"")).join("");
    return `<section class="editor-param-branch" data-param-path="${esc(path.join("/"))}"><h3>${esc(node.name)}</h3>${leaves}${node.children.map(child=>render(child,path)).join("")}</section>`;
  };
  return roots.map(node=>render(node)).join("");
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
  launch.disabled=editor.active?false:!patches.length;
  launch.textContent=editor.active?'Stop Editor':'Launch editor';
  launch.onclick=()=>{
    if (editor.active) {
      if (confirm("Stop Patch edit and return audio control to the Live fleet?")) {
        ws.send("set_edit",{active:false,confirmed:true});
      }
      return;
    }
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
  const engineNote=$("#editor-engine-note");
  engineNote.hidden=!editor.active;
  engineNote.textContent=!editor.active ? "" : closed
    ? "Engine closed. It will stay closed until you explicitly relaunch it."
    : editor.engine==="pd"?"PD is open for live editing.":"Runtime controls are live; GUI editing is PD-only in v1.";
  const actions=$("#editor-session-actions");
  actions.innerHTML=(editor.active&&closed)
    ? `<button id="editor-relaunch">Relaunch</button>`:"";
  $("#editor-relaunch")?.addEventListener("click",()=>ws.send("relaunch_edit",{}));
  const focused=document.activeElement;
  const source=manifestSource(editor,patches,editorPatchChoice);
  if (!$("#manifest-editor").contains(focused)) renderManifestEditor(source);
  renderEditorPreview(editor);
  if ((interacting || focused?.matches?.('input[type="text"], input[type="number"], select'))
      && $("#editor-panel").contains(focused)) return;
  const controls=editorParamTree(editor.declarations||[],editor.params||{});
  $("#editor-params").innerHTML=editor.active
    ? `<h3>master</h3><label><span>master</span><output data-precise="true">${Math.round(master*100)}%</output><input id="editor-master" type="range" min="0" max="1" step="0.01" value="${master}"></label>${controls||'<p class="dim">No manifest parameters.</p>'}`:"";
  document.querySelectorAll("[data-editor-param]").forEach(input=>{
    const send=()=>{const value=input.type==="checkbox"?(input.checked?1:0):(input.type==="range"?Number(input.value):input.value);editor.params[input.dataset.editorParam]=value;ws.send("set_editor_param",{name:input.dataset.editorParam,value});};
    if(input.type==="range") {
      let pending=null;
      input.oninput=()=>{if(input.previousElementSibling?.tagName==="OUTPUT")input.previousElementSibling.value=input.value;if(pending===null)pending=requestAnimationFrame(()=>{pending=null;send();});};
      input.onchange=send;
      const output=input.previousElementSibling;
      // Precision typed entry on the readout (40-precision-param-input). The
      // editor re-render already bails while a number field is focused, so the
      // guard just reconciles the readout after commit.
      if(output?.dataset.precise==="true") window.PrecisionField.attach(output, {
        min: input.min===""?null:Number(input.min),
        max: input.max===""?null:Number(input.max),
        integer: input.step==="1",
        value: Number(input.value),
        label: input.dataset.editorParam,
        disabled: input.disabled,
      }, value=>{editor.params[input.dataset.editorParam]=value;ws.send("set_editor_param",{name:input.dataset.editorParam,value});input.value=value;},
         editing=>{if(!editing)renderEditor();});
    } else {
      input.onchange=send;
    }
  });
  const editorMaster=$("#editor-master");
  if(editorMaster) {
    editorMaster.oninput=()=>{master=Number(editorMaster.value);editorMaster.previousElementSibling.value=Math.round(master*100)+"%";ws.send("set_master",{value:master});};
    // Master is a 0..1 level shown as integer percent; precision entry drives it
    // in whole percent to match the readout and the slider's 1% step
    // (40-precision-param-input).
    const masterOut=editorMaster.previousElementSibling;
    if(masterOut?.dataset.precise==="true") window.PrecisionField.attach(masterOut, {
      min:0, max:100, integer:true, value:Math.round(master*100), label:"master", disabled:false,
    }, value=>{master=value/100;editorMaster.value=master;ws.send("set_master",{value:master});},
       editing=>{if(!editing)renderEditor();});
  }
}
function row(d, seat) {
  const status = d.online ? (Number(d.engine_alive) === 0 ? "crashed" : "online") : "offline";
  const heartbeatAt = heartbeats.get(d.uid);
  const assignment=d.revoking_assignment?"clearing assignment":seat?`bound · Seat ${seat.id}`:"unbound";
  const telemetry=[d.version,d.rssi != null ? `${d.rssi} dBm` : null].filter(Boolean).join(" · ");
  return `<button class="device-row ${d.uid===selected?'selected':''} ${badgeTone(d.patch_badge)}" data-uid="${esc(d.uid)}"><i class="dot ${status}"></i><i class="heartbeat-blip${heartbeatAt?' pulse':''}" ${heartbeatAt?`data-heartbeat-at="${esc(heartbeatAt)}"`:''} aria-hidden="true"></i><span><strong>${esc(Identity.primary(d,installation))}</strong>${telemetry?`<small>${esc(telemetry)}</small>`:''}<small class="device-binding-badge">${esc(assignment)}</small></span>${deviceEnabledIndicator(d)}${pinnedMarker(d)}${patchBadge(d.patch_badge)}</button>`;
}

function deviceEnabledPresentation(d) {
  const desired=d.device_enabled!==false;
  const status=String(d.enabled_status||"").toLowerCase();
  const unsettled=status&&status!=="current"&&status!=="confirmed";
  const state=desired?"Device enabled":"Device disabled";
  const suffix=unsettled?` · ${status}`:"";
  return {desired,status,label:state+suffix,terse:(desired?"enabled":"disabled")+suffix};
}

function deviceEnabledIndicator(d) {
  const enabled=deviceEnabledPresentation(d);
  const slash=enabled.desired?'':'<path d="M3 3l18 18"></path>';
  return `<span class="device-enabled-indicator ${enabled.desired?'enabled':'disabled'} ${enabled.status&&enabled.status!=="current"&&enabled.status!=="confirmed"?'unsettled':''}" data-device-enabled-indicator data-enabled-status="${esc(enabled.status||'current')}" role="img" aria-label="${esc(enabled.label)}" title="${esc(enabled.label)}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 5L6 9H3v6h3l5 4V5z"></path><path d="M15.5 9.5a4 4 0 010 5"></path>${slash}</svg></span>`;
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
function renderHeader() {
  const ds = Object.values(installation.devices || {}), online = ds.filter(d => d.online).length;
  $("#online-count").textContent = `${online} / ${ds.length} online`;
  $("#host-version").textContent = installation.host_version || "—";
  const mode=installation.supervisor?.mode||"off";
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
  activateSeatSidebar("seats");
  // The Control tab's target filter reads the same shared key, so choosing a
  // Seat here is the choice it lands on (37/10).
  window.SeatFilter?.selectSeat(id);
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
  // Effective desired = the device's pin if any, else the fleet default
  // (thread 37); the badge is computed against it, so the panel must match.
  const desired=d.desired_patch||installation.fleet_patch||{};
  const fetchPhase=desired.name?(d.fetch||{})[`patch:${desired.name}`]:null;
  const rows=installed.map(patch=>`<tr><td>${patch.git?'◆ ':''}${esc(patch.name)}</td><td>${patch.active?'active':'inactive'}</td><td>${patch.manifest?'valid':'invalid'}</td><td>${patch.git?'git-managed':'host-mirrored'}</td><td>${copyIdentity(patch.fingerprint,'unreported')}</td></tr>`).join("");
  const remediation=allowRemediation&&d.online&&["missing","stale","stale_unverified","mismatch","failed","timeout"].includes(d.patch_badge)
    ? `<button id="fleet-patch-retry">Sync to ${d.patch_pinned?'pinned':'fleet'} patch</button>`:"";
  const follow=d.patch_pinned&&d.online?'<button id="patch-follow-fleet">Follow fleet patch</button>':"";
  // Hand-off to the Patches tab, pre-scoped to this device (37/11). Deployment
  // itself stays on the Patch tab; this is a shortcut to it, not a second picker.
  const setPatch=d.virtual?"":`<button id="device-set-patch" ${d.online?'':'disabled'}>Set patch…</button>`;
  const unboundNote=!allowRemediation&&desired.name
    ? '<p class="dim patch-target-note">Assign this device to a Seat before syncing content. OSC v1.5 does not UID-target patch distribution or switching.</p>':"";
  const pull=allowRemediation&&d.online&&active?.git?'<button id="patch-pull">Pull latest</button>':"";
  const switchAttempt=d.patch_switch||{};
  return `<section id="patch-diagnostics"><div class="section-head"><h2>Patch diagnostics</h2>${pinnedMarker(d)}${patchBadge(d.patch_badge)}</div><p class="dim">observed current: <b>${esc(active?.name??d.report?.patch??'—')}</b></p><dl><dt>Desired patch${d.patch_pinned?' (pinned)':''}</dt><dd>${esc(desired.name||'not set')}</dd><dt>Desired fingerprint</dt><dd>${copyIdentity(desired.fingerprint,'—')}</dd><dt>Reported content identity</dt><dd>${copyIdentity(active?.fingerprint,'unreported')}</dd><dt>Observed active patch</dt><dd>${esc(active?.name??d.report?.patch??'—')}</dd><dt>Switch attempt</dt><dd>${esc(switchAttempt.status||'none')}${switchAttempt.reason?` · ${esc(switchAttempt.reason)}`:''}</dd><dt>Fetch phase</dt><dd>${esc(fetchPhase||'none')}</dd><dt>Manifest / framework git</dt><dd>${esc(active?.manifest?'valid manifest':'invalid or unreported manifest')} · ${active?.git?'git-managed patch':'host-mirrored patch'} · bopOS ${esc(d.report?.git_rev||'—')}</dd></dl><h3>Installed patches</h3><div class="patch-table-wrap"><table class="patch-table"><thead><tr><th>Patch</th><th>State</th><th>Manifest</th><th>Source</th><th>Fingerprint / content identity</th></tr></thead><tbody>${rows||'<tr><td colspan="5">No patch listing reported.</td></tr>'}</tbody></table></div>${remediation||pull||follow||setPatch?`<div class="actions patch-remediation">${setPatch}${remediation}${pull}${follow}</div>`:''}${unboundNote}${d.virtual?'<p class="dim">Host-backed simulated fleet; patch choice is controlled globally and needs no Send step.</p>':''}</section>`;
}
function bindPatchDiagnostics(d) {
  const retry=$("#fleet-patch-retry");
  if(retry) retry.onclick=()=>ws.send("retry_fleet_patch",{uid:d.uid});
  const pull=$("#patch-pull");
  if(pull) pull.onclick=()=>{if(confirm(`Pull latest active Git patch on ${Identity.primary(d,installation)}? It reboots.`))ws.send("pull_patch",{uid:d.uid});};
  const follow=$("#patch-follow-fleet");
  if(follow) follow.onclick=()=>{if(confirm(`Clear the pin on ${Identity.primary(d,installation)} and follow the fleet patch again? This device converges to the fleet default and restarts.`))ws.send("clear_device_patch",{uid:d.uid});};
  const setPatch=$("#device-set-patch");
  if(setPatch) setPatch.onclick=()=>startSetPatchHandoff(d);
}

// Pinning a patch needs a Seat, because OSC v1.5 targets content by Seat. The
// operator should not have to learn that: an unbound device is offered one in
// a single step, and the hand-off completes once the binding lands (37/11).
let pendingPatchHandoff=null;

function seatForDevice(uid) {
  return Object.values(installation.seats||{}).find(item=>item.bound===uid)||null;
}

function handoffToPatchTab(uid) {
  fleetPatchTarget=uid;
  patchHandoffDevice=uid;
  activateTab("patches");
  render();
}

function startSetPatchHandoff(d) {
  if (seatForDevice(d.uid)) { handoffToPatchTab(d.uid); return; }
  const alias=Identity.primary(d,installation);
  if (!confirm(`${alias} has no Seat. Targeting a patch at one device addresses it by Seat, so bopOS will give ${alias} a Seat of its own. Continue?`)) return;
  const id=nextFreeId();
  ws.send("add_seat",{id,name:alias,positions:[]});
  ws.send("bind_seat",{id,uid:d.uid,confirmed:false});
  pendingPatchHandoff=d.uid;
}

// The binding arrives asynchronously; finish the hand-off when it does.
function resumePatchHandoff() {
  if (!pendingPatchHandoff) return;
  const uid=pendingPatchHandoff;
  if (!seatForDevice(uid)) return;
  pendingPatchHandoff=null;
  handoffToPatchTab(uid);
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
  if (seat.bound && !currentKnown) options.push(`<option value="${esc(seat.bound)}" ${bindingChoice===seat.bound?'selected':''}>${esc(Identity.primary(seat.bound,installation))} · remembered offline</option>`);
  if (currentKnown?.revoking_assignment) options.push(`<option value="${esc(currentKnown.uid)}" ${bindingChoice===currentKnown.uid?'selected':''} disabled>${esc(Identity.primary(currentKnown,installation))} · clearing old assignment</option>`);
  options.push(...available.map(device=>`<option value="${esc(device.uid)}" ${device.uid===bindingChoice?'selected':''}>${esc(Identity.primary(device,installation))} · ${device.online?'online':'offline'}</option>`));
  if (!seat.bound) options.unshift(`<option value="" ${bindingChoice?'':'selected'}>Choose a device</option>`);
  const room=installation.room||{}, origin=room.origin||[0,0];
  const positions=(seat.positions||[]).map((position,index)=>`<div class="position-row" data-seat-element="${index}"><strong>element ${index}</strong><label>x <input data-axis="x" type="number" step="0.01" value="${Math.round((position[0]-origin[0])*100)/100}"></label><label>y <input data-axis="y" type="number" step="0.01" value="${Math.round((position[1]-origin[1])*100)/100}"></label><button data-remove-element="${index}" class="danger">Remove</button></div>`).join('');
  const binding=seat.bound ? installation.devices?.[seat.bound] : null;
  const groupChecks=groupCatalog().map(group=>`<label class="membership-check"><input type="checkbox" data-seat-group="${group.id}" ${(seat.groups||[]).includes(Number(group.id))?'checked':''}><span><strong>${esc(group.name)}</strong><small>g${group.id}</small></span></label>`).join('');
  const groupSync=binding?.group_sync?.status;
  const choiceRevoking=!!devices.find(device=>device.uid===bindingChoice)?.revoking_assignment;
  const elementLimit=(seat.positions||[]).length>=2;
  panel.innerHTML=`<div class="seat-inspector-section"><h3>Seat workspace</h3>
    <div class="assign"><label>name <input id="seat-name" type="text" value="${esc(seat.name||'')}"></label><button id="seat-rename">Apply name</button></div>
    <div class="assign"><label>ID <input id="seat-id" type="number" min="0" step="1" value="${seat.id}"></label><button id="seat-reindex">Reindex</button><button id="seat-remove" class="danger">Delete Seat</button></div></div>
    <div class="seat-inspector-section"><h3>Elements</h3><div class="position-grid">${positions||'<p class="dim">No elements positioned yet.</p>'}</div><button id="seat-element-add" ${elementLimit?'disabled':''}>Add element</button></div>
    <div class="seat-inspector-section"><h3>Groups</h3><div class="membership-list">${groupChecks||'<p class="dim">Open the Groups tab to create a group.</p>'}</div><small class="dim seat-group-sync">${seat.bound?`Node membership: ${esc(groupSync||'waiting')}`:'Membership retained while this Seat is unbound'}</small></div>
    <div class="seat-inspector-section"><h3>Physical device</h3><small class="dim seat-binding-note">${seat.bound?`${esc(Identity.primary(binding||seat.bound,installation))} · ${binding?.online?'online':binding?'offline':'waiting to be seen'}${binding?.ip?` · ${esc(binding.ip)}`:''}`:'No device assigned'}</small>
    <div class="assign"><label>device <select id="seat-device">${options.join('')||'<option value="">No available devices</option>'}</select></label><button id="seat-identify" ${choiceRevoking?'disabled':''}>Identify</button><button id="seat-bind" ${choiceRevoking?'disabled':''}>${seat.bound?'Assign / replace':'Assign'}</button>${seat.bound?'<button id="seat-unbind">Unassign</button>':''}</div></div>`;
  const savePositions=positionsValue=>{seat.positions=positionsValue;ws.send("update_seat",{id:seat.id,positions:positionsValue});Spatial.render(installation,selectedSeat,selectSeat,ws,groupView());};
  panel.querySelectorAll('[data-seat-element] input').forEach(input=>input.onchange=()=>{
    const row=input.closest('[data-seat-element]'), index=Number(row.dataset.seatElement);
    const x=Number(row.querySelector('[data-axis="x"]').value), y=Number(row.querySelector('[data-axis="y"]').value);
    if (!Number.isFinite(x)||!Number.isFinite(y)) return;
    const next=structuredClone(seat.positions||[]); next[index]=[Math.round((x+origin[0])*100)/100,Math.round((y+origin[1])*100)/100]; savePositions(next);
  });
  panel.querySelectorAll('[data-remove-element]').forEach(button=>button.onclick=()=>{const next=structuredClone(seat.positions||[]);next.splice(Number(button.dataset.removeElement),1);savePositions(next);});
  $("#seat-element-add").onclick=()=>{if((seat.positions||[]).length<2)savePositions([...(seat.positions||[]),[Number(origin[0])||0,Number(origin[1])||0]]);};
  $("#seat-rename").onclick=()=>ws.send("update_seat",{id:seat.id,name:$("#seat-name").value});
  $("#seat-reindex").onclick=()=>{const next=Number($("#seat-id").value);if(Number.isInteger(next)&&next>=0&&next!==Number(seat.id)&&confirm(`Change Seat ID ${seat.id} to ${next}? Current presets follow the new ID; saved venues stay unchanged.`))ws.send("reindex_seat",{id:seat.id,new_id:next});};
  $("#seat-remove").onclick=()=>{if(confirm(`Delete Seat ${seat.id}? Its current preset entries will also be removed.`))ws.send("remove_seat",{id:seat.id});};
  panel.querySelectorAll("[data-seat-group]").forEach(input=>input.onchange=()=>{const next=new Set((seat.groups||[]).map(Number));input.checked?next.add(Number(input.dataset.seatGroup)):next.delete(Number(input.dataset.seatGroup));seat.groups=[...next].sort((a,b)=>a-b);ws.send("set_seat_groups",{id:Number(seat.id),groups:seat.groups});renderGroups();renderGroupMap();Spatial.render(installation,selectedSeat,selectSeat,ws,groupView());});
  const chosen=()=>$("#seat-device").value;
  $("#seat-device").onchange=()=>seatBindingDrafts.set(seat.id,chosen());
  $("#seat-identify").onclick=()=>{const uid=chosen();if(uid&&installation.devices?.[uid])ws.send("identify",{uid});};
  $("#seat-bind").onclick=()=>{const uid=chosen();if(!uid)return;const replacing=seat.bound&&seat.bound!==uid;if(!replacing||confirm(`Replace ${seat.bound} with ${uid} on Seat ${seat.id}?`))ws.send("bind_seat",{id:seat.id,uid,confirmed:!!replacing});};
  const unbind=$("#seat-unbind");if(unbind)unbind.onclick=()=>{if(confirm(`Unassign ${seat.bound} from Seat ${seat.id}?`))ws.send("unbind_seat",{id:seat.id});};
}

function audioConfigEqual(left,right) {
  return ["card","mixer_control","sample_rate","period_size","nperiods"]
    .every(key=>(left?.[key]??null)===(right?.[key]??null));
}

function audioSection(d) {
  const audio=d.report?.audio;
  if(!audio||!audio.configured) return `<section id="device-audio"><div class="section-head"><div><h2>Audio</h2><p class="dim">Refresh the report to load audio settings and detected cards.</p></div></div></section>`;
  const configured=audio.configured, active=audio.active, cards=Array.isArray(audio.cards)?audio.cards:[];
  const available=cards.some(card=>card.id===configured.card);
  const cardOptions=[
    ...(!available?[`<option value="${esc(configured.card)}" selected disabled>${esc(configured.card)} — unavailable</option>`]:[]),
    ...cards.map(card=>`<option value="${esc(card.id)}" ${card.id===configured.card?'selected':''}>${esc(card.label||card.id)} · ${esc(card.id)}</option>`)
  ].join('');
  const rates=[22050,32000,44100,48000,88200,96000];
  const periods=[64,128,256,512,1024,2048];
  const latency=Math.round(Number(configured.period_size)*Number(configured.nperiods)/Number(configured.sample_rate)*10000)/10;
  const mismatch=active&&!audioConfigEqual(configured,active);
  const receipt=d.audio_apply;
  const feedback=receipt?.phase==="applied"?"Applied; audio engine restarted."
    :receipt?.phase==="rolled-back"?"Could not start requested settings; restored the previous configuration."
    :receipt?.phase==="rollback-failed"?"Audio recovery failed; inspect the node before use."
    :receipt?.phase==="invalid"?"The node rejected those audio settings."
    :receipt?.phase==="timeout"?"Audio apply timed out; refreshing observed state."
    :audio.status==="applying"?"Applying settings and restarting audio…"
    :audio.error||"";
  return `<section id="device-audio" data-audio-status="${esc(audio.status||'unknown')}">
    <div class="section-head"><div><h2>Audio</h2><p class="dim">${active?`${esc(active.card)} · ${esc(active.sample_rate)} Hz · ${esc(active.period_size)} frames × ${esc(active.nperiods)}`:"No active JACK configuration reported"}${mismatch?' · saved settings differ':''}</p></div><span class="audio-state">${esc(audio.status||"unknown")}</span></div>
    <div class="audio-config-grid">
      <label>sound card<select id="audio-card" ${d.online&&cards.length?'':'disabled'}>${cardOptions||'<option disabled>No playback cards detected</option>'}</select></label>
      <label>sample rate<select id="audio-rate" ${d.online?'':'disabled'}>${rates.map(value=>`<option value="${value}" ${value===Number(configured.sample_rate)?'selected':''}>${value} Hz</option>`).join('')}</select></label>
      <label>buffer size<select id="audio-period" ${d.online?'':'disabled'}>${periods.map(value=>`<option value="${value}" ${value===Number(configured.period_size)?'selected':''}>${value} frames</option>`).join('')}</select></label>
      <label>periods<select id="audio-nperiods" ${d.online?'':'disabled'}>${[2,3].map(value=>`<option value="${value}" ${value===Number(configured.nperiods)?'selected':''}>${value}</option>`).join('')}</select></label>
    </div>
    <p class="dim audio-buffering">Approximate device buffering: <span id="audio-latency">${latency} ms</span>. End-to-end latency may be higher.</p>
    <div class="audio-apply-row"><button id="audio-apply" ${!d.online||!available||audio.status==="applying"?'disabled':''}>Save &amp; restart audio engine</button><output id="audio-feedback" class="${receipt?.status==="err"?'error':''}" aria-live="polite">${esc(feedback)}</output></div>
  </section>`;
}

function logSection(d) {
  const log=d.report?.log;
  if(!log||!log.destination) return `<section id="device-log"><div class="section-head"><div><h2>Logging</h2><p class="dim">Refresh the report to load the log destination.</p></div></div></section>`;
  const destination=log.destination, effective=log.effective, usbPresent=!!log.usb_present;
  if(logDestinationDrafts.get(d.uid)===destination) logDestinationDrafts.delete(d.uid);
  const choice=logDestinationDrafts.get(d.uid)??destination;
  const fellBack=destination==="usb"&&effective==="internal";
  const receipt=d.log_apply;
  const feedback=receipt?.phase==="applied"?(fellBack?"Saved — USB not mounted, logging to internal storage.":"Saved log destination.")
    :receipt?.phase==="invalid"?"The node rejected that log destination."
    :receipt?.phase==="timeout"?"Log destination apply timed out; refreshing observed state."
    :receipt?.status==="pending"?"Saving log destination…"
    :fellBack?"USB selected but no stick is mounted — logging to internal storage.":"";
  const sub=`Writing to ${effective==="usb"?"USB stick":"internal storage"}${fellBack?" (USB not mounted)":""} · USB ${usbPresent?"present":"absent"}`;
  const opt=(value,label)=>`<option value="${value}" ${value===choice?'selected':''}>${label}</option>`;
  return `<section id="device-log" data-log-effective="${esc(effective||'internal')}" data-log-usb="${usbPresent?'1':'0'}">
    <div class="section-head"><div><h2>Logging</h2><p class="dim">${esc(sub)}</p></div><span class="log-state">${esc(effective||'internal')}</span></div>
    <div class="log-config-row">
      <label>destination<select id="log-destination" ${d.online?'':'disabled'}>${opt("internal","Internal storage (SD card)")}${opt("usb","USB stick")}</select></label>
      <button id="log-apply" ${!d.online||choice===destination?'disabled':''}>Save log destination</button>
      <output id="log-feedback" class="${receipt?.status==="err"?'error':''}" aria-live="polite">${esc(feedback)}</output>
    </div></section>`;
}

// The Device tab renders the same live controls the Control tab does, through
// the shared component (37/07). Only the scope and the send differ: a device
// write targets one device, resolved node-side to its seat selector.
let deviceControlInteracting=false;
const deviceSurface=window.ControlSurface.create({
  getState:()=>installation,
  deviceForSeat:seat=>seat?.bound?installation.devices?.[seat.bound]:null,
  deviceForScope:uid=>installation.devices?.[uid],
  send:({scope,id,name,value})=>ws.send("set_live_param",{scope,id,name,value}),
  sendAutomation:({scope,id,name,args})=>ws.send("set_live_automation",{scope,id,name,args}),
  setInteracting:editing=>{deviceControlInteracting=editing;},
  requestRender:()=>renderDeviceDetail(),
});

const DEVICE_CONTROL_OPEN="bopos.device-control-open";
function deviceControlOpen() {
  // Collapsed by default (Bob, 2026-07-25); the choice is remembered.
  try { return localStorage.getItem(DEVICE_CONTROL_OPEN)==="1"; }
  catch (_error) { return false; }
}
function setDeviceControlOpen(open) {
  try { localStorage.setItem(DEVICE_CONTROL_OPEN,open?"1":"0"); }
  catch (_error) { /* private mode: the panel just forgets */ }
}

// A pinned device runs its own patch, so the server publishes that patch's
// full parameter schema on the device; everything else uses the fleet-wide one.
function deviceLiveSchema(d) {
  const schema=d?.live_controls?.declarations?.length?d.live_controls:installation.live_controls;
  if(!schema||!Array.isArray(schema.declarations))return null;
  // Event declarations travel beside the params (they are not `/p/*` values)
  // and are folded back in here, at the surface that renders rows — so nothing
  // else that reads `declarations` ever sees them.
  const items=[...schema.declarations,...(Array.isArray(schema.events)?schema.events:[])];
  return {patch:schema.patch,declarations:items.map(item=>({...item,path:item.path||[]}))};
}

function deviceControlSection(d) {
  const seat=Object.values(installation.seats||{}).find(item=>item.bound===d.uid);
  const schema=deviceLiveSchema(d);
  const open=deviceControlOpen();
  const declarations=schema?.declarations||[];
  const live=!!d.online&&Number(d.engine_alive)!==0;
  // Offline shows last known values, disabled — never hidden (Bob, 2026-07-25).
  const disabled=!seat||!live;
  const why=!seat?'Unbound device — showing patch defaults. Live control targets content by Seat, so bind this device to a Seat first.'
    :!live?'Offline — showing the last known values.':'';
  // The preset row now names the patch (panel anatomy item 2), so the head
  // line keeps only what the row cannot say: where that patch came from.
  const presets=declarations.length?deviceSurface.presetRow(schema?.patch,`device:${d.uid}`):"";
  const body=!declarations.length
    ? '<p class="dim">This patch declares no parameters.</p>'
    : `${presets}<div class="promoted-controls">${deviceSurface.tree("device",d.uid,seat?[seat]:[],declarations,disabled)}</div>`;
  const source=schema?.patch?`<p class="dim">${d.patch_pinned?'pinned to this device':'fleet patch'}</p>`:"";
  return `<section id="device-control" class="device-control${disabled?' disabled':''}">
    <div class="section-head"><div><h2>Device control</h2>${source}</div><button id="device-control-toggle" aria-expanded="${open}" aria-controls="device-control-body">${open?'Hide':'Show'}</button></div>
    <div id="device-control-body" ${open?'':'hidden'}>${why?`<p class="dim">${esc(why)}</p>`:''}${body}</div>
  </section>`;
}

function renderDeviceDetail() {
  const d=installation.devices?.[selected];
  if (!d || d.virtual) { $("#detail").innerHTML='<section><p class="dim">Select a physical device.</p></section>'; return; }
  const active=document.activeElement;
  if ($("#detail").contains(active) && active.matches('input,select')) { updateDeviceEnabledControls(d);updateDeviceHostnameControls(d);return; }
  const seat=Object.values(installation.seats||{}).find(item=>item.bound===d.uid);
  const emptySeats=Object.values(installation.seats||{}).filter(item=>!item.bound).sort((a,b)=>a.id-b.id);
  const assignOptions=emptySeats.map(item=>`<option value="${item.id}">${esc(item.name||`Seat ${item.id}`)} · ID ${item.id}</option>`).join('');
  const health=!d.online?'offline':Number(d.engine_alive)===0?'engine stopped':'healthy';
  const displayAlias=Identity.primary(d,installation);
  const hostnameTarget=displayAlias.trim().toLowerCase().replace(/\s+/g,"-");
  const hostnamePending=d.hostname_status==="pending";
  const hostnameCurrent=String(d.hostname||"").toLowerCase()===hostnameTarget;
  const hostnameActionLabel=hostnamePending?"Setting…":hostnameCurrent?"Hostname set":d.hostname_status==="err"?"Retry hostname":"Set hostname";
  const enabled=deviceEnabledPresentation(d);
  const binding=d.revoking_assignment
    ? '<section id="device-binding"><h2>Assignment</h2><p class="dim">Clearing a stale node assignment. This device cannot be rebound until it acknowledges ID -1.</p></section>'
    : seat
      ? `<section id="device-binding"><div class="section-head"><div><h2>Assignment</h2><p class="dim">Bound to ${esc(seat.name||`Seat ${seat.id}`)} · ID ${seat.id}</p></div><button id="device-open-seat">Open Seat</button></div></section>`
      : `<section id="device-binding"><h2>Assignment</h2><p class="dim">Unbound physical device. Assignment uses the same authoritative Seat transaction.</p><div class="assign"><label>empty Seat <select id="device-seat" ${assignOptions?'':'disabled'}>${assignOptions||'<option>No empty Seats</option>'}</select></label><button id="device-bind" ${assignOptions&&d.online?'':'disabled'}>Assign</button></div></section>`;
  $("#detail").innerHTML=`<section><div class="section-head device-title"><h2>${esc(displayAlias)} ${d.undeclared?'<b class="badge">UNDECLARED</b>':''}</h2><div class="device-enabled-control"><output id="device-enabled-status" aria-live="polite">${esc(enabled.terse)}</output><button id="device-enabled-toggle">${d.device_enabled===false?'Enable':'Disable'}</button></div></div><div class="assign device-alias-editor"><label>device alias <input id="device-alias" type="text" maxlength="25" pattern="[A-Za-z]{2,12} [A-Za-z]{2,12}" value="${esc(displayAlias)}"></label><button id="device-alias-save">Rename</button><button id="device-alias-reset">Reset</button><button id="device-hostname-set" ${!d.online||hostnamePending||hostnameCurrent?'disabled':''}>${hostnameActionLabel}</button></div><dl><dt>Hostname</dt><dd id="device-hostname-value">${esc(d.hostname||'—')}</dd><dt>UID</dt><dd><code>${esc(d.uid)}</code></dd><dt>Seat</dt><dd>${seat?`${esc(seat.name||`Seat ${seat.id}`)} · ID ${seat.id}`:'unbound'}</dd><dt>Health</dt><dd class="device-health ${health==='healthy'?'online':health==='offline'? 'offline':''}">${health}</dd><dt>Last seen</dt><dd>${d.last_seen?ago(d.last_seen):'—'}</dd><dt>Version</dt><dd>${esc(d.version)}</dd><dt>Engine</dt><dd>${d.engine_alive?'alive':'stopped'}</dd><dt>RSSI</dt><dd>${d.rssi==null?'wired / unavailable':esc(`${d.rssi} dBm`)}</dd><dt>IP</dt><dd>${esc(d.ip)}</dd><dt>Converged</dt><dd>${d.rev?`${esc(d.rev.sha)} (${esc(d.rev.model)}, ${ago(d.rev.at)})${d.rev.status?` · ${esc(d.rev.status)} ${esc(d.rev.phase||'unknown')}`:''}`:'—'}</dd></dl></section>
    ${binding}
    ${patchDiagnostics(d,!!seat)}
    <section><h2>Actions</h2><div class="actions"><button data-identify ${d.online?'':'disabled'}>Identify</button>${["reboot","shutdown","restart-engine","updatebopos"].map(v=>`<button data-action="${v}" ${d.online?'':'disabled'}>${actionLabel(v)}</button>`).join('')}${seat?'':'<button id="device-forget">Forget</button>'}</div></section>
    ${deviceControlSection(d)}
    ${audioSection(d)}
    ${logSection(d)}
    <section class="device-assets-summary"><div class="section-head"><div><h2>Assets</h2><p class="dim">${!Array.isArray(d.assets)?'Inventory not yet reported':`${d.assets.length} installed slot${d.assets.length===1?'':'s'}`}</p></div><button id="device-open-assets">Open Assets</button></div></section>
    <section><div class="section-head"><h2>Report</h2><button id="refresh-report" ${d.online?'':'disabled'}>Refresh report</button></div>${report(d.report)}</section>`;
  bindDeviceDetailControls(d); bindPatchDiagnostics(d);
}

function updateDeviceEnabledControls(d) {
  const enabled=deviceEnabledPresentation(d), button=$("#device-enabled-toggle"), status=$("#device-enabled-status");
  if(button)button.textContent=d.device_enabled===false?"Enable":"Disable";
  if(status)status.value=enabled.terse;
}

function updateDeviceHostnameControls(d) {
  const alias=Identity.primary(d,installation);
  const target=alias.trim().toLowerCase().replace(/\s+/g,"-");
  const pending=d.hostname_status==="pending";
  const current=String(d.hostname||"").toLowerCase()===target;
  const button=$("#device-hostname-set");
  if(button){button.disabled=!d.online||pending||current;button.textContent=pending?"Setting…":current?"Hostname set":d.hostname_status==="err"?"Retry hostname":"Set hostname";}
  const value=$("#device-hostname-value");if(value)value.textContent=d.hostname||"—";
}

function bindDeviceDetailControls(d) {
  const alias=Identity.primary(d,installation), registryEntry=installation.device_registry?.[d.uid]||{};
  document.querySelectorAll("#detail [data-action]").forEach(button=>button.onclick=()=>{const verb=button.dataset.action;if(!confirm(`${actionLabel(verb)} ${alias}?`))return;ws.send("action",{uid:d.uid,verb});});
  document.querySelectorAll("#detail [data-identify]").forEach(button=>button.onclick=()=>ws.send("identify",{uid:d.uid}));
  const openSeat=$("#device-open-seat");if(openSeat)openSeat.onclick=()=>{const seat=Object.values(installation.seats||{}).find(item=>item.bound===d.uid);if(seat){selectSeat(Number(seat.id));activateTab("seats");}};
  const bind=$("#device-bind");if(bind)bind.onclick=()=>{const id=Number($("#device-seat").value);if(Number.isInteger(id))ws.send("bind_seat",{id,uid:d.uid,confirmed:false});};
  const aliasSave=$("#device-alias-save");if(aliasSave)aliasSave.onclick=()=>{const input=$("#device-alias"),value=input.value;if(input.reportValidity()){input.blur();ws.send("set_device_alias",{uid:d.uid,alias:value});}};
  const aliasReset=$("#device-alias-reset");if(aliasReset)aliasReset.onclick=()=>{if(registryEntry.source!=="custom"||confirm(`Reset custom alias ${alias} to its generated name?`))ws.send("reset_device_alias",{uid:d.uid});};
  const hostnameSet=$("#device-hostname-set");if(hostnameSet)hostnameSet.onclick=()=>ws.send("set_device_hostname",{uid:d.uid});
  const enabledToggle=$("#device-enabled-toggle");if(enabledToggle)enabledToggle.onclick=()=>{const current=installation.devices?.[d.uid]||d;ws.send("set_device_enabled",{uid:d.uid,value:current.device_enabled===false?1:0});};
  bindAudioControls(d);
  bindLogControls(d);
  bindDeviceControl(d);
  const forget=$("#device-forget");if(forget)forget.onclick=()=>{const loss=registryEntry.source==="custom"?" Its custom alias will be deleted.":"";if(confirm(`Forget ${alias}?${loss}`))ws.send("forget_device",{uid:d.uid});};
  $("#refresh-report").onclick=()=>ws.send("request_report",{uid:d.uid});
  const openAssets=$("#device-open-assets");if(openAssets)openAssets.onclick=()=>{assetTarget=d.uid;activateTab("assets");renderAssets();};
}

function bindDeviceControl(d) {
  const toggle=$("#device-control-toggle");
  if(toggle)toggle.onclick=()=>{setDeviceControlOpen(!deviceControlOpen());renderDeviceDetail();};
  const body=$("#device-control-body");
  if(body&&!body.hidden)deviceSurface.bind(body);
}

function bindAudioControls(d) {
  const audio=d.report?.audio, card=$("#audio-card"), rate=$("#audio-rate"), period=$("#audio-period"), nperiods=$("#audio-nperiods"), apply=$("#audio-apply");
  if(!audio?.configured||!card||!rate||!period||!nperiods||!apply)return;
  const cards=Array.isArray(audio.cards)?audio.cards:[];
  const config=()=>{
    const selected=cards.find(item=>item.id===card.value);
    const retainMixer=card.value===audio.configured.card
      && (audio.configured.mixer_control==null
        || selected?.mixer_controls?.includes(audio.configured.mixer_control));
    return {
      card:card.value,
      mixer_control:retainMixer?audio.configured.mixer_control:null,
      sample_rate:Number(rate.value),
      period_size:Number(period.value),
      nperiods:Number(nperiods.value)
    };
  };
  const refresh=()=>{
    const value=config(), selected=cards.find(item=>item.id===value.card);
    apply.disabled=!d.online||audio.status==="applying"||!selected||audioConfigEqual(value,audio.configured);
    const latency=Math.round(value.period_size*value.nperiods/value.sample_rate*10000)/10;
    const output=$("#audio-latency");if(output)output.textContent=`${latency} ms`;
  };
  card.onchange=refresh;
  [rate,period,nperiods].forEach(control=>control.onchange=refresh);
  refresh();
  apply.onclick=()=>{
    const desired=config();
    if(!confirm(`Restart the audio engine on ${Identity.primary(d,installation)}? Audio will stop briefly while these settings are tested.`))return;
    apply.disabled=true;
    const feedback=$("#audio-feedback");if(feedback){feedback.className="";feedback.value="Applying settings and restarting audio…";}
    ws.send("set_audio_config",{uid:d.uid,config:desired});
  };
}

function bindLogControls(d) {
  const log=d.report?.log, select=$("#log-destination"), apply=$("#log-apply");
  if(!log?.destination||!select||!apply)return;
  const refresh=()=>{apply.disabled=!d.online||select.value===log.destination;};
  select.onchange=()=>{logDestinationDrafts.set(d.uid,select.value);refresh();};
  refresh();
  apply.onclick=()=>{
    const destination=select.value;
    logDestinationDrafts.delete(d.uid);
    const feedback=$("#log-feedback");if(feedback){feedback.className="";feedback.value="Saving log destination…";}
    apply.disabled=true;
    ws.send("set_log_config",{uid:d.uid,destination});
  };
}

function actionLabel(verb) { return verb === "updatebopos" ? "Update bopOS" : verb.replaceAll("-", " "); }
function formatBytes(value) {
  const bytes = Number(value) || 0;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024*1024) return `${(bytes/1024).toFixed(1)} KB`;
  return `${(bytes/1024/1024).toFixed(1)} MB`;
}

function assetTargets() {
  const seats=Object.values(installation.seats||{}), devices=Object.values(installation.devices||{});
  const assigned=new Set(seats.map(seat=>seat.bound).filter(Boolean));
  return devices.map(device=>{
    const reasons=[];
    if(device.virtual) reasons.push("simulation");
    if(!device.online) reasons.push("offline");
    if(!device.virtual&&!assigned.has(device.uid)) reasons.push("unassigned");
    return {device,reasons,eligible:reasons.length===0};
  }).sort((a,b)=>Number(b.eligible)-Number(a.eligible)||Identity.primary(a.device,installation).localeCompare(Identity.primary(b.device,installation)));
}
function selectedAssetDevice(targets=assetTargets()) {
  const eligible=targets.filter(target=>target.eligible);
  if(!eligible.some(target=>target.device.uid===assetTarget)) assetTarget=eligible[0]?.device.uid||null;
  return eligible.find(target=>target.device.uid===assetTarget)?.device||null;
}
function assetInventoryState(device,item) {
  if(!device||device.assets===null||!Array.isArray(device.assets)) return {label:"unknown",installed:null};
  const installed=device.assets.find(asset=>asset.name===item.name);
  if(!installed) return {label:"absent",installed:null};
  if(installed.fingerprint===null||typeof installed.fingerprint!=="string") return {label:"unknown",installed};
  return {label:installed.fingerprint===item.fingerprint?"current":"stale",installed};
}
function fingerprintTail(value) {
  return typeof value==="string"&&value ? `…${value.slice(-10)}` : null;
}
function copyIdentity(value, fallback="unknown") {
  const tail=fingerprintTail(value);
  if(!tail) return `<code>${esc(fallback)}</code>`;
  return `<button type="button" class="identity-copy" data-copy-identity="${esc(value)}" title="${esc(value)}" aria-label="Copy full identity ${esc(value)}"><code>${esc(tail)}</code><span class="copy-feedback" aria-live="polite"></span></button>`;
}
function assetFacts(item) {
  const modified=Number(item.modified);
  const timestamp=Number.isFinite(modified)&&modified>0 ? new Date(modified*1000) : null;
  return `<dl class="asset-facts"><dt>Files</dt><dd>${item.files==null?'unknown':esc(item.files)}</dd><dt>Size</dt><dd>${item.bytes==null?'unknown':formatBytes(item.bytes)}</dd><dt>Modified</dt><dd>${timestamp?`<time datetime="${timestamp.toISOString()}">${timestamp.toLocaleString()}</time>`:'unknown'}</dd><dt>Fingerprint</dt><dd>${copyIdentity(item.fingerprint)}</dd></dl>`;
}
function assetLiveState(device,slot,observed) {
  const phase=device?.fetch?.[slot];
  if(phase==="sent"||phase==="queued") return "queued";
  if(phase==="fetching") return "fetching";
  if(phase==="err") return "failed";
  if(phase==="timeout") return "timed out";
  return observed;
}
function assetCatalogRow(device,item) {
  const observed=assetInventoryState(device,item), state=assetLiveState(device,item.name,observed.label);
  const pending=state==="queued"||state==="fetching";
  let action="", actionLabel="";
  if(observed.label==="absent") { action="send"; actionLabel="Send"; }
  else if(observed.label==="stale") { action="update"; actionLabel="Update"; }
  else if(observed.label==="unknown") { action="send-update"; actionLabel="Send / update"; }
  const unavailable=!device||pending;
  const reason=!device?"Choose an online, assigned physical device":pending?"Transfer already in progress":"";
  const primary=action?`<button data-asset-action="${action}" aria-label="${esc(`${actionLabel} ${item.name} to ${device?Identity.primary(device,installation):'selected device'}`)}" ${unavailable?`disabled title="${esc(reason)}"`:''}>${actionLabel}</button>`:'';
  // Remove is offered on any installed catalog pack (current/stale/unknown),
  // not just device-only extras. The active-slot warning lives in
  // confirmAssetAction; server + node treat the drop by name (39-remove-installed-pack-from-device).
  const removable=device&&observed.installed;
  const remove=removable?`<button class="danger" data-asset-action="remove" aria-label="${esc(`Remove ${item.name} from ${Identity.primary(device,installation)}`)}" ${pending?'disabled title="Transfer already in progress"':''}>Remove</button>`:'';
  const controls=`${primary}${remove}`||'<span class="asset-no-action">No action needed</span>';
  return `<article class="asset-row" data-slot="${esc(item.name)}" data-state="${esc(state)}"><div class="asset-row-main"><strong>${esc(item.name)}</strong>${assetFacts(item)}</div><span class="asset-state asset-state-${state.replace(/[^a-z0-9]+/gi,'-')}" role="status" aria-live="polite">${esc(state)}</span><div class="asset-row-action">${controls}</div></article>`;
}
function assetExtraRow(device,item) {
  const state=assetLiveState(device,item.name,"extra"), pending=state==="queued"||state==="fetching";
  return `<article class="asset-row asset-extra" data-slot="${esc(item.name)}" data-state="${esc(state)}"><div class="asset-row-main"><strong>${esc(item.name)}</strong>${assetFacts(item)}</div><span class="asset-state asset-state-${state.replace(/[^a-z0-9]+/gi,'-')}" role="status" aria-live="polite">${esc(state)}</span><div class="asset-row-action"><button class="danger" data-asset-action="remove" aria-label="${esc(`Remove ${item.name} from ${Identity.primary(device,installation)}`)}" ${pending?'disabled title="Transfer already in progress"':''}>Remove</button></div></article>`;
}
function assetIsActive(device,slot) {
  return Array.isArray(device?.active_asset_slots)&&device.active_asset_slots.includes(slot);
}
function confirmAssetAction(device,slot,action) {
  const active=assetIsActive(device,slot);
  if(action==="remove") {
    if(active) return confirm(`Asset slot "${slot}" is declared by the active patch. Removing it can immediately break the running patch. Safer sequence: send a new side-by-side generation, switch the patch, then remove the old slot. Remove anyway?`);
    return confirm(`Remove asset slot "${slot}" from ${Identity.primary(device,installation)}?`);
  }
  if(active&&action!=="send") return confirm(`Asset slot "${slot}" is declared by the active patch. Updating it in place can expose the running engine to a partial update or broken files. Safer sequence: send a new side-by-side generation, switch the patch, then remove the old slot. ${action==="update"?'Update':'Send / update'} anyway?`);
  return true;
}
function resolveAssetFeedback(device) {
  const pending=assetFeedbackPending;
  if(!pending||!device||device.uid!==pending.uid||!Array.isArray(device.assets)) return;
  const observedAt=Number(device.assets_observed_at)||0;
  if(observedAt<=pending.observedAt) return;
  const installed=device.assets.find(item=>item.name===pending.slot);
  const resolved=pending.action==="remove" ? !installed : installed?.fingerprint===pending.fingerprint;
  if(!resolved) return;
  assetFeedback=pending.action==="remove"
    ? `Removed ${pending.slot} from ${Identity.primary(device,installation)}; confirmed by observed inventory.`
    : `${pending.slot} is current on ${Identity.primary(device,installation)}; confirmed by observed inventory.`;
  assetFeedbackPending=null;
}
function renderAssets() {
  const select=$("#asset-target"), catalog=$("#asset-catalog"), extras=$("#asset-extras");
  if(!select||!catalog||!extras) return;
  const active=document.activeElement, focused=active===select, focusRow=active?.closest?.("[data-slot]"), focusSlot=focusRow?.dataset.slot, focusAction=active?.dataset?.assetAction, focusRefresh=active?.id==="asset-refresh";
  const targets=assetTargets(), device=selectedAssetDevice(targets);
  resolveAssetFeedback(device);
  select.innerHTML=targets.length?targets.map(target=>`<option value="${esc(target.device.uid)}" ${target.device.uid===assetTarget?'selected':''} ${target.eligible?'':`disabled`} >${esc(Identity.primary(target.device,installation))}${target.reasons.length?` — ${esc(target.reasons.join(', '))}`:''}</option>`).join(''):'<option disabled>No devices discovered</option>';
  select.disabled=!targets.some(target=>target.eligible);
  select.onchange=()=>{assetTarget=select.value;assetFeedback="";renderAssets();};
  if(focused) select.focus();
  const ineligible=targets.filter(target=>!target.eligible);
  $("#asset-target-reasons").innerHTML=ineligible.length?ineligible.map(target=>`<span><strong>${esc(Identity.primary(target.device,installation))}</strong> · ${esc(target.reasons.join(' · '))}</span>`).join(''):targets.length?'<span class="dim">Every discovered device is eligible.</span>':'<span class="dim">No devices discovered.</span>';
  $("#asset-catalog-summary").textContent=`${distribution.assets.length} host slot${distribution.assets.length===1?'':'s'}${device?` · compared with ${Identity.primary(device,installation)}`:''}`;
  $("#asset-feedback").textContent=assetFeedback;
  catalog.innerHTML=distribution.assets.length?distribution.assets.map(item=>assetCatalogRow(device,item)).join(''):'<p class="empty">No asset slots in the host catalog.</p>';
  const hostNames=new Set(distribution.assets.map(item=>item.name));
  const extraItems=device&&Array.isArray(device.assets)?device.assets.filter(item=>!hostNames.has(item.name)):[];
  const inventoryBanner=!device?'<p class="asset-inventory-note">Choose an eligible target to compare its observed inventory.</p>':!Array.isArray(device.assets)?'<p class="asset-inventory-note unknown">Inventory unknown — this node has not replied yet, or does not support asset inventory.</p>':`<p class="asset-inventory-note current">Observed ${device.assets.length} installed slot${device.assets.length===1?'':'s'}${device.assets_observed_at?` · ${ago(device.assets_observed_at)}`:''}.</p>`;
  const quarantine=device?.assets_quarantine?.length?`<p class="asset-inventory-note unknown">Inventory incomplete: ${device.assets_quarantine.length} malformed entr${device.assets_quarantine.length===1?'y was':'ies were'} excluded.</p>`:"";
  extras.innerHTML=`${inventoryBanner}${quarantine}${extraItems.length?`<div class="asset-extras-heading"><h3>Device-only slots</h3><p class="dim">Installed on this device but absent from the host catalog.</p></div>${extraItems.map(item=>assetExtraRow(device,item)).join('')}`:''}`;
  document.querySelectorAll("#tab-assets [data-asset-action]").forEach(button=>button.onclick=()=>{
    const row=button.closest("[data-slot]"), slot=row.dataset.slot, action=button.dataset.assetAction;
    if(!device||!confirmAssetAction(device,slot,action)) return;
    assetFeedback=action==="remove"?`Removing ${slot} from ${Identity.primary(device,installation)}…`:`${action==="update"?'Updating':'Sending'} ${slot} to ${Identity.primary(device,installation)}…`;
    const hostItem=distribution.assets.find(item=>item.name===slot);
    assetFeedbackPending={uid:device.uid,slot,action,observedAt:Number(device.assets_observed_at)||0,fingerprint:hostItem?.fingerprint||null};
    $("#asset-feedback").textContent=assetFeedback;
    if(action==="remove") ws.send("drop_distribution",{uid:device.uid,kind:"asset",name:slot});
    else ws.send("send_distribution",{uid:device.uid,kind:"asset",name:slot,confirmed_active:false});
  });
  $("#asset-refresh").onclick=()=>{assetFeedback="Refreshing host catalog…";$("#asset-feedback").textContent=assetFeedback;ws.send("refresh_distribution",{});};
  if(focusSlot&&focusAction) document.querySelector(`#tab-assets [data-slot="${CSS.escape(focusSlot)}"] [data-asset-action="${CSS.escape(focusAction)}"]`)?.focus();
  else if(focusRefresh) $("#asset-refresh").focus();
}
function nextFreeId() { const used = new Set(Object.values(installation.seats||{}).map(s=>Number(s.id))); let id=0; while (used.has(id)) id++; return id; }
function report(r) { if (!r) return '<p class="dim">No report loaded.</p>'; const keys=["hostname","engine","patch","git_rev","uptime","has_i2c","has_wifi","audio_channels","screen","update_model","contract_version","device_enabled","mute_all","output_enabled"]; return `<dl>${keys.map(k=>`<dt>${k}</dt><dd>${k==='uptime'?human(r[k]):esc(r[k])}</dd>`).join('')}</dl>`; }
function human(seconds) { seconds=Number(seconds)||0; return `${Math.floor(seconds/3600)}h ${Math.floor(seconds%3600/60)}m ${seconds%60}s`; }
function ago(epoch) { const s=Math.max(0,Math.round(Date.now()/1000-Number(epoch))); return s<60?`${s}s ago`:s<3600?`${Math.floor(s/60)}m ago`:`${Math.floor(s/3600)}h ago`; }
$("#mute-all").onclick=()=>{muted=!muted;installation.muted=muted;ws.send("mute_all",{value:muted?1:0});render();};
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
