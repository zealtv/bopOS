// Seats workspace: roster, group map, room settings and Seat inspector.
function activateSeatSidebar(mode, moveFocus = false) {
  seatSidebarMode = mode === "groups" ? "groups" : "seats";
  const seats = seatSidebarMode === "seats";
  $("#seat-sidebar-tab").setAttribute("aria-selected", seats ? "true" : "false");
  $("#group-sidebar-tab").setAttribute("aria-selected", seats ? "false" : "true");
  $("#seat-sidebar-tab").tabIndex = seats ? 0 : -1;
  $("#group-sidebar-tab").tabIndex = seats ? -1 : 0;
  $("#seat-sidebar-panel").hidden = !seats;
  $("#group-sidebar-panel").hidden = seats;
  if (moveFocus) $(seats ? "#seat-sidebar-tab" : "#group-sidebar-tab").focus();
}
$("#seat-sidebar-tab").onclick = () => activateSeatSidebar("seats");
$("#group-sidebar-tab").onclick = () => activateSeatSidebar("groups");
$("#seat-sidebar-tabs").onkeydown = (event) => {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  event.preventDefault();
  const groups = event.key === "ArrowRight" || event.key === "End";
  activateSeatSidebar(groups ? "groups" : "seats", true);
};
activateSeatSidebar(seatSidebarMode);

