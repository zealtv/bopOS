// Seat-owned live controls. /facilitator remains the standalone entry; the
// Dashboard tab embeds the same surface.
const embedded = new URLSearchParams(location.search).get("embedded") === "1";
if (embedded) document.body.classList.add("embedded");
const ws = new BopSocket("/ws");
let installation = {devices: {}, seats: {}, groups: {}};
let muted = false;
let master = 1.0;
const openCommandDevices = new Set();
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

// The parameter rows themselves live in control-surface.js (37/07) so the
// Device tab can render the identical surface. This page keeps what is its
// own: which cards exist, master/silence, and device commands. Events
// are no longer this page's business — the top event panel was retired in
// `04-event-fire-affordance` and firing lives on the panel's own rows.
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
  // The panel paints its own lead-progress sweep, so the send reports back the
  // lead it actually put on the wire rather than letting the surface guess.
  sendEvent: ({scope, id, identity, elements}) => {
    const selector = scope === "all" ? "all" : scope === "group" ? `g${id}` : String(id);
    const leadMs = Math.min(10000, Math.max(0, Number(installation.event_lead_ms ?? 500) || 0));
    ws.send("fire_event", {selector, identity, elements, lead_ms: leadMs});
    return leadMs;
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
  // ---- presets (41-preset-primitive/07) ----------------------------------
  // The catalog is listing metadata only; preset bodies stay server-side.
  presetCatalog: patch => installation.preset_catalog?.[patch] || [],
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
  requestCapturePreview: ({key, scope, id, patch}) => {
    capturePreviews.delete(key);
    pendingPreview = key;
    const payload = {scope, patch};
    if (id != null) payload.id = Number(id);
    ws.send("preview_preset_capture", payload);
  },
  capturePreview: key => capturePreviews.get(key) || null,
  // A report belongs to the row whose targets it covers exactly — an apply
  // broadcast carries no card key, and any client's apply may produce it.
  presetReport: (_key, members) => {
    if (!lastPresetReport) return null;
    const targets = new Set(Object.keys(lastPresetReport.targets || {}));
    const mine = (members || []).map(seat => String(seat.id));
    return mine.length && mine.length === targets.size
      && mine.every(id => targets.has(id)) ? lastPresetReport : null;
  },
});

// Capture previews and apply reports are per-row transient state: the surface
// renders them, this page holds them.
const capturePreviews = new Map();
let pendingPreview = null;
let lastPresetReport = null;

// The shared target picker's seat domain (02-component-unification/07). This
// replaces `SeatFilter`'s mode-exclusive All/Groups/Seat tabs: a target is now
// All, or any mixture of groups and Seats, and each selected entry gets a card.
// This page only decides which cards a chosen target implies.
//
// Group chips carry the `g<id>` wire selector rather than the Show inspector's
// portable `group:<name>`: nothing here is persisted into a portable document,
// and an id cannot be ambiguous when two groups share a name.
//
// The selection is this host's own (`storageKey`), which is what lets
// `08-control-tab-columns` give each column a target. `followFocusSeat` keeps
// the one genuinely shared thing: choosing a Seat on the Seats tab moves this
// picker to that Seat, across the iframe boundary.
const targetPicker = window.TargetPicker.create({
  host: $("#target-picker-host"),
  id: "control",
  storageKey: "bopos.target.control",
  followFocusSeat: true,
  // All stays offerable and never becomes the fallback (D5, Bob 2026-07-31).
  // A target of Seat 7 that loses Seat 7 becomes NO target — this surface
  // renders an unresolved state instead of silently driving the whole venue.
  pruneFallback: "empty",
  spec: () => ({
    label: "Control target",
    sections: window.TargetPicker.seatSections(
      {groups: groups(), seats: seats(), groupSelector: "id"}),
  }),
  onChange: () => { renderCards(); $("#cards").scrollTop = 0; },
});

function liveSchema() {
  const schema = installation.live_controls;
  if (!schema || typeof schema.patch !== "string" || !Array.isArray(schema.declarations)) return null;
  // The embedded page is the desktop Control tab and exposes the complete
  // manifest. The standalone facilitator/iPad surface remains deliberately
  // curated by the manifest's `dashboard: true` compatibility field.
  // Event declarations travel beside the params (they are not `/p/*` values);
  // the surface that renders rows folds them back in, so nothing else that
  // reads `declarations` ever sees them.
  const items = [...schema.declarations,
                 ...(Array.isArray(schema.events) ? schema.events : [])];
  const visible = embedded
    ? items
    : items.filter(declaration => declaration?.dashboard === true);
  const valid = visible.every(declaration =>
    declaration &&
    typeof declaration.identity === "string" && declaration.identity.length > 0 &&
    typeof declaration.name === "string" &&
    (declaration.path == null || Array.isArray(declaration.path)));
  if (!valid) return null;
  const declarations = visible.map(declaration => ({...declaration, path: declaration.path || []}));
  return {patch: schema.patch, declarations};
}

