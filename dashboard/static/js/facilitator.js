// Seat-owned live controls. /facilitator remains the standalone entry; the
// Dashboard tab embeds the same surface.
if (new URLSearchParams(location.search).get("embedded") === "1") document.body.classList.add("embedded");
const ws = new BopSocket("/ws");
let installation = {devices: {}, seats: {}, groups: {}};
let cueLeadModified = false;
let muted = false;
let master = 1.0;
let presetNames = [];
let liveScopeView = "aggregate";
let renderedCueSignature = null;
const openCommandDevices = new Set();
const takeoverAnnouncements = new Map();
const automationAnchors = new Map();
let fadeAnimationFrame = null;
let lastReducedFadeUpdate = 0;
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

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

function valueForSeat(seat, declaration) {
  return seat.params?.[declaration.identity] ?? declaration.default ?? "";
}

function automationForSeat(seat, declaration) {
  if (!seat || declaration.type === "s") return null;
  const entry = installation.automation?.[String(seat.id)]?.[declaration.identity];
  return entry && ["fade", "loop", "lfo"].includes(entry.kind) ? entry : null;
}

function aggregateValue(members, declaration) {
  if (!members.length) return {value: declaration.default ?? "", mixed: false, automation: null, automationMixed: false};
  const values = members.map(seat => valueForSeat(seat, declaration));
  const automation = members.map(seat => automationForSeat(seat, declaration));
  const signature = entry => entry ? JSON.stringify(entry.args) : null;
  const firstSignature = signature(automation[0]);
  const automationMixed = automation.some(entry => signature(entry) !== firstSignature);
  return {value: values[0], mixed: values.some(value => !Object.is(value, values[0])),
          automation: automationMixed ? null : automation[0], automationMixed};
}

function automationPresentation(entry, mixed = false) {
  if (mixed) return {glyph: "∿̸", label: "mixed"};
  if (!entry) return null;
  if (entry.kind === "fade") return {glyph: "╱", label: "fade"};
  if (entry.kind === "loop") return {glyph: "⟳", label: "loop"};
  const shape = entry.shape || "unknown";
  const glyph = ["sine", "tri", "drift"].includes(shape) ? "∿" : "⌁";
  return {glyph, label: `${shape} LFO`};
}

function automationKey(seat, declaration) {
  return `${seat?.id ?? "none"}:${declaration.identity}`;
}

function refreshAutomationAnchors(state) {
  const declarations = new Map((state.live_controls?.declarations || []).map(item => [item.identity, item]));
  const now = Date.now();
  const present = new Set();
  for (const [seatId, entries] of Object.entries(state.automation || {})) {
    for (const [identity, entry] of Object.entries(entries || {})) {
      const declaration = declarations.get(identity);
      if (!declaration || declaration.type === "s") continue;
      let parsed;
      try { parsed = window.ParamSpec.parse(entry.args || [], declaration.type); }
      catch (_error) { continue; }
      const key = `${seatId}:${identity}`;
      const commandSignature = JSON.stringify(entry.args || []);
      const signature = JSON.stringify([entry.args, entry.sent_at]);
      const expected = window.ParamSpec.phaseAnchor(entry, parsed, now);
      const previous = automationAnchors.get(key);
      const predicted = previous ? previous.elapsedMs + now - previous.atMs : 0;
      const period = expected.periodMs;
      const rawError = period > 0 ? Math.abs(((expected.elapsedMs - predicted + period / 2) % period + period) % period - period / 2) : Math.abs(expected.elapsedMs - predicted);
      const meaningful = rawError > Math.max(40, period * .02);
      // Reapplying an identical synchronized LFO is idempotent node-side: it
      // remains on the leader's absolute-time phase. Preserve the live browser
      // anchor too, rather than restarting its CSS animation for a looping Show
      // step's new sent_at. Changed commands and free LFOs are new instances.
      const sameSynchronizedLfo = previous && parsed.mode === "lfo" && !parsed.free &&
        previous.commandSignature === commandSignature;
      if (!previous || (!sameSynchronizedLfo && (previous.signature !== signature || meaningful))) {
        automationAnchors.set(key, {...expected, atMs: now, signature, commandSignature});
      }
      present.add(key);
    }
  }
  for (const key of automationAnchors.keys()) if (!present.has(key)) automationAnchors.delete(key);
}

