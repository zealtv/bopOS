(function () {
  const root = document.querySelector("#show-root");
  if (!root || typeof ws === "undefined") return;

  let shows = {names: [], current: null};
  let show = {schema: 1, name: "", items: []};
  let playback = {steps: {}};
  let playbackAt = performance.now();
  let focus = {kind: null, uid: null};
  let countdownTimer = null;
  let showError = "";
  let pendingMessageAdd = null;
  let pendingItemAdd = null;
  let targetDisclosure = {uid: null, open: false};
  let scrollFocusedRow = false;
  let clipboard = null;
  let showRowsHeight = 480;
  let showRowsScrollTop = 0;
  let rowsResizeDrag = null;
  let showDrag = null;
  let suppressDragClick = false;
  let renderPending = false;
  let relevantStateSignature = null;

  const THEN_ACTIONS = [
    ["stop", "Stop"],
    ["play_again", "Play again"],
    ["next_step", "Next step"],
    ["previous_step", "Previous step"],
    ["any_in_section", "Any in section"],
    ["other_in_section", "Other in section"],
    ["goto", "Go to..."],
    ["next_section", "Next section"],
    ["previous_section", "Previous section"],
  ];

  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, c => (
    {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]
  ));

  function stepByUid(uid) {
    return (show.items || []).find(item => item.kind === "step" && item.uid === uid) || null;
  }

  function messageByUid(uid) {
    for (const item of show.items || []) {
      if (item.kind !== "step") continue;
      const message = (item.messages || []).find(candidate => candidate.uid === uid);
      if (message) return {step: item, message};
    }
    return {step: null, message: null};
  }

  function focused(kind, uid) {
    return focus.kind === kind && focus.uid === uid;
  }

  function setFocus(kind, uid) {
    if (kind !== "message" || targetDisclosure.uid !== uid) {
      targetDisclosure = {uid: null, open: false};
    }
    focus = {kind, uid};
    render();
  }

  function stepLabel(step) {
    const alias = step?.alias;
    return alias && alias.trim() ? alias.trim() : "Untitled step";
  }

  function messageLabel(message) {
    const alias = message?.alias;
    if (alias && alias.trim()) return alias.trim();
    const address = String(message?.address || "");
    if (address === "/cue") {
      const cue = message.args?.[0]?.value;
      return cue ? `/cue ${cue}` : "/cue";
    }
    const parts = address.split("/").filter(Boolean);
    return parts.length ? parts[parts.length - 1] : (address || "message");
  }

  function terseDuration(seconds) {
    const parts = secondsParts(seconds);
    if (!parts.h && !parts.m) return `${parts.s}s`;
    let out = parts.h ? `${parts.h}h` : "";
    if (parts.m || (parts.h && parts.s)) out += `${parts.m}m`;
    if (parts.s) out += `${parts.s}`;
    return out;
  }

  const PILL_PALETTE_SIZE = 8;

  function pillColourClass(message) {
    const alias = (message?.alias || "").trim();
    if (!alias) return "";
    let hash = 2166136261;
    for (let index = 0; index < alias.length; index++) {
      hash ^= alias.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return ` show-pill-${(hash >>> 0) % PILL_PALETTE_SIZE}`;
  }

  function allSteps() {
    return (show.items || []).filter(item => item.kind === "step");
  }

  function stepOptions(selectedUid) {
    return allSteps().map(step => {
      const label = `${stepLabel(step)} · ${step.uid}`;
      return `<option value="${escapeHtml(step.uid)}" ${step.uid === selectedUid ? "selected" : ""}>${escapeHtml(label)}</option>`;
    }).join("");
  }

  function secondsParts(value) {
    const total = Math.max(0, Math.round(Number(value) || 0));
    return {
      h: Math.floor(total / 3600),
      m: Math.floor((total % 3600) / 60),
      s: total % 60,
    };
  }

  function currentInstallation() {
    try { return typeof installation === "object" && installation ? installation : {}; }
    catch (_error) { return {}; }
  }

  function currentDistribution() {
    try { return typeof distribution === "object" && distribution ? distribution : {}; }
    catch (_error) { return {}; }
  }

  function paramIdentity(declaration) {
    if (typeof declaration?.identity === "string" && declaration.identity) return declaration.identity;
    const path = Array.isArray(declaration?.path) ? declaration.path.filter(Boolean).join("/") : "";
    const name = declaration?.name || "";
    return [path, name].filter(Boolean).join("/") || name;
  }

  function manifestFromStagedPatch() {
    const state = currentInstallation();
    const patch = state.live_controls?.patch || state.live_cues?.patch || state.params_patch || state.fleet_patch?.name;
    const catalog = currentDistribution();
    const item = (catalog.patches || []).find(candidate => candidate.name === patch);
    const manifest = item?.manifest && typeof item.manifest === "object" ? item.manifest : null;
    const params = Array.isArray(manifest?.params) ? manifest.params
      : Array.isArray(state.live_controls?.declarations) ? state.live_controls.declarations : [];
    const cues = Array.isArray(manifest?.cues) ? manifest.cues
      : Array.isArray(state.live_cues?.cues) ? state.live_cues.cues : [];
    return {
      patch,
      params: params.map(param => ({...param, identity: paramIdentity(param)})).filter(param => param.identity),
      cues: cues.filter(cue => cue && typeof cue.id === "string" && cue.id),
    };
  }

  function seats() {
    const state = currentInstallation();
    return Object.values(state.seats || {}).sort((a, b) => Number(a.id) - Number(b.id));
  }

  function groups() {
    const state = currentInstallation();
    return Object.values(state.groups || {}).sort((a, b) => Number(a.id) - Number(b.id));
  }

  function showRelevantStateSignature() {
    const state = currentInstallation();
    return JSON.stringify({
      cue_lead_ms: state.cue_lead_ms ?? 500,
      manifest: manifestFromStagedPatch(),
      seats: seats().map(seat => ({id: seat.id, name: seat.name, groups: seat.groups || []})),
      groups: groups().map(group => ({id: group.id, name: group.name})),
    });
  }

  function targetList(message) {
    const target = message?.target;
    if (Array.isArray(target)) return target.length ? target : ["all"];
    return typeof target === "string" && target ? [target] : ["all"];
  }

  function terseTargets(message) {
    const list = targetList(message);
    return list.includes("all") ? "all" : list.join("+");
  }

  function toggledTargets(message, selector) {
    if (selector === "all") return ["all"];
    const current = targetList(message).filter(entry => entry !== "all");
    const next = current.includes(selector)
      ? current.filter(entry => entry !== selector)
      : [...current, selector];
    return next.length ? next : ["all"];
  }

  function renderTargetPicker(message, disabled) {
    const selected = targetList(message);
    const isAll = selected.includes("all");
    const off = disabled ? " disabled" : "";
    const groupChips = groups().map((group, index) => {
      const value = `g${group.id}`;
      const on = !isAll && selected.includes(value);
      return `<button type="button" class="show-target-chip show-target-group slot-${index % 4}${on ? " on" : ""}" data-target-toggle="${escapeHtml(value)}" aria-pressed="${on}"${off}><span class="show-target-swatch" aria-hidden="true"></span>${escapeHtml(group.name || `Group ${group.id}`)}<small>g${escapeHtml(group.id)}</small></button>`;
    }).join("");
    const seatChips = seats().map(seat => {
      const value = String(seat.id);
      const on = !isAll && selected.includes(value);
      return `<button type="button" class="show-target-chip show-target-seat${on ? " on" : ""}" data-target-toggle="${escapeHtml(value)}" aria-pressed="${on}" title="${escapeHtml(seat.name || `Seat ${seat.id}`)}"${off}>${escapeHtml(value)}</button>`;
    }).join("");
    const summary = isAll
      ? '<span class="dim">every Seat</span>'
      : selected.map(entry => `<button type="button" class="show-target-chip show-target-selected" data-target-remove="${escapeHtml(entry)}" title="Remove ${escapeHtml(entry)}"${off}>${escapeHtml(entry)}<span aria-hidden="true"> ×</span></button>`).join("");
    const open = targetDisclosure.uid === message.uid && targetDisclosure.open ? " open" : "";
    return `<details class="show-inspector-section show-target-picker${disabled ? " show-disabled-field" : ""}" data-target-disclosure="${escapeHtml(message.uid)}"${open}>
      <summary><span>Target</span><output class="show-target-terse">${escapeHtml(terseTargets(message))}</output></summary>
      <div class="show-target-body">
        <div class="show-target-summary">${summary}</div>
        <div class="show-target-chips">
          <button type="button" class="show-target-chip show-target-all${isAll ? " on" : ""}" data-target-toggle="all" aria-pressed="${isAll}"${off}>All</button>
          ${groupChips}
        </div>
        ${seatChips ? `<div class="show-target-chips show-target-roster">${seatChips}</div>` : ""}
      </div>
    </details>`;
  }

  function inferMessageMode(message) {
    if (message.address === "/cue") return "cue";
    if (message.address === "/pt") return "point";
    if (message.address?.startsWith("/p/")) return "param";
    return "raw";
  }

  function argValue(arg) {
    return arg?.value ?? "";
  }

  function numberAttr(value, fallback = "") {
    return Number.isFinite(Number(value)) ? Number(value) : fallback;
  }

  function typedArg(kind, value) {
    if (kind === "s") return {type: "s", value: String(value ?? "")};
    if (kind === "i") return {type: "i", value: Math.trunc(Number(value) || 0)};
    const number = Number(value) || 0;
    return {type: "f", value: Number(number.toPrecision(6))};
  }

  const parseParamArgs = window.ParamSpec.parse;

  function wirePreview(message) {
    const args = (message.args || []).map(arg => `${arg.type}:${String(arg.value)}`).join(", ");
    return `${message.address || "/"} ${args ? `[${args}]` : "[]"} -> ${terseTargets(message)}`;
  }

  function friendlyShowError() {
    if (showError === "duration_s == 0 requires a finite play_count.") {
      return "Duration 0 needs a finite play count.";
    }
    return showError;
  }

  function playbackState(uid) {
    const state = playback?.steps?.[uid];
    return state || {state: "stopped", iteration: 0, remaining_s: null};
  }

  function remainingSeconds(uid) {
    const state = playbackState(uid);
    if (state.state !== "playing" && state.state !== "paused") return null;
    const base = Number(state.remaining_s);
    if (!Number.isFinite(base)) return null;
    if (state.state === "paused") return Math.max(0, base);
    return Math.max(0, base - ((performance.now() - playbackAt) / 1000));
  }

  function iconButton(action, uid, glyph, label, stateClass = "", disabled = false) {
    return `<button class="show-icon-button${stateClass}" data-show-action="${action}" data-show-uid="${uid}" title="${escapeHtml(label)}" aria-label="${escapeHtml(label)}" ${disabled ? "disabled" : ""}><span class="show-glyph show-glyph-${glyph}" aria-hidden="true"></span></button>`;
  }

  function stepTransport(step) {
    const state = playbackState(step.uid).state;
    const uid = escapeHtml(step.uid);
    const name = stepLabel(step);
    if (state === "playing") {
      return iconButton("step_stop", uid, "stop", `Stop ${name}`, " show-state-playing")
        + iconButton("step_pause", uid, "pause", `Pause ${name}`)
        + iconButton("step_trigger_next", uid, "next", `Trigger next action for ${name}`);
    }
    if (state === "paused") {
      return iconButton("step_resume", uid, "play", `Resume ${name}`, " show-state-paused")
        + iconButton("step_stop", uid, "stop", `Stop ${name}`);
    }
    return iconButton("step_start", uid, "play", `Play ${name}`, " show-state-stopped");
  }

  function messagePills(step) {
    const messages = step.messages || [];
    if (!messages.length) return '<span class="show-no-messages">No messages</span>';
    return messages.map(message => {
      const selected = focused("message", message.uid) ? " focused" : "";
      const title = `${message.address || ""} -> ${terseTargets(message)}`;
      return `<button class="show-message-pill${pillColourClass(message)}${selected}" data-show-message-focus="${escapeHtml(message.uid)}" data-show-step="${escapeHtml(step.uid)}" data-drag-message="${escapeHtml(message.uid)}" title="${escapeHtml(title)}"><span class="show-pill-drag" aria-hidden="true">⋮</span>${escapeHtml(messageLabel(message))}</button>`;
    }).join("");
  }

  function dividerRow(item, index) {
    const selected = focused("divider", item.uid) ? " focused" : "";
    return `<div class="show-divider-row${selected}" data-show-divider-row="${escapeHtml(item.uid)}" data-show-index="${index}" role="button" tabindex="0" aria-label="Section divider">
      <button type="button" class="show-drag-handle show-divider-drag" data-drag-item="${escapeHtml(item.uid)}" aria-label="Drag section divider">⋮⋮</button>
    </div>`;
  }

  function stepRow(step, index) {
    const remaining = remainingSeconds(step.uid);
    const stateName = playbackState(step.uid).state || "stopped";
    const selected = focused("step", step.uid) ? " focused" : "";
    const playing = stateName === "playing" || stateName === "paused" ? " active" : "";
    const armed = playback?.armed === step.uid ? " show-step-armed" : "";
    const duration = Number(step.duration_s);
    const fraction = remaining != null && duration > 0
      ? Math.min(1, Math.max(0, 1 - (remaining / duration))) : null;
    const progressDuration = stateName === "playing" && remaining > 0
      ? `;--show-progress-duration:${remaining}s` : "";
    const progress = fraction == null ? ""
      : `<div class="show-step-progress" style="width:${fraction * 100}%${progressDuration}"></div>`;
    const time = remaining == null
      ? `<span class="show-step-duration">${terseDuration(step.duration_s)}</span>`
      : `<span class="show-remaining" title="${stateName === "paused" ? "paused" : "remaining"}">${terseDuration(remaining)}</span>`;
    const gotoMissing = playbackState(step.uid).goto_missing
      ? '<span class="show-goto-missing" title="goto target no longer exists; stopped">goto?</span>' : "";
    return `<div class="show-step-row show-step-${escapeHtml(stateName)}${selected}${playing}${armed}" data-show-step-row="${escapeHtml(step.uid)}" data-show-index="${index}" role="row" tabindex="0">
      ${progress}
      <button type="button" class="show-drag-handle" data-drag-item="${escapeHtml(step.uid)}" aria-label="Drag ${escapeHtml(stepLabel(step))}">⋮⋮</button>
      <div class="show-step-transport">${stepTransport(step)}</div>
      <strong class="show-step-alias" title="${escapeHtml(stepLabel(step))}">${escapeHtml(stepLabel(step))}</strong>
      <div class="show-message-pills">${messagePills(step)}</div>
      <div class="show-step-time">${gotoMissing}${time}</div>
    </div>`;
  }

  function renderEmptyState() {
    const names = shows.names || [];
    const options = names.map(name => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("");
    root.innerHTML = `<div class="show-empty">
      <div>
        <p class="eyebrow">Show control</p>
        <h2>Show</h2>
        <p class="dim">Create or load a show to start building performance steps.</p>
      </div>
      <form id="show-create-form" class="show-create-form">
        <label>new show <input id="show-create-name" type="text" autocomplete="off" placeholder="opening-set"></label>
        <button type="submit">Create show</button>
      </form>
      <div class="show-picker" ${names.length ? "" : "hidden"}>
        <label>saved shows <select id="show-load-select">${options}</select></label>
        <button id="show-load-button" type="button">Load show</button>
      </div>
    </div>`;
  }

  function renderTransport() {
    const activeEntry = Object.entries(playback?.steps || {})
      .find(([_uid, state]) => ["playing", "paused"].includes(state?.state));
    const activeUid = activeEntry?.[0] || null;
    const activeState = activeEntry?.[1]?.state || null;
    const activeStep = stepByUid(activeUid);
    const focusedUid = focus.kind === "step" ? focus.uid
      : focus.kind === "message" ? messageByUid(focus.uid).step?.uid : null;
    const startUid = focusedUid || allSteps()[0]?.uid || null;
    const playAction = activeState === "playing" ? "step_pause"
      : activeState === "paused" ? "step_resume" : "step_start";
    const playUid = activeUid || startUid;
    const playGlyph = activeState === "playing" ? "pause" : "play";
    const playLabel = activeState === "playing" ? `Pause ${stepLabel(activeStep)}`
      : activeState === "paused" ? `Resume ${stepLabel(activeStep)}`
      : `Play ${stepLabel(stepByUid(startUid))}`;
    const cueLead = currentInstallation().cue_lead_ms ?? 500;
    return `<div class="show-transport-strip">
      <div><p class="eyebrow">Show control</p><h2>${escapeHtml(show.name || shows.current || "Show")}</h2></div>
      <div class="show-manage">
        <select id="show-switch-select" aria-label="Saved shows">${(shows.names || []).map(name =>
          `<option value="${escapeHtml(name)}" ${name === shows.current ? "selected" : ""}>${escapeHtml(name)}</option>`).join("")}</select>
        <button id="show-switch-load" type="button">Load</button>
        <button id="show-manage-new" type="button">New</button>
        <button id="show-manage-rename" type="button">Rename</button>
        <button id="show-manage-delete" class="danger" type="button">Delete</button>
      </div>
      <div class="show-transport-actions">
        <label class="show-cue-lead">cue lead · ms <input id="show-cue-lead" type="number" min="100" max="10000" step="50" value="${escapeHtml(cueLead)}"></label>
        ${iconButton(playAction, escapeHtml(playUid || ""), playGlyph, playLabel, " show-global-transport", !playUid)}
        ${iconButton("step_stop", escapeHtml(activeUid || ""), "stop", activeStep ? `Stop ${stepLabel(activeStep)}` : "Stop active step", " show-global-transport", !activeUid)}
        ${iconButton("step_trigger_next", escapeHtml(activeUid || ""), "next", activeStep ? `Trigger next action for ${stepLabel(activeStep)}` : "Trigger next action", " show-global-transport", !activeUid)}
      </div>
    </div>`;
  }

  function renderLoadedShow() {
    const items = Array.isArray(show.items) ? show.items : [];
    const rows = items.map((item, index) => item.kind === "divider" ? dividerRow(item, index) : stepRow(item, index)).join("");
    root.innerHTML = `${renderTransport()}<div class="show-workspace">
      <div class="show-list-shell">
        <div class="show-rows-box" style="height:${showRowsHeight}px">
          <div class="show-rows" role="table" aria-label="Show steps">${rows || '<p class="empty">This show has no steps yet.</p>'}</div>
        </div>
        <div class="show-rows-resize" role="separator" aria-label="Resize Show step list" aria-orientation="horizontal" tabindex="0"></div>
        <div class="show-add-bar">
          <button type="button" data-item-add-end="step">+ Step</button>
          <button type="button" data-item-add-end="divider">+ Divider</button>
        </div>
      </div>
      <aside class="show-inspector-shell" aria-label="Show inspector">${renderInspector()}</aside>
    </div>`;
  }

  function renderInspector() {
    if (focus.kind === "step") {
      const step = stepByUid(focus.uid);
      if (step) return renderStepInspector(step);
    }
    if (focus.kind === "message") {
      const found = messageByUid(focus.uid);
      if (found.message) return renderMessageInspector(found.step, found.message);
    }
    if (focus.kind === "divider") {
      const divider = (show.items || []).find(item => item.kind === "divider" && item.uid === focus.uid);
      if (divider) return renderDividerInspector(divider);
    }
    return `<h3>Inspector</h3><p class="dim">Select a step or message.</p>`;
  }

  function renderArrange(item) {
    const uid = escapeHtml(item.uid);
    return `<section class="show-inspector-section">
      <div class="show-inspector-subhead"><h4>Arrange</h4></div>
      <div class="show-arrange-grid">
        <button type="button" data-item-add="step" data-item-uid="${uid}">Step below</button>
        <button type="button" data-item-add="divider" data-item-uid="${uid}">Divider below</button>
        <button type="button" class="danger" data-item-delete="${uid}">Delete ${item.kind}</button>
      </div>
    </section>`;
  }

  function renderDividerInspector(divider) {
    return `<h3>Divider inspector</h3>
      <div class="show-inspector-form" data-show-divider-editor="${escapeHtml(divider.uid)}">
        <p class="show-inspector-context">Section divider</p>
        ${renderArrange(divider)}
      </div>`;
  }

  function renderStepInspector(step) {
    const parts = secondsParts(step.duration_s);
    const loop = step.play_count == null;
    const actions = Array.isArray(step.then_actions) && step.then_actions.length
      ? step.then_actions : [{type: "stop"}];
    const modelValidation = Number(step.duration_s) === 0 && step.play_count == null
      ? "Duration 0 needs a finite play count." : "";
    const validation = modelValidation || friendlyShowError()
      ? `<p class="show-field-error">${escapeHtml(modelValidation || friendlyShowError())}</p>` : "";
    const actionRows = actions.map((action, index) => renderThenAction(action, index)).join("");
    return `<h3>Step inspector</h3>
      <div class="show-inspector-form" data-show-step-editor="${escapeHtml(step.uid)}">
        <label>alias <input id="show-step-alias" type="text" autocomplete="off" value="${escapeHtml(step.alias || "")}" placeholder="Untitled step"></label>
        <fieldset class="show-duration-fields"><legend>duration</legend>
          <label>h <input data-duration-part="h" type="number" min="0" step="1" value="${parts.h}"></label>
          <label>m <input data-duration-part="m" type="number" min="0" max="59" step="1" value="${parts.m}"></label>
          <label>s <input data-duration-part="s" type="number" min="0" max="59" step="1" value="${parts.s}"></label>
        </fieldset>
        ${validation}
        <div class="show-play-count-row">
          <label>play n times <input id="show-play-count" type="number" min="1" step="1" value="${loop ? "" : escapeHtml(step.play_count)}" ${loop ? "disabled" : ""}></label>
          <label class="show-check"><input id="show-play-forever" type="checkbox" ${loop ? "checked" : ""}> loop forever</label>
        </div>
        <section class="show-inspector-section">
          <div class="show-inspector-subhead"><h4>Then actions</h4><button type="button" data-add-then-action>Add row</button></div>
          <div class="show-then-list">${actionRows}</div>
        </section>
        <button type="button" id="show-add-message">Add message</button>
        ${renderArrange(step)}
        <output class="show-inspector-error" aria-live="polite">${escapeHtml(friendlyShowError())}</output>
      </div>`;
  }

  function renderThenAction(action, index) {
    const type = action?.type || "stop";
    const options = THEN_ACTIONS.map(([value, label]) =>
      `<option value="${value}" ${value === type ? "selected" : ""}>${escapeHtml(label)}</option>`).join("");
    const stale = type === "goto" && action.target_uid && !stepByUid(action.target_uid)
      ? `<option value="${escapeHtml(action.target_uid)}" selected>missing step · ${escapeHtml(action.target_uid)}</option>` : "";
    const goto = type === "goto"
      ? `<select data-then-goto="${index}" aria-label="goto target">${stale}${stepOptions(action.target_uid) || '<option value="">No steps</option>'}</select>` : "";
    return `<div class="show-then-row" data-then-index="${index}">
      <select data-then-type="${index}" aria-label="then action">${options}</select>
      ${goto}
      ${index > 0 ? `<button type="button" class="danger" data-remove-then="${index}">Remove</button>` : ""}
    </div>`;
  }

  function renderMessageInspector(step, message) {
    const mode = inferMessageMode(message);
    const targetDisabled = mode === "cue" || mode === "point";
    return `<h3>Message inspector</h3>
      <div class="show-inspector-form" data-show-message-editor="${escapeHtml(message.uid)}">
        <p class="show-inspector-context">${escapeHtml(stepLabel(step))}</p>
        <label>alias <input id="show-message-alias" type="text" autocomplete="off" value="${escapeHtml(message.alias || "")}" placeholder="${escapeHtml(messageLabel(message))}"></label>
        ${renderTargetPicker(message, targetDisabled)}
        <label>payload mode
          <select id="show-message-mode">
            <option value="param" ${mode === "param" ? "selected" : ""}>parameter</option>
            <option value="cue" ${mode === "cue" ? "selected" : ""}>cue</option>
            <option value="point" ${mode === "point" ? "selected" : ""}>point</option>
            <option value="raw" ${mode === "raw" ? "selected" : ""}>raw</option>
          </select>
        </label>
        ${renderPayloadBuilder(message, mode)}
        <label>wire form <output id="show-wire-preview">${escapeHtml(wirePreview(message))}</output></label>
        <output class="show-inspector-error" aria-live="polite">${escapeHtml(friendlyShowError())}</output>
      </div>`;
  }

  function renderPayloadBuilder(message, mode) {
    if (mode === "param") return renderParamBuilder(message);
    if (mode === "cue") return renderCueBuilder(message);
    if (mode === "point") return renderPointBuilder(message);
    return renderRawBuilder(message);
  }

  function renderParamBuilder(message) {
    const manifest = manifestFromStagedPatch();
    const identity = message.address?.startsWith("/p/") ? message.address.slice(3) : manifest.params[0]?.identity || "";
    const declaration = manifest.params.find(param => param.identity === identity) || manifest.params[0] || {type: "f", min: 0, max: 1, default: 0, name: "value", identity};
    const options = manifest.params.map(param => {
      const label = `${param.path?.length ? `${param.path.join("/")} / ` : ""}${param.name || param.identity}`;
      return `<option value="${escapeHtml(param.identity)}" ${param.identity === identity ? "selected" : ""}>${escapeHtml(label)}</option>`;
    }).join("");
    const numeric = declaration.type === "f" || declaration.type === "i";
    let parsed = null;
    if (numeric) {
      try { parsed = parseParamArgs(message.args || [], declaration.type); }
      catch (_error) { parsed = null; }
    }
    const rawFallback = numeric && !parsed;
    const mode = parsed?.mode || "value";
    const generator = numeric && !rawFallback ? `<label>generator
      <select id="show-param-generator">
        ${["value", "fade", "loop", "lfo", "stop"].map(kind => `<option value="${kind}" ${mode === kind ? "selected" : ""}>${kind}</option>`).join("")}
      </select>
    </label>` : "";
    const fields = rawFallback
      ? renderParamRawFallback(message)
      : renderParamGeneratorFields(declaration, parsed || {mode: "value", value: message.args?.[0]?.value ?? declaration.default ?? ""});
    const preview = !rawFallback && parsed ? renderParamPreview(parsed, declaration) : "";
    return `<section class="show-inspector-section" data-payload-builder="param">
      <label>parameter <select id="show-param-picker">${options || '<option value="">No staged params</option>'}</select></label>
      ${generator}
      ${fields}
      ${preview}
      <small class="dim">${escapeHtml(declaration.type || "f")}${declaration.min != null || declaration.max != null ? ` · ${escapeHtml(declaration.min ?? "…")} to ${escapeHtml(declaration.max ?? "…")}` : ""}</small>
    </section>`;
  }

  function renderParamPreview(parsed, declaration) {
    if (!["fade", "loop", "lfo"].includes(parsed.mode)) return "";
    if (parsed.mode === "lfo" && ["sh", "drift"].includes(parsed.shape)) {
      return '<p class="show-param-preview-random" data-param-preview-random>random — not previewable</p>';
    }
    const points = [];
    if (parsed.mode === "lfo") {
      const count = 64;
      for (let index = 0; index <= count; index += 1) {
        const time = index / count * 2;
        points.push([time, window.ParamSpec.shapeFraction(parsed.shape, time + parsed.phase, parsed.curve)]);
      }
    } else {
      const cycles = parsed.mode === "loop" ? 2 : 1;
      const duration = Math.max(1, window.ParamSpec.totalDuration(parsed));
      let time = 0;
      let start = Number(parsed.from ?? declaration.default ?? parsed.segments[0]?.value ?? 0);
      points.push([0, start]);
      for (let cycle = 0; cycle < cycles; cycle += 1) {
        for (const segment of parsed.segments) {
          const steps = Math.max(2, Math.min(16, Math.ceil(segment.duration.ms / 100)));
          for (let index = 1; index <= steps; index += 1) {
            const fraction = index / steps;
            const bent = window.ParamSpec.shapeFraction("saw", fraction, parsed.curve);
            points.push([(time + segment.duration.ms * fraction) / duration,
              start + (segment.value - start) * bent]);
          }
          time += segment.duration.ms;
          start = segment.value;
        }
        if (parsed.mode === "loop" && cycle + 1 < cycles) {
          start = Number(declaration.default ?? parsed.segments[0]?.value ?? 0);
          points.push([time / duration, start]);
        }
      }
    }
    if (!points.length) return "";
    const values = points.map(point => point[1]);
    let low = parsed.mode === "lfo" ? 0 : Number(declaration.min ?? Math.min(...values));
    let high = parsed.mode === "lfo" ? 1 : Number(declaration.max ?? Math.max(...values));
    if (!Number.isFinite(low)) low = Math.min(...values);
    if (!Number.isFinite(high)) high = Math.max(...values);
    if (high === low) high = low + 1;
    const maxTime = Math.max(...points.map(point => point[0]), 1);
    const path = points.map(([time, value], index) => {
      const x = 8 + time / maxTime * 224;
      const y = 64 - (value - low) / (high - low) * 56;
      return `${index ? "L" : "M"}${x.toFixed(2)} ${Math.min(64, Math.max(8, y)).toFixed(2)}`;
    }).join(" ");
    const label = parsed.mode === "lfo" ? `${parsed.shape} LFO preview` : `${parsed.mode} preview`;
    return `<figure class="show-param-preview" data-param-preview><figcaption>${escapeHtml(label)} · value / time</figcaption><svg viewBox="0 0 240 72" role="img" aria-label="${escapeHtml(label)}"><path class="show-param-preview-axis" d="M8 8V64H232"></path><path class="show-param-preview-line" d="${path}"></path></svg></figure>`;
  }

  function paramValueAttrs(declaration) {
    return `step="${declaration.type === "i" ? "1" : "any"}" ${declaration.min != null ? `min="${escapeHtml(declaration.min)}"` : ""} ${declaration.max != null ? `max="${escapeHtml(declaration.max)}"` : ""}`;
  }

  function renderParamGeneratorFields(declaration, parsed) {
    if (declaration.type === "s") {
      return `<label>value <input id="show-param-value" type="text" value="${escapeHtml(parsed.value ?? declaration.default ?? "")}"></label>`;
    }
    if (parsed.mode === "value") {
      return `<label>value <input id="show-param-value" type="number" ${paramValueAttrs(declaration)} value="${escapeHtml(parsed.value)}"></label>`;
    }
    if (parsed.mode === "stop") return '<p class="dim show-param-stop">Stops automation and holds its current output.</p>';
    if (parsed.mode === "lfo") {
      const shapes = ["sine", "tri", "saw", "square", "sh", "drift"];
      return `<div class="show-param-lfo">
        <label>shape <select data-param-lfo="shape">${shapes.map(shape => `<option value="${shape}" ${parsed.shape === shape ? "selected" : ""}>${shape}</option>`).join("")}</select></label>
        <label>min <input data-param-lfo="min" type="number" ${paramValueAttrs(declaration)} value="${escapeHtml(parsed.min)}"></label>
        <label>max <input data-param-lfo="max" type="number" ${paramValueAttrs(declaration)} value="${escapeHtml(parsed.max)}"></label>
        <label>period <span class="show-param-duration"><input data-param-lfo="period" type="number" min="0" step="any" value="${escapeHtml(parsed.period.amount)}"><select data-param-lfo="period-unit">${renderUnitOptions(parsed.period.unit)}</select></span></label>
        <label>phase <input data-param-lfo="phase" type="number" min="0" max="1" step="0.01" value="${escapeHtml(parsed.phase)}"></label>
        <label class="show-check">free <input data-param-lfo="free" type="checkbox" ${parsed.free ? "checked" : ""}></label>
        <label>curve <input data-param-lfo="curve" type="number" step="any" value="${escapeHtml(parsed.curve || "")}"></label>
      </div>`;
    }
    const from = parsed.mode === "fade" && parsed.segments.length === 1
      ? `<label>from · optional <input data-param-from type="number" ${paramValueAttrs(declaration)} value="${escapeHtml(parsed.from ?? "")}"></label>` : "";
    return `<div class="show-param-segments" data-param-segments>
      ${parsed.segments.map((segment, index) => renderParamSegment(segment, index, declaration, parsed.segments.length)).join("")}
    </div>
    <button type="button" data-add-param-segment>Add segment</button>
    ${from}
    <label>curve <input data-param-curve type="number" step="any" value="${escapeHtml(parsed.curve || "")}"></label>
    <p class="show-field-error show-param-loop-hint" ${parsed.mode === "loop" && parsed.segments.length < 2 ? "" : "hidden"}>loop needs at least two segments</p>`;
  }

  function renderUnitOptions(selected) {
    return ["ms", "s", "m", "h"].map(unit => `<option value="${unit}" ${unit === selected ? "selected" : ""}>${unit}</option>`).join("");
  }

  function renderParamSegment(segment, index, declaration, count) {
    return `<div class="show-param-segment" data-param-segment="${index}">
      <label>destination <input data-param-segment-value type="number" ${paramValueAttrs(declaration)} value="${escapeHtml(segment.value)}"></label>
      <label>duration <span class="show-param-duration"><input data-param-segment-duration type="number" min="0" step="any" value="${escapeHtml(segment.duration.amount)}"><select data-param-segment-unit>${renderUnitOptions(segment.duration.unit)}</select></span></label>
      <button type="button" class="danger" data-remove-param-segment aria-label="Remove segment" ${count <= 1 ? "disabled" : ""}>Remove</button>
    </div>`;
  }

  function renderParamRawFallback(message) {
    const args = (message.args || []).map((arg, index) => renderRawArg(arg, index)).join("");
    return `<div class="show-param-raw" data-param-raw-fallback>
      <p class="show-field-error">unrecognised automation form — raw arguments</p>
      <div class="show-inspector-subhead"><h4>Arguments</h4><button type="button" data-add-raw-arg>Add arg</button></div>
      <div class="show-raw-args">${args || '<p class="dim">No arguments.</p>'}</div>
    </div>`;
  }

  function renderCueBuilder(message) {
    const manifest = manifestFromStagedPatch();
    const cueId = message.address === "/cue" ? String(argValue(message.args?.[0]) || "") : manifest.cues[0]?.id || "";
    const options = manifest.cues.map(cue => `<option value="${escapeHtml(cue.id)}" ${cue.id === cueId ? "selected" : ""}>${escapeHtml(cue.label || cue.id)}</option>`).join("");
    return `<section class="show-inspector-section" data-payload-builder="cue">
      <label>cue <select id="show-cue-picker">${options || '<option value="">No staged cues</option>'}</select></label>
    </section>`;
  }

  function renderPointBuilder(message) {
    const args = message.address === "/pt" ? message.args || [] : [];
    return `<section class="show-inspector-section show-point-builder" data-payload-builder="point">
      <label>element <input data-point-field="element" type="number" min="0" step="1" value="${escapeHtml(numberAttr(args[0]?.value, 0))}"></label>
      <label>x <input data-point-field="x" type="number" step="0.01" value="${escapeHtml(numberAttr(args[1]?.value, 0))}"></label>
      <label>y <input data-point-field="y" type="number" step="0.01" value="${escapeHtml(numberAttr(args[2]?.value, 0))}"></label>
      <label>radius <input data-point-field="r" type="number" min="0" step="0.01" value="${escapeHtml(numberAttr(args[3]?.value, 1))}"></label>
      <label>enabled <input data-point-field="enabled" type="number" min="0" max="1" step="1" value="${escapeHtml(numberAttr(args[4]?.value, 1))}"></label>
    </section>`;
  }

  function renderRawBuilder(message) {
    const args = (message.args || []).map((arg, index) => renderRawArg(arg, index)).join("");
    return `<section class="show-inspector-section" data-payload-builder="raw">
      <label>address <input id="show-raw-address" type="text" value="${escapeHtml(message.address || "/")}" placeholder="/p/name"></label>
      <div class="show-inspector-subhead"><h4>Arguments</h4><button type="button" data-add-raw-arg>Add arg</button></div>
      <div class="show-raw-args">${args || '<p class="dim">No arguments.</p>'}</div>
    </section>`;
  }

  function renderRawArg(arg, index) {
    return `<div class="show-raw-arg" data-raw-arg="${index}">
      <select data-raw-type="${index}" aria-label="arg type">
        <option value="f" ${arg.type === "f" ? "selected" : ""}>f</option>
        <option value="i" ${arg.type === "i" ? "selected" : ""}>i</option>
        <option value="s" ${arg.type === "s" ? "selected" : ""}>s</option>
      </select>
      <input data-raw-value="${index}" type="${arg.type === "s" ? "text" : "number"}" step="any" value="${escapeHtml(arg.value ?? "")}" aria-label="arg value">
      <button type="button" class="danger" data-remove-raw-arg="${index}">Remove</button>
    </div>`;
  }

  function render() {
    if (rowsResizeDrag || showDrag?.active) {
      renderPending = true;
      return;
    }
    // Re-rendering rebuilds the saved-shows picker with the current show
    // selected, which would wipe an operator's uncommitted dropdown choice
    // on every countdown tick. An uncommitted choice is a live value that
    // differs from the option rendered selected; carry it across the rebuild.
    const oldPicker = root.querySelector("#show-switch-select");
    const renderedShow = oldPicker?.querySelector("option[selected]")?.value;
    const pickedShow = oldPicker && oldPicker.value !== renderedShow ? oldPicker.value : null;
    const oldCueLead = root.querySelector("#show-cue-lead");
    const cueLeadDraft = oldCueLead && document.activeElement === oldCueLead
      ? oldCueLead.value : null;
    const oldRowsBox = root.querySelector(".show-rows-box");
    if (oldRowsBox) {
      // Hidden tabs report a zero clientHeight during startup broadcasts;
      // keep the intended default until the box has real layout geometry.
      if (oldRowsBox.clientHeight >= 160) showRowsHeight = oldRowsBox.clientHeight;
      showRowsScrollTop = oldRowsBox.scrollTop;
    }
    if (!shows.current) renderEmptyState();
    else renderLoadedShow();
    const rowsBox = root.querySelector(".show-rows-box");
    if (rowsBox) rowsBox.scrollTop = showRowsScrollTop;
    if (pickedShow) {
      const picker = root.querySelector("#show-switch-select");
      if (picker && [...picker.options].some(option => option.value === pickedShow)) {
        picker.value = pickedShow;
      }
    }
    if (cueLeadDraft != null) {
      const cueLead = root.querySelector("#show-cue-lead");
      if (cueLead) {
        cueLead.value = cueLeadDraft;
        cueLead.focus({preventScroll: true});
      }
    }
    if (scrollFocusedRow) {
      const row = focus.kind === "step"
        ? root.querySelector(`[data-show-step-row="${focus.uid}"]`)
        : focus.kind === "divider"
          ? root.querySelector(`[data-show-divider-row="${focus.uid}"]`) : null;
      row?.scrollIntoView({block: "nearest"});
      if (rowsBox) showRowsScrollTop = rowsBox.scrollTop;
      scrollFocusedRow = false;
    }
    // Re-rendering replaces the DOM and drops element focus, which breaks
    // keyboard copy/paste on the focused pill/row; restore it unless the
    // user is in a form control.
    const active = document.activeElement;
    if (active && active !== document.body) return;
    const selector = focus.kind === "message" ? `[data-show-message-focus="${focus.uid}"]`
      : focus.kind === "step" ? `[data-show-step-row="${focus.uid}"]`
      : focus.kind === "divider" ? `[data-show-divider-row="${focus.uid}"]` : null;
    if (selector) root.querySelector(selector)?.focus({preventScroll: true});
  }

  function sendTransport(type, uid) {
    playback.steps ||= {};
    if (type === "step_start" && uid) {
      playback.steps[uid] = {state: "playing", iteration: 1, remaining_s: null};
    } else if (type === "step_stop" && uid) {
      delete playback.steps[uid];
    } else if (type === "step_pause" && uid) {
      const remaining = remainingSeconds(uid);
      playback.steps[uid] = {...playbackState(uid), state: "paused", remaining_s: remaining};
    } else if (type === "step_resume" && uid) {
      playback.steps[uid] = {...playbackState(uid), state: "playing"};
      playbackAt = performance.now();
    } else if (type === "stop_all_steps") {
      playback = {steps: {}};
    }
    syncCountdownTimer();
    render();
    if (type === "stop_all_steps") ws.send(type, {});
    else if (uid) ws.send(type, {uid});
  }

  function updateStep(uid, patch) {
    showError = "";
    ws.send("update_step", {uid, ...patch});
  }

  function updateMessage(uid, patch) {
    showError = "";
    ws.send("update_message", {uid, ...patch});
  }

  function readDuration() {
    const h = Math.max(0, Math.trunc(Number(root.querySelector('[data-duration-part="h"]')?.value) || 0));
    const m = Math.min(59, Math.max(0, Math.trunc(Number(root.querySelector('[data-duration-part="m"]')?.value) || 0)));
    const s = Math.min(59, Math.max(0, Math.trunc(Number(root.querySelector('[data-duration-part="s"]')?.value) || 0)));
    return h * 3600 + m * 60 + s;
  }

  function currentThenActions(step) {
    const actions = Array.isArray(step.then_actions) && step.then_actions.length
      ? step.then_actions : [{type: "stop"}];
    return structuredClone(actions);
  }

  function normalizeAction(type) {
    if (type === "goto") {
      return {type, target_uid: allSteps()[0]?.uid || ""};
    }
    return {type};
  }

  function itemByUid(uid) {
    return (show.items || []).find(item => item.uid === uid) || null;
  }

  function copyMessage(message) {
    clipboard = {
      alias: message.alias, address: message.address,
      args: structuredClone(message.args || []),
      target: structuredClone(targetList(message)),
    };
    render();
  }

  function pasteMessage(stepUid) {
    const step = stepByUid(stepUid);
    if (!clipboard || !step) return;
    showError = "";
    pendingMessageAdd = {step_uid: stepUid, known: new Set((step.messages || []).map(message => message.uid)), expand_target: false};
    ws.send("add_message", {step_uid: stepUid, message: structuredClone(clipboard)});
  }

  function deleteMessage(uid) {
    showError = "";
    ws.send("remove_message", {uid});
  }

  function deleteItem(uid) {
    const item = itemByUid(uid);
    if (!item) return;
    if (item.kind === "step" && (item.messages || []).length
        && !confirm(`Delete step "${stepLabel(item)}" and its ${item.messages.length} message(s)?`)) return;
    showError = "";
    ws.send("remove_item", {uid});
  }

  function addItem(kind, afterUid) {
    showError = "";
    if (kind === "step") {
      pendingItemAdd = {kind, known: new Set((show.items || []).map(item => item.uid))};
    }
    ws.send(kind === "divider" ? "add_divider" : "add_step", {after_uid: afterUid || null});
  }

  function clearDragMarkers() {
    root.querySelectorAll(".show-drop-row,.show-drop-before,.show-drop-after")
      .forEach(node => node.classList.remove("show-drop-row", "show-drop-before", "show-drop-after"));
  }

  function rowItemUid(row) {
    return row?.dataset.showStepRow || row?.dataset.showDividerRow || null;
  }

  function autoScrollShowRows(clientY) {
    const box = root.querySelector(".show-rows-box");
    if (!box) return;
    const bounds = box.getBoundingClientRect();
    if (clientY < bounds.top + 36) box.scrollTop -= 14;
    else if (clientY > bounds.bottom - 36) box.scrollTop += 14;
  }

  function messageDropAt(clientX, clientY) {
    const hit = document.elementFromPoint(clientX, clientY);
    const row = hit?.closest?.("[data-show-step-row]");
    if (!row) return null;
    const pills = [...row.querySelectorAll("[data-drag-message]")]
      .filter(pill => pill.dataset.dragMessage !== showDrag.uid);
    let afterUid = null;
    let nextPill = null;
    for (const pill of pills) {
      const bounds = pill.getBoundingClientRect();
      const before = clientY < bounds.top + bounds.height / 2
        || (clientY <= bounds.bottom && clientX < bounds.left + bounds.width / 2);
      if (before) {
        nextPill = pill;
        break;
      }
      afterUid = pill.dataset.dragMessage;
    }
    clearDragMarkers();
    row.classList.add("show-drop-row");
    if (nextPill) nextPill.classList.add("show-drop-before");
    else if (pills.length) pills[pills.length - 1].classList.add("show-drop-after");
    return {toStepUid: row.dataset.showStepRow, afterUid};
  }

  function itemDropAt(clientY) {
    const rows = [...root.querySelectorAll("[data-show-step-row],[data-show-divider-row]")]
      .filter(row => rowItemUid(row) !== showDrag.uid);
    let afterUid = null;
    let nextRow = null;
    for (const row of rows) {
      const bounds = row.getBoundingClientRect();
      if (clientY < bounds.top + bounds.height / 2) {
        nextRow = row;
        break;
      }
      afterUid = rowItemUid(row);
    }
    clearDragMarkers();
    if (nextRow) nextRow.classList.add("show-drop-before");
    else if (rows.length) rows[rows.length - 1].classList.add("show-drop-after");
    return {afterUid};
  }

  root.addEventListener("pointerdown", event => {
    if (event.button !== 0 || rowsResizeDrag || showDrag) return;
    const itemHandle = event.target.closest("[data-drag-item]");
    const message = event.target.closest("[data-drag-message]");
    const source = itemHandle || message;
    if (!source) return;
    showDrag = {
      pointerId: event.pointerId,
      kind: itemHandle ? "item" : "message",
      uid: itemHandle?.dataset.dragItem || message.dataset.dragMessage,
      source,
      startX: event.clientX,
      startY: event.clientY,
      active: false,
      drop: null,
    };
    source.setPointerCapture(event.pointerId);
    if (itemHandle) event.preventDefault();
  });

  root.addEventListener("pointermove", event => {
    if (!showDrag || event.pointerId !== showDrag.pointerId) return;
    const distance = Math.hypot(event.clientX - showDrag.startX, event.clientY - showDrag.startY);
    if (!showDrag.active && distance < 7) return;
    if (!showDrag.active) {
      showDrag.active = true;
      suppressDragClick = true;
      showDrag.source.classList.add("show-dragging");
      root.classList.add("show-drag-active");
    }
    autoScrollShowRows(event.clientY);
    showDrag.drop = showDrag.kind === "message"
      ? messageDropAt(event.clientX, event.clientY)
      : itemDropAt(event.clientY);
    event.preventDefault();
  });

  function finishShowDrag(event, commit) {
    if (!showDrag || event.pointerId !== showDrag.pointerId) return;
    const drag = showDrag;
    showDrag = null;
    if (drag.source.hasPointerCapture?.(event.pointerId)) drag.source.releasePointerCapture(event.pointerId);
    drag.source.classList.remove("show-dragging");
    root.classList.remove("show-drag-active");
    clearDragMarkers();
    if (commit && drag.active && drag.drop) {
      showError = "";
      if (drag.kind === "message") {
        ws.send("move_message", {uid: drag.uid, to_step_uid: drag.drop.toStepUid,
                                  after_uid: drag.drop.afterUid});
      } else {
        ws.send("move_item", {uid: drag.uid, after_uid: drag.drop.afterUid});
      }
    }
    if (drag.active) {
      event.preventDefault();
      setTimeout(() => { suppressDragClick = false; }, 0);
    }
    if (renderPending) {
      renderPending = false;
      render();
    }
  }

  root.addEventListener("pointerup", event => finishShowDrag(event, true));
  root.addEventListener("pointercancel", event => finishShowDrag(event, false));
  root.addEventListener("click", event => {
    if (!suppressDragClick) return;
    event.preventDefault();
    event.stopImmediatePropagation();
  }, true);

  document.addEventListener("keydown", event => {
    const showPanel = root.closest(".tab-panel");
    const meta = event.ctrlKey || event.metaKey;
    if (showPanel?.hidden || event.target.closest?.("input,select,textarea")
        || !meta || event.shiftKey || event.key.toLowerCase() !== "z") return;
    ws.send("undo_show", {});
    event.preventDefault();
    event.stopPropagation();
  }, true);

  root.addEventListener("pointerdown", event => {
    const handle = event.target.closest(".show-rows-resize");
    if (!handle || event.button !== 0) return;
    const box = root.querySelector(".show-rows-box");
    if (!box) return;
    rowsResizeDrag = {pointerId: event.pointerId, startY: event.clientY, startHeight: box.clientHeight};
    handle.setPointerCapture(event.pointerId);
    event.preventDefault();
  });

  root.addEventListener("pointermove", event => {
    if (!rowsResizeDrag || event.pointerId !== rowsResizeDrag.pointerId) return;
    const box = root.querySelector(".show-rows-box");
    if (!box) return;
    showRowsHeight = Math.max(160, Math.round(rowsResizeDrag.startHeight + event.clientY - rowsResizeDrag.startY));
    box.style.height = `${showRowsHeight}px`;
    event.preventDefault();
  });

  function finishRowsResize(event) {
    if (!rowsResizeDrag || event.pointerId !== rowsResizeDrag.pointerId) return;
    const handle = event.target.closest(".show-rows-resize");
    if (handle?.hasPointerCapture(event.pointerId)) handle.releasePointerCapture(event.pointerId);
    rowsResizeDrag = null;
    if (renderPending) {
      renderPending = false;
      render();
    }
  }

  root.addEventListener("pointerup", finishRowsResize);
  root.addEventListener("pointercancel", finishRowsResize);

  root.addEventListener("toggle", event => {
    const disclosure = event.target.closest?.("[data-target-disclosure]");
    if (!disclosure) return;
    targetDisclosure = {uid: disclosure.dataset.targetDisclosure, open: disclosure.open};
  }, true);

  function paramModeDefaultArgs(declaration, mode) {
    const type = declaration?.type || "f";
    const value = declaration?.default ?? (type === "s" ? "" : 0);
    if (type === "s" || mode === "value") return [typedArg(type, value)];
    if (mode === "fade") return [typedArg(type, value), typedArg("s", "1s")];
    if (mode === "loop") return [
      typedArg("s", "loop"), typedArg(type, value), typedArg("s", "1s"),
      typedArg(type, value), typedArg("s", "1s"),
    ];
    if (mode === "lfo") return [
      typedArg("s", "lfo"), typedArg("s", "sine"),
      typedArg(type, declaration?.min ?? 0), typedArg(type, declaration?.max ?? 1),
      typedArg("s", "4s"),
    ];
    return [typedArg("s", "stop")];
  }

  function currentParamDeclaration(message, identity = null) {
    const manifest = manifestFromStagedPatch();
    const selected = identity ?? (message.address?.startsWith("/p/") ? message.address.slice(3) : "");
    return manifest.params.find(param => param.identity === selected)
      || manifest.params[0] || {identity: selected, type: "f", default: 0};
  }

  function inputNumber(editor, selector) {
    const value = Number(editor.querySelector(selector)?.value);
    return Number.isFinite(value) ? value : null;
  }

  function durationString(editor, amountSelector, unitSelector) {
    const amount = inputNumber(editor, amountSelector);
    const unit = editor.querySelector(unitSelector)?.value || "ms";
    if (amount == null || amount < 0) return null;
    return `${String(Number(amount))}${unit}`;
  }

  function compileParamEditor(message, editor) {
    const declaration = currentParamDeclaration(message);
    const type = declaration.type || "f";
    const mode = editor.querySelector("#show-param-generator")?.value || "value";
    if (mode === "value") {
      const input = editor.querySelector("#show-param-value");
      return input ? [typedArg(type, input.value)] : null;
    }
    if (mode === "stop") return [typedArg("s", "stop")];
    if (mode === "lfo") {
      const minimum = inputNumber(editor, '[data-param-lfo="min"]');
      const maximum = inputNumber(editor, '[data-param-lfo="max"]');
      const periodAmount = inputNumber(editor, '[data-param-lfo="period"]');
      const period = durationString(editor, '[data-param-lfo="period"]', '[data-param-lfo="period-unit"]');
      const phase = inputNumber(editor, '[data-param-lfo="phase"]');
      const curve = inputNumber(editor, '[data-param-lfo="curve"]');
      if (minimum == null || maximum == null || periodAmount == null || periodAmount <= 0 || period == null
          || phase == null || phase < 0 || phase > 1 || curve == null) return null;
      const args = [
        typedArg("s", "lfo"), typedArg("s", editor.querySelector('[data-param-lfo="shape"]')?.value || "sine"),
        typedArg(type, minimum), typedArg(type, maximum), typedArg("s", period),
      ];
      if (phase !== 0) args.push(typedArg("s", `p:${String(Number(phase))}`));
      if (editor.querySelector('[data-param-lfo="free"]')?.checked) args.push(typedArg("s", "f"));
      if (curve !== 0) args.push(typedArg("s", `c:${String(Number(curve))}`));
      return args;
    }
    const rows = [...editor.querySelectorAll("[data-param-segment]")];
    const hint = editor.querySelector(".show-param-loop-hint");
    if (hint) hint.hidden = !(mode === "loop" && rows.length < 2);
    if (!rows.length || (mode === "loop" && rows.length < 2)) return null;
    const args = mode === "loop" ? [typedArg("s", "loop")] : [];
    if (mode === "fade" && rows.length === 1) {
      const from = editor.querySelector("[data-param-from]")?.value.trim();
      if (from) args.push(typedArg(type, from));
    }
    for (const row of rows) {
      const value = row.querySelector("[data-param-segment-value]")?.value;
      const duration = durationString(row, "[data-param-segment-duration]", "[data-param-segment-unit]");
      if (value == null || duration == null) return null;
      args.push(typedArg(type, value), typedArg("s", duration));
    }
    const curve = inputNumber(editor, "[data-param-curve]");
    if (curve == null) return null;
    if (curve !== 0) args.push(typedArg("s", `c:${String(Number(curve))}`));
    return args;
  }

  function applyModeDefault(message, mode) {
    const manifest = manifestFromStagedPatch();
    if (mode === "param") {
      const declaration = manifest.params[0];
      const identity = declaration?.identity || "gain";
      const type = declaration?.type || "f";
      const value = declaration?.default ?? (type === "s" ? "" : 0);
      updateMessage(message.uid, {address: `/p/${identity}`, args: [typedArg(type, value)], target: targetList(message)});
    } else if (mode === "cue") {
      updateMessage(message.uid, {address: "/cue", args: [{type: "s", value: manifest.cues[0]?.id || ""}], target: targetList(message)});
    } else if (mode === "point") {
      updateMessage(message.uid, {address: "/pt", args: [
        {type: "i", value: 0}, {type: "f", value: 0}, {type: "f", value: 0},
        {type: "f", value: 1}, {type: "i", value: 1},
      ], target: targetList(message)});
    } else {
      updateMessage(message.uid, {address: "/raw", args: message.args || [], target: targetList(message)});
    }
  }

  root.addEventListener("click", event => {
    const action = event.target.closest("[data-show-action]");
    if (action) {
      event.stopPropagation();
      sendTransport(action.dataset.showAction, action.dataset.showUid);
      return;
    }
    if (event.target.closest("#show-load-button")) {
      const name = root.querySelector("#show-load-select")?.value;
      if (name) ws.send("load_show", {name});
      return;
    }
    if (event.target.closest("#show-switch-load")) {
      const name = root.querySelector("#show-switch-select")?.value;
      if (!name || name === shows.current) return;
      const busy = Object.values(playback?.steps || {}).some(state => ["playing", "paused"].includes(state?.state));
      if (busy && !confirm(`Load show "${name}"? Playback of the current show stops.`)) return;
      ws.send("load_show", {name});
      return;
    }
    if (event.target.closest("#show-manage-new")) {
      const name = prompt("New show name:", "");
      if (name?.trim()) ws.send("create_show", {name: name.trim()});
      return;
    }
    if (event.target.closest("#show-manage-rename")) {
      const name = prompt("Rename show:", shows.current || "");
      if (name?.trim() && name.trim() !== shows.current) ws.send("rename_show", {name: name.trim()});
      return;
    }
    if (event.target.closest("#show-manage-delete")) {
      const name = root.querySelector("#show-switch-select")?.value;
      if (name && confirm(`Delete show "${name}"? The file is removed.`)) ws.send("delete_show", {name});
      return;
    }
    const pill = event.target.closest("[data-show-message-focus]");
    if (pill) {
      event.stopPropagation();
      setFocus("message", pill.dataset.showMessageFocus);
      return;
    }
    const divider = event.target.closest("[data-show-divider-row]");
    if (divider) {
      setFocus("divider", divider.dataset.showDividerRow);
      return;
    }
    const row = event.target.closest("[data-show-step-row]");
    if (row) setFocus("step", row.dataset.showStepRow);
  });

  root.addEventListener("change", event => {
    if (event.target.id === "show-cue-lead") {
      const ms = Math.min(10000, Math.max(100, Math.trunc(Number(event.target.value) || 500)));
      event.target.value = ms;
      ws.send("set_cue_lead", {ms});
      return;
    }
    const stepEditor = event.target.closest("[data-show-step-editor]");
    if (stepEditor) {
      const step = stepByUid(stepEditor.dataset.showStepEditor);
      if (!step) return;
      if (event.target.id === "show-step-alias") updateStep(step.uid, {alias: event.target.value.trim() || null});
      if (event.target.matches("[data-duration-part]")) updateStep(step.uid, {duration_s: readDuration()});
      if (event.target.id === "show-play-forever") {
        const next = event.target.checked ? null : Math.max(1, Math.trunc(Number(root.querySelector("#show-play-count")?.value) || 1));
        updateStep(step.uid, {play_count: next});
      }
      if (event.target.id === "show-play-count") updateStep(step.uid, {play_count: Math.max(1, Math.trunc(Number(event.target.value) || 1))});
      if (event.target.matches("[data-then-type]")) {
        const actions = currentThenActions(step);
        const index = Number(event.target.dataset.thenType);
        actions[index] = normalizeAction(event.target.value);
        updateStep(step.uid, {then_actions: actions});
      }
      if (event.target.matches("[data-then-goto]")) {
        const actions = currentThenActions(step);
        const index = Number(event.target.dataset.thenGoto);
        actions[index] = {type: "goto", target_uid: event.target.value};
        updateStep(step.uid, {then_actions: actions});
      }
      return;
    }

    const messageEditor = event.target.closest("[data-show-message-editor]");
    if (messageEditor) {
      const {message} = messageByUid(messageEditor.dataset.showMessageEditor);
      if (!message) return;
      if (event.target.id === "show-message-alias") updateMessage(message.uid, {alias: event.target.value.trim() || null});
      if (event.target.id === "show-message-mode") applyModeDefault(message, event.target.value);
      if (event.target.id === "show-param-picker") {
        const oldDeclaration = currentParamDeclaration(message);
        let mode = "value";
        try { mode = parseParamArgs(message.args || [], oldDeclaration.type).mode; }
        catch (_error) { mode = "value"; }
        const declaration = currentParamDeclaration(message, event.target.value);
        if (declaration.type === "s") mode = "value";
        updateMessage(message.uid, {address: `/p/${event.target.value}`, args: paramModeDefaultArgs(declaration, mode)});
      }
      if (event.target.id === "show-param-generator") {
        const declaration = currentParamDeclaration(message);
        updateMessage(message.uid, {args: paramModeDefaultArgs(declaration, event.target.value)});
      }
      if (event.target.id === "show-param-value") {
        const declaration = currentParamDeclaration(message);
        updateMessage(message.uid, {args: [typedArg(declaration.type || "f", event.target.value)]});
      }
      if (event.target.matches("[data-param-segment-value], [data-param-segment-duration], [data-param-segment-unit], [data-param-from], [data-param-curve], [data-param-lfo]")) {
        const args = compileParamEditor(message, messageEditor);
        if (args) updateMessage(message.uid, {args});
      }
      if (event.target.id === "show-cue-picker") updateMessage(message.uid, {address: "/cue", args: [{type: "s", value: event.target.value}]});
      if (event.target.matches("[data-point-field]")) {
        const values = {};
        messageEditor.querySelectorAll("[data-point-field]").forEach(input => values[input.dataset.pointField] = input.value);
        updateMessage(message.uid, {address: "/pt", args: [
          typedArg("i", values.element), typedArg("f", values.x), typedArg("f", values.y),
          typedArg("f", values.r), typedArg("i", values.enabled),
        ]});
      }
      if (event.target.id === "show-raw-address") updateMessage(message.uid, {address: event.target.value.trim() || "/"});
      if (event.target.matches("[data-raw-type], [data-raw-value]")) {
        const args = (message.args || []).map((arg, index) => {
          const type = messageEditor.querySelector(`[data-raw-type="${index}"]`)?.value || arg.type || "f";
          const value = messageEditor.querySelector(`[data-raw-value="${index}"]`)?.value ?? arg.value;
          return typedArg(type, value);
        });
        updateMessage(message.uid, {args});
      }
    }
  });

  root.addEventListener("click", event => {
    const itemAdd = event.target.closest("[data-item-add]");
    if (itemAdd) {
      addItem(itemAdd.dataset.itemAdd, itemAdd.dataset.itemUid);
      return;
    }
    const itemAddEnd = event.target.closest("[data-item-add-end]");
    if (itemAddEnd) {
      const items = show.items || [];
      addItem(itemAddEnd.dataset.itemAddEnd, items.length ? items[items.length - 1].uid : null);
      return;
    }
    const itemDelete = event.target.closest("[data-item-delete]");
    if (itemDelete) {
      deleteItem(itemDelete.dataset.itemDelete);
      return;
    }
    const stepEditor = event.target.closest("[data-show-step-editor]");
    if (stepEditor) {
      const step = stepByUid(stepEditor.dataset.showStepEditor);
      if (!step) return;
      if (event.target.matches("[data-add-then-action]")) {
        updateStep(step.uid, {then_actions: [...currentThenActions(step), {type: "stop"}]});
      }
      if (event.target.matches("[data-remove-then]")) {
        const actions = currentThenActions(step);
        const index = Number(event.target.dataset.removeThen);
        if (index <= 0) return;
        actions.splice(index, 1);
        updateStep(step.uid, {then_actions: actions});
      }
      if (event.target.id === "show-add-message") {
        pendingMessageAdd = {step_uid: step.uid, known: new Set((step.messages || []).map(message => message.uid)), expand_target: true};
        ws.send("add_message", {step_uid: step.uid, message: {alias: null, address: "/p/gain", args: [{type: "f", value: 0}], target: ["all"]}});
      }
    }

    const messageEditor = event.target.closest("[data-show-message-editor]");
    if (messageEditor) {
      const {message} = messageByUid(messageEditor.dataset.showMessageEditor);
      if (!message) return;
      if (event.target.matches("[data-add-param-segment]")) {
        const declaration = currentParamDeclaration(message);
        const segments = messageEditor.querySelector("[data-param-segments]");
        const count = segments?.querySelectorAll("[data-param-segment]").length || 0;
        if (segments) {
          segments.insertAdjacentHTML("beforeend", renderParamSegment({
            value: declaration.default ?? 0,
            duration: {amount: "1", unit: "s"},
          }, count, declaration, count + 1));
          segments.querySelectorAll("[data-remove-param-segment]").forEach(button => button.disabled = false);
          const args = compileParamEditor(message, messageEditor);
          if (args) updateMessage(message.uid, {args});
        }
      }
      if (event.target.matches("[data-remove-param-segment]")) {
        const rows = messageEditor.querySelectorAll("[data-param-segment]");
        if (rows.length <= 1) return;
        event.target.closest("[data-param-segment]")?.remove();
        const remaining = messageEditor.querySelectorAll("[data-param-segment]");
        if (remaining.length === 1) remaining[0].querySelector("[data-remove-param-segment]").disabled = true;
        const args = compileParamEditor(message, messageEditor);
        if (args) updateMessage(message.uid, {args});
      }
      const toggle = event.target.closest("[data-target-toggle]");
      if (toggle) {
        updateMessage(message.uid, {target: toggledTargets(message, toggle.dataset.targetToggle)});
      }
      const removal = event.target.closest("[data-target-remove]");
      if (removal) {
        const remaining = targetList(message).filter(entry => entry !== removal.dataset.targetRemove);
        updateMessage(message.uid, {target: remaining.length ? remaining : ["all"]});
      }
      if (event.target.matches("[data-add-raw-arg]")) {
        updateMessage(message.uid, {args: [...(message.args || []), {type: "f", value: 0}]});
      }
      if (event.target.matches("[data-remove-raw-arg]")) {
        const args = [...(message.args || [])];
        args.splice(Number(event.target.dataset.removeRawArg), 1);
        updateMessage(message.uid, {args});
      }
    }
  });

  root.addEventListener("keydown", event => {
    const meta = event.ctrlKey || event.metaKey;
    const key = event.key.toLowerCase();
    if (event.target.closest("input, select, textarea")) return;
    const pill = event.target.closest("[data-show-message-focus]");
    const row = event.target.closest("[data-show-step-row]");
    const divider = event.target.closest("[data-show-divider-row]");
    if (meta && key === "c" && pill) {
      const {message} = messageByUid(pill.dataset.showMessageFocus);
      if (message) copyMessage(message);
      event.preventDefault();
      return;
    }
    if (meta && key === "x" && pill) {
      const {message} = messageByUid(pill.dataset.showMessageFocus);
      if (message) {
        copyMessage(message);
        deleteMessage(message.uid);
      }
      event.preventDefault();
      return;
    }
    if (meta && key === "v" && (pill || row)) {
      pasteMessage(pill ? pill.dataset.showStep : row.dataset.showStepRow);
      event.preventDefault();
      return;
    }
    if (["Delete", "Backspace"].includes(event.key)) {
      if (pill) deleteMessage(pill.dataset.showMessageFocus);
      else if (row) deleteItem(row.dataset.showStepRow);
      else if (divider) deleteItem(divider.dataset.showDividerRow);
      if (pill || row || divider) event.preventDefault();
      return;
    }
    if (["Enter", " "].includes(event.key)) {
      if (divider) {
        event.preventDefault();
        setFocus("divider", divider.dataset.showDividerRow);
      } else if (row && !pill) {
        event.preventDefault();
        setFocus("step", row.dataset.showStepRow);
      }
    }
  });

  root.addEventListener("submit", event => {
    if (event.target.id !== "show-create-form") return;
    event.preventDefault();
    const name = root.querySelector("#show-create-name")?.value.trim();
    if (name) ws.send("create_show", {name});
  });

  ws.on("shows", data => {
    shows = {names: data?.names || [], current: data?.current || null};
    if (!shows.current) focus = {kind: null, uid: null};
    render();
  });
  ws.on("show", data => {
    show = data || {schema: 1, name: "", items: []};
    if (pendingItemAdd) {
      const added = (show.items || []).find(item =>
        item.kind === pendingItemAdd.kind && !pendingItemAdd.known.has(item.uid));
      if (added) {
        focus = {kind: added.kind, uid: added.uid};
        scrollFocusedRow = true;
        pendingItemAdd = null;
      }
    }
    if (pendingMessageAdd) {
      const step = stepByUid(pendingMessageAdd.step_uid);
      const added = (step?.messages || []).find(message => !pendingMessageAdd.known.has(message.uid));
      if (added) {
        focus = {kind: "message", uid: added.uid};
        targetDisclosure = {uid: added.uid, open: Boolean(pendingMessageAdd.expand_target)};
        pendingMessageAdd = null;
      }
    }
    const validFocus = focus.kind === "step"
      ? stepByUid(focus.uid)
      : focus.kind === "divider"
        ? (show.items || []).some(item => item.kind === "divider" && item.uid === focus.uid)
        : (show.items || []).some(item => item.kind === "step" && (item.messages || []).some(message => message.uid === focus.uid));
    if (!validFocus) focus = {kind: null, uid: null};
    render();
  });
  ws.on("show_playback", data => {
    playback = data || {steps: {}};
    playbackAt = performance.now();
    syncCountdownTimer();
    render();
  });
  function syncCountdownTimer() {
    const hasTimedPlaying = Object.values(playback.steps || {}).some(state =>
      state?.state === "playing" && Number.isFinite(Number(state.remaining_s)));
    if (hasTimedPlaying && !countdownTimer) {
      countdownTimer = setInterval(updateCountdownLabels, 500);
    }
    if (!hasTimedPlaying && countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
  }
  function updateCountdownLabels() {
    root.querySelectorAll("[data-show-step-row]").forEach(row => {
      const remaining = remainingSeconds(row.dataset.showStepRow);
      const label = row.querySelector(".show-remaining");
      if (label && remaining != null) label.textContent = terseDuration(remaining);
    });
  }
  function renderForRelevantStateChange() {
    const signature = showRelevantStateSignature();
    if (signature === relevantStateSignature) return;
    relevantStateSignature = signature;
    render();
  }
  ws.on("state", renderForRelevantStateChange);
  ws.on("distribution", renderForRelevantStateChange);
  // ------------------------------------------------------------------
  // OSC consoles (stitch 7). These live outside #show-root so the
  // high-rate osc_in/osc_out stream never re-renders the show table, and
  // show-state renders never wipe the console DOM.
  // ------------------------------------------------------------------
  const CONSOLE_LIMIT = 500;
  const CONSOLE_VISIBLE = 200;
  const consoleHost = document.createElement("div");
  consoleHost.id = "show-consoles";
  root.after(consoleHost);
  consoleHost.innerHTML = ["out", "in"].map(kind => `
    <details class="show-console" data-console="${kind}">
      <summary>${kind === "out" ? "Outgoing OSC" : "Incoming OSC"}
        <output data-console-count aria-live="off"></output></summary>
      <div class="show-console-bar">
        <input data-console-filter type="text" autocomplete="off" spellcheck="false"
               placeholder="filter: /p/* !/sync" aria-label="${kind} console filter">
        <button type="button" data-console-pause>Pause</button>
        <button type="button" data-console-clear>Clear</button>
      </div>
      <div class="show-console-log" data-console-log tabindex="0"></div>
    </details>`).join("");

  const consoles = {
    out: {entries: [], paused: false, filter: "", autoScroll: true, dirty: false, total: 0},
    in: {entries: [], paused: false, filter: "", autoScroll: true, dirty: false, total: 0},
  };
  let consoleFlush = null;

  function consolePanel(kind) {
    return consoleHost.querySelector(`[data-console="${kind}"]`);
  }

  function filterTerms(text) {
    return text.trim().toLowerCase().split(/\s+/).filter(Boolean).map(term => {
      const negated = term.startsWith("!");
      const body = negated ? term.slice(1) : term;
      const pattern = new RegExp(body.split("*").map(part =>
        part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join(".*"));
      return {negated, pattern};
    }).filter(term => term.pattern.source !== "(?:)");
  }

  function consoleLine(kind, entry) {
    const stamp = new Date(entry.ts * 1000).toLocaleTimeString("en-GB", {hour12: false})
      + "." + String(Math.floor((entry.ts % 1) * 1000)).padStart(3, "0");
    const args = (entry.args || []).map(String).join(" ");
    const peer = kind === "out" ? `-> ${entry.target || ""}` : `<- ${entry.source || ""}`;
    return `${stamp}  ${entry.address}${args ? "  " + args : ""}  ${peer}`;
  }

  function renderConsole(kind) {
    const state = consoles[kind];
    const panel = consolePanel(kind);
    const log = panel.querySelector("[data-console-log]");
    let lines = state.entries.map(entry => entry.line);
    let terms;
    try { terms = filterTerms(state.filter); } catch (_error) { terms = []; }
    if (terms.length) {
      lines = lines.filter(line => {
        const lower = line.toLowerCase();
        return terms.every(term => term.negated
          ? !term.pattern.test(lower) : term.pattern.test(lower));
      });
    }
    const shown = lines.slice(-CONSOLE_VISIBLE);
    log.textContent = shown.join("\n");
    panel.querySelector("[data-console-count]").value =
      `${shown.length} shown · ${state.total} seen`;
    if (state.autoScroll) log.scrollTop = log.scrollHeight;
    state.dirty = false;
  }

  for (const kind of ["out", "in"]) {
    consolePanel(kind).open = false;
    renderConsole(kind);
  }

  function scheduleConsoleFlush() {
    if (consoleFlush !== null) return;
    consoleFlush = setTimeout(() => {
      consoleFlush = null;
      for (const kind of ["out", "in"]) {
        if (consoles[kind].dirty && !consoles[kind].paused) renderConsole(kind);
      }
    }, 150);
  }

  function pushConsole(kind, data) {
    if (!data || typeof data.address !== "string") return;
    const state = consoles[kind];
    state.total += 1;
    state.entries.push({line: consoleLine(kind, data)});
    if (state.entries.length > CONSOLE_LIMIT) state.entries.shift();
    state.dirty = true;
    if (!state.paused) scheduleConsoleFlush();
  }

  consoleHost.addEventListener("input", event => {
    const panel = event.target.closest("[data-console]");
    if (!panel || !event.target.matches("[data-console-filter]")) return;
    const state = consoles[panel.dataset.console];
    state.filter = event.target.value;
    renderConsole(panel.dataset.console);
  });

  consoleHost.addEventListener("click", event => {
    const panel = event.target.closest("[data-console]");
    if (!panel) return;
    const state = consoles[panel.dataset.console];
    if (event.target.matches("[data-console-pause]")) {
      state.paused = !state.paused;
      event.target.textContent = state.paused ? "Resume" : "Pause";
      if (!state.paused) renderConsole(panel.dataset.console);
    }
    if (event.target.matches("[data-console-clear]")) {
      state.entries = [];
      state.total = 0;
      renderConsole(panel.dataset.console);
    }
  });

  consoleHost.addEventListener("scroll", event => {
    const log = event.target;
    if (!log.matches?.("[data-console-log]")) return;
    const panel = log.closest("[data-console]");
    consoles[panel.dataset.console].autoScroll =
      log.scrollTop + log.clientHeight >= log.scrollHeight - 24;
  }, true);

  ws.on("osc_out", data => pushConsole("out", data));
  ws.on("osc_in", data => pushConsole("in", data));

  window.ShowInspectorError = message => {
    showError = message || "Show edit failed.";
    if (shows.current) render();
  };
  ws.on("error", data => {
    window.ShowInspectorError(data?.message);
  });

  render();
})();
