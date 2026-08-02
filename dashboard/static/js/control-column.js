// One independently targetable Control surface card.
//
// The HOST page owns fleet state, its websocket, and page furniture. This
// component owns the state that must not leak between columns: its target
// picker, ControlSurface instance, cards, preset previews/reports, and open
// per-device command disclosures.
//
// Since `4-n-columns/1-columns-layout` the Control tab mounts SEVERAL of these
// side by side, so anything that used to be "the surface's" is now the
// column's: its own labelled region, its own live region, its own ✕. Capture
// left the column entirely — it is venue-wide and belongs to the tab (D1), so
// N columns cannot mean N capture buttons sending N different scopes.
//
// Since `3-iframe-retirement` the column also owns its own MARKUP. It is
// mounted in two documents now — the Control tab of `index.html` and the
// standalone Remote page — and a skeleton authored twice in HTML would be the
// same duplication the component thread keeps deleting. Nothing inside is
// addressed by id, so `4-n-columns` can mount several without collisions.
// Appearance is `css/control-column.css` (the shell) plus `control-panel.css`
// (the card face, which belongs to the control panel, not to us).
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
    // The Control tab owns its columns' persistence itself (D9), so it passes
    // no storage key and supplies these instead. Remote, the single-column
    // host, keeps the picker's own key and never sees them.
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
    // D8: the Devices tab owns device lifecycle, so a `full` host hands off to
    // it rather than carrying Update bopOS / Reboot / Shutdown per card. Remote
    // has no Devices tab and passes nothing, which is exactly why it keeps the
    // commands themselves.
    openDevice,
  }) {
    if (!host) throw new Error("ControlColumn requires a host");
    host.classList.add("control-column");
    // The column IS the labelled region, and its label is its target (D4) — so
    // region navigation reads `all`, `Left`, `Seat 7` rather than N identical
    // "Live controls". The name is set on every render, in `nameRegion`.
    host.setAttribute("role", "region");
    // Head order is deliberate: picker and ✕ come FIRST in the DOM, so a
    // keyboard operator reaches the next column's target without traversing
    // forty parameter rows. No positive tabindex anywhere — DOM order is
    // already the reading order.
    host.innerHTML = `<div class="control-column-head"><div class="control-column-picker"></div>${onRemove
        ? '<button type="button" class="control-column-close" title="Remove card" aria-label="Remove card">✕</button>' : ""}</div>
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
      // ONE live region per column, not one per card. A column showing three
      // Seats used to carry three, and two columns showing the same Seat would
      // have announced the same sentence twice with nothing to say which one
      // acted — so the message is prefixed with the column's own target.
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

    // The column's own name, and the prefix on everything it announces. Terse
    // by design (D4): the closed picker's readout IS the column's title, so a
    // 342px column spends no height on a heading that repeats it.
    function terseTarget() {
      return window.TargetPicker.terse(
        targetPicker.selection(), targetSpec().sections, {emptyTerse: "no target"});
    }

    const targetPicker = window.TargetPicker.create({
      host: pickerHost,
      id,
      storageKey,
      initialSelection: initialTarget,
      defaultOpen,
      onOpenChange,
      // D7 (Bob, 2026-07-31): Control never follows the focus Seat, at any N.
      // A column that silently re-aimed itself when someone touched the Seats
      // tab is wrong the moment there is more than one of them, and the Seats →
      // Control workflow returns as an explicit action owned by `4-n-columns`.
      pruneFallback: "empty",
      spec: targetSpec,
      onChange: selection => {
        renderCards();
        nameRegion();
        cards.scrollTop = 0;
        onTargetChange?.(selection);
      },
    });

    function nameRegion() {
      host.setAttribute("aria-label", `Control column ${terseTarget()}`);
    }

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

    // D8's overflow. `Send all` is a rescue action for a returning node, not a
    // live gesture, and on a `full` host the device hand-off keeps it company —
    // so one ⋯ per card replaces both a permanent button and, on Control, a
    // whole `Device setup` disclosure. A group card has neither and renders no
    // ⋯ at all rather than an empty menu.
    function cardOverflow(scope, targetId, device, schemaAvailable) {
      const items = [];
      if (scope === "all" || scope === "seat") {
        items.push(replayButton(scope, targetId, !schemaAvailable));
      }
      if (full && scope === "seat" && device && openDevice) {
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
      if (full || !device) return "";
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
      // An emptied group keeps its column and says so out loud: `aria-disabled`
      // rather than a member count in a `<small>` nobody reads aloud (D5).
      const emptyGroup = scope === "group" && empty;
      return `<article class="live-card ${scope}-card${emptyGroup ? " empty-group" : ""}${scope === "seat" && !live ? " offline" : ""}" data-live-scope="${scope}"${targetId == null ? "" : ` data-live-id="${targetId}"`}${emptyGroup ? ' aria-disabled="true"' : ""}>
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
        pickerHost.querySelector("summary")?.focus();
      },
      setSole: () => {},
      destroy: () => host.remove(),
      element: host,
    };
  }

  window.ControlColumn = {create};
})();
