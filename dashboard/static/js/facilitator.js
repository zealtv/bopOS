// Seat-owned live controls. /facilitator remains the standalone entry; the
// Dashboard tab embeds the same surface.
if (new URLSearchParams(location.search).get("embedded") === "1") document.body.classList.add("embedded");
const ws = new BopSocket("/ws");
let installation = {devices: {}, seats: {}, groups: {}};
let cueLeadModified = false;
let muted = false;
let master = 1.0;
let presetNames = [];
let renderedCueSignature = null;
const openCommandDevices = new Set();
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

// The parameter rows themselves live in control-surface.js (37/07) so the
// Device tab can render the identical surface. This page keeps what is its
// own: which cards exist, cues, master/silence, presets, device commands.
const surface = window.ControlSurface.create({
  getState: () => installation,
  deviceForSeat: seat => deviceForSeat(seat),
  send: ({scope, id, name, value}) => {
    const numericId = id == null ? null : Number(id);
    const payload = {scope, name, value};
    if (numericId != null) payload.id = numericId;
    ws.send("set_live_param", payload);
    updateLocalParams(scope, numericId, name, value);
  },
  // A drawer-authored generator takes the same targeting but carries a §3.2
  // argument list, so it needs its own verb; the server records the automation
  // and clears it again on `stop`.
  sendAutomation: ({scope, id, name, args}) => {
    const numericId = id == null ? null : Number(id);
    const payload = {scope, name, args};
    if (numericId != null) payload.id = numericId;
    ws.send("set_live_automation", payload);
  },
  setInteracting: editing => { interacting = editing; },
  requestRender: () => render(),
});

// All / Groups / Seat. The filter is the reusable component (37/10); this page
// only decides which cards a chosen target implies.
const targetFilter = window.SeatFilter.create({
  host: $("#target-filter-host"),
  getSeats: () => seats(),
  label: "Control target",
  onChange: () => { renderCards(); renderPresets(); $("#cards").scrollTop = 0; },
});

function liveSchema() {
  const schema = installation.live_controls;
  if (!schema || typeof schema.patch !== "string" || !Array.isArray(schema.declarations)) return null;
  const valid = schema.declarations.every(declaration =>
    declaration && declaration.dashboard === true &&
    typeof declaration.identity === "string" && declaration.identity.length > 0 &&
    typeof declaration.name === "string" &&
    (declaration.path == null || Array.isArray(declaration.path)));
  if (!valid) return null;
  const declarations = schema.declarations.map(declaration => ({...declaration, path: declaration.path || []}));
  return {patch: schema.patch, declarations};
}

function liveCueSchema() {
  const schema = installation.live_cues;
  if (!schema || typeof schema.patch !== "string" || !Array.isArray(schema.cues)) return null;
  const cues = schema.cues.filter(cue => cue && typeof cue.id === "string" && cue.id.length > 0);
  return {patch: schema.patch, cues};
}

function seats() {
  return Object.values(installation.seats || {}).sort((a, b) => Number(a.id) - Number(b.id));
}

function groups() {
  return Object.values(installation.groups || {}).sort((a, b) => Number(a.id) - Number(b.id));
}

function groupSeats(id) {
  return seats().filter(seat => (seat.groups || []).map(Number).includes(Number(id)));
}

function deviceForSeat(seat) {
  const devices = Object.values(installation.devices || {});
  return (seat.bound ? installation.devices?.[seat.bound] : null) ||
    devices.find(device => device.virtual && Number(device.seat_id) === Number(seat.id));
}

function replayButton(scope, id, disabled) {
  return `<button class="send-all" data-replay-live data-live-scope="${scope}"${id == null ? "" : ` data-live-id="${esc(id)}"`} ${disabled ? "disabled" : ""}>Send all</button>`;
}