function automationModel(entry, declaration, seat, catchupValue) {
  if (!entry) return null;
  let parsed;
  try { parsed = window.ParamSpec.parse(entry.args || [], declaration.type); }
  catch (_error) { return null; }
  const anchor = automationAnchors.get(automationKey(seat, declaration)) ||
    {...window.ParamSpec.phaseAnchor(entry, parsed), atMs: Date.now()};
  const elapsedMs = Math.max(0, anchor.elapsedMs + Date.now() - anchor.atMs);
  const periodMs = window.ParamSpec.totalDuration(parsed);
  if (parsed.mode === "fade" && elapsedMs >= periodMs) return null;
  const model = {parsed, elapsedMs, periodMs, target: parsed.segments?.at(-1)?.value};
  if (parsed.mode === "lfo") {
    model.minimum = window.ParamSpec.position(parsed.min, declaration);
    model.maximum = window.ParamSpec.position(parsed.max, declaration);
    model.marker = !["sh", "drift"].includes(parsed.shape);
  } else if (parsed.mode === "loop") {
    model.marker = true;
    const samples = [];
    const total = Math.max(1, periodMs);
    let start = Number(catchupValue);
    if (!Number.isFinite(start)) start = Number(declaration.default ?? parsed.segments[0].value);
    let offset = 0;
    samples.push(`${window.ParamSpec.position(start, declaration).toFixed(5)} 0%`);
    for (const segment of parsed.segments) {
      const duration = segment.duration.ms;
      const steps = Math.max(1, Math.min(12, Math.ceil(duration / 80)));
      for (let index = 1; index <= steps; index += 1) {
        const fraction = index / steps;
        // saw wraps at phase 1 (periodic); a one-shot ramp must end at 1.
        const bent = fraction >= 1 ? 1 : window.ParamSpec.shapeFraction("saw", fraction, parsed.curve);
        const value = start + (segment.value - start) * bent;
        const time = (offset + duration * fraction) / total * 100;
        samples.push(`${window.ParamSpec.position(value, declaration).toFixed(5)} ${time.toFixed(3)}%`);
      }
      offset += duration;
      start = segment.value;
    }
    samples.push(`${window.ParamSpec.position(catchupValue, declaration).toFixed(5)} 100%`);
    model.loopEasing = `linear(${samples.join(",")})`;
  }
  return model;
}

function scopeAttrs(scope, id, declaration) {
  return `data-live-param data-live-scope="${scope}"${id == null ? "" : ` data-live-id="${esc(id)}"`} data-param-path="${esc(declaration.identity)}"`;
}

