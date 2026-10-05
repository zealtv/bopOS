let installation = { devices: {} };
let selected = null;
let selectedSeat = null;
let selectedGroup = null;
let focusedGroup = null;
let visibleGroups = [null, null, null, null];
let groupMemberFilter = "";
let seatRosterFilter = "";
let seatSidebarMode = "seats";
let groupMessage = "";
let muted = false;
let master = 1.0;
const heartbeats = new Map();
const seatBindingDrafts = new Map();
const logDestinationDrafts = new Map(); // uid -> unsaved log destination choice
let patchFilter = "";
let distribution = { assets: [], patches: [] };
let assetFeedback = "";
let assetFeedbackPending = null;
let deviceFilter = "all";
let editorPatchChoice = null;
let manifestDraft = null;
let manifestBaseline = null;
let manifestDirty = false;
let manifestFeedback = "";
let manifestDrag = null;
const REMOTE_COMMANDS = ["restart-engine", "updatebopos", "reboot", "shutdown"];
let remoteCommandDraft = null;
let remoteCommandSaving = false;
let remoteCommandFeedback = "";
let pendingCreatedPatch = null;
const $ = (selector) => document.querySelector(selector);
const esc = (value) =>
  String(value ?? "—").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const Identity = window.DeviceIdentity;
const performanceActive = () => installation.performance === true;
$("#performance-toggle").onclick = () => ws.send("set_performance", { active: !performanceActive() });

async function copyFullIdentity(button) {
  const value = button.dataset.copyIdentity;
  let copied = false;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      copied = true;
    }
  } catch (_error) {}
  if (!copied) {
    const input = document.createElement("textarea");
    input.value = value;
    input.setAttribute("readonly", "");
    input.style.position = "fixed";
    input.style.opacity = "0";
    document.body.append(input);
    input.select();
    try {
      copied = document.execCommand("copy");
    } catch (_error) {}
    input.remove();
  }
  const feedback = button.querySelector(".copy-feedback");
  if (feedback) {
    feedback.textContent = copied ? "Copied" : "Copy failed";
    setTimeout(() => {
      if (feedback.isConnected) feedback.textContent = "";
    }, 1400);
  }
}
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-copy-identity]");
  if (button) copyFullIdentity(button);
});
const GROUP_SLOTS = window.GroupSlots.palette;
const TAB_NAMES = ["show", "control", "seats", "devices", "patches", "assets"];
// The Control tab was called Dashboard until 2026-07-25 (37/10). Existing
// bookmarks and links still say #dashboard, so keep resolving it.
const TAB_ALIASES = { dashboard: "control" };
function tabFromHash(hash) {
  const name = TAB_ALIASES[hash] || hash;
  return TAB_NAMES.includes(name) ? name : null;
}
let activeTab = tabFromHash(location.hash.slice(1)) || "show";