function deviceCommands(device) {
  if (!device) return "";
  const commands = (installation.facilitator_commands || []).map(command =>
    `<button data-device-command="${esc(command)}" data-uid="${esc(device.uid)}" class="${destructiveCommands.has(command) ? "hold" : ""}">${esc(commandLabel(command))}${destructiveCommands.has(command) ? " — hold" : ""}</button>`).join("");
  if (!commands) return "";
  return `<details class="device-commands" data-command-uid="${esc(device.uid)}" ${openCommandDevices.has(device.uid) ? "open" : ""}><summary>Device setup</summary><div>${commands}</div></details>`;
}

function liveCard(scope, item, members, declarations, schemaAvailable) {
  const id = scope === "all" ? null : Number(item.id);
  const empty = members.length === 0;
  const device = scope === "seat" ? deviceForSeat(item) : null;
  const live = !!device?.online && Number(device.engine_alive) !== 0;
  const name = scope === "all" ? "All Seats" : (item.name || `${scope === "group" ? "Group" : "Seat"} ${item.id}`);
  const meta = scope === "all" ? `${members.length} Seats` : scope === "group"
    ? `g${item.id} · ${members.length} ${members.length === 1 ? "Seat" : "Seats"}`
    : `Seat ${item.id} · ${device ? (device.online ? "online" : "offline") : (item.bound ? "offline" : "unbound")}`;
  const controls = declarations.length ? `<div class="promoted-controls">${surface.tree(scope, id, members, declarations, empty)}</div>` : "";
  const cardKey = `${scope}:${id ?? "all"}`;
  return `<article class="live-card ${scope}-card${scope === "group" && empty ? " empty-group" : ""}${scope === "seat" && !live ? " offline" : ""}" data-live-scope="${scope}"${id == null ? "" : ` data-live-id="${id}"`}>
    <div class="live-card-head">${scope === "seat" ? `<i class="dot ${live ? "ok" : ""}" aria-hidden="true"></i>` : ""}<span class="name"><strong>${esc(name)}</strong><small>${esc(meta)}</small></span>${scope === "all" || scope === "seat" ? replayButton(scope, id, !schemaAvailable) : ""}</div>
    ${controls}${scope === "seat" ? deviceCommands(device) : ""}<output class="live-param-status visually-hidden" aria-live="polite">${esc(surface.announcement(cardKey))}</output>
  </article>`;
}

ws.on("connection", connected => { $("#ws-status").textContent = connected ? "" : "reconnecting…"; $("#ws-status").className = connected ? "online" : "offline"; });
// The facilitator view was silently swallowing server ws_error messages (no
// handler → ws.js buffers and never surfaces them). A rejected set_live_param
// then looked like "nothing happened" (thread 43). Surface it like dashboard.js.
ws.on("error", data => { alert(data?.message || "The dashboard rejected that action."); });
ws.on("state", data => {
  installation = data; muted = !!data.muted; master = Number(data.master ?? 1);
  surface.refreshAnchors(data);
  presetNames = Object.keys(data.presets || {}).sort();
  if (!cueLeadModified) $("#cue-lead").value = Number(data.cue_lead_ms ?? 500);
  render();
  const loading = $("#initial-loading");
  if (loading) loading.hidden = true;
});
ws.on("device_update", data => {
  if (data?.devices) installation = data;
  else if (data?.uid) installation.devices[data.uid] = data;
  render();
});
ws.on("params_declaration", data => { if (data?.uid) installation.devices[data.uid] = data; render(); });
ws.on("device_offline", data => { if (installation.devices[data.uid]) { installation.devices[data.uid].online = false; render(); } });
ws.on("mute_all", data => { muted = !!data.value; renderControls(); });
ws.on("master", data => { master = Number(data.value); renderControls(); });
ws.on("presets", data => { presetNames = data.names || []; renderPresets(); });
ws.on("cue_scheduled", data => {
  const cue = (liveCueSchema()?.cues || []).find(item => item.id === data.cue_id);
  const status = $("#cue-status");
  if (status) status.value = `${cue?.label || data.cue_id} scheduled · ${data.lead_ms} ms`;
});