function paramControl(scope, id, members, declaration, disabled) {
  const state = scope === "seat"
    ? {value: valueForSeat(members[0], declaration), mixed: false,
       automation: automationForSeat(members[0], declaration), automationMixed: false}
    : aggregateValue(members, declaration);
  const mixed = state.mixed || state.automationMixed;
  const value = state.value;
  const sourceSeat = members[0];
  const model = state.automationMixed ? null : automationModel(state.automation, declaration, sourceSeat, value);
  const automation = automationPresentation(model ? state.automation : null, state.automationMixed);
  const attrs = scopeAttrs(scope, id, declaration);
  const valueLabel = state.mixed ? `${declaration.name}, mixed values` : declaration.name;
  const label = automation ? `${valueLabel}, automated, ${automation.label}` : valueLabel;
  const common = `${attrs} data-param-name="${esc(declaration.name)}" aria-label="${esc(label)}" ${automation ? 'data-automated="true"' : ""} ${disabled ? "disabled" : ""}`;
  const mixedText = state.automationMixed ? '<span class="live-param-auto-mixed">auto·mixed</span>' : "";
  let input;
  if (declaration.type === "s") {
    input = `<input ${common} type="text" value="${mixed ? "" : esc(value)}" ${mixed ? 'placeholder="mixed" data-mixed="true"' : ""}>`;
  } else if (declaration.type === "i" && Number(declaration.min) === 0 && Number(declaration.max) === 1) {
    input = `<input ${common} type="checkbox" ${!mixed && Number(value) ? "checked" : ""} ${mixed ? 'data-mixed="true"' : ""}>`;
  } else {
    const kind = model?.parsed.mode === "lfo" ? model.parsed.shape : model?.parsed.mode;
    const display = state.automationMixed ? "auto·mixed" : state.mixed ? "mixed"
      : model?.parsed.mode === "fade" ? `→ ${model.target}`
      : model ? `${value} · ${kind}` : value;
    const rangeValue = mixed ? (declaration.default ?? declaration.min ?? 0) : value;
    let motion = "";
    if (model) {
      const shape = model.parsed.mode === "lfo" ? model.parsed.shape : model.parsed.mode;
      const styles = [`--auto-period:${model.periodMs}ms`, `--auto-elapsed:${model.elapsedMs}ms`];
      if (model.minimum != null) {
        const span = model.maximum - model.minimum;
        styles.push(`--auto-min-pos:${model.minimum * 100}%`, `--auto-max-pos:${model.maximum * 100}%`);
        for (const fraction of [.03806, .14645, .30866, .5, .69134, .85355, .96194]) {
          // slice(2): "0.03806" -> "03806" must match var(--auto-p03806);
          // a leading dot would make the custom-property name invalid CSS.
          styles.push(`--auto-p${String(fraction).slice(2)}:${(model.minimum + span * fraction) * 100}%`);
        }
      }
      if (model.loopEasing) styles.push(`--auto-loop-easing:${model.loopEasing}`);
      const marker = model.marker ? `<span class="live-param-marker auto-shape-${esc(shape)}${model.parsed.free ? " free" : ""}" style="${esc(styles.join(";"))}" aria-hidden="true"></span>` : "";
      motion = marker;
    }
    const fadeAttrs = model?.parsed.mode === "fade"
      ? `data-fade-anchor="${esc(Date.now() - model.elapsedMs)}" data-fade-duration="${esc(model.periodMs)}" data-fade-from="${esc(model.parsed.from ?? state.automation?.from ?? value)}" data-fade-curve="${esc(model.parsed.curve ?? 0)}" data-fade-segments="${esc(JSON.stringify(model.parsed.segments.map(segment => ({value: segment.value, ms: segment.duration.ms}))))}"`
      : "";
    // A plain numeric readout (not mixed/automated) doubles as a click-to-type
    // precision field (40-precision-param-input); mixed/automation states keep a
    // static readout so takeover semantics are unchanged.
    const preciseReadout = !state.automationMixed && !state.mixed && !model;
    input = `<output${preciseReadout ? ' data-precise="true"' : ""}>${esc(display)}</output><span class="live-param-range-wrap">${motion}<input ${common} type="range" min="${esc(declaration.min ?? 0)}" max="${esc(declaration.max ?? 1)}" step="${declaration.type === "i" ? 1 : 0.01}" value="${esc(rangeValue)}" ${mixed ? 'data-mixed="true"' : ""} ${fadeAttrs}></span>`;
  }
  const glyph = automation ? `<span class="live-param-glyph" aria-hidden="true">${automation.glyph}</span>` : "";
  const online = scope !== "seat" || (!!deviceForSeat(sourceSeat)?.online && Number(deviceForSeat(sourceSeat)?.engine_alive) !== 0);
  const deviceOutputDisabled = scope === "seat" && !!(deviceForSeat(sourceSeat)?.device_enabled === false || deviceForSeat(sourceSeat)?.output_enabled === false);
  return `<label class="live-param${mixed ? " mixed" : ""}${automation ? " automated" : ""}${!online ? " automation-offline" : ""}${deviceOutputDisabled ? " automation-muted" : ""}" data-param-path="${esc(declaration.identity)}"><span class="live-param-name">${esc(declaration.name)}${glyph}</span>${declaration.type === "i" && Number(declaration.min) === 0 && Number(declaration.max) === 1 ? mixedText : ""}${input}</label>`;
}

function paramTree(scope, id, members, declarations, disabled) {
  const roots = {branches: new Map(), leaves: []};
  for (const declaration of declarations) {
    let node = roots;
    for (const segment of declaration.path) {
      if (!node.branches.has(segment)) node.branches.set(segment, {branches: new Map(), leaves: []});
      node = node.branches.get(segment);
    }
    node.leaves.push(declaration);
  }
  const renderNode = (node, trail = []) => {
    const leaves = node.leaves.map(declaration => paramControl(scope, id, members, declaration, disabled)).join("");
    const branches = [...node.branches.entries()].map(([name, child]) => {
      const path = [...trail, name];
      return `<section class="live-param-branch" data-param-branch="${esc(path.join("/"))}"><h3>${esc(name)}</h3>${renderNode(child, path)}</section>`;
    }).join("");
    return leaves + branches;
  };
  return renderNode(roots);
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
  const controls = declarations.length ? `<div class="promoted-controls">${paramTree(scope, id, members, declarations, empty)}</div>` : "";
  const cardKey = `${scope}:${id ?? "all"}`;
  return `<article class="live-card ${scope}-card${scope === "group" && empty ? " empty-group" : ""}${scope === "seat" && !live ? " offline" : ""}" data-live-scope="${scope}"${id == null ? "" : ` data-live-id="${id}"`}>
    <div class="live-card-head">${scope === "seat" ? `<i class="dot ${live ? "ok" : ""}" aria-hidden="true"></i>` : ""}<span class="name"><strong>${esc(name)}</strong><small>${esc(meta)}</small></span>${scope === "all" || scope === "seat" ? replayButton(scope, id, !schemaAvailable) : ""}</div>
    ${controls}${scope === "seat" ? deviceCommands(device) : ""}<output class="live-param-status visually-hidden" aria-live="polite">${esc(takeoverAnnouncements.get(cardKey) || "")}</output>
  </article>`;
}

