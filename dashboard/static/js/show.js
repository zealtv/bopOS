(function () {
  const root = document.querySelector("#show-root");
  if (!root || typeof ws === "undefined") return;

  let shows = {names: [], current: null};
  let show = {schema: 1, name: "", items: []};
  let playback = {steps: {}};
  let playbackAt = performance.now();
  let focus = {kind: null, uid: null};
  let countdownTimer = null;

  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, c => (
    {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]
  ));

  function stepByUid(uid) {
    return (show.items || []).find(item => item.kind === "step" && item.uid === uid) || null;
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

  function formatDuration(seconds) {
    seconds = Math.max(0, Math.round(Number(seconds) || 0));
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    const parts = [];
    if (hours) parts.push(`${hours}h`);
    if (minutes || hours) parts.push(`${minutes}m`);
    parts.push(`${secs}s`);
    return parts.join(" ");
  }

  function playCountSummary(value) {
    return value == null ? "loop" : `${Number(value) || 1}x`;
  }

  function thenSummary(actions) {
    if (!Array.isArray(actions) || !actions.length) return "stop";
    return actions.map(action => {
      const type = action?.type || "stop";
      if (type === "goto") {
        const target = stepByUid(action.target_uid);
        return `goto ${target ? stepLabel(target) : action.target_uid || "missing"}`;
      }
      return type.replaceAll("_", " ");
    }).join(" / ");
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

  function transportLabel(uid) {
    const state = playbackState(uid);
    if (state.state === "playing") return "Stop";
    if (state.state === "paused") return "Resume";
    return "Play";
  }

  function primaryTransportVerb(uid) {
    const state = playbackState(uid);
    if (state.state === "playing") return "step_stop";
    if (state.state === "paused") return "step_resume";
    return "step_start";
  }

  function stepTransport(step) {
    const state = playbackState(step.uid).state;
    const uid = escapeHtml(step.uid);
    const primary = `<button class="show-state-button show-state-${escapeHtml(state)}" data-show-action="${primaryTransportVerb(step.uid)}" data-show-uid="${uid}" title="${transportLabel(step.uid)} ${escapeHtml(stepLabel(step))}"><span class="show-control-icon" aria-hidden="true"></span><span>${transportLabel(step.uid)}</span></button>`;
    if (state === "playing") {
      return `${primary}<button class="show-mini-button" data-show-action="step_pause" data-show-uid="${uid}">Pause</button><button class="show-mini-button" data-show-action="step_trigger_next" data-show-uid="${uid}">Next</button>`;
    }
    if (state === "paused") {
      return `${primary}<button class="show-mini-button" data-show-action="step_stop" data-show-uid="${uid}">Stop</button>`;
    }
    return primary;
  }

  function messagePills(step) {
    const messages = step.messages || [];
    if (!messages.length) return '<span class="show-no-messages">No messages</span>';
    return messages.map(message => {
      const selected = focused("message", message.uid) ? " focused" : "";
      const title = `${message.address || ""} -> ${message.target || "all"}`;
      return `<button class="show-message-pill${selected}" data-show-message-focus="${escapeHtml(message.uid)}" data-show-step="${escapeHtml(step.uid)}" title="${escapeHtml(title)}">${escapeHtml(messageLabel(message))}</button>`;
    }).join("");
  }

  function dividerRow(item, index) {
    return `<div class="show-divider-row" data-show-item="${escapeHtml(item.uid)}" data-show-index="${index}" role="separator" aria-label="Section divider"></div>`;
  }

  function stepRow(step, index) {
    const state = playbackState(step.uid);
    const remaining = remainingSeconds(step.uid);
    const stateName = state.state || "stopped";
    const selected = focused("step", step.uid) ? " focused" : "";
    const playing = stateName === "playing" || stateName === "paused" ? " active" : "";
    const remainingText = remaining == null ? "" : `<span class="show-remaining">${stateName === "paused" ? "paused" : "remaining"} ${formatDuration(remaining)}</span>`;
    const iteration = Number(state.iteration) > 0 ? `<span>iteration ${Number(state.iteration)}</span>` : "";
    return `<div class="show-step-row show-step-${escapeHtml(stateName)}${selected}${playing}" data-show-step-row="${escapeHtml(step.uid)}" data-show-index="${index}" role="row" tabindex="0">
      <div class="show-step-transport">${stepTransport(step)}</div>
      <div class="show-step-main">
        <div class="show-step-title"><strong>${escapeHtml(stepLabel(step))}</strong><small>${escapeHtml(stateName)}</small></div>
        <div class="show-message-pills">${messagePills(step)}</div>
      </div>
      <div class="show-step-facts">
        <span>${formatDuration(step.duration_s)} / ${playCountSummary(step.play_count)}</span>
        ${iteration}
        ${remainingText}
      </div>
      <div class="show-step-then">${escapeHtml(thenSummary(step.then_actions))}</div>
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
      <div class="show-rows" role="table" aria-label="Show steps">${rows || '<p class="empty">This show has no steps yet.</p>'}</div>
      <aside class="show-inspector-shell" aria-label="Show inspector"><h3>Inspector</h3><p class="dim">Select a step or message.</p></aside>
    </div>`;
  }

  function render() {
    if (!shows.current) renderEmptyState();
    else renderLoadedShow();
  }

  function sendTransport(type, uid) {
    if (type === "stop_all_steps") ws.send(type, {});
    else if (uid) ws.send(type, {uid});
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
    const row = event.target.closest("[data-show-step-row]");
    if (row) setFocus("step", row.dataset.showStepRow);
  });

  root.addEventListener("keydown", event => {
    const row = event.target.closest("[data-show-step-row]");
    if (!row || !["Enter", " "].includes(event.key)) return;
    event.preventDefault();
    setFocus("step", row.dataset.showStepRow);
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
    const validFocus = focus.kind === "step"
      ? stepByUid(focus.uid)
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

  render();
})();