function groupCatalog() {
  return Object.values(installation.groups || {}).sort((a, b) => Number(a.id) - Number(b.id));
}
function groupById(id) {
  return installation.groups?.[String(id)] || installation.groups?.[id] || null;
}
function groupMembers(id) {
  return Object.values(installation.seats || {})
    .filter((seat) => (seat.groups || []).includes(Number(id)))
    .sort((a, b) => Number(a.id) - Number(b.id));
}
function visibleGroupIds() {
  return visibleGroups.filter((id) => id !== null);
}
function reconcileGroupView() {
  const valid = new Set(groupCatalog().map((group) => Number(group.id)));
  visibleGroups = Array.from({ length: 4 }, (_item, index) => {
    const id = visibleGroups[index];
    return id !== null && valid.has(Number(id)) ? Number(id) : null;
  });
  if (!valid.has(Number(focusedGroup))) focusedGroup = null;
  if (!valid.has(Number(selectedGroup))) selectedGroup = null;
}
function groupView() {
  return { visible: visibleGroupIds(), visibleSlots: [...visibleGroups], focused: focusedGroup, slots: GROUP_SLOTS };
}
// Adapted Lucide eye/eye-off geometry; see THIRD_PARTY_NOTICES.md.
function eyeIcon(shown) {
  const slash = shown ? "" : '<path d="M2 2l20 20"></path>';
  return [
    `<svg class="visibility-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M1 ` +
      `12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"></path>`,
    `<circle cx="12" cy="12" r="3"></circle>${slash}</svg>`,
  ].join("");
}
function ensureGroupVisible(id) {
  id = Number(id);
  if (visibleGroups.includes(id)) return true;
  const slot = visibleGroups.findIndex((item) => item === null);
  if (slot < 0) {
    groupMessage = "Four groups are already shown; hide one to compare another.";
    return false;
  }
  visibleGroups[slot] = id;
  groupMessage = "";
  return true;
}
function focusGroup(id) {
  id = Number(id);
  selectedGroup = id;
  groupMemberFilter = "";
  activateSeatSidebar("groups");
  if (focusedGroup === id) focusedGroup = null;
  else if (ensureGroupVisible(id)) focusedGroup = id;
  renderGroups();
  renderGroupMap();
  Spatial.render(installation, selectedSeat, selectSeat, ws, groupView());
}
function toggleGroupVisible(id) {
  id = Number(id);
  if (visibleGroups.includes(id)) {
    visibleGroups = visibleGroups.map((item) => (item === id ? null : item));
    if (focusedGroup === id) focusedGroup = null;
    groupMessage = "";
  } else ensureGroupVisible(id);
  renderGroups();
  renderGroupMap();
  Spatial.render(installation, selectedSeat, selectSeat, ws, groupView());
}
function clearGroupView() {
  focusedGroup = null;
  visibleGroups = [null, null, null, null];
  groupMessage = "";
  renderGroups();
  renderGroupMap();
  Spatial.render(installation, selectedSeat, selectSeat, ws, groupView());
}
function groupMarker(id) {
  const index = visibleGroups.indexOf(Number(id));
  if (index < 0) return '<i class="group-slot hidden" aria-hidden="true">–</i>';
  const slot = GROUP_SLOTS[index];
  return `<i class="group-slot slot-${index + 1}" style="--group-colour:${slot.colour}" aria-hidden="true">${index + 1}</i>`;
}
function renderGroups() {
  const panel = $("#group-sidebar-panel"),
    content = $("#groups-content"),
    summary = $("#groups-summary");
  if (!panel || !content || !summary) return;
  const previousFilter = $("#group-member-filter");
  const restoreFilterFocus = document.activeElement === previousFilter;
  const filterSelection = restoreFilterFocus ? [previousFilter.selectionStart, previousFilter.selectionEnd] : null;
  reconcileGroupView();
  const groups = groupCatalog();
  summary.textContent = `${visibleGroupIds().length} shown · ${groups.length} total`;
  const rows = groups
    .map((group) => {
      const id = Number(group.id),
        visible = visibleGroups.includes(id),
        count = groupMembers(id).length;
      const action = `${visible ? "Hide" : "Show"} ${group.name} ${visible ? "from" : "on"} map`;
      return [
        `<div class="group-row${focusedGroup === id ? " focused" : ""}${selectedGroup === id ? " selected" : ""}" data-group-row="${id}">
      <button class="group-focus" data-group-focus="${id}" aria-pressed="${focusedGroup === id}">${groupMarker(id)}<span><strong>${esc(group.name)}</strong>`,
        `<small>g${id} · ${count} ${count === 1 ? "Seat" : "Seats"}</small>`,
        `</span>`,
        `</button>
      <button class="group-eye" data-group-eye="${id}" aria-pressed="${visible}" aria-label="${esc(action)}" title="${esc(action)}">${eyeIcon(visible)}</button>
      <details class="group-overflow icon-menu"><summary aria-label="Actions for ${esc(group.name)}" title="Group actions">…</summary>`,
        `<div>`,
        `<button data-group-rename="${id}">Rename</button>`,
        `<button data-group-delete="${id}" class="danger">Delete</button>`,
        `</div>`,
        `</details>
    </div>`,
      ].join("");
    })
    .join("");
  const active = groupById(selectedGroup);
  const members = active ? groupMembers(active.id) : [];
  const seatQuery = groupMemberFilter.trim().toLowerCase();
  const memberRows = active
    ? Object.values(installation.seats || {})
        .sort((a, b) => Number(a.id) - Number(b.id))
        .map((seat) => {
          const checked = (seat.groups || []).includes(Number(active.id));
          const search = String(seat.name || `Seat ${seat.id}`)
            .trim()
            .toLowerCase();
          const device = seat.bound ? installation.devices?.[seat.bound] : null;
          const sync = !seat.bound ? "unbound" : device?.group_sync?.status || (device?.online ? "waiting" : "offline");
          return groupMemberRow({
            search,
            seatQuery,
            seat,
            checked,
            sync,
          });
        })
        .join("")
    : "";
  const detail = active
    ? groupDetailMarkup({
        active,
        members,
        memberRows,
        seatQuery,
      })
    : "";
  content.innerHTML = `<div class="group-rows">${
    rows || '<p class="dim">No groups yet</p>'
    }</div><p id="group-limit" class="group-limit" role="status" ${
    groupMessage ? "" : "hidden"
    }>${
    esc(groupMessage)
    }</p>${
    detail
    }`;
  $("#group-create").onclick = () => {
    const name = prompt("Group name:", "");
    if (name?.trim()) ws.send("create_group", { name: name.trim() });
  };
  content.querySelectorAll("[data-group-focus]").forEach((button) => (button.onclick = () => focusGroup(button.dataset.groupFocus)));
  content.querySelectorAll("[data-group-eye]").forEach((button) => (button.onclick = () => toggleGroupVisible(button.dataset.groupEye)));
  content.querySelectorAll("[data-group-rename]").forEach(
    (button) =>
      (button.onclick = () => {
        const group = groupById(button.dataset.groupRename);
        const name = group && prompt("Rename group:", group.name);
        if (name?.trim()) ws.send("rename_group", { id: Number(group.id), name: name.trim() });
      }),
  );
  content.querySelectorAll("[data-group-delete]").forEach(
    (button) =>
      (button.onclick = () => {
        const group = groupById(button.dataset.groupDelete);
        if (group && confirm(`Delete ${group.name} (g${group.id})? Seat memberships will be removed.`)) {
          visibleGroups = visibleGroups.map((id) => (id === Number(group.id) ? null : id));
          if (focusedGroup === Number(group.id)) focusedGroup = null;
          if (selectedGroup === Number(group.id)) selectedGroup = null;
          ws.send("delete_group", { id: Number(group.id) });
        }
      }),
  );
  const show = $("#group-show-map");
  if (show)
    show.onclick = () => {
      if (focusedGroup !== Number(active.id)) focusGroup(active.id);
    };
  const memberFilter = $("#group-member-filter");
  if (memberFilter) {
    const applyFilter = () => {
      groupMemberFilter = memberFilter.value;
      const value = groupMemberFilter.trim().toLowerCase();
      let matches = 0;
      content.querySelectorAll("[data-group-member-filter]").forEach((row) => {
        row.hidden = !!value && !row.dataset.groupMemberFilter.startsWith(value);
        if (!row.hidden) matches++;
      });
      const empty = $("#group-filter-empty");
      if (empty) empty.hidden = !value || matches > 0;
    };
    memberFilter.oninput = applyFilter;
    memberFilter.onchange = applyFilter;
    memberFilter.onkeydown = (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        applyFilter();
      }
    };
    if (restoreFilterFocus) {
      memberFilter.focus();
      if (filterSelection.every((value) => value !== null)) memberFilter.setSelectionRange(...filterSelection);
    }
  }
  content.querySelectorAll("[data-group-member]").forEach(
    (input) =>
      (input.onchange = () => {
        const seat = installation.seats?.[String(input.dataset.groupMember)];
        if (!seat || !active) return;
        const next = new Set((seat.groups || []).map(Number));
        input.checked ? next.add(Number(active.id)) : next.delete(Number(active.id));
        seat.groups = [...next].sort((a, b) => a - b);
        ws.send("set_seat_groups", { id: Number(seat.id), groups: seat.groups });
        renderGroupMap();
        Spatial.render(installation, selectedSeat, selectSeat, ws, groupView());
      }),
  );
}
function renderGroupMap() {
  const bar = $("#group-map-bar"),
    legend = $("#group-map-legend"),
    message = $("#group-map-message");
  if (!bar || !legend || !message) return;
  bar.hidden = !visibleGroupIds().length;
  legend.innerHTML = visibleGroups
    .map((id, index) => {
      if (id === null) return "";
      const group = groupById(id);
      if (!group) return "";
      return `<button class="group-legend-chip${
        focusedGroup === id ? " focused" : ""
        }" data-group-legend="${
        id
        }">${
        groupMarker(id)
        }<span>${
        esc(group.name)
        } <small>g${
        id
        }</small></span></button>`;
    })
    .join("");
  legend.querySelectorAll("[data-group-legend]").forEach((button) => (button.onclick = () => focusGroup(button.dataset.groupLegend)));
  $("#group-view-clear").onclick = clearGroupView;
  const focused = groupById(focusedGroup),
    empty = focused && groupMembers(focused.id).length === 0;
  message.hidden = !empty;
  message.textContent = empty ? `No Seats in ${focused.name} (g${focused.id})` : "";
}
function seatRow(seat) {
  const d = occupant(seat),
    state = d?.virtual ? "sim" : d?.online ? "live" : "empty";
  const uid = d?.uid || "";
  const heartbeatAt = heartbeats.get(uid);
  const name = seat.name || `Seat ${seat.id}`;
  const classes = `${Number(seat.id) === Number(selectedSeat) ? "selected" : ""} ${badgeTone(d?.patch_badge)}`;
  const tone = state === "live" ? "online" : state === "sim" ? "sim" : "offline";
  const heartbeat = uid
    ? `<i class="heartbeat-blip${heartbeatAt ? " pulse" : ""}" ` +
      `${heartbeatAt ? `data-heartbeat-at="${esc(heartbeatAt)}"` : ""} aria-hidden="true"></i>`
    : "";
  return [
    `<div class="device-row seat-row ${classes}" data-uid="${esc(uid)}" data-seat-id="${seat.id}"`,
    ` data-seat-filter="${esc(String(name).trim().toLowerCase())}" role="button" tabindex="0">`,
    `<i class="dot ${tone}"></i>${heartbeat}<span>`,
    `<input data-seat-name aria-label="Seat ${seat.id} name" value="${esc(name)}"><small>ID ${seat.id} · ${state}</small>`,
    `</span>${d ? patchBadge(d.patch_badge) : ""}</div>`,
  ].join("");
}