ws.on("connection", connected => { $("#ws-status").textContent = connected ? "" : "reconnecting…"; $("#ws-status").className = connected ? "online" : "offline"; });
ws.on("state", data => {
  installation = data; muted = !!data.muted; master = Number(data.master ?? 1);
  refreshAutomationAnchors(data);
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
  if (event.target.matches('input[type="range"], input[type="checkbox"][data-automated="true"]')) interacting = true;
});
document.addEventListener("pointerup", () => {
  if (!interacting) return;
  // Checkbox change/click follows pointerup; keep the render guard through that
  // event so the automated input survives long enough to send its plain value.
  setTimeout(() => { interacting = false; render(); }, 0);
});

function render() {
  $("#venue-name").textContent = installation.name || "bopOS";
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
  const cards = liveScopeView === "seats"
    ? allSeats.map(seat => liveCard("seat", seat, [seat], declarations, declarations.length > 0))
    : [liveCard("all", {}, allSeats, declarations, declarations.length > 0 && allSeats.length > 0),
       ...groups().map(group => liveCard("group", group, groupSeats(group.id), declarations, declarations.length > 0))];
  $("#cards").dataset.liveView = liveScopeView;
  $("#cards").setAttribute("aria-labelledby", liveScopeView === "seats" ? "live-scope-seats" : "live-scope-aggregate");
  $("#cards").innerHTML = cards.join("") || '<p class="empty">No Seats</p>';
  bindCards();
}

function activateLiveScope(view, moveFocus = false) {
  liveScopeView = view === "seats" ? "seats" : "aggregate";
  document.querySelectorAll("[data-live-scope-view]").forEach(button => {
    const active = button.dataset.liveScopeView === liveScopeView;
    button.setAttribute("aria-selected", active ? "true" : "false");
    button.tabIndex = active ? 0 : -1;
    if (active && moveFocus) button.focus();
  });
  renderCards();
  $("#cards").scrollTop = 0;
}

document.querySelectorAll("[data-live-scope-view]").forEach(button => {
  button.onclick = () => activateLiveScope(button.dataset.liveScopeView);
  button.onkeydown = event => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "ArrowRight" || event.key === "End" ? "seats" : "aggregate";
    activateLiveScope(next, true);
  };
});

function updateLocalParams(scope, id, identity, value) {
  const members = scope === "all" ? seats() : scope === "group" ? groupSeats(id) : seats().filter(seat => Number(seat.id) === Number(id));
  for (const seat of members) {
    seat.params ||= {};
    seat.params[identity] = value;
  }
}

function fadeValueAt(input, elapsedMs) {
  const segments = JSON.parse(input.dataset.fadeSegments || "[]");
  const curve = Number(input.dataset.fadeCurve);
  let value = Number(input.dataset.fadeFrom);
  let offset = 0;
  for (const segment of segments) {
    const duration = Number(segment.ms);
    const target = Number(segment.value);
    if (elapsedMs >= offset + duration) {
      value = target;
      offset += duration;
      continue;
    }
    const fraction = duration > 0 ? Math.max(0, (elapsedMs - offset) / duration) : 1;
    const bent = fraction >= 1 ? 1 : window.ParamSpec.shapeFraction("saw", fraction, curve);
    return value + (target - value) * bent;
  }
  return value;
}

function finishFade(input, value) {
  input.value = value;
  const control = input.closest(".live-param");
  const output = control?.querySelector("output");
  if (output) output.value = input.value;
  control?.classList.remove("automated");
  control?.querySelector(".live-param-glyph")?.remove();
  control?.querySelector(".live-param-marker")?.remove();
  input.removeAttribute("data-automated");
  input.setAttribute("aria-label", input.dataset.paramName || "parameter");
  for (const name of ["data-fade-anchor", "data-fade-duration", "data-fade-from", "data-fade-curve", "data-fade-segments"]) input.removeAttribute(name);
}

