// One independently targetable Control surface column.
//
// The facilitator page owns fleet state, its websocket, and page furniture.
// This component owns the state that must not leak between columns: its target
// picker, ControlSurface instance, cards, preset previews/reports, and open
// per-device command disclosures.
(function () {
  "use strict";

  const esc = value => String(value ?? "—").replace(
    /[&<>"']/g,
    character => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"}[character]),
  );
  const destructiveCommands = new Set(["updatebopos", "reboot", "shutdown"]);

  function create({
    host,
    id = "control",
    storageKey = "bopos.target.control",
    full = false,
    getState,
    isInteracting,
    setInteracting,
    send,
    sendEvent,
    sendAutomation,
    replay,
    applyPreset,
    savePreset,
    deletePreset,
    requestCapturePreview,
    requestShowCapturePreview,
    captureShowStep,
    sendCommand,
  }) {
    if (!host) throw new Error("ControlColumn requires a host");
    host.classList.add("control-column");
    const $ = selector => host.querySelector(selector);
    const cards = $("#cards");
    const pickerHost = $("#target-picker-host");
    const status = $("#event-status");
    if (!cards || !pickerHost || !status) {
      throw new Error("ControlColumn host is missing its cards, picker, or status element");
    }

    const openCommandDevices = new Set();
    const capturePreviews = new Map();
    let pendingPreview = null;
    let lastPresetReport = null;
    const state = () => getState?.() || {devices: {}, seats: {}, groups: {}};

    function seats() {
      return Object.values(state().seats || {})
        .sort((a, b) => Number(a.id) - Number(b.id));
    }

    function groups() {
      return Object.values(state().groups || {})
        .sort((a, b) => Number(a.id) - Number(b.id));
    }

    function groupSeats(groupId) {
      return seats().filter(seat =>
        (seat.groups || []).map(Number).includes(Number(groupId)));
    }

    function deviceForSeat(seat) {
      if (!seat) return null;
      const installation = state();
      const devices = Object.values(installation.devices || {});
      return (seat.bound ? installation.devices?.[seat.bound] : null) ||
        devices.find(device =>
          device.virtual && Number(device.seat_id) === Number(seat.id));
    }

    const surface = window.ControlSurface.create({
      getState: state,
      deviceForSeat,
      send: ({scope, id: targetId, name, value}) => {
        const numericId = targetId == null ? null : Number(targetId);
        send?.({scope, id: numericId, name, value});
        updateLocalParams(scope, numericId, name, value);
      },
      sendEvent,
      sendAutomation,
      setInteracting,
      requestRender: () => render(),
      presetCatalog: patch => state().preset_catalog?.[patch] || [],
      applyPreset,
      savePreset,
      deletePreset,
      requestCapturePreview: ({key, scope, id: targetId, patch}) => {
        capturePreviews.delete(key);
        pendingPreview = key;
        requestCapturePreview?.({scope, id: targetId, patch});
      },
      capturePreview: key => capturePreviews.get(key) || null,
      presetReport: (_key, members) => {
        if (!lastPresetReport) return null;
        const targets = new Set(Object.keys(lastPresetReport.targets || {}));
        const mine = (members || []).map(seat => String(seat.id));
        return mine.length && mine.length === targets.size &&
          mine.every(seatId => targets.has(seatId)) ? lastPresetReport : null;
      },
    });

    const targetPicker = window.TargetPicker.create({
      host: pickerHost,
      id,
      storageKey,
      followFocusSeat: true,
      pruneFallback: "empty",
      spec: () => ({
        label: "Control target",
        sections: window.TargetPicker.seatSections({
          groups: groups(),
          seats: seats(),
          groupSelector: "id",
        }),
      }),
      onChange: () => {
        renderCards();
        cards.scrollTop = 0;
      },
    });

    function liveSchema() {
      const schema = state().live_controls;
      if (!schema || typeof schema.patch !== "string" ||
          !Array.isArray(schema.declarations)) return null;
      const items = [
        ...schema.declarations,
        ...(Array.isArray(schema.events) ? schema.events : []),
      ];
      const visible = full
        ? items
        : items.filter(declaration => declaration?.dashboard === true);
      const valid = visible.every(declaration =>
        declaration &&
        typeof declaration.identity === "string" &&
        declaration.identity.length > 0 &&
        typeof declaration.name === "string" &&
        (declaration.path == null || Array.isArray(declaration.path)));
      if (!valid) return null;
      return {
        patch: schema.patch,
        declarations: visible.map(declaration => ({
          ...declaration,
          path: declaration.path || [],
        })),
      };
    }

    function liveEventSchema() {
      const schema = state().live_controls;
      if (!schema || typeof schema.patch !== "string" ||
          !Array.isArray(schema.events)) return null;
      return {
        patch: schema.patch,
        events: schema.events.filter(declaration =>
          declaration &&
          typeof declaration.identity === "string" &&
          declaration.identity.length > 0 &&
          (full || declaration.dashboard === true)),
      };
    }

    function replayButton(scope, targetId, disabled) {
      return `<button class="send-all" data-replay-live data-live-scope="${scope}"${targetId == null ? "" : ` data-live-id="${esc(targetId)}"`} ${disabled ? "disabled" : ""}>Send all</button>`;
    }

    function commandLabel(command) {
      return command === "updatebopos"
        ? "Update bopOS"
        : command.replaceAll("-", " ").replaceAll("_", " ");
    }

    function deviceCommands(device) {
      if (!device) return "";
      const commands = (state().facilitator_commands || []).map(command =>
        `<button data-device-command="${esc(command)}" data-uid="${esc(device.uid)}" class="${destructiveCommands.has(command) ? "hold" : ""}">${esc(commandLabel(command))}${destructiveCommands.has(command) ? " — hold" : ""}</button>`).join("");
      if (!commands) return "";
      return `<details class="device-commands" data-command-uid="${esc(device.uid)}" ${openCommandDevices.has(device.uid) ? "open" : ""}><summary>Device setup</summary><div>${commands}</div></details>`;
    }

    function liveCard(scope, item, members, declarations, schemaAvailable, patch) {
      const targetId = scope === "all" ? null : Number(item.id);
      const empty = members.length === 0;
      const device = scope === "seat" ? deviceForSeat(item) : null;
      const live = !!device?.online && Number(device.engine_alive) !== 0;
      const name = scope === "all"
        ? "All Seats"
        : (item.name || `${scope === "group" ? "Group" : "Seat"} ${item.id}`);
      const meta = scope === "all"
        ? `${members.length} Seats`
        : scope === "group"
          ? `g${item.id} · ${members.length} ${members.length === 1 ? "Seat" : "Seats"}`
          : `Seat ${item.id} · ${device ? (device.online ? "online" : "offline") : (item.bound ? "offline" : "unbound")}`;
      const controls = declarations.length
        ? `<div class="promoted-controls">${surface.tree(scope, targetId, members, declarations, empty)}</div>`
        : "";
      const cardKey = `${scope}:${targetId ?? "all"}`;
      const presets = full && declarations.length
        ? surface.presetRow(scope, targetId, members, patch, {
            key: cardKey,
            saveDisabled: scope === "seat" && !live,
          })
        : "";
      return `<article class="live-card ${scope}-card${scope === "group" && empty ? " empty-group" : ""}${scope === "seat" && !live ? " offline" : ""}" data-live-scope="${scope}"${targetId == null ? "" : ` data-live-id="${targetId}"`}>
        <div class="live-card-head">${scope === "seat" ? `<i class="dot ${live ? "ok" : ""}" aria-hidden="true"></i>` : ""}<span class="name"><strong>${esc(name)}</strong><small>${esc(meta)}</small></span>${scope === "all" || scope === "seat" ? replayButton(scope, targetId, !schemaAvailable) : ""}</div>
        ${presets}${controls}${scope === "seat" ? deviceCommands(device) : ""}<output class="live-param-status visually-hidden" aria-live="polite">${esc(surface.announcement(cardKey))}</output>
      </article>`;
    }

    function renderShowCapture() {
      if (!full || !targetPicker.selection().length) return;
      pickerHost.insertAdjacentHTML(
        "beforeend",
        '<button type="button" class="capture-show-step" data-capture-show-step>Capture as Show step</button>',
      );
      pickerHost.querySelector("[data-capture-show-step]").onclick = () => {
        const target = presetScope();
        if (!target) return;
        requestShowCapturePreview?.({
          scope: target.scope,
          ...(target.id == null ? {} : {id: target.id}),
        });
      };
    }

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
      return seat
        ? liveCard("seat", seat, [seat], declarations, available, patch)
        : null;
    }

    function selectionMode(selection) {
      if (!selection.length) return "none";
      if (selection.includes("all")) return "all";
      const kinds = new Set(selection.map(entry =>
        entry.startsWith("g") || entry.startsWith("group:") ? "groups" : "seats"));
      return kinds.size === 1 ? [...kinds][0] : "mixed";
    }

    function lostLabel(selector) {
      if (selector.startsWith("group:")) return `Group ${selector.slice(6)}`;
      if (/^g\d+$/.test(selector)) return `Group ${selector.slice(1)}`;
      return `Seat ${selector}`;
    }

    function unresolvedTarget() {
      const lost = targetPicker.dropped();
      const said = lost.length
        ? `${lost.map(lostLabel).join(", ")} ${lost.length === 1 ? "is" : "are"} no longer in this venue.`
        : "No target chosen.";
      return `<p class="live-unresolved">${esc(said)}<button type="button" data-choose-target>choose a target</button></p>`;
    }

    function renderCards() {
      if (isInteracting?.()) return;
      const schema = liveSchema();
      const declarations = schema?.declarations || [];
      const allSeats = seats();
      const available = declarations.length > 0;
      const selection = targetPicker.selection();
      const patch = schema?.patch;
      cards.dataset.liveView = selectionMode(selection);
      if (!selection.length) {
        cards.innerHTML = unresolvedTarget();
        cards.querySelector("[data-choose-target]").onclick = () =>
          targetPicker.reveal();
        return;
      }
      const rendered = selection.includes("all")
        ? [liveCard(
            "all", {}, allSeats, declarations,
            available && allSeats.length > 0, patch,
          )]
        : selection
            .map(entry => selectedCard(entry, declarations, available, patch))
            .filter(Boolean);
      cards.innerHTML = rendered.join("") || '<p class="empty">No Seats</p>';
      bindCards();
    }

    function updateLocalParams(scope, targetId, identity, value) {
      const members = scope === "all"
        ? seats()
        : scope === "group"
          ? groupSeats(targetId)
          : seats().filter(seat => Number(seat.id) === Number(targetId));
      for (const seat of members) {
        seat.params ||= {};
        seat.params[identity] = value;
      }
    }

    function bindCards() {
      surface.bind(cards);
      cards.querySelectorAll("[data-replay-live]").forEach(button => {
        button.onclick = () => replay?.({
          scope: button.dataset.liveScope,
          ...(button.dataset.liveId == null
            ? {}
            : {id: Number(button.dataset.liveId)}),
        });
      });
      cards.querySelectorAll("[data-device-command]").forEach(button =>
        bindCommandButton(button, button.dataset.uid));
      cards.querySelectorAll("details[data-command-uid]").forEach(details => {
        details.ontoggle = () => {
          if (details.open) openCommandDevices.add(details.dataset.commandUid);
          else openCommandDevices.delete(details.dataset.commandUid);
        };
      });
    }

    function presetScope() {
      const selection = targetPicker.selection();
      if (!selection.length) return null;
      if (selection.includes("all")) return {scope: "all", id: null};
      const seatOnly = selection.every(entry =>
        !entry.startsWith("g") && !entry.startsWith("group:"));
      if (seatOnly && selection.length === 1) {
        const seat = seats().find(item => String(item.id) === selection[0]);
        if (seat) return {scope: "seat", id: Number(seat.id)};
      }
      if (seatOnly) return {scope: "all", id: null};
      return {scope: "groups", id: null};
    }

    function bindCommandButton(button, uid) {
      const command = button.dataset.deviceCommand;
      const device = state().devices?.[uid];
      const target = device?.alias || "device";
      if (!destructiveCommands.has(command)) {
        button.onclick = () => {
          if (window.confirm(`${commandLabel(command)} ${target}?`)) {
            sendCommand?.({uid, verb: command});
          }
        };
        return;
      }
      let timer = null;
      const cancel = () => {
        clearTimeout(timer);
        timer = null;
        button.classList.remove("holding");
      };
      button.onpointerdown = () => {
        button.classList.add("holding");
        timer = setTimeout(() => {
          timer = null;
          button.classList.remove("holding");
          sendCommand?.({uid, verb: command});
        }, 1200);
      };
      button.onpointerup = cancel;
      button.onpointercancel = cancel;
      button.onpointerleave = cancel;
    }

    function render() {
      targetPicker.render();
      renderShowCapture();
      renderCards();
    }

    function refresh(nextState) {
      surface.refreshAnchors(nextState);
      render();
    }

    function acceptCapturePreview(data) {
      if (!pendingPreview) return false;
      capturePreviews.set(pendingPreview, data);
      pendingPreview = null;
      render();
      return true;
    }

    function reportPresetSaved(data) {
      status.value = `Saved ${data.name}${data.omitted?.length
        ? ` · ${data.omitted.length} omitted as mixed`
        : ""}`;
    }

    function reportPresetApplied(data) {
      lastPresetReport = data;
      render();
    }

    function handleShowCapturePreview(data) {
      const applied = Number(data?.applied) || 0;
      const total = Number(data?.total) || 0;
      const omitted = Number(data?.omitted) || 0;
      if (!data?.show_loaded) {
        window.alert("Load or create a Show before capturing a preset arrangement.");
        return;
      }
      if (!applied) {
        window.alert(`${applied} of ${total} targets have a preset applied; there is nothing to capture.`);
        return;
      }
      const noun = applied === 1 ? "target has" : "targets have";
      const other = omitted === 1 ? "the other 1 will" : `the other ${omitted} will`;
      const omission = omitted ? `; ${other} not be captured` : "";
      if (window.confirm(`${applied} of ${total} ${noun} a preset applied${omission}. Add this arrangement as a Show step?`)) {
        captureShowStep?.({scope: data.scope, id: data.id});
      }
    }

    function reportEventScheduled(data) {
      const declaration = (liveEventSchema()?.events || [])
        .find(item => item.identity === data.identity);
      status.value = `${declaration?.name || data.identity} scheduled · ${data.lead_ms} ms`;
    }

    return {
      render,
      refresh,
      acceptCapturePreview,
      reportPresetSaved,
      reportPresetApplied,
      handleShowCapturePreview,
      reportEventScheduled,
    };
  }

  window.ControlColumn = {create};
})();