function renderRoom() {
  const room = installation.room || {};
  const w = $("#room-w"),
    d = $("#room-d"),
    ox = $("#origin-x"),
    oy = $("#origin-y");
  if (!w) return;
  if (![w, d, ox, oy].includes(document.activeElement)) {
    w.value = room.width ?? 10;
    d.value = room.depth ?? 8;
    ox.value = room.origin?.[0] ?? 0;
    oy.value = room.origin?.[1] ?? 0;
    ox.max = room.width ?? 10;
    oy.max = room.depth ?? 8;
  }
}
["room-w", "room-d", "origin-x", "origin-y"].forEach((id) => {
  const input = document.getElementById(id);
  if (input)
    input.onchange = () =>
      ws.send("set_room", {
        width: Number($("#room-w").value),
        depth: Number($("#room-d").value),
        origin: [Number($("#origin-x").value), Number($("#origin-y").value)],
      });
});

function selectSeat(id) {
  activateSeatSidebar("seats");
  // The Control tab's target picker follows the same shared key, so choosing a
  // Seat here is the target it lands on (37/10, kept by
  // 02-component-unification/07 — everything else about a target is per host).
  window.TargetPicker?.focusSeat(id);
  selectedSeat = id;
  const seat = installation.seats?.[String(id)] || installation.seats?.[id];
  const d = seat && occupant(seat);
  selected = d?.uid || null;
  if (d && !d.declared) ws.send("request_params", { uid: d.uid });
  if (d) ws.send("request_patches", { uid: d.uid });
  render();
}