function animateFades() {
  fadeAnimationFrame = null;
  const inputs = [...document.querySelectorAll('[data-fade-anchor][data-automated="true"]')];
  if (!inputs.length) return;
  const now = Date.now();
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const reducedUpdateDue = now - lastReducedFadeUpdate >= 1000;
  let updated = false;
  for (const input of inputs) {
    const control = input.closest(".live-param");
    if (control?.classList.contains("taking-over") || input.matches(":active")) continue;
    const elapsed = Math.max(0, now - Number(input.dataset.fadeAnchor));
    const duration = Number(input.dataset.fadeDuration);
    const complete = elapsed >= duration;
    if (reducedMotion && !reducedUpdateDue && !complete) continue;
    const value = fadeValueAt(input, Math.min(elapsed, duration));
    if (complete) finishFade(input, value);
    else {
      input.value = value;
      const output = control?.querySelector("output");
      if (output) output.value = input.value;
    }
    updated = true;
  }
  if (reducedMotion && updated) lastReducedFadeUpdate = now;
  if (document.querySelector('[data-fade-anchor][data-automated="true"]')) fadeAnimationFrame = requestAnimationFrame(animateFades);
}

function startFadeAnimator() {
  if (fadeAnimationFrame == null && document.querySelector('[data-fade-anchor][data-automated="true"]')) {
    fadeAnimationFrame = requestAnimationFrame(animateFades);
  }
}

function bindCards() {
  document.querySelectorAll("[data-live-param]").forEach(input => {
    if (input.type === "checkbox" && input.dataset.mixed === "true") input.indeterminate = true;
    let last = 0, timer = null, takingOver = false, takeoverSent = false;
    const beginTakeover = () => {
      if (input.dataset.automated !== "true") return;
      takingOver = true;
      input.closest(".live-param")?.classList.add("taking-over");
    };
    const announceTakeover = value => {
      if (!takingOver) return;
      const card = input.closest(".live-card");
      const cardId = card?.dataset.liveId ?? "all";
      const key = `${card?.dataset.liveScope}:${cardId}`;
      const message = `${input.dataset.paramName} automation stopped, set to ${value}`;
      takeoverAnnouncements.set(key, message);
      const status = card?.querySelector(".live-param-status");
      if (status) status.value = message;
      setTimeout(() => takeoverAnnouncements.delete(key), 2000);
    };
    const send = (override) => {
      if (takingOver && takeoverSent) return;
      input.indeterminate = false;
      input.dataset.mixed = "false";
      input.closest(".live-param")?.classList.remove("mixed");
      // `override` carries the exact typed value from the precision field, which
      // bypasses the range's coarse step so full precision reaches the wire.
      const value = override !== undefined ? override
        : input.type === "checkbox" ? (input.checked ? 1 : 0) : input.type === "range" ? Number(input.value) : input.value;
      const scope = input.dataset.liveScope;
      const id = input.dataset.liveId == null ? null : Number(input.dataset.liveId);
      const payload = {scope, name: input.dataset.paramPath, value};
      if (id != null) payload.id = id;
      ws.send("set_live_param", payload);
      updateLocalParams(scope, id, input.dataset.paramPath, value);
      if (takingOver) {
        takeoverSent = true;
        announceTakeover(value);
      }
    };
    input.onpointerdown = beginTakeover;
    if (input.type === "range") {
      input.oninput = () => {
        const output = input.closest(".live-param")?.querySelector("output");
        if (output?.tagName === "OUTPUT") output.value = input.value;
        const now = performance.now();
        if (takingOver) return;
        if (now - last >= 33) { last = now; send(); }
        else { clearTimeout(timer); timer = setTimeout(send, 33 - (now - last)); }
      };
      input.onchange = send;
      input.onpointerup = send;
      const output = input.closest(".live-param")?.querySelector('output[data-precise="true"]');
      if (output) window.PrecisionField.attach(output, {
        min: input.min === "" ? null : Number(input.min),
        max: input.max === "" ? null : Number(input.max),
        integer: input.step === "1",
        value: Number(input.value),
        label: input.dataset.paramName,
        disabled: input.disabled,
      }, value => { input.value = value; send(value); },
         editing => { interacting = editing; if (!editing) render(); });
    } else input.onchange = send;
  });
  startFadeAnimator();
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

function renderPresets() {
  $("#preset-section").hidden = document.body.classList.contains("embedded") || presetNames.length === 0;
  $("#presets").innerHTML = presetNames.map(name => `<button class="chip" data-preset="${esc(name)}">${esc(name)}</button>`).join("");
  document.querySelectorAll("[data-preset]").forEach(button => button.onclick = () => ws.send("load_preset", {name: button.dataset.preset}));
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
