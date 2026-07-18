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
  let clipboard = null;

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

  function hasMixedForwardSync(step) {
    if (!step?.forward_sync) return false;
    const messages = step.messages || [];
    return messages.some(message => message.address === "/cue") &&
      messages.some(message => message.address !== "/cue");
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
    return [path, name].filter(Boolean).join("/") || (declaration?.group || name);
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
    return `<section class="show-inspector-section show-target-picker${disabled ? " show-disabled-field" : ""}">
      <div class="show-inspector-subhead"><h4>Target</h4><output class="show-target-terse">${escapeHtml(terseTargets(message))}</output></div>
      <div class="show-target-summary">${summary}</div>
      <div class="show-target-chips">
        <button type="button" class="show-target-chip show-target-all${isAll ? " on" : ""}" data-target-toggle="all" aria-pressed="${isAll}"${off}>All</button>
        ${groupChips}
      </div>
      ${seatChips ? `<div class="show-target-chips show-target-roster">${seatChips}</div>` : ""}
    </section>`;
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

  function iconButton(action, uid, glyph, label, stateClass = "") {
    return `<button class="show-icon-button${stateClass}" data-show-action="${action}" data-show-uid="${uid}" title="${escapeHtml(label)}" aria-label="${escapeHtml(label)}"><span class="show-glyph show-glyph-${glyph}" aria-hidden="true"></span></button>`;
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
      return `<button class="show-message-pill${pillColourClass(message)}${selected}" data-show-message-focus="${escapeHtml(message.uid)}" data-show-step="${escapeHtml(step.uid)}" title="${escapeHtml(title)}">${escapeHtml(messageLabel(message))}</button>`;
    }).join("");
  }

  function dividerRow(item, index) {
    const selected = focused("divider", item.uid) ? " focused" : "";
    return `<div class="show-divider-row${selected}" data-show-divider-row="${escapeHtml(item.uid)}" data-show-index="${index}" role="button" tabindex="0" aria-label="Section divider"></div>`;
  }

  function stepRow(step, index) {
    const remaining = remainingSeconds(step.uid);
    const stateName = playbackState(step.uid).state || "stopped";
    const selected = focused("step", step.uid) ? " focused" : "";
    const playing = stateName === "playing" || stateName === "paused" ? " active" : "";
    const time = remaining == null
      ? `<span class="show-step-duration">${terseDuration(step.duration_s)}</span>`
      : `<span class="show-remaining" title="${stateName === "paused" ? "paused" : "remaining"}">${terseDuration(remaining)}</span>`;
    const gotoMissing = playbackState(step.uid).goto_missing
      ? '<span class="show-goto-missing" title="goto target no longer exists; stopped">goto?</span>' : "";
    return `<div class="show-step-row show-step-${escapeHtml(stateName)}${selected}${playing}" data-show-step-row="${escapeHtml(step.uid)}" data-show-index="${index}" role="row" tabindex="0">
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
    const playing = Object.entries(playback?.steps || {})
      .filter(([_uid, state]) => state?.state === "playing")
      .map(([uid]) => stepByUid(uid))
      .filter(Boolean);
    const aliases = playing.map(stepLabel).slice(0, 4).join(", ");
    const overflow = playing.length > 4 ? ` +${playing.length - 4}` : "";
    return `<div class="show-transport-strip">
      <div><p class="eyebrow">Show control</p><h2>${escapeHtml(show.name || shows.current || "Show")}</h2></div>
      <div class="show-transport-actions">
        <output id="show-playing-indicator" aria-live="polite">${playing.length ? `${playing.length} playing: ${escapeHtml(aliases)}${overflow}` : "0 playing"}</output>
        <button id="show-stop-all" class="danger" type="button">Stop all</button>
      </div>
    </div>`;
  }

  function renderLoadedShow() {
    const items = Array.isArray(show.items) ? show.items : [];
    const rows = items.map((item, index) => item.kind === "divider" ? dividerRow(item, index) : stepRow(item, index)).join("");
    root.innerHTML = `${renderTransport()}<div class="show-workspace">
      <div>
        <div class="show-rows" role="table" aria-label="Show steps">${rows || '<p class="empty">This show has no steps yet.</p>'}</div>
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
    const paste = item.kind === "step"
      ? `<button type="button" data-paste-message="${uid}" ${clipboard ? "" : "disabled"}>Paste message</button>` : "";
    return `<section class="show-inspector-section">
      <div class="show-inspector-subhead"><h4>Arrange</h4></div>
      <div class="show-arrange-grid">
        <button type="button" data-item-move="-1" data-item-uid="${uid}">Move up</button>
        <button type="button" data-item-move="1" data-item-uid="${uid}">Move down</button>
        <button type="button" data-item-add="step" data-item-uid="${uid}">Step below</button>
        <button type="button" data-item-add="divider" data-item-uid="${uid}">Divider below</button>
        ${paste}
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
    const actions = Array.isArray(step.then_actions) ? step.then_actions : [];
    const modelValidation = Number(step.duration_s) === 0 && step.play_count == null
      ? "Duration 0 needs a finite play count." : "";
    const validation = modelValidation || friendlyShowError()
      ? `<p class="show-field-error">${escapeHtml(modelValidation || friendlyShowError())}</p>` : "";
    const syncHint = hasMixedForwardSync(step)
      ? '<p class="show-sync-hint">Forward-sync schedules /cue about 500 ms ahead; non-cue messages still send immediately.</p>' : "";
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
          <div class="show-then-list">${actionRows || '<p class="dim">No rows means stop.</p>'}</div>
        </section>
        <label class="show-check"><input id="show-forward-sync" type="checkbox" ${step.forward_sync ? "checked" : ""}> forward-sync cue messages</label>
        ${syncHint}
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
      <button type="button" class="danger" data-remove-then="${index}">Remove</button>
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
        ${renderMessageEdit(step, message)}
        <label>wire form <output id="show-wire-preview">${escapeHtml(wirePreview(message))}</output></label>
        <output class="show-inspector-error" aria-live="polite">${escapeHtml(friendlyShowError())}</output>
      </div>`;
  }

  function renderMessageEdit(step, message) {
    const uid = escapeHtml(message.uid);
    const others = allSteps().filter(candidate => candidate.uid !== step.uid);
    const moveOptions = others.map(candidate =>
      `<option value="${escapeHtml(candidate.uid)}">${escapeHtml(stepLabel(candidate))}</option>`).join("");
    return `<section class="show-inspector-section">
      <div class="show-inspector-subhead"><h4>Edit</h4></div>
      <div class="show-arrange-grid">
        <button type="button" data-message-copy="${uid}">Copy</button>
        <button type="button" data-message-cut="${uid}">Cut</button>
        <button type="button" data-message-move="-1" data-message-uid="${uid}">Move left</button>
        <button type="button" data-message-move="1" data-message-uid="${uid}">Move right</button>
        <button type="button" class="danger" data-message-delete="${uid}">Delete</button>
      </div>
      ${others.length ? `<label>move to step
        <select data-message-move-step="${uid}">
          <option value="" selected>choose a step…</option>${moveOptions}
        </select></label>` : ""}
    </section>`;
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
    const value = argValue(message.args?.[0]) || declaration.default || "";
    const options = manifest.params.map(param => {
      const label = `${param.path?.length ? `${param.path.join("/")} / ` : ""}${param.name || param.identity}`;
      return `<option value="${escapeHtml(param.identity)}" ${param.identity === identity ? "selected" : ""}>${escapeHtml(label)}</option>`;
    }).join("");
    const inputType = declaration.type === "s" ? "text" : "number";
    const attrs = declaration.type === "s" ? "" : `step="${declaration.type === "i" ? "1" : "any"}" ${declaration.min != null ? `min="${escapeHtml(declaration.min)}"` : ""} ${declaration.max != null ? `max="${escapeHtml(declaration.max)}"` : ""}`;
    return `<section class="show-inspector-section" data-payload-builder="param">
      <label>parameter <select id="show-param-picker">${options || '<option value="">No staged params</option>'}</select></label>
      <label>value <input id="show-param-value" type="${inputType}" ${attrs} value="${escapeHtml(value)}"></label>
      <small class="dim">${escapeHtml(declaration.type || "f")}${declaration.min != null || declaration.max != null ? ` · ${escapeHtml(declaration.min ?? "…")} to ${escapeHtml(declaration.max ?? "…")}` : ""}</small>
    </section>`;
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
    if (!shows.current) renderEmptyState();
    else renderLoadedShow();
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
    return structuredClone(Array.isArray(step.then_actions) ? step.then_actions : []);
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

  function moveItem(uid, direction) {
    const items = show.items || [];
    const index = items.findIndex(item => item.uid === uid);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= items.length) return;
    const afterUid = direction < 0
      ? (target > 0 ? items[target - 1].uid : null)
      : items[target].uid;
    showError = "";
    ws.send("move_item", {uid, after_uid: afterUid});
  }

  function moveMessage(step, message, direction) {
    const messages = step.messages || [];
    const index = messages.findIndex(candidate => candidate.uid === message.uid);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= messages.length) return;
    const afterUid = direction < 0
      ? (target > 0 ? messages[target - 1].uid : null)
      : messages[target].uid;
    showError = "";
    ws.send("move_message", {uid: message.uid, to_step_uid: step.uid, after_uid: afterUid});
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
    pendingMessageAdd = {step_uid: stepUid, known: new Set((step.messages || []).map(message => message.uid))};
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
    ws.send(kind === "divider" ? "add_divider" : "add_step", {after_uid: afterUid || null});
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
    if (event.target.closest("#show-stop-all")) {
      sendTransport("stop_all_steps");
      return;
    }
    if (event.target.closest("#show-load-button")) {
      const name = root.querySelector("#show-load-select")?.value;
      if (name) ws.send("load_show", {name});
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
      if (event.target.id === "show-forward-sync") updateStep(step.uid, {forward_sync: event.target.checked});
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
        const manifest = manifestFromStagedPatch();
        const declaration = manifest.params.find(param => param.identity === event.target.value) || {type: "f", default: 0};
        updateMessage(message.uid, {address: `/p/${event.target.value}`, args: [typedArg(declaration.type || "f", declaration.default ?? 0)]});
      }
      if (event.target.id === "show-param-value") {
        const manifest = manifestFromStagedPatch();
        const identity = message.address?.startsWith("/p/") ? message.address.slice(3) : "";
        const declaration = manifest.params.find(param => param.identity === identity) || {type: message.args?.[0]?.type || "f"};
        updateMessage(message.uid, {args: [typedArg(declaration.type || "f", event.target.value)]});
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
      if (event.target.matches("[data-message-move-step]")) {
        const destinationUid = event.target.value;
        const destination = stepByUid(destinationUid);
        if (destination) {
          const tail = (destination.messages || []).slice(-1)[0];
          showError = "";
          ws.send("move_message", {uid: message.uid, to_step_uid: destinationUid,
                                   after_uid: tail ? tail.uid : null});
        }
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
    const itemMove = event.target.closest("[data-item-move]");
    if (itemMove) {
      moveItem(itemMove.dataset.itemUid, Number(itemMove.dataset.itemMove));
      return;
    }
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
    const copyButton = event.target.closest("[data-message-copy]");
    if (copyButton) {
      const {message} = messageByUid(copyButton.dataset.messageCopy);
      if (message) copyMessage(message);
      return;
    }
    const cutButton = event.target.closest("[data-message-cut]");
    if (cutButton) {
      const {message} = messageByUid(cutButton.dataset.messageCut);
      if (message) {
        copyMessage(message);
        deleteMessage(message.uid);
      }
      return;
    }
    const pasteButton = event.target.closest("[data-paste-message]");
    if (pasteButton) {
      pasteMessage(pasteButton.dataset.pasteMessage);
      return;
    }
    const messageDelete = event.target.closest("[data-message-delete]");
    if (messageDelete) {
      deleteMessage(messageDelete.dataset.messageDelete);
      return;
    }
    const messageMove = event.target.closest("[data-message-move]");
    if (messageMove) {
      const {step, message} = messageByUid(messageMove.dataset.messageUid);
      if (message) moveMessage(step, message, Number(messageMove.dataset.messageMove));
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
        actions.splice(Number(event.target.dataset.removeThen), 1);
        updateStep(step.uid, {then_actions: actions});
      }
      if (event.target.id === "show-add-message") {
        pendingMessageAdd = {step_uid: step.uid, known: new Set((step.messages || []).map(message => message.uid))};
        ws.send("add_message", {step_uid: step.uid, message: {alias: null, address: "/p/gain", args: [{type: "f", value: 0}], target: ["all"]}});
      }
    }

    const messageEditor = event.target.closest("[data-show-message-editor]");
    if (messageEditor) {
      const {message} = messageByUid(messageEditor.dataset.showMessageEditor);
      if (!message) return;
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
    if (event.target.closest("input, select, textarea")) return;
    const pill = event.target.closest("[data-show-message-focus]");
    const row = event.target.closest("[data-show-step-row]");
    const divider = event.target.closest("[data-show-divider-row]");
    const meta = event.ctrlKey || event.metaKey;
    const key = event.key.toLowerCase();
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
    if (pendingMessageAdd) {
      const step = stepByUid(pendingMessageAdd.step_uid);
      const added = (step?.messages || []).find(message => !pendingMessageAdd.known.has(message.uid));
      if (added) {
        focus = {kind: "message", uid: added.uid};
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
    render();
    const hasTimedState = Object.values(playback.steps || {}).some(state => ["playing", "paused"].includes(state?.state) && Number.isFinite(Number(state.remaining_s)));
    if (hasTimedState && !countdownTimer) countdownTimer = setInterval(render, 500);
    if (!hasTimedState && countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
  });
  window.ShowInspectorError = message => {
    showError = message || "Show edit failed.";
    if (shows.current) render();
  };
  ws.on("error", data => {
    window.ShowInspectorError(data?.message);
  });

  render();
})();