function activateTab(name, updateHash = true) {
  if (!TAB_NAMES.includes(name)) name = "show";
  activeTab = name;
  document.querySelectorAll("[data-tab]").forEach((button) => {
    const active = button.dataset.tab === name;
    button.setAttribute("aria-selected", active ? "true" : "false");
    button.tabIndex = active ? 0 : -1;
  });
  document.querySelectorAll("[data-tab-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.tabPanel !== name;
  });
  if (updateHash) history.replaceState(null, "", `#${name}`);
  window.scrollTo(0, 0);
  if (name === "seats" && installation.room)
    requestAnimationFrame(() => Spatial.render(installation, selectedSeat, selectSeat, ws, groupView()));
}
document.querySelectorAll("[data-tab]").forEach((button) => {
  button.onclick = () => activateTab(button.dataset.tab);
  button.onkeydown = (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    let index = TAB_NAMES.indexOf(activeTab);
    if (event.key === "ArrowLeft") index = (index - 1 + TAB_NAMES.length) % TAB_NAMES.length;
    if (event.key === "ArrowRight") index = (index + 1) % TAB_NAMES.length;
    if (event.key === "Home") index = 0;
    if (event.key === "End") index = TAB_NAMES.length - 1;
    activateTab(TAB_NAMES[index]);
    $(`[data-tab="${TAB_NAMES[index]}"]`)?.focus();
  };
});
window.addEventListener("hashchange", () => activateTab(tabFromHash(location.hash.slice(1)) || "show", false));
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape" || activeTab !== "seats" || event.target.matches("input,select,textarea")) return;
  if (focusedGroup !== null) {
    focusedGroup = null;
    renderGroups();
    renderGroupMap();
    Spatial.render(installation, selectedSeat, selectSeat, ws, groupView());
  } else if (visibleGroupIds().length) clearGroupView();
});
activateTab(activeTab, false);

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
function render() {
  $("#project-bar-project").textContent = installation.project || "—";
  $("#project-bar-site").textContent = installation.current_site || "—";
  window.ProjectMenu?.render();
  $("#project-bar-patch").textContent = installation.fleet_patch?.name || "—";
  $("#project-bar-show").textContent = installation.current_show || "—";
  const devices = Object.values(installation.devices || {});
  const seats = Object.values(installation.seats || {}).sort((a, b) => a.id - b.id);
  const bound = new Set(seats.map((s) => s.bound).filter(Boolean));
  const physical = devices
    .filter((d) => !d.virtual)
    .sort((a, b) => Number(b.online) - Number(a.online) || (Number(b.last_seen) || 0) - (Number(a.last_seen) || 0));
  const visible = physical.filter((device) => {
    if (deviceFilter === "online" || deviceFilter === "offline") return !!device.online === (deviceFilter === "online");
    if (deviceFilter === "bound" || deviceFilter === "unbound") return bound.has(device.uid) === (deviceFilter === "bound");
    return true;
  });
  $("#assigned").innerHTML = seats.map(seatRow).join("") || '<p class="dim">No seats</p>';
  const rosterFilter = $("#seat-roster-filter");
  if (rosterFilter && document.activeElement !== rosterFilter) rosterFilter.value = seatRosterFilter;
  const applyRosterFilter = () => {
    seatRosterFilter = rosterFilter?.value || "";
    const value = seatRosterFilter.trim().toLowerCase();
    let matches = 0;
    document.querySelectorAll("#assigned [data-seat-filter]").forEach((row) => {
      row.hidden = !!value && !row.dataset.seatFilter.startsWith(value);
      if (!row.hidden) matches++;
    });
    const empty = $("#seat-roster-filter-empty");
    if (empty) empty.hidden = !value || matches > 0;
  };
  if (rosterFilter) rosterFilter.oninput = applyRosterFilter;
  applyRosterFilter();
  $("#device-roster").innerHTML =
    visible
      .map((device) =>
        row(
          device,
          seats.find((seat) => seat.bound === device.uid),
        ),
      )
      .join("") || '<p class="dim">No matching devices</p>';
  window.WifiNetworks?.status();
  document.querySelectorAll(".seat-row").forEach((el) => {
    el.onclick = (event) => {
      if (!event.target.closest("input")) selectSeat(Number(el.dataset.seatId));
    };
    const input = el.querySelector("[data-seat-name]");
    input.onchange = () => ws.send("update_seat", { id: Number(el.dataset.seatId), name: input.value });
  });
  document.querySelectorAll(".device-row:not(.seat-row)").forEach((el) => (el.onclick = () => select(el.dataset.uid)));
  $("#device-filter").value = deviceFilter;
  $("#device-filter").onchange = (event) => {
    deviceFilter = event.target.value;
    render();
  };
  $("#forget-offline").onclick = () => {
    if (confirm("Forget all offline unbound devices from this runtime roster?")) ws.send("forget_offline_unbound", {});
  };
  $("#seat-add").onclick = () => {
    const id = nextFreeId();
    selectedSeat = id;
    selected = null;
    ws.send("add_seat", { id, name: `Seat ${id}`, positions: [] });
  };

  renderEditor();
  renderPatchesTab();
  renderAssets();
  renderGroups();
  renderGroupMap();
  Spatial.render(installation, selectedSeat, selectSeat, ws, groupView());
  renderRoom();
  renderHeader();
  renderSeatDetail();
  renderDeviceDetail();
}
function occupant(seat) {
  const devices = Object.values(installation.devices || {});
  return devices.find((d) => d.virtual && Number(d.seat_id) === Number(seat.id)) || installation.devices?.[seat.bound];
}
function reconcileSelection() {
  if (selectedSeat != null) {
    const seat = installation.seats?.[String(selectedSeat)] || installation.seats?.[selectedSeat];
    if (!seat) {
      selectedSeat = null;
      selected = null;
      return;
    }
    selected = occupant(seat)?.uid || null;
    return;
  }
  if (!selected || !installation.devices?.[selected]) {
    selected = null;
    return;
  }
  const seat = Object.values(installation.seats || {}).find((item) => item.bound === selected);
  if (seat) selectedSeat = seat.id;
}