function renderSeatDetail() {
  const panel = $("#seat-detail");
  if (!panel) return;
  const seat = installation.seats?.[String(selectedSeat)] || installation.seats?.[selectedSeat];
  if (!seat) {
    panel.innerHTML = '<p class="dim">Select a Seat on the map or in the list.</p>';
    return;
  }
  const active = document.activeElement;
  if (interacting || (panel.contains(active) && active.matches("input,select"))) return;
  const devices = Object.values(installation.devices || {}).filter((device) => !device.virtual);
  const boundElsewhere = new Set(
    Object.values(installation.seats || {})
      .filter((other) => Number(other.id) !== Number(seat.id))
      .map((other) => other.bound)
      .filter(Boolean),
  );
  const available = devices.filter(
    (device) => !device.revoking_assignment && (!boundElsewhere.has(device.uid) || device.uid === seat.bound),
  );
  if (seatBindingDrafts.get(seat.id) === seat.bound) seatBindingDrafts.delete(seat.id);
  const bindingChoice = seatBindingDrafts.get(seat.id) ?? seat.bound ?? "";
  const currentKnown = devices.find((device) => device.uid === seat.bound);
  const options = [];
  if (seat.bound && !currentKnown)
    options.push(
      `<option value="${
        esc(seat.bound)
        }" ${
        bindingChoice === seat.bound ? "selected" : ""
        }>${
        esc(Identity.primary(seat.bound, installation))
        } · remembered offline</option>`,
    );
  if (currentKnown?.revoking_assignment)
    options.push(
      `<option value="${
        esc(currentKnown.uid)
        }" ${
        bindingChoice === currentKnown.uid ? "selected" : ""
        } disabled>${
        esc(Identity.primary(currentKnown, installation))
        } · clearing old assignment</option>`,
    );
  options.push(
    ...available.map(
      (device) =>
        `<option value="${
          esc(device.uid)
          }" ${
          device.uid === bindingChoice ? "selected" : ""
          }>${
          esc(Identity.primary(device, installation))
          } · ${
          device.online ? "online" : "offline"
          }</option>`,
    ),
  );
  if (!seat.bound) options.unshift(`<option value="" ${bindingChoice ? "" : "selected"}>Choose a device</option>`);
  const room = installation.room || {},
    origin = room.origin || [0, 0];
  const positions = (seat.positions || []).map((position, index) => seatPositionRow(index, position, origin)).join("");
  const binding = seat.bound ? installation.devices?.[seat.bound] : null;
  const groupChecks = groupCatalog()
    .map((group) => seatGroupMembership(group, seat))
    .join("");
  const groupSync = binding?.group_sync?.status;
  const choiceRevoking = !!devices.find((device) => device.uid === bindingChoice)?.revoking_assignment;
  const elementLimit = (seat.positions || []).length >= 2;
  panel.innerHTML = [
    `<div class="seat-inspector-section"><h3>Seat workspace</h3>
    <div class="assign">`,
    `<label>name <input id="seat-name" type="text" value="${esc(seat.name || "")}"></label>`,
    `<button id="seat-rename">Apply name</button>`,
    `</div>
    <div class="assign">`,
    `<label>ID <input id="seat-id" type="number" min="0" step="1" value="${seat.id}"></label>`,
    `<button id="seat-reindex">Reindex</button>`,
    `<button id="seat-remove" class="danger">Delete Seat</button>`,
    `</div>
    <div class="assign">`,
    `<button id="seat-open-control">Open in Control</button>`,
    `</div>`,
    `</div>
    <div class="seat-inspector-section"><h3>Elements</h3>`,
    `<div class="position-grid">${positions || '<p class="dim">No elements positioned yet.</p>'}</div>`,
    `<button id="seat-element-add" ${elementLimit ? "disabled" : ""}>Add element</button>`,
    `</div>
    <div class="seat-inspector-section"><h3>Groups</h3>`,
    `<div class="membership-list">${groupChecks || '<p class="dim">Open the Groups tab to create a group.</p>'}</div>`,
    `<small class="dim seat-group-sync">${
      seat.bound ? `Node membership: ${
      esc(groupSync || "waiting")
      }` : "Membership retained while this Seat is unbound"
      }</small>`,
    `</div>
    <div class="seat-inspector-section"><h3>Physical device</h3>`,
    `<small class="dim seat-binding-note">${
      seat.bound ? `${
      esc(Identity.primary(binding || seat.bound, installation))
      } · ${
      binding?.online ? "online" : binding ? "offline" : "waiting to be seen"
      }${
      binding?.ip ? ` · ${
      esc(binding.ip)
      }` : ""
      }` : "No device assigned"
      }</small>
    <div class="assign">`,
    `<label>device <select id="seat-device">${options.join("") || '<option value="">No available devices</option>'}</select>`,
    `</label>`,
    `<button id="seat-identify" ${choiceRevoking ? "disabled" : ""}>Identify</button>`,
    `<button id="seat-bind" ${
      choiceRevoking ? "disabled" : ""
      }>${
      seat.bound ? "Assign / replace" : "Assign"
      }</button>${
      seat.bound ? '<button id="seat-unbind">Unassign</button>' : ""
      }</div>`,
    `</div>`,
  ].join("");
  const savePositions = (positionsValue) => {
    seat.positions = positionsValue;
    ws.send("update_seat", { id: seat.id, positions: positionsValue });
    Spatial.render(installation, selectedSeat, selectSeat, ws, groupView());
  };
  panel.querySelectorAll("[data-seat-element] input").forEach(
    (input) =>
      (input.onchange = () => {
        const row = input.closest("[data-seat-element]"),
          index = Number(row.dataset.seatElement);
        const x = Number(row.querySelector('[data-axis="x"]').value),
          y = Number(row.querySelector('[data-axis="y"]').value);
        if (!Number.isFinite(x) || !Number.isFinite(y)) return;
        const next = structuredClone(seat.positions || []);
        next[index] = [Math.round((x + origin[0]) * 100) / 100, Math.round((y + origin[1]) * 100) / 100];
        savePositions(next);
      }),
  );
  panel.querySelectorAll("[data-remove-element]").forEach(
    (button) =>
      (button.onclick = () => {
        const next = structuredClone(seat.positions || []);
        next.splice(Number(button.dataset.removeElement), 1);
        savePositions(next);
      }),
  );
  $("#seat-element-add").onclick = () => {
    if ((seat.positions || []).length < 2) savePositions([...(seat.positions || []), [Number(origin[0]) || 0, Number(origin[1]) || 0]]);
  };
  $("#seat-rename").onclick = () => ws.send("update_seat", { id: seat.id, name: $("#seat-name").value });
  // The Seats -> Control workflow, made explicit. Control used to FOLLOW this
  // tab's selection ambiently, which D7 (Bob, 2026-07-31) retired at every N:
  // one click here would silently re-aim a column, persist it, and with several
  // columns destroy an arrangement with no undo. Additive instead -- focus a
  // column already showing this Seat, else append one -- and it performs the
  // tab switch the ambient version never did.
  $("#seat-open-control").onclick = () => {
    window.ControlHost?.openSeat(Number(seat.id));
    activateTab("control");
  };
  $("#seat-reindex").onclick = () => {
    const next = Number($("#seat-id").value);
    if (
      Number.isInteger(next) &&
      next >= 0 &&
      next !== Number(seat.id) &&
      confirm(`Change Seat ID ${seat.id} to ${next}? Live parameter values follow the new ID.`)
    )
      ws.send("reindex_seat", { id: seat.id, new_id: next });
  };
  $("#seat-remove").onclick = () => {
    if (confirm(`Delete Seat ${seat.id}? Its live parameter values will also be removed.`)) ws.send("remove_seat", { id: seat.id });
  };
  panel.querySelectorAll("[data-seat-group]").forEach(
    (input) =>
      (input.onchange = () => {
        const next = new Set((seat.groups || []).map(Number));
        input.checked ? next.add(Number(input.dataset.seatGroup)) : next.delete(Number(input.dataset.seatGroup));
        seat.groups = [...next].sort((a, b) => a - b);
        ws.send("set_seat_groups", { id: Number(seat.id), groups: seat.groups });
        renderGroups();
        renderGroupMap();
        Spatial.render(installation, selectedSeat, selectSeat, ws, groupView());
      }),
  );
  const chosen = () => $("#seat-device").value;
  $("#seat-device").onchange = () => seatBindingDrafts.set(seat.id, chosen());
  $("#seat-identify").onclick = () => {
    const uid = chosen();
    if (uid && installation.devices?.[uid]) ws.send("identify", { uid });
  };
  $("#seat-bind").onclick = () => {
    const uid = chosen();
    if (!uid) return;
    const replacing = seat.bound && seat.bound !== uid;
    if (!replacing || confirm(`Replace ${seat.bound} with ${uid} on Seat ${seat.id}?`))
      ws.send("bind_seat", { id: seat.id, uid, confirmed: !!replacing });
  };
  const unbind = $("#seat-unbind");
  if (unbind)
    unbind.onclick = () => {
      if (confirm(`Unassign ${seat.bound} from Seat ${seat.id}?`)) ws.send("unbind_seat", { id: seat.id });
    };
}

