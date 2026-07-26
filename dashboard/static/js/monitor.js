(function () {
  const STORAGE_KEY = "bopos.monitor.v1";
  const MONITOR_TABS = ["out", "in", "send", "reports", "system"];
  const CONSOLE_LIMIT = 500;
  const CONSOLE_VISIBLE = 200;
  const TRANSPORT_ERROR_LIMIT = 50;
  const DEFAULT_HEIGHT = 320;
  const MIN_HEIGHT = 180;

  function loadLayout() {
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      const right = Array.isArray(value.panes?.right)
        ? value.panes.right.filter(kind => MONITOR_TABS.includes(kind)) : [];
      const left = Array.isArray(value.panes?.left)
        ? value.panes.left.filter(kind => MONITOR_TABS.includes(kind)
          && !right.includes(kind)) : [];
      for (const kind of MONITOR_TABS) {
        if (!left.includes(kind) && !right.includes(kind)) left.push(kind);
      }
      return {
        collapsed: typeof value.collapsed === "boolean" ? value.collapsed : true,
        active: MONITOR_TABS.includes(value.active) ? value.active : "out",
        height: Number.isFinite(value.height) ? value.height : DEFAULT_HEIGHT,
        panes: {left: left.length ? left : [...right], right: left.length ? right : []},
        activeByPane: {
          left: left.includes(value.activeByPane?.left) ? value.activeByPane.left : left[0],
          right: right.includes(value.activeByPane?.right) ? value.activeByPane.right : right[0],
        },
        splitRatio: Number.isFinite(value.splitRatio)
          ? Math.max(30, Math.min(70, value.splitRatio)) : 50,
      };
    } catch (_error) {
      return {
        collapsed: true, active: "out", height: DEFAULT_HEIGHT,
        panes: {left: [...MONITOR_TABS], right: []},
        activeByPane: {left: "out", right: null}, splitRatio: 50,
      };
    }
  }

  const layout = loadLayout();
  const monitor = document.createElement("div");
  monitor.id = "monitor-dock";
  monitor.classList.toggle("is-collapsed", layout.collapsed);
  monitor.innerHTML = `
    <div class="monitor-resize" role="separator" aria-orientation="horizontal"
         aria-label="Resize Monitor" tabindex="0"></div>
    <div class="monitor-header">
      <strong class="monitor-title">Monitor</strong>
      <div class="monitor-tabs" role="tablist" aria-label="Monitor views">
        <button type="button" role="tab" data-monitor-tab="out"
                aria-controls="monitor-panel-out">Outgoing</button>
        <button type="button" role="tab" data-monitor-tab="in"
                aria-controls="monitor-panel-in">Incoming</button>
        <button type="button" role="tab" data-monitor-tab="send"
                aria-controls="monitor-panel-send">Send</button>
        <button type="button" role="tab" data-monitor-tab="reports"
                aria-controls="monitor-panel-reports">Reports</button>
        <button type="button" role="tab" data-monitor-tab="system"
                aria-controls="monitor-panel-system">System</button>
      </div>
      <button type="button" class="monitor-collapse" data-monitor-collapse
              aria-label="Expand Monitor"></button>
    </div>
    <div class="monitor-body">
      ${["out", "in"].map(kind => `
        <div id="monitor-panel-${kind}" class="monitor-panel" role="tabpanel"
             data-monitor-panel="${kind}" data-console="${kind}">
          <div class="monitor-console-bar">
            <input data-console-filter type="text" autocomplete="off" spellcheck="false"
                   placeholder="filter: /p/* !/sync"
                   aria-label="${kind === "out" ? "Outgoing" : "Incoming"} OSC filter">
            <button type="button" data-console-pause>Pause</button>
            <button type="button" data-console-clear>Clear</button>
          </div>
          <div class="monitor-console-log" data-console-log tabindex="0"></div>
        </div>`).join("")}
      <div id="monitor-panel-send" class="monitor-panel" role="tabpanel"
           data-monitor-panel="send">
        <form class="monitor-send-form" data-monitor-send-form>
          <label for="monitor-send-line">OSC message</label>
          <div class="monitor-send-row">
            <input id="monitor-send-line" data-monitor-send-line type="text"
                   autocomplete="off" spellcheck="false"
                   placeholder='/all/os/ping "hello"'>
            <button type="submit">Send</button>
          </div>
          <small>Types are inferred, or force them with i:, f:, s:. Quote strings containing spaces.</small>
          <output class="monitor-feedback" data-monitor-send-feedback
                  aria-live="polite"></output>
        </form>
      </div>
      <div id="monitor-panel-reports" class="monitor-panel" role="tabpanel"
           data-monitor-panel="reports">
        <form class="monitor-report-form" data-monitor-report-form>
          <label>Device
            <select data-monitor-report-device></select>
          </label>
          <label>Report name
            <input data-monitor-report-name type="text" autocomplete="off"
                   spellcheck="false" pattern="[A-Za-z0-9_-]+"
                   placeholder="level">
          </label>
          <button type="submit">Request</button>
          <output class="monitor-feedback" data-monitor-report-feedback
                  aria-live="polite"></output>
        </form>
        <p class="monitor-report-note">Patch values sent to
          <code>to-bopos-report</code> are retained in node memory as latest
          values only. Requests are one-shot; node restart clears them.</p>
        <div class="monitor-report-history" data-monitor-report-history
             aria-label="Report results"></div>
      </div>
      <div id="monitor-panel-system" class="monitor-panel" role="tabpanel"
           data-monitor-panel="system">
        <div class="monitor-system-grid">
          <section class="monitor-system-card">
            <h3>Connection</h3>
            <strong data-monitor-system="connection">disconnected</strong>
            <small>Dashboard WebSocket</small>
          </section>
          <section class="monitor-system-card">
            <h3>Execution</h3>
            <strong data-monitor-system="execution">Live Fleet</strong>
            <small data-monitor-system="mute">output safety unknown</small>
          </section>
          <section class="monitor-system-card">
            <h3>Fleet</h3>
            <strong data-monitor-system="fleet">0 / 0 online</strong>
            <small data-monitor-system="engines">0 engines alive</small>
          </section>
          <section class="monitor-system-card">
            <h3>Clock</h3>
            <strong data-monitor-system="clock">0 / 0 settled</strong>
            <small>at least three offset samples</small>
          </section>
          <section class="monitor-system-card">
            <h3>Show</h3>
            <strong data-monitor-system="show">none loaded</strong>
            <small>current persisted document</small>
          </section>
          <section class="monitor-system-card">
            <h3>Fleet patch</h3>
            <strong data-monitor-system="patch">not set</strong>
            <small data-monitor-system="fingerprint">no desired fingerprint</small>
          </section>
          <section class="monitor-system-card">
            <h3>bopOS</h3>
            <strong data-monitor-system="version">—</strong>
            <small>Dashboard host checkout</small>
          </section>
        </div>
        <section class="monitor-system-errors" data-monitor-transport-errors hidden>
          <div class="monitor-system-errors-head">
            <h3>Transport errors</h3>
            <small data-monitor-transport-error-count></small>
          </div>
          <div class="monitor-system-error-log" data-monitor-transport-error-log
               role="log" aria-live="polite" aria-label="OSC transport errors"></div>
        </section>
      </div>
    </div>`;
  document.querySelector(".tab-stage").after(monitor);
  document.body.classList.add("monitor-mounted");

  const headerTabs = monitor.querySelector(".monitor-tabs");
  const tabButtons = Object.fromEntries(
    [...monitor.querySelectorAll("[data-monitor-tab]")]
      .map(button => [button.dataset.monitorTab, button]));
  const panels = Object.fromEntries(
    [...monitor.querySelectorAll("[data-monitor-panel]")]
      .map(panel => [panel.dataset.monitorPanel, panel]));
  const monitorBody = monitor.querySelector(".monitor-body");
  monitorBody.replaceChildren();

  function createPane(name) {
    const pane = document.createElement("div");
    pane.className = `monitor-pane monitor-pane-${name}`;
    pane.dataset.monitorPane = name;
    pane.innerHTML = `
      <div class="monitor-pane-bar">
        <div class="monitor-pane-tabs" role="tablist"
             aria-label="${name === "left" ? "Left" : "Right"} Monitor pane"></div>
        <details class="monitor-tab-menu">
          <summary aria-label="Monitor tab layout actions">⋯</summary>
          <div class="monitor-tab-menu-items">
            <button type="button" data-monitor-move="left">Move active left</button>
            <button type="button" data-monitor-move="right">Move active right</button>
            <button type="button" data-monitor-move="single">Return to one pane</button>
          </div>
        </details>
      </div>
      <div class="monitor-pane-content"></div>`;
    return pane;
  }

  const leftPane = createPane("left");
  const splitResize = document.createElement("div");
  splitResize.className = "monitor-split-resize";
  splitResize.dataset.monitorSplitResize = "";
  splitResize.setAttribute("role", "separator");
  splitResize.setAttribute("aria-orientation", "vertical");
  splitResize.setAttribute("aria-label", "Resize Monitor split");
  splitResize.tabIndex = 0;
  const rightPane = createPane("right");
  monitorBody.append(leftPane, splitResize, rightPane);
  const paneElements = {left: leftPane, right: rightPane};

  const consoles = {
    out: {entries: [], paused: false, filter: "", autoScroll: true, dirty: false, total: 0},
    in: {entries: [], paused: false, filter: "", autoScroll: true, dirty: false, total: 0},
  };
  let consoleFlush = null;
  const sendHistory = [];
  let sendHistoryIndex = 0;
  let reportDevices = {};
  let systemConnected = false;
  const transportErrors = [];

  function maxHeight() {
    return Math.max(MIN_HEIGHT, Math.floor(window.innerHeight * .55));
  }

  function clampHeight(value) {
    return Math.max(MIN_HEIGHT, Math.min(maxHeight(), Math.round(value)));
  }

  function saveLayout() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
    } catch (_error) {}
  }

  function applyHeight(value, persist = true) {
    layout.height = clampHeight(value);
    monitor.style.setProperty("--monitor-height", `${layout.height}px`);
    document.body.style.setProperty(
      "--monitor-reserved-height", layout.collapsed ? "45px" : `${layout.height}px`);
    monitor.querySelector(".monitor-resize").setAttribute("aria-valuenow", layout.height);
    if (persist) saveLayout();
  }

  function isWide() {
    return monitor.clientWidth >= 1000;
  }

  function paneForKind(kind) {
    return layout.panes.right.includes(kind) ? "right" : "left";
  }

  function renderLayout() {
    const wide = isWide();
    const split = wide && layout.panes.right.length > 0;
    monitor.classList.toggle("monitor-wide", wide);
    monitor.classList.toggle("monitor-split", split);
    monitorBody.style.gridTemplateColumns = split
      ? `${layout.splitRatio}fr 7px ${100 - layout.splitRatio}fr`
      : "minmax(0,1fr) 0 0";
    rightPane.hidden = !split;
    splitResize.hidden = !split;

    if (layout.collapsed) {
      for (const kind of MONITOR_TABS) headerTabs.append(tabButtons[kind]);
    } else {
      headerTabs.replaceChildren();
    }

    const assignments = wide
      ? layout.panes
      : {left: [...MONITOR_TABS], right: []};
    for (const paneName of ["left", "right"]) {
      const pane = paneElements[paneName];
      const tabSlot = pane.querySelector(".monitor-pane-tabs");
      const content = pane.querySelector(".monitor-pane-content");
      const kinds = assignments[paneName];
      const active = wide
        ? (kinds.includes(layout.activeByPane[paneName])
          ? layout.activeByPane[paneName] : kinds[0])
        : layout.active;
      if (wide && active) layout.activeByPane[paneName] = active;
      if (!layout.collapsed) {
        for (const kind of kinds) tabSlot.append(tabButtons[kind]);
      }
      for (const kind of kinds) {
        content.append(panels[kind]);
        panels[kind].hidden = kind !== active;
        const button = tabButtons[kind];
        const selected = kind === active;
        button.setAttribute("aria-selected", selected ? "true" : "false");
        button.tabIndex = selected ? 0 : -1;
        button.draggable = wide && !layout.collapsed;
        button.title = wide
          ? "Drag to a Monitor pane; keyboard actions are in the ⋯ menu"
          : "";
      }
      for (const action of pane.querySelectorAll("[data-monitor-move]")) {
        action.disabled = !split && action.dataset.monitorMove !== "right";
      }
    }
    if (layout.collapsed) {
      for (const kind of MONITOR_TABS) {
        const selected = kind === layout.active;
        tabButtons[kind].setAttribute("aria-selected", selected ? "true" : "false");
        tabButtons[kind].tabIndex = selected ? 0 : -1;
        tabButtons[kind].draggable = false;
      }
    }
  }

  function setActive(kind, {expand = false, persist = true} = {}) {
    if (!MONITOR_TABS.includes(kind)) return;
    layout.active = kind;
    layout.activeByPane[paneForKind(kind)] = kind;
    if (expand) setCollapsed(false, false);
    renderLayout();
    if (persist) saveLayout();
  }

  function setCollapsed(collapsed, persist = true) {
    layout.collapsed = Boolean(collapsed);
    monitor.classList.toggle("is-collapsed", layout.collapsed);
    const button = monitor.querySelector("[data-monitor-collapse]");
    button.setAttribute("aria-expanded", layout.collapsed ? "false" : "true");
    button.setAttribute("aria-label", layout.collapsed ? "Expand Monitor" : "Collapse Monitor");
    button.textContent = layout.collapsed ? "⌃" : "⌄";
    document.body.style.setProperty(
      "--monitor-reserved-height", layout.collapsed ? "45px" : `${layout.height}px`);
    renderLayout();
    if (persist) saveLayout();
  }

  function moveTab(kind, target) {
    if (!MONITOR_TABS.includes(kind)) return;
    if (target === "single") {
      layout.panes.left = [...layout.panes.left, ...layout.panes.right]
        .filter((value, index, values) => values.indexOf(value) === index);
      layout.panes.right = [];
      layout.activeByPane.left = kind;
      layout.activeByPane.right = null;
    } else {
      layout.panes.left = layout.panes.left.filter(value => value !== kind);
      layout.panes.right = layout.panes.right.filter(value => value !== kind);
      layout.panes[target].push(kind);
      layout.activeByPane[target] = kind;
      if (!layout.panes.left.length) {
        layout.panes.left = [...layout.panes.right];
        layout.panes.right = [];
        layout.activeByPane.left = kind;
        layout.activeByPane.right = null;
      }
      if (!layout.panes.right.length) layout.activeByPane.right = null;
    }
    layout.active = kind;
    renderLayout();
    saveLayout();
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

  function consolePanel(kind) {
    return monitor.querySelector(`[data-console="${kind}"]`);
  }

  function renderConsole(kind) {
    const state = consoles[kind];
    const panel = consolePanel(kind);
    const log = panel.querySelector("[data-console-log]");
    let lines = state.entries.map(entry => entry.line);
    let terms;
    try {
      terms = filterTerms(state.filter);
    } catch (_error) {
      terms = [];
    }
    if (terms.length) {
      lines = lines.filter(line => {
        const lower = line.toLowerCase();
        return terms.every(term =>
          term.negated ? !term.pattern.test(lower) : term.pattern.test(lower));
      });
    }
    const visibleLines = lines.slice(-CONSOLE_VISIBLE);
    log.textContent = visibleLines.join("\n");
    if (state.autoScroll) log.scrollTop = log.scrollHeight;
    state.dirty = false;
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

  monitor.addEventListener("input", event => {
    const panel = event.target.closest("[data-console]");
    if (!panel || !event.target.matches("[data-console-filter]")) return;
    const state = consoles[panel.dataset.console];
    state.filter = event.target.value;
    renderConsole(panel.dataset.console);
  });

  monitor.addEventListener("click", event => {
    const tab = event.target.closest("[data-monitor-tab]");
    if (tab) {
      setActive(tab.dataset.monitorTab, {expand: true});
      return;
    }
    if (event.target.closest("[data-monitor-collapse]")) {
      setCollapsed(!layout.collapsed);
      return;
    }
    const move = event.target.closest("[data-monitor-move]");
    if (move) {
      const paneName = move.closest("[data-monitor-pane]").dataset.monitorPane;
      const kind = isWide()
        ? layout.activeByPane[paneName] : layout.active;
      moveTab(kind, move.dataset.monitorMove);
      move.closest("details").open = false;
      tabButtons[kind].focus();
      return;
    }
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

  monitor.addEventListener("keydown", event => {
    const tab = event.target.closest("[data-monitor-tab]");
    if (!tab) return;
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const pane = tab.closest("[data-monitor-pane]")?.dataset.monitorPane;
    const kinds = isWide() && pane ? layout.panes[pane] : MONITOR_TABS;
    let index = kinds.indexOf(tab.dataset.monitorTab);
    if (event.key === "ArrowLeft") index = (index - 1 + kinds.length) % kinds.length;
    if (event.key === "ArrowRight") index = (index + 1) % kinds.length;
    if (event.key === "Home") index = 0;
    if (event.key === "End") index = kinds.length - 1;
    setActive(kinds[index], {expand: true});
    monitor.querySelector(`[data-monitor-tab="${kinds[index]}"]`).focus();
  });

  monitor.addEventListener("dragstart", event => {
    const tab = event.target.closest("[data-monitor-tab]");
    if (!tab || !isWide() || layout.collapsed) {
      event.preventDefault();
      return;
    }
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/x-bopos-monitor-tab", tab.dataset.monitorTab);
    tab.classList.add("monitor-tab-dragging");
    monitor.classList.add("monitor-drag-active");
    if (!layout.panes.right.length) {
      rightPane.hidden = false;
      splitResize.hidden = true;
      monitorBody.style.gridTemplateColumns = "minmax(0,1fr) 0 minmax(0,1fr)";
    }
  });
  monitor.addEventListener("dragover", event => {
    const pane = event.target.closest("[data-monitor-pane]");
    if (!pane || !monitor.classList.contains("monitor-drag-active")) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    for (const candidate of monitor.querySelectorAll("[data-monitor-pane]")) {
      candidate.classList.toggle("monitor-drop-target", candidate === pane);
    }
  });
  monitor.addEventListener("drop", event => {
    const pane = event.target.closest("[data-monitor-pane]");
    if (!pane) return;
    event.preventDefault();
    const kind = event.dataTransfer.getData("text/x-bopos-monitor-tab");
    moveTab(kind, pane.dataset.monitorPane);
  });
  monitor.addEventListener("dragend", () => {
    monitor.classList.remove("monitor-drag-active");
    for (const element of monitor.querySelectorAll(
      ".monitor-tab-dragging,.monitor-drop-target")) {
      element.classList.remove("monitor-tab-dragging", "monitor-drop-target");
    }
    renderLayout();
  });

  monitor.addEventListener("scroll", event => {
    const log = event.target;
    if (!log.matches?.("[data-console-log]")) return;
    const panel = log.closest("[data-console]");
    consoles[panel.dataset.console].autoScroll =
      log.scrollTop + log.clientHeight >= log.scrollHeight - 24;
  }, true);

  const sendForm = panels.send.querySelector("[data-monitor-send-form]");
  const sendLine = panels.send.querySelector("[data-monitor-send-line]");
  const sendFeedback = panels.send.querySelector("[data-monitor-send-feedback]");
  sendForm.addEventListener("submit", event => {
    event.preventDefault();
    try {
      const message = window.OscMessage.parseLine(sendLine.value);
      const command = sendLine.value.trim();
      if (command && sendHistory.at(-1) !== command) sendHistory.push(command);
      sendHistoryIndex = sendHistory.length;
      ws.send("monitor_send", message);
      sendFeedback.textContent = "Sending…";
      sendFeedback.classList.remove("error");
    } catch (error) {
      sendFeedback.textContent = error.message;
      sendFeedback.classList.add("error");
    }
  });
  sendLine.addEventListener("keydown", event => {
    if (!["ArrowUp", "ArrowDown"].includes(event.key) || !sendHistory.length) return;
    event.preventDefault();
    sendHistoryIndex += event.key === "ArrowUp" ? -1 : 1;
    sendHistoryIndex = Math.max(0, Math.min(sendHistory.length, sendHistoryIndex));
    sendLine.value = sendHistoryIndex === sendHistory.length
      ? "" : sendHistory[sendHistoryIndex];
    sendLine.setSelectionRange(sendLine.value.length, sendLine.value.length);
  });
  ws.on("monitor_send_result", result => {
    sendFeedback.textContent = result?.ok ? "Sent." : result?.error || "Send failed.";
    sendFeedback.classList.toggle("error", !result?.ok);
  });

  const reportForm = panels.reports.querySelector("[data-monitor-report-form]");
  const reportDevice = panels.reports.querySelector("[data-monitor-report-device]");
  const reportName = panels.reports.querySelector("[data-monitor-report-name]");
  const reportFeedback = panels.reports.querySelector("[data-monitor-report-feedback]");
  const reportHistory = panels.reports.querySelector("[data-monitor-report-history]");

  function renderReportTargets(state) {
    reportDevices = state?.devices || reportDevices;
    const selected = reportDevice.value;
    reportDevice.replaceChildren();
    const devices = Object.values(reportDevices)
      .filter(device => !device.virtual)
      .sort((left, right) => Number(left.id ?? -1) - Number(right.id ?? -1)
        || String(left.alias || left.hostname || left.uid)
          .localeCompare(String(right.alias || right.hostname || right.uid)));
    if (!devices.length) {
      const option = new Option("No physical Devices", "");
      option.disabled = true;
      option.selected = true;
      reportDevice.add(option);
      return;
    }
    for (const device of devices) {
      const assigned = Number(device.id) >= 0;
      const online = Boolean(device.online);
      const name = device.alias || device.hostname || device.uid;
      const suffix = !assigned ? " · unassigned" : !online ? " · offline" : ` · Seat ${device.id}`;
      const option = new Option(`${name}${suffix}`, device.uid);
      option.disabled = !assigned || !online;
      reportDevice.add(option);
    }
    const restored = [...reportDevice.options].find(
      option => option.value === selected && !option.disabled);
    const first = [...reportDevice.options].find(option => !option.disabled);
    if (restored) restored.selected = true;
    else if (first) first.selected = true;
  }

  function appendReportResult(result) {
    const device = reportDevices[result?.uid] || {};
    const row = document.createElement("article");
    row.className = `monitor-report-result${result?.ok ? "" : " error"}`;
    const heading = document.createElement("strong");
    heading.textContent = `${result?.name || "report"} · ${
      device.alias || device.hostname || `Seat ${result?.id ?? "?"}`}`;
    const values = document.createElement("code");
    values.textContent = result?.ok
      ? (result.values || []).map(value => `${value.type}:${String(value.value)}`).join(" ")
        || "(empty)"
      : result?.error || "No value returned.";
    const time = document.createElement("time");
    const received = Number(result?.ts) * 1000;
    time.textContent = Number.isFinite(received)
      ? new Date(received).toLocaleTimeString("en-GB", {hour12: false}) : "";
    row.append(heading, values, time);
    reportHistory.prepend(row);
    while (reportHistory.children.length > 50) reportHistory.lastElementChild.remove();
  }

  reportForm.addEventListener("submit", event => {
    event.preventDefault();
    if (!reportForm.reportValidity()) return;
    const uid = reportDevice.value;
    const name = reportName.value.trim();
    if (!uid || !name) {
      reportFeedback.textContent = "Choose an assigned online Device and report name.";
      reportFeedback.classList.add("error");
      return;
    }
    reportFeedback.textContent = "Requesting…";
    reportFeedback.classList.remove("error");
    ws.send("monitor_probe", {uid, name});
  });
  ws.on("monitor_probe_status", result => {
    if (result?.ok) return;
    reportFeedback.textContent = result?.error || "Report request failed.";
    reportFeedback.classList.add("error");
  });
  ws.on("probe_result", result => {
    reportFeedback.textContent = result?.ok ? "Received." : result?.error || "No value returned.";
    reportFeedback.classList.toggle("error", !result?.ok);
    appendReportResult(result);
  });
  ws.on("state", renderReportTargets);
  ws.on("device_update", () => renderReportTargets({devices: installation.devices}));
  ws.on("device_offline", () => renderReportTargets({devices: installation.devices}));

  function systemText(name, value) {
    const target = panels.system.querySelector(`[data-monitor-system="${name}"]`);
    if (target) target.textContent = value;
  }

  function renderSystem(state = installation) {
    const devices = Object.values(state?.devices || {}).filter(device => !device.virtual);
    const online = devices.filter(device => device.online);
    const engines = online.filter(device => Number(device.engine_alive) === 1).length;
    const clocked = online.filter(device => Number(device.sync?.samples) >= 3).length;
    const mode = state?.supervisor?.mode || "off";
    const modeName = mode === "simulate" ? "Simulation"
      : mode === "edit" ? "Patch Edit" : "Live Fleet";
    const patch = state?.fleet_patch || {};
    systemText("connection", systemConnected ? "connected" : "disconnected");
    systemText("execution", modeName);
    systemText("mute", state?.muted ? "MUTE ALL active" : "output safety open");
    systemText("fleet", `${online.length} / ${devices.length} online`);
    systemText("engines", `${engines} engine${engines === 1 ? "" : "s"} alive`);
    systemText("clock", `${clocked} / ${online.length} settled`);
    systemText("show", state?.current_show || "none loaded");
    systemText("patch", patch.name || "not set");
    systemText("fingerprint", patch.fingerprint
      ? `fingerprint …${String(patch.fingerprint).slice(-8)}`
      : "no desired fingerprint");
    systemText("version", state?.host_version || "—");
  }

  function renderTransportErrors() {
    const section = panels.system.querySelector("[data-monitor-transport-errors]");
    const count = section.querySelector("[data-monitor-transport-error-count]");
    const output = section.querySelector("[data-monitor-transport-error-log]");
    section.hidden = transportErrors.length === 0;
    count.textContent = `${transportErrors.length} recent`;
    output.textContent = transportErrors.map(entry => {
      const date = new Date(Number(entry.ts || 0) * 1000);
      const stamp = date.toLocaleTimeString("en-GB", {hour12: false})
        + "." + String(date.getMilliseconds()).padStart(3, "0");
      const destination = `${entry.destination || "?"}:${entry.port || "?"}`;
      const errorName = entry.errno == null ? "error" : `errno ${entry.errno}`;
      return `${stamp}  ${entry.address || "OSC send"}  -> ${destination}  `
        + `${errorName}: ${entry.message || "send failed"}`;
    }).join("\n");
    output.scrollTop = output.scrollHeight;
  }

  ws.on("connection", connected => {
    systemConnected = Boolean(connected);
    renderSystem();
  });
  ws.on("state", renderSystem);
  ws.on("osc_transport_error", data => {
    transportErrors.push(data || {});
    if (transportErrors.length > TRANSPORT_ERROR_LIMIT) transportErrors.shift();
    renderTransportErrors();
  });
  for (const event of ["device_update", "device_offline", "heartbeat", "report",
                       "distribution", "show", "show_playback"]) {
    ws.on(event, () => renderSystem());
  }

  const resize = monitor.querySelector(".monitor-resize");
  resize.addEventListener("pointerdown", event => {
    if (layout.collapsed) return;
    event.preventDefault();
    const startY = event.clientY;
    const startHeight = layout.height;
    resize.setPointerCapture(event.pointerId);
    const move = moveEvent => applyHeight(startHeight + startY - moveEvent.clientY, false);
    const finish = finishEvent => {
      resize.removeEventListener("pointermove", move);
      resize.removeEventListener("pointerup", finish);
      resize.removeEventListener("pointercancel", finish);
      if (resize.hasPointerCapture(finishEvent.pointerId)) {
        resize.releasePointerCapture(finishEvent.pointerId);
      }
      saveLayout();
    };
    resize.addEventListener("pointermove", move);
    resize.addEventListener("pointerup", finish);
    resize.addEventListener("pointercancel", finish);
  });
  resize.addEventListener("keydown", event => {
    if (!["ArrowUp", "ArrowDown"].includes(event.key) || layout.collapsed) return;
    event.preventDefault();
    applyHeight(layout.height + (event.key === "ArrowUp" ? 20 : -20));
  });
  splitResize.addEventListener("pointerdown", event => {
    if (!monitor.classList.contains("monitor-split")) return;
    event.preventDefault();
    const startX = event.clientX;
    const startRatio = layout.splitRatio;
    const width = monitorBody.getBoundingClientRect().width;
    splitResize.setPointerCapture(event.pointerId);
    const move = moveEvent => {
      layout.splitRatio = Math.max(
        30, Math.min(70, startRatio + ((moveEvent.clientX - startX) / width) * 100));
      renderLayout();
    };
    const finish = finishEvent => {
      splitResize.removeEventListener("pointermove", move);
      splitResize.removeEventListener("pointerup", finish);
      splitResize.removeEventListener("pointercancel", finish);
      if (splitResize.hasPointerCapture(finishEvent.pointerId)) {
        splitResize.releasePointerCapture(finishEvent.pointerId);
      }
      saveLayout();
    };
    splitResize.addEventListener("pointermove", move);
    splitResize.addEventListener("pointerup", finish);
    splitResize.addEventListener("pointercancel", finish);
  });
  splitResize.addEventListener("keydown", event => {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)
        || !monitor.classList.contains("monitor-split")) return;
    event.preventDefault();
    layout.splitRatio = Math.max(
      30, Math.min(70, layout.splitRatio + (event.key === "ArrowRight" ? 5 : -5)));
    renderLayout();
    saveLayout();
  });
  new ResizeObserver(() => renderLayout()).observe(monitor);
  window.addEventListener("resize", () => applyHeight(layout.height, false));

  applyHeight(layout.height, false);
  setCollapsed(layout.collapsed, false);
  setActive(layout.active, {persist: false});
  for (const kind of ["out", "in"]) renderConsole(kind);
  ws.on("osc_out", data => pushConsole("out", data));
  ws.on("osc_in", data => pushConsole("in", data));
})();