const PATCH_BADGE_LABELS = {
  unset: "not set",
  unknown: "unknown / last seen",
  switching: "switching",
  timeout: "switch timed out",
  failed: "switch failed",
  missing: "missing",
  mismatch: "mismatch",
  stale: "stale",
  stale_unverified: "stale (unverified)",
  current: "current",
};
const PATCH_BADGE_ORDER = [
  "current",
  "switching",
  "timeout",
  "failed",
  "missing",
  "mismatch",
  "stale",
  "stale_unverified",
  "unknown",
  "unset",
];
function patchBadge(value) {
  const badge = value || "unknown",
    label = PATCH_BADGE_LABELS[badge] || badge.replaceAll("_", " ");
  return `<span class="patch-badge patch-badge-${esc(badge)}" title="Fleet patch: ${esc(label)}">${esc(label)}</span>`;
}
function badgeTone(value) {
  return value && !["current", "unset"].includes(value) ? "patch-exception" : "";
}
function fleetPatchSummary() {
  const assigned = Object.values(installation.seats || {})
    .map(occupant)
    .filter(Boolean);
  const counts = new Map();
  assigned.forEach((device) => counts.set(device.patch_badge || "unknown", (counts.get(device.patch_badge || "unknown") || 0) + 1));
  const progress = PATCH_BADGE_ORDER.filter((badge) => counts.has(badge))
    .map((badge) => `${counts.get(badge)} ${PATCH_BADGE_LABELS[badge]}`)
    .join(" · ");
  const targets = `${assigned.length} assigned target${assigned.length === 1 ? "" : "s"}`;
  return installation.fleet_patch?.name ? `${targets}${progress ? ` · ${progress}` : ""}` : `No fleet patch set`;
}
function patchPushReason(d) {
  const reasons = [];
  if (!d.online) reasons.push("offline");
  if (d.virtual) reasons.push("simulated");
  if (d.revoking_assignment || !Object.values(installation.seats || {}).some((seat) => seat.bound === d.uid))
    reasons.push("unassigned");
  return reasons.join(" · ");
}
function contextualExecutionPatch() {
  const editor = installation.editor || {},
    sim = installation.simulation || {};
  if (editor.active && editor.patch) return editor.patch;
  if (activeTab === "patches" && editorPatchChoice) return editorPatchChoice;
  return sim.patch || installation.fleet_patch?.name || editorPatchChoice || null;
}

function setExecutionTarget(target) {
  if (target === "edit" && performanceActive()) return;
  const mode = installation.supervisor?.mode || "off";
  if (target === "off") {
    if (mode === "simulate") {
      if (!confirm("Stop Simulation and return audio control to the Live fleet?")) return;
      ws.send("set_simulation", { active: false, confirmed: true });
    } else if (mode === "edit") {
      if (!confirm("Stop Patch edit and return audio control to the Live fleet?")) return;
      ws.send("set_edit", { active: false, confirmed: true });
    }
    return;
  }
  if (target === "simulate") {
    if (mode === "simulate") return;
    const patch = contextualExecutionPatch();
    const question =
      mode === "edit"
        ? `Stop Patch edit and hear "${patch || "the selected patch"}" in Simulation?`
        : `Run "${patch || "the selected patch"}" in Simulation? Live fleet devices will not be driven.`;
    if (!confirm(question)) return;
    ws.send("set_simulation", { active: true, patch, confirmed: true });
    return;
  }
  if (target === "edit") {
    if (mode === "edit") {
      activateTab("patches");
      focusSelectedPatch();
      return;
    }
    const patch = contextualExecutionPatch();
    if (mode === "simulate") {
      if (!confirm(`Stop Simulation and edit "${patch || "the selected patch"}"?`)) return;
      ws.send("set_simulation", { active: false, confirmed: true });
      if (patch) ws.send("set_edit", { active: true, patch, confirmed: true });
    } else {
      if (patch) {
        if (!confirm(`Open "${patch}" in Patch edit? Live fleet devices will not be driven.`)) return;
        ws.send("set_edit", { active: true, patch, confirmed: true });
      }
    }
    activateTab("patches");
    focusSelectedPatch();
  }
}