function liveEventSchema() {
  const schema = installation.live_controls;
  if (!schema || typeof schema.patch !== "string" || !Array.isArray(schema.events)) return null;
  const events = schema.events.filter(declaration =>
    declaration && typeof declaration.identity === "string" && declaration.identity.length > 0 &&
    (embedded || declaration.dashboard === true));
  return {patch: schema.patch, events};
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
  // An All card in a venue with no Seats has no member to read a device from;
  // the row still renders (disabled), so this must answer rather than throw.
  if (!seat) return null;
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

function liveCard(scope, item, members, declarations, schemaAvailable, patch) {
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
  // Panel anatomy: the preset row sits between the header and the parameter
  // rows, on every card that has parameters.
  //
  // Only when embedded. Bob's Q4 ruling for `41-preset-primitive` is that the
  // standalone facilitator/iPad surface carries NO preset affordance at all —
  // removed, not inert — which supersedes decision 1 of the tied stitch
  // `desktop-ui-overhaul/01-control-panel/7-preset-slot` ("the row is per
  // panel, not per privileged card"). Same reasoning as
  // `04-event-fire-affordance`: an iPad fires, it does not configure.
  const presets = embedded && declarations.length
    ? surface.presetRow(scope, id, members, patch, {key: cardKey,
        // Capturing from a target you cannot hear is refused (F8); applying
        // stays legal, because the values are dashboard state either way.
        saveDisabled: scope === "seat" && !live})
    : "";
  return `<article class="live-card ${scope}-card${scope === "group" && empty ? " empty-group" : ""}${scope === "seat" && !live ? " offline" : ""}" data-live-scope="${scope}"${id == null ? "" : ` data-live-id="${id}"`}>
    <div class="live-card-head">${scope === "seat" ? `<i class="dot ${live ? "ok" : ""}" aria-hidden="true"></i>` : ""}<span class="name"><strong>${esc(name)}</strong><small>${esc(meta)}</small></span>${scope === "all" || scope === "seat" ? replayButton(scope, id, !schemaAvailable) : ""}</div>
    ${presets}${controls}${scope === "seat" ? deviceCommands(device) : ""}<output class="live-param-status visually-hidden" aria-live="polite">${esc(surface.announcement(cardKey))}</output>
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
ws.on("preset_capture_preview", data => {
  if (!pendingPreview) return;
  capturePreviews.set(pendingPreview, data);
  pendingPreview = null;
  render();
});
ws.on("preset_saved", data => {
  const status = $("#event-status");
  if (status) {
    status.value = `Saved ${data.name}${data.omitted?.length
      ? ` · ${data.omitted.length} omitted as mixed` : ""}`;
  }
});
ws.on("preset_applied", data => { lastPresetReport = data; render(); });
ws.on("show_preset_capture_preview", data => {
  const applied = Number(data?.applied) || 0;
  const total = Number(data?.total) || 0;
  const omitted = Number(data?.omitted) || 0;
  if (!data?.show_loaded) {
    alert("Load or create a Show before capturing a preset arrangement.");
    return;
  }
  if (!applied) {
    alert(`${applied} of ${total} targets have a preset applied; there is nothing to capture.`);
    return;
  }
  const noun = applied === 1 ? "target has" : "targets have";
  const other = omitted === 1 ? "the other 1 will" : `the other ${omitted} will`;
  const omission = omitted ? `; ${other} not be captured` : "";
  if (confirm(`${applied} of ${total} ${noun} a preset applied${omission}. Add this arrangement as a Show step?`)) {
    ws.send("capture_show_preset_step", {scope: data.scope, id: data.id});
  }
});
ws.on("event_scheduled", data => {
  const declaration = (liveEventSchema()?.events || []).find(item => item.identity === data.identity);
  const status = $("#event-status");
  if (status) status.value = `${declaration?.name || data.identity} scheduled · ${data.lead_ms} ms`;
});

let interacting = false;
document.addEventListener("pointerdown", event => {
  if (event.target.matches('input[type="range"], button.live-toggle[data-live-param], select.live-enum[data-live-param]')) interacting = true;
});
document.addEventListener("pointerup", () => {
  if (!interacting) return;
  // Click/change follows pointerup; keep the render guard through that event so
  // a live-param toggle or enum (automated or plain) survives a heartbeat
  // re-render long enough to fire its handler and send its value (thread 43).
  setTimeout(() => { interacting = false; render(); }, 0);
});

function render() {
  $("#venue-name").textContent = installation.name || "bopOS";
  targetPicker.render();
  renderShowCapture();
  renderCards(); renderControls(); renderCommands();
}

function renderShowCapture() {
  if (!embedded) return;
  // No target, nothing to capture — and no scope this could be widened to.
  if (!targetPicker.selection().length) return;
  const host = $("#target-picker-host");
  host.insertAdjacentHTML("beforeend",
    '<button type="button" class="capture-show-step" data-capture-show-step>Capture as Show step</button>');
  host.querySelector("[data-capture-show-step]").onclick = () => {
    const target = presetScope();
    if (!target) return;
    ws.send("preview_show_preset_capture", {
      scope: target.scope,
      ...(target.id == null ? {} : {id: target.id}),
    });
  };
}

// One selected entry, one card. The picker has already pruned selectors this
// venue no longer has, so an unresolvable entry here means a group renamed
// between renders rather than stale state.
function selectedCard(selector, declarations, available, patch) {
  if (selector.startsWith("g") || selector.startsWith("group:")) {
    const catalog = groups();
    const group = selector.startsWith("g")
      ? catalog.find(item => `g${item.id}` === selector)
      : catalog.find(item => item.name === selector.slice(6));
    return group
      ? liveCard("group", group, groupSeats(group.id), declarations, available, patch)
      : null;
  }
  const seat = seats().find(item => String(item.id) === selector);
  return seat ? liveCard("seat", seat, [seat], declarations, available, patch) : null;
}

// "all" / "groups" / "seats" / "mixed" — what the selection is made of, for the
// layout to key off.
function selectionMode(selection) {
  if (!selection.length) return "none";
  if (selection.includes("all")) return "all";
  const kinds = new Set(selection.map(entry =>
    entry.startsWith("g") || entry.startsWith("group:") ? "groups" : "seats"));
  return kinds.size === 1 ? [...kinds][0] : "mixed";
}

// What the picker dropped, named the way the operator chose it. A bare "7"
// would not tell anyone which venue thing has gone.
function lostLabel(selector) {
  if (selector.startsWith("group:")) return `Group ${selector.slice(6)}`;
  if (/^g\d+$/.test(selector)) return `Group ${selector.slice(1)}`;
  return `Seat ${selector}`;
}

// No target is a state, not an error, and it renders NO controls — not
// disabled ones; there is nothing they could act on (D5).
function unresolvedTarget() {
  const lost = targetPicker.dropped();
  const said = lost.length
    ? `${lost.map(lostLabel).join(", ")} ${lost.length === 1 ? "is" : "are"} no longer in this venue.`
    : "No target chosen.";
  return `<p class="live-unresolved">${esc(said)}<button type="button" data-choose-target>choose a target</button></p>`;
}

function renderCards() {
  if (interacting) return;
  const schema = liveSchema();
  const declarations = schema?.declarations || [];
  const allSeats = seats();
  const available = declarations.length > 0;
  const selection = targetPicker.selection();
  const patch = schema?.patch;
  $("#cards").dataset.liveView = selectionMode(selection);
  if (!selection.length) {
    $("#cards").innerHTML = unresolvedTarget();
    $("#cards").querySelector("[data-choose-target]").onclick = () => targetPicker.reveal();
    return;
  }
  const cards = selection.includes("all")
    ? [liveCard("all", {}, allSeats, declarations, available && allSeats.length > 0, patch)]
    : selection.map(entry => selectedCard(entry, declarations, available, patch)).filter(Boolean);
  $("#cards").innerHTML = cards.join("") || '<p class="empty">No Seats</p>';
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

// Capture-as-step targets a coarse scope server-side (all / groups / one seat),
// which a mixable selection has to be reduced to: one Seat and nothing else is
// that Seat, anything involving a group is "groups", and everything else — All,
// or several Seats — is the whole venue. The reduction lives here rather than
// widening the server's vocabulary, which `41-preset-primitive` ratified.
// An unresolved target reduces to nothing rather than to the venue: the
// capture affordance is not rendered at all while this returns null.
function presetScope() {
  const selection = targetPicker.selection();
  if (!selection.length) return null;
  if (selection.includes("all")) {
    return {scope: "all", id: null, label: "All Seats"};
  }
  const seatOnly = selection.every(entry =>
    !entry.startsWith("g") && !entry.startsWith("group:"));
  if (seatOnly && selection.length === 1) {
    const seat = seats().find(item => String(item.id) === selection[0]);
    if (seat) {
      return {scope: "seat", id: Number(seat.id),
              label: seat.name || `Seat ${seat.id}`};
    }
  }
  if (seatOnly) return {scope: "all", id: null, label: "All Seats"};
  return {scope: "groups", id: null, label: "Groups"};
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