let interacting = false;
$("#cue-lead").addEventListener("input", () => { cueLeadModified = true; });
document.addEventListener("pointerdown", event => {
  if (event.target.matches('input[type="range"], input[type="checkbox"][data-live-param]')) interacting = true;
});
document.addEventListener("pointerup", () => {
  if (!interacting) return;
  // Checkbox change/click follows pointerup; keep the render guard through that
  // event so a live-param checkbox (automated or plain) survives a heartbeat
  // re-render long enough to fire onchange and send its value (thread 43).
  setTimeout(() => { interacting = false; render(); }, 0);
});

function render() {
  $("#venue-name").textContent = installation.name || "bopOS";
  targetFilter.render();
  renderCues(); renderCards(); renderControls(); renderCommands(); renderPresets();
}

function cueButton(cue) {
  const label = cue.label || cue.id;
  return `<button data-live-cue="${esc(cue.id)}" data-cue-label="${esc(label)}" aria-label="Fire ${esc(label)} cue">${esc(label)}</button>`;
}

function renderCues() {
  const cues = liveCueSchema()?.cues || [];
  const panel = $("#cue-panel");
  panel.hidden = cues.length === 0;
  const signature = JSON.stringify(cues);
  if (!cues.length) {
    renderedCueSignature = signature;
    $("#declared-cues").innerHTML = "";
    $("#cue-status").value = "";
    return;
  }
  if (signature === renderedCueSignature) return;
  renderedCueSignature = signature;
  $("#declared-cues").innerHTML = cues.map(cueButton).join("");
  document.querySelectorAll("[data-live-cue]").forEach(button => button.onclick = () => {
    const lead = $("#cue-lead");
    const leadMs = Math.min(10000, Math.max(100, Number(lead.value) || 500));
    lead.value = leadMs;
    ws.send("fire_cue", {cue_id: button.dataset.liveCue, lead_ms: leadMs});
    button.disabled = true;
    button.style.setProperty("--cue-lead-duration", `${leadMs}ms`);
    button.classList.add("scheduling");
    button.setAttribute("aria-busy", "true");
    setTimeout(() => button.classList.add("triggered"), leadMs);
    setTimeout(() => {
      button.disabled = false;
      button.classList.remove("scheduling", "triggered");
      button.style.removeProperty("--cue-lead-duration");
      button.removeAttribute("aria-busy");
      button.focus({preventScroll: true});
    }, leadMs + 300);
  });
}

function renderCards() {
  if (interacting) return;
  const schema = liveSchema();
  const declarations = schema?.declarations || [];
  const allSeats = seats();
  const available = declarations.length > 0;
  const chosen = targetFilter ? targetFilter.target() : {mode: "all"};
  let cards;
  if (chosen.mode === "seat") {
    // The filter always resolves to a real Seat when one exists, so an empty
    // list here means the venue has no Seats, not that none was chosen.
    cards = chosen.seat ? [liveCard("seat", chosen.seat, [chosen.seat], declarations, available)] : [];
  } else if (chosen.mode === "groups") {
    cards = groups().map(group => liveCard("group", group, groupSeats(group.id), declarations, available));
  } else {
    cards = [liveCard("all", {}, allSeats, declarations, available && allSeats.length > 0)];
  }
  $("#cards").dataset.liveView = chosen.mode;
  $("#cards").innerHTML = cards.join("")
    || `<p class="empty">${chosen.mode === "groups" ? "No groups" : "No Seats"}</p>`;
  bindCards();
}

function updateLocalParams(scope, id, identity, value) {
  const members = scope === "all" ? seats() : scope === "group" ? groupSeats(id) : seats().filter(seat => Number(seat.id) === Number(id));
  for (const seat of members) {
    seat.params ||= {};
    seat.params[identity] = value;
  }
}

function bindCards() {
  surface.bind(document);
  document.querySelectorAll("[data-replay-live]").forEach(button => button.onclick = () => {
    const payload = {scope: button.dataset.liveScope};
    if (button.dataset.liveId != null) payload.id = Number(button.dataset.liveId);
    ws.send("replay_live_params", payload);
  });
  document.querySelectorAll("[data-device-command]").forEach(button => bindCommandButton(button, button.dataset.uid));
  document.querySelectorAll("details[data-command-uid]").forEach(details => {
    details.ontoggle = () => details.open ? openCommandDevices.add(details.dataset.commandUid) : openCommandDevices.delete(details.dataset.commandUid);
  });
}

