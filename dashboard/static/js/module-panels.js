(function () {
  const escape = value => String(value ?? "").replace(/[&<>"']/g,
    char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[char]));
  const HISTORY = 120;

  function displayValue(value) {
    if (typeof value !== "number" || !Number.isFinite(value) || Number.isInteger(value)) return String(value);
    // Pd's %g-style display; stored samples retain their original precision.
    const rounded = Number(value.toPrecision(6));
    const exponent = Math.floor(Math.log10(Math.abs(rounded)));
    return exponent < -4 || exponent >= 6 ? rounded.toExponential() : String(rounded);
  }

  function mount(root, open, captureChanged) {
    // Choices belong to this window/session. All panels use the dock's one
    // capture selection, hence one broker consumer and no additional socket.
    const panels = new Map();
    let painting = false;
    let connected = ws.socket.readyState === WebSocket.OPEN;
    let capturing = false;
    let refusal = "";
    let dropped = 0;
    const feedback = document.createElement("output");
    feedback.className = "module-panels-feedback";
    feedback.setAttribute("role", "status");
    const list = document.createElement("div");
    list.className = "module-panels";
    root.append(feedback, list);
    const key = (uid, name) => JSON.stringify([uid, name]);
    const deviceFor = uid => installation.devices?.[uid];
    const descriptionFor = (uid, name) => installation.io_types?.[
      deviceFor(uid)?.report?.io?.modules?.[name]?.type];

    function syncCheckboxes() {
      for (const input of document.querySelectorAll("#device-io [data-io-monitor]")) {
        input.checked = panels.has(key(selected, input.dataset.ioMonitor));
      }
    }

    function makePanel(uid, name) {
      const description = descriptionFor(uid, name);
      if (!description) return null;
      const element = document.createElement("section");
      element.className = "module-panel";
      element.dataset.moduleName = name;
      element.dataset.moduleUid = uid;
      element.innerHTML = `
        <div class="module-panel-header"><div><strong>${escape(name)}</strong>
          <small data-module-source></small></div>
          <button type="button" data-module-popout>Pop-out</button>
          <button type="button" data-module-close title="Close panel" aria-label="${escape(name)} · Show in Monitor">✕</button></div>
        <output class="module-panel-status" data-module-status aria-live="polite"></output>
        <div class="module-panel-inputs">${description.inputs.map((input, index) => `
          <div class="module-panel-input"><span>${escape(input.channel)}</span>
            <output data-module-value="${index}">— ${escape(input.unit)}</output>
            <svg class="module-panel-spark" viewBox="0 0 240 32" preserveAspectRatio="none"
                 role="img" aria-label="${escape(input.channel)} · ${escape(input.unit)}">
              <path data-module-spark="${index}"></path></svg></div>`).join("")}</div>
        ${description.inputs.length ? '<code class="module-panel-patch" data-module-patch>—</code>' : ''}
        <div class="module-panel-outputs">${description.outputs.map(output => `
          <form class="module-panel-command" data-module-command="${escape(output.command)}">
            <strong>${escape(output.command)}</strong>
            ${output.args.map(arg => `<label>${escape(arg)}<input data-module-arg
              type="text" autocomplete="off" ${arg.includes('optional') ? '' : 'required'}></label>`).join("")}
            <button type="submit">Send</button>
            <output data-module-receipt aria-live="polite"></output></form>`).join("")}</div>`;
      const panel = {uid, name, description, element, history: description.inputs.map(() => []),
        values: null, popup: null, writePending: false};
      element.querySelector("[data-module-close]").onclick = () => toggle(uid, name, false);
      element.querySelector("[data-module-popout]").onclick = () => popout(panel);
      for (const form of element.querySelectorAll("[data-module-command]")) {
        form.onsubmit = event => {
          event.preventDefault();
          if (installation.performance || !connected || !deviceFor(uid)?.online || panel.writePending) return;
          let args;
          try {
            args = [...form.querySelectorAll("[data-module-arg]")].flatMap((input, index) => {
              const label = description.outputs.find(row => row.command === form.dataset.moduleCommand).args[index];
              if (label.includes("text atoms")) return [input.value];
              return input.value.trim() ? OscMessage.parseLine(`/args ${input.value}`).args.map(arg => {
                if (arg.type === "s") throw new Error("invalid-arguments");
                return arg.value;
              }) : [];
            });
          } catch (_error) {
            form.querySelector("[data-module-receipt]").textContent = "invalid-arguments";
            return;
          }
          panel.receipt = deviceFor(uid)?.io_write;
          panel.writePending = true;
          form.querySelector("[data-module-receipt]").textContent = "pending";
          ws.send("io_write", {uid, config: {name, command: form.dataset.moduleCommand, args}});
          refresh();
        };
      }
      list.append(element);
      return panel;
    }

    function toggle(uid, name, enabled, reveal = true) {
      const id = key(uid, name);
      refusal = "";
      if (enabled) {
        // A second source cannot silently replace a device already being watched.
        if ([...panels.values()].some(panel => panel.uid !== uid)) {
          refusal = "another device already has stream consumers";
        } else if (!installation.performance && !panels.has(id)) {
          const panel = makePanel(uid, name);
          if (panel) panels.set(id, panel);
        }
        if (reveal) open();
      } else {
        const panel = panels.get(id);
        panel?.popup?.close();
        panel?.element.remove();
        panels.delete(id);
      }
      refresh();
      syncCheckboxes();
      captureChanged();
    }

    function refresh() {
      feedback.textContent = refusal || (dropped ? `⚠ ${dropped} matching messages dropped` : "");
      for (const panel of panels.values()) {
        const device = deviceFor(panel.uid);
        const module = device?.report?.io?.modules?.[panel.name];
        const available = connected && device?.online && module?.state === "running";
        panel.element.querySelector("[data-module-source]").textContent =
          `${Identity.primary(device || {uid: panel.uid}, installation)} · live`;
        const bridgeError = device?.io_error?.name === "bridge" ? device.io_error.error : null;
        const error = module?.error || device?.io_stream?.error || bridgeError;
        const status = panel.element.querySelector("[data-module-status]");
        status.textContent = installation.performance ? "Performance"
          : !connected || !device?.online ? "offline"
          : error ? `⚠ ${error}` : module?.state || "missing";
        status.classList.toggle("has-error", !!error && !installation.performance);
        const write = device?.io_write;
        if (write?.name === panel.name && write !== panel.receipt) {
          panel.receipt = write;
          panel.writePending = write.status === "pending";
          for (const form of panel.element.querySelectorAll("[data-module-command]")) {
            if (form.dataset.moduleCommand === write.command) {
              form.querySelector("[data-module-receipt]").textContent = write.error || write.phase || write.status;
            }
          }
        }
        for (const input of panel.element.querySelectorAll(".module-panel-command input, .module-panel-command button")) {
          input.disabled = installation.performance || !available || panel.writePending;
        }
      }
    }

    function selection(visible) {
      const active = visible && connected && !installation.performance
        ? [...panels.values()].filter(panel => !panel.popup && deviceFor(panel.uid)?.online
          && deviceFor(panel.uid)?.report?.io?.modules?.[panel.name]?.state === "running") : [];
      if (capturing && !active.length) {
        for (const panel of panels.values()) for (const history of panel.history) {
          history.push(null);
          if (history.length > HISTORY) history.shift();
        }
      }
      capturing = !!active.length;
      return active.length ? {uid: active[0].uid, names: active.map(panel => panel.name)} : null;
    }

    function paint() {
      painting = false;
      for (const panel of panels.values()) {
        if (!panel.values) continue;
        const output = panel.element.querySelector("[data-module-patch]");
        if (output) output.textContent = `/${panel.name} ${panel.values.map(displayValue).join(" ")}`;
        panel.description.inputs.forEach((input, index) => {
          const value = panel.values[index];
          panel.element.querySelector(`[data-module-value="${index}"]`).textContent =
            `${displayValue(value ?? "—")} ${input.unit}`;
          const history = panel.history[index];
          const [low, high] = input.range;
          let path = "", gap = true;
          history.forEach((sample, n) => {
            if (sample === null) { gap = true; return; }
            const y = 30 - Math.max(0, Math.min(1, (sample - low) / (high - low))) * 28;
            path += `${gap ? "M" : "L"}${n * 240 / Math.max(1, history.length - 1)},${y} `;
            gap = false;
          });
          panel.element.querySelector(`[data-module-spark="${index}"]`).setAttribute("d", path);
        });
      }
    }

    function popout(panel) {
      const dockCollapsed = document.querySelector("#monitor-dock").classList.contains("is-collapsed");
      const url = new URL(location.href);
      url.search = "";
      url.searchParams.set("monitor", panel ? "panel" : "dock");
      for (const item of panel ? [panel] : [...panels.values()].filter(item => !item.popup)) {
        url.searchParams.append("module", key(item.uid, item.name));
      }
      const popup = window.open(url.href, "_blank", "popup,width=1000,height=700");
      if (!popup) return;
      if (panel) {
        panel.popup = popup;
        panel.element.hidden = true;
      } else {
        window.MonitorDock.collapse();
      }
      captureChanged();
      const timer = setInterval(() => {
        if (!popup.closed) return;
        clearInterval(timer);
        if (panel) { panel.popup = null; panel.element.hidden = false; }
        else if (!dockCollapsed) window.MonitorDock.expand();
        captureChanged();
      }, 500);
    }

    // Install handlers before the dock makes its first complete selection.
    ws.on("io_samples", data => {
      if (!capturing) return;
      for (const [name, values] of Object.entries(data.values || {})) {
        const panel = panels.get(key(data.uid, name));
        if (!panel || panel.popup) continue;
        panel.values = values;
        panel.history.forEach((history, index) => {
          history.push(Number.isFinite(values[index]) ? values[index] : null);
          if (history.length > HISTORY) history.shift();
        });
      }
      // Every original poll is inspected and retained before coalescing paint.
      if (!painting) { painting = true; requestAnimationFrame(paint); }
    });
    ws.on("capture_counters", data => {
      dropped = data.modules?.dropped_since_subscribe || 0;
      if (dropped) {
        if (data.modules?.dropped_interval) {
          for (const panel of panels.values()) for (const history of panel.history) {
            history.push(null);
            if (history.length > HISTORY) history.shift();
          }
        }
      }
      feedback.textContent = refusal || (dropped ? `⚠ ${dropped} matching messages dropped` : "");
    });
    ws.on("capture_status", data => {
      refusal = data.error || "";
      if (!data.error) dropped = 0;
      refresh();
    });
    ws.on("error", data => {
      for (const panel of panels.values()) {
        if (!panel.writePending) continue;
        panel.writePending = false;
        for (const form of panel.element.querySelectorAll("[data-module-command]")) {
          if (form.querySelector("[data-module-receipt]").textContent === "pending") {
            form.querySelector("[data-module-receipt]").textContent = data.message;
          }
        }
      }
      refresh();
    });
    ws.on("connection", active => {
      connected = active;
      if (!active) for (const panel of panels.values()) {
        panel.writePending = false;
        panel.values = null;
        panel.history.forEach(history => history.splice(0));
        panel.element.querySelectorAll("[data-module-value], [data-module-patch]").forEach(output => output.textContent = "—");
        panel.element.querySelectorAll("[data-module-spark]").forEach(path => path.setAttribute("d", ""));
      }
      refresh();
      captureChanged();
    });
    for (const event of ["state", "device_update", "device_offline", "device_removed"]) {
      ws.on(event, () => { refresh(); captureChanged(); });
    }
    window.ModulesMonitor = {toggle, has: (uid, name) => panels.has(key(uid, name))};
    document.querySelector("[data-monitor-popout]").onclick = () => popout(null);
    return {selection};
  }

  window.ModulePanels = {mount};
})();