function nextFreeId() {
  const used = new Set(Object.values(installation.seats || {}).map((s) => Number(s.id)));
  let id = 0;
  while (used.has(id)) id++;
  return id;
}

function groupMemberRow({ search, seatQuery, seat, checked, sync }) {
  return [
    `<label class="membership-check" data-group-member-filter="${esc(search)}" ${seatQuery && !search.startsWith(seatQuery) ? "hidden" : ""}>`,
    `<input type="checkbox" data-group-member="${seat.id}" ${checked ? "checked" : ""}><span><strong>${esc(seat.name || `Seat ${seat.id}`)}</strong>`,
    `<small>Seat ${seat.id} · ${esc(sync)}</small>`,
    `</span>`,
    `</label>`,
  ].join("");
}

function groupDetailMarkup({ active, members, memberRows, seatQuery }) {
  return [
    `<section class="group-detail">`,
    `<div class="group-detail-head">`,
    `<div><strong>${esc(active.name)}</strong>`,
    `<small>g${active.id} · ${members.length} ${members.length === 1 ? "Seat" : "Seats"}</small>`,
    `</div>`,
    `<button id="group-show-map">Show on map</button>`,
    `</div>`,
    `<label class="group-filter">Filter Seats <input id="group-member-filter" ` +
      `type="text" placeholder="Names beginning with…" value="${esc(groupMemberFilter)}"></label>`,
    `<div class="membership-list">${memberRows || '<p class="dim">No Seats to add yet.</p>'}</div>`,
    `<p id="group-filter-empty" class="dim" ${
      seatQuery &&
      memberRows &&
      !Object.values(installation.seats || {}).some((seat) =>
        String(seat.name || `Seat ${seat.id}`)
          .trim()
          .toLowerCase()
          .startsWith(seatQuery),
      )
        ? ""
        : "hidden"
    }>No Seat names begin with this filter.</p>`,
    `</section>`,
  ].join("");
}

function seatPositionRow(index, position, origin) {
  return [
    `<div class="position-row" data-seat-element="${index}"><strong>element ${index}</strong>`,
    `<label>x <input data-axis="x" type="number" step="0.01" value="${Math.round((position[0] - origin[0]) * 100) / 100}"></label>`,
    `<label>y <input data-axis="y" type="number" step="0.01" value="${Math.round((position[1] - origin[1]) * 100) / 100}"></label>`,
    `<button data-remove-element="${index}" class="danger">Remove</button>`,
    `</div>`,
  ].join("");
}

function seatGroupMembership(group, seat) {
  return [
    `<label class="membership-check">`,
    `<input type="checkbox" data-seat-group="${
      group.id
      }" ${
      (seat.groups || []).includes(Number(group.id)) ? "checked" : ""
      }><span><strong>${
      esc(group.name)
      }</strong>`,
    `<small>g${group.id}</small>`,
    `</span>`,
    `</label>`,
  ].join("");
}