function renderControls() {
  if (!interacting) $("#master").value = master;
  $("#master-out").value = Math.round(master * 100) + "%";
  const silence = $("#silence");
  silence.textContent = muted ? "RESUME" : "SILENCE ALL";
  silence.classList.toggle("active", muted);
}

// Presets follow the target filter (Bob, 2026-07-25): saving under All is a
// different preset from saving under Seat 2, so both the save and the load
// carry the current target. The shelf is no longer hidden when embedded — the
// Control tab reserves a place for it.
function presetScope() {
  const chosen = targetFilter.target();
  if (chosen.mode === "seat" && chosen.seat) {
    return {scope: "seat", id: Number(chosen.seat.id),
            label: chosen.seat.name || `Seat ${chosen.seat.id}`};
  }
  if (chosen.mode === "groups") return {scope: "groups", id: null, label: "Groups"};
  return {scope: "all", id: null, label: "All Seats"};
}

function renderPresets() {
  const scope = presetScope();
  // Embedded, the Control tab owns the preset shelf (it has Save as…), so this
  // page's own shelf stays a standalone-only affordance rather than a second
  // copy inside the iframe.
  $("#preset-section").hidden = document.body.classList.contains("embedded");
  const label = $("#preset-scope");
  if (label) label.value = scope.label;
  $("#presets").innerHTML = presetNames.length
    ? presetNames.map(name => `<button class="chip" data-preset="${esc(name)}">${esc(name)}</button>`).join("")
    : '<span class="dim">No presets saved</span>';
  document.querySelectorAll("[data-preset]").forEach(button => button.onclick = () => {
    const target = presetScope();
    ws.send("load_preset", {name: button.dataset.preset, scope: target.scope, id: target.id});
  });
}

const destructiveCommands = new Set(["updatebopos", "reboot", "shutdown"]);
function commandLabel(command) { return command === "updatebopos" ? "Update bopOS" : command.replaceAll("-", " ").replaceAll("_", " "); }
function renderCommands() {
  const commands = installation.facilitator_commands || [];
  $("#facilitator-commands").innerHTML = commands.length ? `<span class="command-scope-label">Fleet setup</span>${commands.map(command =>
    `<button data-command="${esc(command)}" class="${destructiveCommands.has(command) ? "hold" : ""}">${esc(commandLabel(command))}${destructiveCommands.has(command) ? " — hold" : ""}</button>`).join("")}` : "";
  document.querySelectorAll("[data-command]").forEach(button => bindCommandButton(button, "all"));
}
function bindCommandButton(button, uid) {
  const command = button.dataset.command || button.dataset.deviceCommand;
  const target = uid === "all" ? "all devices" : (installation.devices?.[uid]?.alias || "device");
  if (!destructiveCommands.has(command)) {
    button.onclick = () => { if (confirm(`${commandLabel(command)} ${target}?`)) ws.send("action", {uid, verb: command}); };
    return;
  }
  let timer = null;
  const cancel = () => { clearTimeout(timer); timer = null; button.classList.remove("holding"); };
  button.onpointerdown = () => {
    button.classList.add("holding");
    timer = setTimeout(() => { timer = null; button.classList.remove("holding"); ws.send("action", {uid, verb: command}); }, 1200);
  };
  button.onpointerup = cancel;
  button.onpointercancel = cancel;
  button.onpointerleave = cancel;
}

{
  const masterInput = $("#master");
  let last = 0, timer;
  const send = () => { master = Number(masterInput.value); ws.send("set_master", {value: master}); renderControls(); };
  masterInput.oninput = () => { const now = performance.now(); if (now - last >= 33) { last = now; send(); } else { clearTimeout(timer); timer = setTimeout(send, 33 - (now - last)); } };
  masterInput.onchange = send;
  masterInput.onpointerup = send;
}
$("#silence").onclick = () => { muted = !muted; ws.send("mute_all", {value: muted ? 1 : 0}); renderControls(); };