function renderHeader() {
  const ds = Object.values(installation.devices || {}),
    online = ds.filter((d) => d.online).length;
  $("#online-count").textContent = `${online} / ${ds.length} online`;
  $("#host-version").textContent = installation.host_version || "—";
  const mode = installation.supervisor?.mode || "off";
  const activePerformance = performanceActive();
  $("#performance-toggle").setAttribute("aria-checked", String(activePerformance));
  const physical = ds.filter((device) => !device.virtual);
  const pending = physical.filter(
    (device) => device.report?.performance !== activePerformance && (device.online || typeof device.report?.performance === "boolean"),
  ).length;
  const unknown = physical.some((device) => device.online && typeof device.report?.performance !== "boolean");
  const warning = $("#performance-warning");
  warning.hidden = pending === 0;
  warning.textContent = pending
    ? activePerformance && !unknown
      ? `⚠ ${pending} devices still in development`
      : `⚠ Performance · ${pending} / ${physical.length}`
    : "";
  document.querySelectorAll("[data-execution-target]").forEach((button) => {
    button.disabled = activePerformance && button.dataset.executionTarget === "edit";
    const active = button.dataset.executionTarget === mode;
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
  $("#mute-all").classList.toggle("active", muted);
  $("#mute-all").textContent = muted ? "MUTED — UNMUTE" : "MUTE ALL";
  // MUTE ALL lives in the Monitor dock's Globals panel, which is hidden while
  // the dock is collapsed; the header flag keeps a muted fleet always visible.
  const muteFlag = document.querySelector("[data-monitor-mute-flag]");
  if (muteFlag) muteFlag.hidden = !muted;
  if (document.activeElement !== $("#master")) $("#master").value = master;
  $("#master-out").value = Math.round(master * 100) + "%";
  const editorMaster = $("#editor-master");
  if (editorMaster && document.activeElement !== editorMaster) editorMaster.value = master;
  if (editorMaster?.previousElementSibling) editorMaster.previousElementSibling.value = Math.round(master * 100) + "%";
}
function select(uid) {
  selected = uid;
  const d = installation.devices[uid];
  selectedSeat = Object.values(installation.seats || {}).find((s) => s.bound === uid)?.id ?? d?.seat_id ?? null;
  if (!d.declared) ws.send("request_params", { uid });
  ws.send("request_patches", { uid });
  render();
}
let interacting = false;
document.addEventListener("pointerdown", (e) => {
  if (e.target.closest("#detail input, #detail select, #editor-panel input, #editor-panel select")) interacting = true;
});
document.addEventListener("pointerup", () => {
  interacting = false;
});

function actionLabel(verb) {
  return verb === "updatebopos" ? "Update bopOS" : verb.replaceAll("-", " ");
}
function fingerprintTail(value) {
  return typeof value === "string" && value ? `…${value.slice(-10)}` : null;
}
function copyIdentity(value, fallback = "unknown") {
  const tail = fingerprintTail(value);
  if (!tail) return `<code>${esc(fallback)}</code>`;
  return [
    `<button type="button" class="identity-copy" data-copy-identity="${
      esc(value)
      }" title="${
      esc(value)
      }" aria-label="Copy full identity ${
      esc(value)
      }"><code>${
      esc(tail)
      }</code>`,
    `<span class="copy-feedback" aria-live="polite"></span>`,
    `</button>`,
  ].join("");
}
function report(r) {
  if (!r) return '<p class="dim">No report loaded.</p>';
  const keys = [
    "hostname",
    "engine",
    "patch",
    "git_rev",
    "uptime",
    "has_i2c",
    "has_wifi",
    "audio_channels",
    "screen",
    "update_model",
    "contract_version",
    "device_enabled",
    "mute_all",
    "output_enabled",
  ];
  return `<dl>${keys.map((k) => `<dt>${k}</dt><dd>${k === "uptime" ? human(r[k]) : esc(r[k])}</dd>`).join("")}</dl>`;
}
function human(seconds) {
  seconds = Number(seconds) || 0;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m ${seconds % 60}s`;
}
function ago(epoch) {
  const s = Math.max(0, Math.round(Date.now() / 1000 - Number(epoch)));
  return s < 60 ? `${s}s ago` : s < 3600 ? `${Math.floor(s / 60)}m ago` : `${Math.floor(s / 3600)}h ago`;
}
$("#mute-all").onclick = () => {
  muted = !muted;
  installation.muted = muted;
  ws.send("mute_all", { value: muted ? 1 : 0 });
  render();
};
{
  const input = $("#master");
  let last = 0,
    timer;
  const send = () => {
    master = Number(input.value);
    ws.send("set_master", { value: master });
    renderHeader();
  };
  input.oninput = () => {
    const now = performance.now();
    if (now - last >= 33) {
      last = now;
      send();
    } else {
      clearTimeout(timer);
      timer = setTimeout(send, 33 - (now - last));
    }
  };
  input.onchange = send;
  input.onpointerup = send;
}
document.querySelectorAll("[data-all]").forEach(
  (b) =>
    (b.onclick = () => {
      const verb = b.dataset.all;
      if (!confirm(`${actionLabel(verb)} all physical devices?`)) return;
      ws.send("action", { uid: "all", verb });
    }),
);
document
  .querySelectorAll("[data-execution-target]")
  .forEach((button) => (button.onclick = () => setExecutionTarget(button.dataset.executionTarget)));
