// Shared target-card renderer. Desktop Control mounts one instance per
// authored selector with a single-select picker; Remote mounts one derived
// instance that emits All, every group and every Seat without picker chrome.
// The host owns fleet state, transport and page furniture. This component owns
// card markup, ControlSurface state, preset reports and Remote command state.
(function () {
  "use strict";

  const esc = value => String(value ?? "—").replace(
    /[&<>"']/g,
    character => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"}[character]),
  );
  const destructiveCommands = new Set(["updatebopos", "reboot", "shutdown"]);
  const CARD_MAX_WIDTH = 560;
  const CARD_GAP = 12;

  function create({
    host,
    id = "control",
    storageKey = "bopos.target.control",
    capabilities = {},
    // Control owns card membership persistence, so its picker has no key.
    initialTarget = null,
    defaultOpen = true,
    singleTarget = false,
    unavailableTargets = () => new Set(),
    onTargetChange,
    onOpenChange,
    onRemove,
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
    sendCommand,
    // The desktop can hand off device lifecycle to its Devices tab; Remote
    // instead enables the per-card commands because it has no such tab.
    openDevice,
  }) {
    if (!host) throw new Error("ControlColumn requires a host");
    host.classList.add("control-column");
    const fullManifest = capabilities.fullManifest ?? false;
    const presetMenu = capabilities.presetMenu ?? false;
    const showTargetPicker = capabilities.targetPicker ?? true;
    const deriveAllTargets = capabilities.deriveAllTargets ?? false;
    const showDeviceCommands = capabilities.deviceCommands ?? false;
    const showDeviceHandoff = capabilities.deviceHandoff ?? false;
    const groupSlot = capabilities.groupSlot || (() => -1);
    host.classList.add("target-card");
    if (deriveAllTargets) host.classList.add("control-column-derived");
    // The shell is the labelled region. Its name is refreshed with its target.
    host.setAttribute("role", "region");
    // Control's picker and close action precede its controls in DOM order.
    host.innerHTML = `${showTargetPicker ? `<div class="control-column-head"><div class="control-column-picker"></div>${onRemove
        ? '<button type="button" class="control-column-close" title="Remove card" aria-label="Remove card">✕</button>' : ""}</div>` : ""}
      <div class="control-column-cards"><p class="empty">Waiting for devices…</p></div>
      <output class="control-column-status" role="status" aria-live="polite"></output>`;
    const cards = host.querySelector(".control-column-cards");
    const pickerHost = host.querySelector(".control-column-picker");
    const status = host.querySelector(".control-column-status");
    const closeButton = host.querySelector(".control-column-close");
    // Momentary, not latching: no `aria-pressed`, or design-language §8 gives
    // it the latching square radius (and announces a state it does not have).
    if (closeButton) closeButton.onclick = () => onRemove();

    const openCommandDevices = new Set();
    const openOverflows = new Set();
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
      // One live region per authored Control card, or one for derived Remote.
      announce: message => { status.value = `${terseTarget()}: ${message}`; },
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

    function targetSpec() {
      const unavailable = unavailableTargets?.() || new Set();
      const sections = window.TargetPicker.seatSections({
        groups: groups(),
        seats: seats(),
        groupSelector: "id",
      }).map(section => ({
        ...section,
        chips: (section.chips || []).map(chip => ({
          ...chip,
          disabled: chip.disabled || unavailable.has(chip.value),
        })),
      }));
      return {
        label: "Control target",
        sections,
        multiple: !singleTarget,
        allDisabled: unavailable.has("all"),
      };
    }

    // The closed Control picker is the card title; Remote uses a document label.
    function terseTarget() {
      if (deriveAllTargets) return "Remote";
      return window.TargetPicker.terse(
        targetPicker.selection(), targetSpec().sections, {emptyTerse: "no target"});
    }

    const targetPicker = showTargetPicker
      ? window.TargetPicker.create({
          host: pickerHost,
          id,
          storageKey,
          initialSelection: initialTarget,
          defaultOpen,
          onOpenChange,
          pruneFallback: "empty",
          spec: targetSpec,
          onChange: selection => {
            renderCards();
            nameRegion();
            onTargetChange?.(selection);
          },
        })
      : {
          selection: () => [
            "all",
            ...groups().map(group => `g${group.id}`),
            ...seats().map(seat => String(seat.id)),
          ],
          dropped: () => [],
          render: () => {},
          reveal: () => {},
          set: () => {},
        };

    function nameRegion() {
      host.setAttribute("aria-label", deriveAllTargets
        ? "Remote controls"
        : `Control card ${terseTarget()}`);
    }

    function identityClasses(scope, targetId) {
      if (scope === "all") return " target-card target-card-all";
      if (scope !== "group") return " target-card";
      const slot = Number(groupSlot(targetId));
      return slot >= 0 && slot < window.GroupSlots.palette.length
        ? ` target-card target-card-group group-slot-${slot + 1}`
        : " target-card";
    }

    function identityStyle(scope, targetId) {
      if (scope !== "group") return "";
      const slot = Number(groupSlot(targetId));
      return slot >= 0 && slot < window.GroupSlots.palette.length
        ? ` style="--group-colour:var(--group-slot-${slot + 1})"`
        : "";
    }

    function decorateHost() {
      host.classList.remove(
        "target-card-all", "target-card-group",
        "group-slot-1", "group-slot-2", "group-slot-3", "group-slot-4",
      );
      host.style.removeProperty("--group-colour");
      if (deriveAllTargets) return;
      const selector = targetPicker.selection()[0];
      if (selector === "all") host.classList.add("target-card-all");
      if (!/^g\d+$/.test(selector || "")) return;
      const slot = Number(groupSlot(Number(selector.slice(1))));
      if (slot < 0 || slot >= window.GroupSlots.palette.length) return;
      host.classList.add("target-card-group", `group-slot-${slot + 1}`);
      host.style.setProperty("--group-colour", `var(--group-slot-${slot + 1})`);
    }

    function liveSchema() {
      const schema = state().live_controls;
      if (!schema || typeof schema.patch !== "string" ||
          !Array.isArray(schema.declarations)) return null;
      const items = [
        ...schema.declarations,
        ...(Array.isArray(schema.events) ? schema.events : []),
      ];
      const visible = fullManifest
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
          (fullManifest || declaration.dashboard === true)),
      };
    }

    function replayButton(scope, targetId, disabled) {
      return `<button class="send-all" data-replay-live data-live-scope="${scope}"${targetId == null ? "" : ` data-live-id="${esc(targetId)}"`} ${disabled ? "disabled" : ""}>Send all</button>`;
    }

    // D8's overflow. `Send all` is a rescue action for a returning node, not a
    // live gesture, and on a desktop host the device hand-off keeps it company —
    // so one ⋯ per card replaces both a permanent button and, on Control, a
    // whole `Device setup` disclosure. A group card has neither and renders no
    // ⋯ at all rather than an empty menu.
    function cardOverflow(scope, targetId, device, schemaAvailable) {
      const items = [];
      if (scope === "all" || scope === "seat") {
        items.push(replayButton(scope, targetId, !schemaAvailable));
      }
      if (showDeviceHandoff && scope === "seat" && device && openDevice) {
        items.push(`<button type="button" class="open-device" data-open-device="${esc(device.uid)}">Device setup…</button>`);
      }
      if (!items.length) return "";
      const key = `${scope}:${targetId ?? "all"}`;
      // `icon-menu` is the app-wide opt-out from design-language §9's ▸/▾
      // (`style.css` §9): this summary IS the icon, and a marker beside the ⋯
      // reads as two controls.
      return `<details class="live-card-overflow icon-menu" data-overflow-key="${esc(key)}"${
        openOverflows.has(key) ? " open" : ""}>
        <summary title="More actions" aria-label="More actions">⋯</summary>
        <div class="live-card-overflow-menu">${items.join("")}</div>
      </details>`;
    }

    function commandLabel(command) {
      return command === "updatebopos"
        ? "Update bopOS"
        : command.replaceAll("-", " ").replaceAll("_", " ");
    }

    // Remote only, since D8. On an iPad away from the rack a per-device reboot
    // earns its place; inside a live parameter panel on the desk it is three
    // hold-to-confirm buttons one disclosure from the faders, times N cards
    // times N columns, for something the Devices tab owns.
    function deviceCommands(device) {
      if (!showDeviceCommands || !device) return "";
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
      const presets = presetMenu && declarations.length
        ? surface.presetRow(scope, targetId, members, patch, {
            key: cardKey,
            saveDisabled: scope === "seat" && !live,
          })
        : "";
      // An emptied group keeps its column and says so out loud: `aria-disabled`
      // rather than a member count in a `<small>` nobody reads aloud (D5).
      const emptyGroup = scope === "group" && empty;
      const identity = deriveAllTargets ? identityClasses(scope, targetId) : "";
      const identityCss = deriveAllTargets ? identityStyle(scope, targetId) : "";
      return `<article class="live-card ${scope}-card${identity}${emptyGroup ? " empty-group" : ""}${scope === "seat" && !live ? " offline" : ""}"${identityCss} data-live-scope="${scope}"${targetId == null ? "" : ` data-live-id="${targetId}"`}${emptyGroup ? ' aria-disabled="true"' : ""}>
        <div class="live-card-head">${scope === "seat" ? `<i class="dot ${live ? "ok" : ""}" aria-hidden="true"></i>` : ""}<span class="name"><strong>${esc(name)}</strong><small>${esc(meta)}</small></span>${cardOverflow(scope, targetId, device, schemaAvailable)}</div>
        ${presets}${controls}${scope === "seat" ? deviceCommands(device) : ""}
      </article>`;
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
        cards.style.removeProperty("--target-grid-max");
        cards.innerHTML = unresolvedTarget();
        cards.querySelector("[data-choose-target]").onclick = () =>
          targetPicker.reveal();
        return;
      }
      const rendered = deriveAllTargets
        ? [
            liveCard(
              "all", {}, allSeats, declarations,
              available && allSeats.length > 0, patch,
            ),
            ...selection.filter(entry => entry !== "all")
              .map(entry => selectedCard(entry, declarations, available, patch))
              .filter(Boolean),
          ]
        : selection.includes("all")
        ? [liveCard(
            "all", {}, allSeats, declarations,
            available && allSeats.length > 0, patch,
          )]
        : selection
            .map(entry => selectedCard(entry, declarations, available, patch))
            .filter(Boolean);
      if (deriveAllTargets && rendered.length) {
        cards.style.setProperty(
          "--target-grid-max",
          `${rendered.length * CARD_MAX_WIDTH + (rendered.length - 1) * CARD_GAP}px`,
        );
      } else {
        cards.style.removeProperty("--target-grid-max");
      }
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
      cards.querySelectorAll("details[data-overflow-key]").forEach(details => {
        details.ontoggle = () => {
          if (details.open) openOverflows.add(details.dataset.overflowKey);
          else openOverflows.delete(details.dataset.overflowKey);
        };
      });
      cards.querySelectorAll("[data-open-device]").forEach(button => {
        button.onclick = () => openDevice?.(button.dataset.openDevice);
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
      nameRegion();
      decorateHost();
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
      reportEventScheduled,
      target: () => targetPicker.selection(),
      setTarget: next => targetPicker.set(next),
      revealTarget: () => targetPicker.reveal(),
      focus: () => {
        host.scrollIntoView({block: "nearest", inline: "nearest"});
        pickerHost?.querySelector("summary")?.focus();
      },
      setSole: () => {},
      destroy: () => host.remove(),
      element: host,
    };
  }

  window.ControlColumn = {create};
})();
