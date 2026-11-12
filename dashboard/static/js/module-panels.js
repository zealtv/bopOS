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

  // Browser key codes to the kernel names the bridge sends (84-key-input).
  // Number-row keys keep the key_ prefix; codes not listed are not sent.
  const KEY_NAMES = {Space: "space", Enter: "enter", Escape: "esc", Backspace: "backspace",
    ShiftLeft: "leftshift", ShiftRight: "rightshift", ControlLeft: "leftctrl", ControlRight: "rightctrl",
    AltLeft: "leftalt", AltRight: "rightalt", MetaLeft: "leftmeta", MetaRight: "rightmeta",
    Minus: "minus", Equal: "equal", BracketLeft: "leftbrace", BracketRight: "rightbrace",
    Semicolon: "semicolon", Quote: "apostrophe", Backquote: "grave", Backslash: "backslash",
    Comma: "comma", Period: "dot", Slash: "slash", CapsLock: "capslock", Home: "home", End: "end",
    PageUp: "pageup", PageDown: "pagedown", Insert: "insert", Delete: "delete",
    NumpadEnter: "kpenter", NumpadAdd: "kpplus", NumpadSubtract: "kpminus",
    NumpadMultiply: "kpasterisk", NumpadDivide: "kpslash", NumpadDecimal: "kpdot"};
  function keyName(code) {
    let match;
    if ((match = /^Key([A-Z])$/.exec(code))) return match[1].toLowerCase();
    if ((match = /^Digit(\d)$/.exec(code))) return `key_${match[1]}`;
    if ((match = /^Numpad(\d)$/.exec(code))) return `kp${match[1]}`;
    if ((match = /^F(\d|1[0-2])$/.exec(code))) return `f${match[1]}`;
    if ((match = /^Arrow(Up|Down|Left|Right)$/.exec(code))) return match[1].toLowerCase();
    return KEY_NAMES[code] || null;
  }
  // A Makey Makey's default keys, front then back.
  const MAKEY_KEYS = ["up", "down", "left", "right", "space", "w", "a", "s", "d", "f", "g"];

  function mount(root, open, captureChanged) {
    // Choices belong to this window/session. All panels use the dock's one
    // capture selection, hence one broker consumer and no additional socket.
    const panels = new Map();
    let painting = false;
    let connected = ws.socket.readyState === WebSocket.OPEN;
    let capturing = false;
    let refusal = "";
    let dropped = 0;
    let editorSession = null;
    let inputPending = false;
    const isPopup = new URLSearchParams(location.search).has("monitor");
    const picker = document.querySelector("#editor-input-source");
    const feedback = document.createElement("output");
    feedback.className = "module-panels-feedback";
    feedback.setAttribute("role", "status");
    const list = document.createElement("div");
    list.className = "module-panels";
    root.append(feedback, list);
    const key = (uid, name) => JSON.stringify([uid, name]);
    const deviceFor = uid => installation.devices?.[uid];
    const descriptionFor = (uid, name) => installation.io_types?.[uid === "simulated"
      ? installation.editor?.io_modules?.find(row => row.name === name)?.type
      : deviceFor(uid)?.report?.io?.modules?.[name]?.type];

    function drive(panel, index, value, rest = null) {
      // Inert until a fresh editor_io sample restores this session's values.
      if (!panel.ready) return;
      panel.values[index] = value;
      ws.send("set_editor_input_value", {generation: installation.editor.generation,
        name: panel.name, index, value, rest});
      paint();
    }

    function syncCheckboxes() {
      for (const input of document.querySelectorAll("#device-io [data-io-monitor]")) {
        input.checked = panels.has(key(selected, input.dataset.ioMonitor));
      }
    }

    function makePanel(uid, name) {
      const description = descriptionFor(uid, name);
      if (!description) return null;
      const simulated = uid === "simulated";
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
              <path data-module-spark="${index}"></path></svg>
            ${simulated ? `<div class="module-panel-drive"><input type="range" data-module-slider="${index}"
              aria-label="${escape(input.channel)} · ${escape(input.unit)}" min="${input.range[0]}"
              max="${input.range[1]}" step="any"><button type="button" data-module-pad="${index}"
              aria-label="${escape(input.channel)}" aria-pressed="false">${escape(input.channel)}</button></div>` : ''}</div>`).join("")}</div>
        ${description.inputs.length ? '<code class="module-panel-patch" data-module-patch>—</code>' : ''}
        <div class="module-panel-outputs">${description.outputs.map(output => `
          ${simulated ? `<div class="module-panel-command"><strong>${escape(output.command)}</strong>
            <output data-module-written="${escape(output.command)}">—</output></div>` : `<form class="module-panel-command" data-module-command="${escape(output.command)}">
            <strong>${escape(output.command)}</strong>
            ${output.args.map(arg => `<label>${escape(arg)}<input data-module-arg
              type="text" autocomplete="off" ${arg.includes('optional') ? '' : 'required'}></label>`).join("")}
            <button type="submit">Send</button>
            <output data-module-receipt aria-live="polite"></output></form>`}`).join("")}</div>`;
      const panel = {uid, name, description, element, history: description.inputs.map(() => []),
        values: simulated ? [...(installation.editor?.input?.values?.[name] || description.inputs.map(() => 0))] : null,
        popup: null, writePending: false, simulated, ready: false, held: new Map()};
      if (simulated && installation.editor.io_modules.find(row => row.name === name)?.type === "ssd1306") {
        const preview = document.createElement("pre");
        preview.className = "module-panel-oled";
        preview.setAttribute("data-module-oled", "");
        element.querySelector(".module-panel-outputs").prepend(preview);
      }
      for (const slider of element.querySelectorAll("[data-module-slider]")) {
        const index = Number(slider.dataset.moduleSlider);
        slider.value = panel.values[index];
        slider.oninput = () => drive(panel, index, Number(slider.value));
      }
      for (const pad of element.querySelectorAll("[data-module-pad]")) {
        const index = Number(pad.dataset.modulePad);
        const press = () => {
          if (pad.disabled || panel.held.has(index)) return;
          const [low, high] = description.inputs[index].range;
          const rest = Number(element.querySelector(`[data-module-slider="${index}"]`).value);
          panel.held.set(index, rest);
          pad.setAttribute("aria-pressed", "true");
          drive(panel, index, rest > (low + high) / 2 ? low : high, rest);
        };
        const release = () => {
          if (!panel.held.has(index)) return;
          const rest = panel.held.get(index);
          panel.held.delete(index);
          pad.setAttribute("aria-pressed", "false");
          drive(panel, index, rest);
        };
        pad.onpointerdown = event => { event.preventDefault(); pad.setPointerCapture(event.pointerId); press(); };
        pad.onpointerup = pad.onpointercancel = pad.onlostpointercapture = release;
        pad.onkeydown = event => { if ([" ", "Enter"].includes(event.key)) { event.preventDefault(); press(); } };
        pad.onkeyup = event => { if ([" ", "Enter"].includes(event.key)) { event.preventDefault(); release(); } };
        pad.onblur = release;
      }
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
        if (uid !== "simulated" && [...panels.values()].some(panel => !panel.simulated && panel.uid !== uid)) {
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
        panel.element.hidden = !!panel.popup || (!panel.simulated && installation.editor?.input?.source === "simulated");
        panel.element.querySelector("[data-module-source]").textContent =
          panel.simulated ? "simulated" : `${Identity.primary(device || {uid: panel.uid}, installation)} · live`;
        const bridgeError = device?.io_error?.name === "bridge" ? device.io_error.error : null;
        const error = module?.error || device?.io_stream?.error || bridgeError;
        const status = panel.element.querySelector("[data-module-status]");
        status.textContent = installation.performance ? "Performance"
          : !connected || !device?.online ? "offline"
          : error ? `⚠ ${error}` : module?.state || "missing";
        if (panel.simulated && connected && !installation.performance) status.textContent = "";
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
        for (const input of panel.element.querySelectorAll("[data-module-slider], [data-module-pad]")) {
          input.disabled = !connected || installation.performance || !panel.ready;
        }
      }
    }

    function selection(visible) {
      const active = visible && connected && !installation.performance
        ? [...panels.values()].filter(panel => !panel.element.hidden && (panel.simulated
          ? installation.editor?.input?.source === "simulated"
          : deviceFor(panel.uid)?.online && deviceFor(panel.uid)?.report?.io?.modules?.[panel.name]?.state === "running")) : [];
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

    // Simulated keys and pointer: events, not polled values, so they skip the
    // driver-description panels and go out one message per press or move.
    let inputPanel = null;

    function sendInput(address, args) {
      if (!inputPanel || !connected || installation.performance) return;
      ws.send("send_editor_input", {generation: installation.editor.generation, address, args});
      inputPanel.element.querySelector("[data-input-sent]").textContent =
        `/io/${address} ${args.map(displayValue).join(" ")}`;
    }

    function pressInput(address, label, down) {
      if (!inputPanel) return;
      const id = `${address} ${label}`;
      if (down === inputPanel.held.has(id)) return;
      if (down) inputPanel.held.add(id); else inputPanel.held.delete(id);
      for (const pad of inputPanel.element.querySelectorAll(`[data-input-pad="${CSS.escape(id)}"]`)) {
        pad.setAttribute("aria-pressed", String(down));
      }
      sendInput(address, [label, down ? 1 : 0]);
    }

    function releaseInputs() {
      if (!inputPanel) return;
      for (const id of [...inputPanel.held]) pressInput(...id.split(" "), false);
    }

    function makeInputPanel() {
      const element = document.createElement("section");
      element.className = "module-panel input-panel";
      element.dataset.inputPanel = "";
      const pad = (address, label, text = label) => `<button type="button" data-input-pad="${address} ${label}"
        aria-pressed="false">${escape(text)}</button>`;
      element.innerHTML = `
        <div class="module-panel-header"><div><strong>key · mouse</strong>
          <small data-module-source>simulated</small></div></div>
        <div class="input-panel-keys" role="group" aria-label="Keys">${MAKEY_KEYS.map(label => pad("key", label)).join("")}</div>
        <label class="input-panel-type">Type keys<input type="text" readonly data-input-type
          placeholder="Focus here and type" autocomplete="off"></label>
        <div class="input-panel-mouse">
          <div class="input-panel-xy" data-input-xy tabindex="0" role="application"><span data-input-dot></span></div>
          <div class="input-panel-buttons" role="group" aria-label="Mouse">
            ${pad("mouse", "left", "left click")}${pad("mouse", "right", "right click")}
            <button type="button" data-input-wheel="1">wheel ↑</button>
            <button type="button" data-input-wheel="-1">wheel ↓</button></div></div>
        <code class="module-panel-patch" data-input-sent>—</code>`;
      const panel = {element, held: new Set(), x: .5, y: .5};
      for (const button of element.querySelectorAll("[data-input-pad]")) {
        const [address, label] = button.dataset.inputPad.split(" ");
        const down = () => pressInput(address, label, true), up = () => pressInput(address, label, false);
        button.onpointerdown = event => { event.preventDefault(); button.setPointerCapture(event.pointerId); down(); };
        button.onpointerup = button.onpointercancel = button.onlostpointercapture = up;
        button.onkeydown = event => { if ([" ", "Enter"].includes(event.key) && !event.repeat) { event.preventDefault(); down(); } };
        button.onkeyup = event => { if ([" ", "Enter"].includes(event.key)) { event.preventDefault(); up(); } };
        button.onblur = up;
      }
      for (const button of element.querySelectorAll("[data-input-wheel]")) {
        button.onclick = () => sendInput("mouse", ["wheel", Number(button.dataset.inputWheel)]);
      }
      const typing = element.querySelector("[data-input-type]");
      typing.onkeydown = event => {
        const label = keyName(event.code);
        // Tab stays a way out of the field.
        if (!label || event.code === "Tab") return;
        event.preventDefault();
        if (!event.repeat) pressInput("key", label, true);
      };
      typing.onkeyup = event => {
        const label = keyName(event.code);
        if (!label || event.code === "Tab") return;
        event.preventDefault();
        pressInput("key", label, false);
      };
      typing.onblur = releaseInputs;
      const surface = element.querySelector("[data-input-xy]");
      const place = () => {
        const dot = surface.querySelector("[data-input-dot]");
        dot.style.left = `${panel.x * 100}%`;
        dot.style.top = `${panel.y * 100}%`;
        surface.setAttribute("aria-label",
          `Pointer position x ${panel.x.toFixed(2)}, y ${panel.y.toFixed(2)}; drag, or use arrow keys`);
      };
      const moveTo = (x, y) => {
        panel.x = Math.max(0, Math.min(1, x));
        panel.y = Math.max(0, Math.min(1, y));
        place();
        sendInput("mouse", ["xy", panel.x, panel.y]);
      };
      const fromPointer = event => {
        const box = surface.getBoundingClientRect();
        moveTo((event.clientX - box.left) / box.width, (event.clientY - box.top) / box.height);
      };
      surface.onpointerdown = event => { event.preventDefault(); surface.setPointerCapture(event.pointerId); surface.focus(); fromPointer(event); };
      surface.onpointermove = event => { if (surface.hasPointerCapture(event.pointerId)) fromPointer(event); };
      surface.onkeydown = event => {
        const step = event.shiftKey ? .1 : .02;
        const delta = {ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step]}[event.key];
        if (!delta) return;
        event.preventDefault();
        moveTo(panel.x + delta[0], panel.y + delta[1]);
      };
      place();
      list.prepend(element);
      return panel;
    }

    function syncInputPanel(wanted) {
      if (wanted && !inputPanel) inputPanel = makeInputPanel();
      if (!wanted && inputPanel) {
        releaseInputs();
        inputPanel.element.remove();
        inputPanel = null;
      }
      if (inputPanel) {
        const disabled = !connected || installation.performance;
        for (const control of inputPanel.element.querySelectorAll("button, input, [data-input-xy]")) {
          if (control.matches("[data-input-xy]")) control.setAttribute("aria-disabled", String(disabled));
          else control.disabled = disabled;
        }
        inputPanel.element.classList.toggle("is-disabled", disabled);
      }
    }

    function syncEditor() {
      const editor = installation.editor || {};
      const source = editor.input?.source || "";
      const live = source === "simulated" ? []
        : Object.entries(deviceFor(source)?.report?.io?.modules || {}).map(([name, module]) => [name, module.type]);
      const session = JSON.stringify([editor.generation, source, editor.io_modules || [], live]);
      const control = document.querySelector("#editor-input-control");
      if (control) control.hidden = !editor.active || installation.performance;
      if (picker) {
        const choices = [new Option("—", ""), new Option("simulated", "simulated")];
        for (const device of Object.values(installation.devices || {}).filter(device => !device.virtual)) {
          const option = new Option(`${Identity.primary(device, installation)} · live`, device.uid);
          option.disabled = !device.online;
          choices.push(option);
        }
        picker.replaceChildren(...choices);
        picker.value = source;
        picker.disabled = !connected || installation.performance;
      }
      syncInputPanel(!isPopup && editor.active && source === "simulated");
      if (session === editorSession) return;
      editorSession = session;
      // A new session starts with a fresh panel, like the simulated modules.
      syncInputPanel(false);
      syncInputPanel(!isPopup && editor.active && source === "simulated");
      for (const [id, panel] of panels) {
        if (!panel.simulated && !panel.editorOwned) continue;
        panel.popup?.close();
        panel.element.remove();
        panels.delete(id);
      }
      if (!isPopup && editor.active && source) {
        const names = source === "simulated" ? (editor.io_modules || []).map(row => row.name)
          : Object.keys(deviceFor(source)?.report?.io?.modules || {});
        for (const name of names) {
          const id = key(source, name);
          if (panels.has(id)) continue;
          const panel = makePanel(source, name);
          if (panel) { panel.editorOwned = true; panels.set(id, panel); }
        }
        open();
      }
      refresh();
      syncCheckboxes();
      paint();
    }

    if (picker) picker.onchange = () => {
      inputPending = true;
      refusal = "";
      // Release this editor's visual consumer before changing its device.
      // Independently opened panels still hold their own source interest.
      for (const [id, panel] of panels) {
        if (!panel.editorOwned) continue;
        panel.popup?.close();
        panel.element.remove();
        panels.delete(id);
      }
      editorSession = null;
      captureChanged();
      ws.send("set_editor_input", {source: picker.value || null});
    };
    window.addEventListener("blur", () => {
      releaseInputs();
      for (const panel of panels.values()) for (const [index, rest] of panel.held) {
        drive(panel, index, rest);
        panel.element.querySelector(`[data-module-pad="${index}"]`).setAttribute("aria-pressed", "false");
      }
      for (const panel of panels.values()) panel.held.clear();
    });
    ws.on("editor_io", data => {
      if (data.generation !== installation.editor?.generation || installation.editor?.input?.source !== "simulated") return;
      for (const panel of panels.values()) {
        if (!panel.simulated) continue;
        panel.ready = true;
        panel.values = data.values[panel.name] || panel.values;
        for (const output of panel.element.querySelectorAll("[data-module-written]")) {
          const values = data.outputs[panel.name]?.[output.dataset.moduleWritten];
          output.textContent = values ? values.map(displayValue).join(" ") || "✓" : "—";
        }
        const preview = panel.element.querySelector("[data-module-oled]");
        const screen = data.outputs[panel.name]?.preview;
        if (preview && screen) {
          preview.textContent = screen.lines.join("\n");
          preview.classList.toggle("is-inverted", screen.invert);
          preview.style.opacity = .2 + .8 * screen.contrast / 255;
        }
        panel.description.inputs.forEach((_input, index) => {
          const slider = panel.element.querySelector(`[data-module-slider="${index}"]`);
          if (!panel.held.has(index) && document.activeElement !== slider) slider.value = panel.values[index];
          panel.history[index].push(panel.values[index]);
          if (panel.history[index].length > HISTORY) panel.history[index].shift();
        });
      }
      refresh();
      if (!painting) { painting = true; requestAnimationFrame(paint); }
    });

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
      if (inputPending) { refusal = data.message; inputPending = false; }
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
        panel.ready = false;
        panel.values = null;
        panel.history.forEach(history => history.splice(0));
        panel.element.querySelectorAll("[data-module-value], [data-module-patch]").forEach(output => output.textContent = "—");
        panel.element.querySelectorAll("[data-module-spark]").forEach(path => path.setAttribute("d", ""));
      }
      refresh();
      syncEditor();
      captureChanged();
    });
    for (const event of ["state", "device_update", "report", "device_offline", "device_removed"]) {
      ws.on(event, () => { syncEditor(); refresh(); captureChanged(); if (event === "state") inputPending = false; });
    }
    window.ModulesMonitor = {toggle, has: (uid, name) => panels.has(key(uid, name))};
    document.querySelector("[data-monitor-popout]").onclick = () => popout(null);
    return {selection};
  }

  window.ModulePanels = {mount};
})();
