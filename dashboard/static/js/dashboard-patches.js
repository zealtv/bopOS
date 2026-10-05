// Patches workspace and the local manifest/audition editor.
function projectPatches() {
  return Array.isArray(installation.patches) ? installation.patches : [];
}
function catalogPatch(name) {
  return (distribution.patches || []).find((item) => item.name === name) || null;
}
function patchEngine(item) {
  const manifest = item?.manifest && typeof item.manifest === "object" ? item.manifest : {};
  return [manifest.engine ?? item?.engine, manifest.entrypoint ?? item?.entrypoint].filter(Boolean).join(" · ");
}
// New Version's suggested name: bump a trailing number (kite-v2 -> kite-v3,
// keeping zero padding), else append -v2; skip names the catalog already has.
function nextVersionName(live, taken) {
  let name = live;
  do {
    const match = /^(.*?)(\d+)$/.exec(name);
    name = match ? `${match[1]}${String(Number(match[2]) + 1).padStart(match[2].length, "0")}` : `${name}-v2`;
  } while (taken.has(name));
  return name;
}
function focusSelectedPatch() {
  requestAnimationFrame(() => ($("#patch-list .patch-item.selected") || $("#patch-filter"))?.focus());
}
function selectPatch(name) {
  if (name === editorPatchChoice) return;
  editorPatchChoice = name;
  manifestDraft = null;
  manifestBaseline = null;
  manifestDirty = false;
  manifestFeedback = "";
  render();
}
function launchEditor(patch) {
  const editor = installation.editor || {},
    mode = installation.supervisor?.mode || "off";
  if (editor.active && editor.patch === patch) {
    if (confirm("Stop Patch edit and return audio control to the Live fleet?")) ws.send("set_edit", { active: false, confirmed: true });
    return;
  }
  if (mode !== "edit") {
    const question =
      mode === "simulate"
        ? `Stop the running Simulation and edit "${patch}"?`
        : `Open "${patch}" in Patch edit? Live fleet devices will not be driven.`;
    if (!confirm(question)) return;
  }
  ws.send("set_edit", { active: true, patch, confirmed: mode !== "edit" });
}
function deployPatch(name) {
  if (
    confirm(
      `Deploy "${name}" as the fleet patch? The dashboard will converge patch bytes, then restart ` +
        `audio engines across online assigned devices.`,
    )
  )
    ws.send("set_fleet_patch", { patch: name, confirmed: true });
}
function patchPushList() {
  return `<ul id="patch-push-list">${Object.values(installation.devices || {}).map((device) => {
    const reason = patchPushReason(device);
    return `<li data-push-uid="${esc(device.uid)}"><strong>${esc(Identity.primary(device, installation))}</strong> <span class="dim">${esc(reason || "Will receive patch")}</span></li>`;
  }).join("")}</ul>`;
}
function renderPatchesTab() {
  const list = $("#patch-list"),
    detail = $("#patch-detail");
  if (!list || !detail) return;
  const live = installation.fleet_patch?.name || "";
  const editor = installation.editor || {},
    editing = installation.supervisor?.mode === "edit";
  const names = projectPatches();
  const filter = $("#patch-filter");
  filter.oninput = () => {
    patchFilter = filter.value;
    renderPatchesTab();
  };
  const needle = patchFilter.trim().toLowerCase();
  const shown = names.filter((name) => !needle || name.toLowerCase().includes(needle));
  list.innerHTML = shown
    .map((name) => {
      const item = catalogPatch(name);
      const note = name === live ? fleetPatchSummary() : item?.valid ? patchEngine(item).split(" · ")[0] : PATCH_BADGE_LABELS.missing;
      return patchRosterRow(name, note, live);
    })
    .join("");
  list.querySelectorAll("[data-patch]").forEach((button) => {
    button.onclick = () => selectPatch(button.dataset.patch);
  });
  $("#refresh-distribution").onclick = () => ws.send("refresh_distribution", {});
  const taken = new Set((distribution.patches || []).map((item) => item.name));
  const newVersion = $("#patch-new-version");
  newVersion.disabled = performanceActive() || !live || !catalogPatch(live)?.valid;
  newVersion.onclick = () => openVersionDialog(live, taken);
  const addable = (distribution.patches || []).filter((item) => item.valid && !names.includes(item.name)).map((item) => item.name);
  const addExisting = $("#patch-add-existing");
  addExisting.disabled = !addable.length;
  addExisting.onclick = () => {
    $("#patch-add-select").innerHTML = addable.map((name) => `<option value="${esc(name)}">${esc(name)}</option>`).join("");
    $("#patch-add-dialog").showModal();
  };
  $("#patch-add-dialog").onclose = () => {
    const dialog = $("#patch-add-dialog"),
      name = $("#patch-add-select").value;
    if (dialog.returnValue === "add" && name) {
      pendingCreatedPatch = name;
      ws.send("add_project_patch", { patch: name });
    }
  };
  const patch = editorPatchChoice,
    item = catalogPatch(patch);
  if (!patch) {
    detail.innerHTML = `<p class="dim">${esc(fleetPatchSummary())}</p>`;
    return;
  }
  const isLive = patch === live,
    editingThis = editor.active && editor.patch === patch;
  const lastPushed =
    isLive && installation.fleet_patch?.staged_at
      ? new Date(installation.fleet_patch.staged_at * 1000).toLocaleString([], {
          day: "numeric",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "";
  detail.innerHTML = [
    `<div class="patch-detail-head"><h2>${esc(patch)}${isLive ? ' <span class="patch-live-tag">Live</span>' : ""}</h2>`,
    `<div class="patch-detail-actions">`,
    `<button id="patch-edit">${editingThis ? "Stop Editor" : "Edit"}</button>`,
    `<button id="patch-deploy">${isLive ? "Push" : "Set Live"}</button>`,
    `</div>`,
    `</div>
    <p class="dim">${
          isLive
            ? "The live fleet runs this patch. Edit and push it in place, or make a New Version."
            : "Not live. Set Live pushes it to the fleet and switches every device to it."
      }</p>
    <dl>`,
    `<dt>Devices</dt>`,
    `<dd>${
      isLive ? `<output id="fleet-patch-summary">${
      esc(fleetPatchSummary())
      }</output>` : live ? `on ${
      esc(live)
      } (live)` : esc(fleetPatchSummary())
      }</dd>${
      lastPushed ? `<dt>Last pushed</dt><dd>${
      esc(lastPushed)
      }</dd>` : ""
      }<dt>Engine</dt>`,
    `<dd>${esc(item?.valid ? patchEngine(item) : PATCH_BADGE_LABELS.missing)}</dd>`,
    `</dl>`,
    `<h3>Push targets</h3>${patchPushList()}`,
  ].join("");
  const edit = $("#patch-edit"),
    deploy = $("#patch-deploy");
  edit.disabled = performanceActive() || (!item?.valid && !editingThis);
  edit.onclick = () => launchEditor(patch);
  deploy.disabled = performanceActive() || !item?.valid || editing;
  deploy.onclick = () => deployPatch(patch);
}
function openVersionDialog(live, taken) {
  const dialog = $("#patch-version-dialog"),
    input = $("#patch-version-name"),
    error = $("#patch-version-error"),
    create = $("#patch-version-create");
  dialog.querySelectorAll("[data-patch-version-live]").forEach((node) => {
    node.textContent = live;
  });
  input.value = nextVersionName(live, taken);
  const check = () => {
    const name = input.value.trim();
    const exists = taken.has(name);
    error.textContent = exists ? `Patch '${name}' already exists.` : "";
    create.disabled = !name || exists;
  };
  input.oninput = check;
  check();
  dialog.onclose = () => {
    const name = input.value.trim();
    if (dialog.returnValue === "create" && name && !taken.has(name)) {
      pendingCreatedPatch = name;
      ws.send("new_patch_version", { name });
    }
  };
  dialog.returnValue = "";
  dialog.showModal();
  input.select();
}

function manifestSource(editor, patches, patch) {
  const item = patches.find((candidate) => candidate.name === patch) || {};
  const embedded = item.manifest && typeof item.manifest === "object" ? item.manifest : {};
  const current = editor.patch === patch ? editor : {};
  const params = current.declarations || embedded.params || item.params || item.declarations;
  const events = current.events || embedded.events || item.events;
  return {
    engine: current.engine ?? embedded.engine ?? item.engine,
    entrypoint: current.entrypoint ?? embedded.entrypoint ?? item.entrypoint,
    caps: current.caps ?? embedded.caps ?? item.caps ?? [],
    slots: current.slots ?? embedded.slots ?? item.slots ?? [],
    params: Array.isArray(params) ? params : [],
    events: Array.isArray(events) ? events : [],
    io_modules: current.io_modules || embedded.io_modules || [],
    available: Array.isArray(params) || Array.isArray(events) || Boolean(current.engine || embedded.engine || item.engine),
    editable: Boolean(!performanceActive() && editor.active && editor.patch === patch),
  };
}
function resetManifestDraft(patch, source) {
  manifestDraft = {
    patch,
    params: structuredClone(source.params),
    events: structuredClone(source.events),
    io_modules: structuredClone(source.io_modules),
  };
  manifestBaseline = structuredClone(manifestDraft);
  manifestDirty = false;
}
function manifestValue(value) {
  if (Array.isArray(value))
    return value.length ? value.map((item) => (typeof item === "string" ? item : JSON.stringify(item))).join(", ") : "none";
  return value ?? "—";
}
function paramIdentity(param) {
  const path = Array.isArray(param?.path) ? param.path : [];
  return [...path, param?.name || ""].join("/");
}
function manifestParamsForSave(params) {
  return structuredClone(params).map((param) => {
    if (!Array.isArray(param.path) || !param.path.length) delete param.path;
    if (param.kind === "toggle" || param.kind === "enum") {
      delete param.min;
      delete param.max;
    }
    delete param.group;
    delete param.facilitator;
    return param;
  });
}
function manifestEventsForSave(events) {
  return events.map((declaration) => {
    const arity = Math.min(3, Math.max(0, Math.trunc(Number(declaration.arity) || 0)));
    const defaults = Array.isArray(declaration.defaults) ? declaration.defaults : [];
    return {
      name: String(declaration.name || ""),
      arity,
      defaults: Array.from({ length: arity }, (_unused, index) => Number(defaults[index]) || 0),
      dashboard: declaration.dashboard === true,
    };
  });
}
function setManifestParamKind(param, kind) {
  param.kind = kind;
  if (kind === "float" || kind === "int") {
    delete param.options;
    if (typeof param.min !== "number") param.min = 0;
    if (typeof param.max !== "number") param.max = 1;
    if (typeof param.default !== "number") param.default = 0;
  } else if (kind === "toggle") {
    delete param.options;
    delete param.min;
    delete param.max;
    param.default = Number(param.default) === 1 ? 1 : 0;
  } else if (kind === "enum") {
    delete param.min;
    delete param.max;
    if (!Array.isArray(param.options) || param.options.length < 2) param.options = ["option 0", "option 1"];
    if (!Number.isInteger(param.default) || param.default < 0 || param.default >= param.options.length) param.default = 0;
  } else {
    delete param.options;
    delete param.min;
    delete param.max;
    if (typeof param.default !== "string") param.default = "";
  }
}
function paramManifestRow(param, index) {
  const kind = param.kind || "float";
  const path = Array.isArray(param.path) ? param.path.join("/") : "";
  const bounds =
    kind === "float" || kind === "int"
      ? [
          `
    <label>min<input data-manifest-field="min" type="number" step="any" value="${esc(param.min ?? "")}"></label>
    <label>max<input data-manifest-field="max" type="number" step="any" value="${esc(param.max ?? "")}"></label>`,
        ].join("")
      : "";
  const options =
    kind === "enum"
      ? `<label>options · one per line<textarea data-manifest-field="options" rows="2">${esc((param.options || []).join("\n"))}</textarea></label>`
      : "";
  const defaultType = kind === "text" ? "text" : "number";
  return [
    `<div class="manifest-row manifest-param" data-param-index="${index}">
    <button type="button" class="manifest-drag-handle" data-manifest-drag="params" data-manifest-drag-index="${
      index
      }" aria-label="Drag parameter ${
      esc(paramIdentity(param) || index + 1)
      }">⋮⋮</button>
    <label>path<input data-manifest-field="path" type="text" value="${esc(path)}" placeholder="e.g. instrument/marimba" autocomplete="off"></label>
    <label>name<input data-manifest-field="name" type="text" value="${esc(param.name || "")}" autocomplete="off"></label>
    <label>kind<select data-manifest-field="kind">${
      ["float", "int", "toggle", "enum", "text"].map((value) => `<option value="${
      value
      }" ${
      kind === value ? "selected" : ""
      }>${
      value
      }</option>`).join("")
      }</select>`,
    `</label>
    ${bounds}${options}
    <label>default<input data-manifest-field="default" type="${
      defaultType
      }" ${
      defaultType === "number" ? 'step="any"' : ""
      } value="${
      esc(param.default ?? "")
      }"></label>
    <label class="manifest-check">`,
    `<input data-manifest-field="dashboard" type="checkbox" ${param.dashboard === true ? "checked" : ""}> Remote</label>
    <button data-remove-param="${index}" class="danger">Remove</button>
  </div>`,
  ].join("");
}
function eventManifestRow(declaration, index) {
  const arity = Math.min(3, Math.max(0, Math.trunc(Number(declaration.arity) || 0)));
  const defaults = Array.isArray(declaration.defaults) ? declaration.defaults : [];
  const elements = Array.from(
    { length: arity },
    (_unused, element) => `
    <label>element ${element}<input data-event-default="${element}" type="number" step="any" value="${esc(defaults[element] ?? 0)}"></label>`,
  ).join("");
  return [
    `<div class="manifest-row manifest-event" data-event-index="${index}" data-arity="${arity}">
    <button type="button" class="manifest-drag-handle" data-manifest-drag="events" data-manifest-drag-index="${
      index
      }" aria-label="Drag event ${
      esc(declaration.name || index + 1)
      }">⋮⋮</button>
    <label>name<input data-manifest-field="name" type="text" value="${esc(declaration.name || "")}" autocomplete="off"></label>
    <label>arity<input data-manifest-field="arity" type="number" min="0" max="3" step="1" value="${arity}"></label>
    ${elements}
    <label class="manifest-check">`,
    `<input data-manifest-field="dashboard" type="checkbox" ${declaration.dashboard === true ? "checked" : ""}> Remote</label>
    <button data-remove-event="${index}" class="danger">Remove</button>
  </div>`,
  ].join("");
}
function bindManifestEditor(source) {
  document.querySelectorAll(".manifest-io").forEach((row) => {
    const index = Number(row.dataset.ioIndex);
    row.querySelectorAll("[data-io-field]").forEach((input) => {
      input.oninput = input.onchange = () => {
        manifestDraft.io_modules[index][input.dataset.ioField] = input.type === "checkbox" ? input.checked : input.value;
        manifestDirty = true;
      };
    });
    row.querySelector("[data-remove-io]").onclick = () => {
      manifestDraft.io_modules.splice(index, 1);
      manifestDirty = true;
      renderManifestEditor(source);
    };
  });
  document.querySelectorAll(".manifest-param").forEach((row) => {
    const index = Number(row.dataset.paramIndex);
    row.querySelectorAll("[data-manifest-field]").forEach((input) => {
      const update = () => {
        const field = input.dataset.manifestField;
        if (field === "kind") {
          setManifestParamKind(manifestDraft.params[index], input.value);
          manifestDirty = true;
          renderManifestEditor(source);
          return;
        }
        if (field === "path") {
          manifestDraft.params[index][field] = input.value === "" ? [] : input.value.split("/");
        } else if (field === "options") {
          manifestDraft.params[index][field] = input.value.split("\n");
        } else if (input.type === "checkbox") {
          manifestDraft.params[index][field] = input.checked;
        } else if (input.type === "number") {
          manifestDraft.params[index][field] = input.value === "" ? "" : Number(input.value);
        } else {
          manifestDraft.params[index][field] = input.value;
        }
        manifestDirty = true;
      };
      input.oninput = update;
      input.onchange = update;
    });
  });
  document.querySelectorAll(".manifest-event").forEach((row) => {
    const index = Number(row.dataset.eventIndex);
    manifestDraft.events[index].defaults = Array.isArray(manifestDraft.events[index].defaults) ? manifestDraft.events[index].defaults : [];
    row.querySelectorAll("[data-manifest-field]").forEach((input) => {
      const update = () => {
        const declaration = manifestDraft.events[index];
        const field = input.dataset.manifestField;
        if (field === "arity") {
          const arity = Math.min(3, Math.max(0, Math.trunc(Number(input.value) || 0)));
          declaration.arity = arity;
          declaration.defaults = Array.from({ length: arity }, (_unused, element) => Number(declaration.defaults?.[element]) || 0);
          manifestDirty = true;
          renderManifestEditor(source);
          return;
        }
        declaration[field] = input.type === "checkbox" ? input.checked : input.value;
        manifestDirty = true;
      };
      input.oninput = update;
      input.onchange = update;
    });
    row.querySelectorAll("[data-event-default]").forEach(
      (input) =>
        (input.oninput = () => {
          manifestDraft.events[index].defaults[Number(input.dataset.eventDefault)] = Number(input.value) || 0;
          manifestDirty = true;
        }),
    );
  });
  document.querySelectorAll("[data-remove-param]").forEach(
    (button) =>
      (button.onclick = () => {
        const param = manifestDraft.params[Number(button.dataset.removeParam)];
        if (
          !confirm(
            `Remove parameter "${paramIdentity(param) || "unnamed"}"? Engine routes do not change automatically; update the corresponding route in the patch.`,
          )
        )
          return;
        manifestDraft.params.splice(Number(button.dataset.removeParam), 1);
        manifestDirty = true;
        renderManifestEditor(source);
      }),
  );
  document.querySelectorAll("[data-remove-event]").forEach(
    (button) =>
      (button.onclick = () => {
        manifestDraft.events.splice(Number(button.dataset.removeEvent), 1);
        manifestDirty = true;
        renderManifestEditor(source);
      }),
  );
  bindManifestReorder(source);
}
function clearManifestDropMarkers() {
  document.querySelectorAll(".manifest-drop-before,.manifest-drop-after").forEach((row) => {
    row.classList.remove("manifest-drop-before", "manifest-drop-after");
  });
}
function manifestDropAt(kind, clientY) {
  const container = $(kind === "params" ? "#manifest-params" : "#manifest-events");
  const selector = kind === "params" ? ".manifest-param" : ".manifest-event";
  if (!container) return null;
  const bounds = container.getBoundingClientRect();
  if (clientY < bounds.top || clientY > bounds.bottom) {
    clearManifestDropMarkers();
    return null;
  }
  const rows = [...container.querySelectorAll(selector)].filter((row) => row !== manifestDrag?.row);
  let index = 0,
    next = null;
  for (const row of rows) {
    const rowBounds = row.getBoundingClientRect();
    if (clientY < rowBounds.top + rowBounds.height / 2) {
      next = row;
      break;
    }
    index += 1;
  }
  clearManifestDropMarkers();
  if (next) next.classList.add("manifest-drop-before");
  else if (rows.length) rows[rows.length - 1].classList.add("manifest-drop-after");
  return index;
}
function finishManifestDrag(event, commit, source) {
  if (!manifestDrag || event.pointerId !== manifestDrag.pointerId) return;
  const drag = manifestDrag;
  manifestDrag = null;
  if (drag.handle.hasPointerCapture?.(event.pointerId)) drag.handle.releasePointerCapture(event.pointerId);
  drag.row.classList.remove("manifest-dragging");
  $("#manifest-editor")?.classList.remove("manifest-drag-active");
  clearManifestDropMarkers();
  if (commit && drag.active && drag.drop !== null) {
    const items = manifestDraft[drag.kind];
    const [item] = items.splice(drag.index, 1);
    items.splice(drag.drop, 0, item);
    if (drag.drop !== drag.index) manifestDirty = true;
    renderManifestEditor(source);
  }
  if (drag.active) event.preventDefault();
}
function bindManifestReorder(source) {
  const panel = $("#manifest-editor");
  if (!panel) return;
  panel.onpointerdown = (event) => {
    if (event.button !== 0 || manifestDrag) return;
    const handle = event.target.closest("[data-manifest-drag]");
    if (!handle || handle.disabled) return;
    manifestDrag = {
      pointerId: event.pointerId,
      kind: handle.dataset.manifestDrag,
      index: Number(handle.dataset.manifestDragIndex),
      handle,
      row: handle.closest(".manifest-row"),
      startX: event.clientX,
      startY: event.clientY,
      active: false,
      drop: null,
    };
    handle.focus();
    handle.setPointerCapture(event.pointerId);
    event.preventDefault();
  };
  panel.onpointermove = (event) => {
    if (!manifestDrag || event.pointerId !== manifestDrag.pointerId) return;
    const distance = Math.hypot(event.clientX - manifestDrag.startX, event.clientY - manifestDrag.startY);
    if (!manifestDrag.active && distance < 7) return;
    if (!manifestDrag.active) {
      manifestDrag.active = true;
      manifestDrag.row.classList.add("manifest-dragging");
      panel.classList.add("manifest-drag-active");
    }
    if (event.clientY < 70) window.scrollBy(0, -14);
    else if (event.clientY > window.innerHeight - 70) window.scrollBy(0, 14);
    manifestDrag.drop = manifestDropAt(manifestDrag.kind, event.clientY);
    event.preventDefault();
  };
  panel.onpointerup = (event) => finishManifestDrag(event, true, source);
  panel.onpointercancel = (event) => finishManifestDrag(event, false, source);
}
function renderManifestEditor(source) {
  const panel = $("#manifest-editor");
  if (!panel) return;
  const patch = editorPatchChoice;
  panel.hidden = !patch;
  if (!patch) return;
  if (
    !manifestDraft ||
    manifestDraft.patch !== patch ||
    (!manifestDirty &&
      JSON.stringify({ params: source.params, events: source.events, io_modules: source.io_modules }) !==
        JSON.stringify({ params: manifestDraft.params, events: manifestDraft.events, io_modules: manifestDraft.io_modules }))
  ) {
    resetManifestDraft(patch, source);
  }
  $("#manifest-readonly").innerHTML =
    `<dl><dt>Engine</dt><dd>${
      esc(manifestValue(source.engine))
      }</dd><dt>Entrypoint</dt><dd>${
      esc(manifestValue(source.entrypoint))
      }</dd><dt>Capabilities</dt><dd>${
      esc(manifestValue(source.caps))
      }</dd><dt>Asset slots</dt><dd>${
      esc(manifestValue(source.slots))
      }</dd></dl>`;
  $("#manifest-params").innerHTML = manifestDraft.params.map(paramManifestRow).join("") || '<p class="dim">No parameters declared.</p>';
  $("#manifest-events").innerHTML = manifestDraft.events.map(eventManifestRow).join("") || '<p class="dim">No events declared.</p>';
  $("#manifest-io").innerHTML =
    manifestDraft.io_modules
      .map((module, index) =>
        [
          `
    <div class="manifest-row manifest-io" data-io-index="${index}">
      <label>Name<input data-io-field="name" value="${esc(module.name)}"></label>
      <label>Type<select data-io-field="type">${Object.keys(installation.io_types || {})
        .map((type) => `<option ${module.type === type ? "selected" : ""}>${esc(type)}</option>`)
        .join("")}</select>`,
          `</label>
      <label>Address<input data-io-field="address" value="${esc(module.address)}" placeholder="0x48"></label>
      <label class="manifest-check">`,
          `<input data-io-field="optional" type="checkbox" ${module.optional ? "checked" : ""}>Optional</label>
      <button data-remove-io="${index}" aria-label="Remove IO module" title="Remove IO module">✕</button>
    </div>`,
        ].join(""),
      )
      .join("") || '<p class="dim">No IO modules declared.</p>';
  const addIO = $("#manifest-add-io");
  addIO.disabled = !source.editable;
  addIO.onclick = () => {
    manifestDraft.io_modules.push({ name: "", type: "ads1115", address: "0x48", optional: false });
    manifestDirty = true;
    renderManifestEditor(source);
  };
  $("#manifest-feedback").textContent =
    manifestFeedback ||
    (source.editable
      ? "Path/name changes create a new OSC identity; engine routes never change automatically."
      : "Launch this patch in edit mode to change its manifest.");
  const addParam = $("#manifest-add-param"),
    addEvent = $("#manifest-add-event");
  addParam.disabled = !source.editable;
  addEvent.disabled = !source.editable;
  addParam.onclick = () => {
    manifestDraft.params.push({ path: [], name: "", kind: "float", min: 0, max: 1, default: 0, dashboard: false });
    manifestDirty = true;
    renderManifestEditor(source);
  };
  addEvent.onclick = () => {
    manifestDraft.events.push({ name: "", arity: 0, defaults: [], dashboard: false });
    manifestDirty = true;
    renderManifestEditor(source);
  };
  const save = $("#manifest-save");
  save.disabled = !source.available || !source.editable;
  save.title = !source.available
    ? "Manifest data is not available for this patch."
    : !source.editable
      ? "Launch this patch in the editor before saving."
      : "";
  save.onclick = () => {
    const before = (manifestBaseline?.params || []).map(paramIdentity);
    const after = manifestDraft.params.map(paramIdentity);
    const changed = before.filter((identity) => identity && !after.includes(identity));
    if (
      changed.length &&
      !confirm(
        `Save parameter move/rename/removal (${changed.map((item) => `/p/${item}`).join(", ")})? Engine routes do not follow manifest changes.`,
      )
    )
      return;
    manifestFeedback = "Saving manifest…";
    ws.send("save_patch_manifest", {
      patch,
      params: manifestParamsForSave(manifestDraft.params),
      events: manifestEventsForSave(manifestDraft.events),
      io_modules: structuredClone(manifestDraft.io_modules),
    });
    save.blur();
    $("#manifest-feedback").textContent = manifestFeedback;
  };
  bindManifestEditor(source);
  if (!source.editable)
    panel.querySelectorAll("input,select,textarea,button").forEach((control) => {
      control.disabled = true;
    });
}

function canonicalRemoteCommands(value) {
  const selected = new Set(Array.isArray(value) ? value : []);
  return REMOTE_COMMANDS.filter((command) => selected.has(command));
}
function sameRemoteCommands(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}
// Remote device commands save on click (mockup 1): each change sends the
// whole selection; the checkboxes follow the project state again once it
// reflects the last selection sent.
function renderRemoteCommandEditor() {
  const current = canonicalRemoteCommands(installation.facilitator_commands);
  if (remoteCommandSaving && sameRemoteCommands(current, remoteCommandDraft)) {
    remoteCommandSaving = false;
    remoteCommandFeedback = "Saved project setting.";
  }
  if (!remoteCommandSaving) remoteCommandDraft = [...current];
  document.querySelectorAll("[data-remote-command]").forEach((input) => {
    input.checked = remoteCommandDraft.includes(input.dataset.remoteCommand);
    input.onchange = () => {
      remoteCommandDraft = REMOTE_COMMANDS.filter((command) => {
        const option = document.querySelector(`[data-remote-command="${command}"]`);
        return option?.checked;
      });
      remoteCommandSaving = true;
      remoteCommandFeedback = "Saving project setting…";
      ws.send("set_facilitator_commands", { commands: [...remoteCommandDraft] });
      renderRemoteCommandEditor();
    };
  });
  $("#remote-command-feedback").textContent = remoteCommandFeedback;
}

function renderEditorPreview(editor) {
  Spatial.renderEditor(editor, ws);
  const free = $("#editor-event-identity"),
    fire = $("#editor-event-fire");
  if (!free || !fire || !editor.active) return;
  const send = (identity, elements = []) => {
    if (!identity) return;
    ws.send("fire_editor_event", { identity, elements });
    $("#editor-event-status").value = `Firing ${identity}…`;
  };
  fire.onclick = () => send(free.value.trim());
  free.onkeydown = (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      fire.click();
    }
  };
}
function renderEditor() {
  renderRemoteCommandEditor();
  $("#editor-panel").hidden = performanceActive();
  if (performanceActive()) {
    for (const selector of ["#patch-version-dialog", "#patch-add-dialog"]) {
      const dialog = $(selector);
      if (dialog?.open) dialog.close("cancel");
    }
  }
  const editor = installation.editor || { active: false, status: "off", declarations: [], params: {} };
  const patches = (distribution.patches || []).filter((item) => item.valid);
  // The Patches list is the picker: keep a chosen patch while it is the
  // project's (or the one being edited); otherwise the edited one, the Patch,
  // or the first of the project's patches.
  const names = projectPatches();
  const selectable = (name) => name && (names.includes(name) || name === editor.patch);
  // A patch just created, versioned or added is selected once it is both in
  // the catalog and the project's.
  if (pendingCreatedPatch && names.includes(pendingCreatedPatch) && patches.some((item) => item.name === pendingCreatedPatch)) {
    editorPatchChoice = pendingCreatedPatch;
    pendingCreatedPatch = null;
    manifestDraft = null;
    manifestBaseline = null;
    manifestDirty = false;
  }
  if (!selectable(editorPatchChoice)) {
    editorPatchChoice = [editor.active ? editor.patch : null, installation.fleet_patch?.name, names[0]].find(selectable) || null;
  }
  const newPatch = $("#editor-new-patch");
  newPatch.disabled = performanceActive();
  newPatch.onclick = () => {
    const name = prompt("New patch name (letters, numbers, . _ or -):", "")?.trim();
    if (!name) return;
    manifestFeedback = `Creating ${name}…`;
    ws.send("create_patch", { name });
    renderEditor();
  };
  $("#editor-status").textContent = editor.active ? `${editor.status || "running"} · ${editor.patch}` : editor.status || "off";
  const closed = editor.active && editor.engine_alive != null && Number(editor.engine_alive) === 0;
  const engineNote = $("#editor-engine-note");
  engineNote.hidden = !editor.active;
  engineNote.textContent = !editor.active
    ? ""
    : closed
      ? "Engine closed. It will stay closed until you explicitly relaunch it."
      : editor.engine === "pd"
        ? "PD is open for live editing."
        : "Runtime controls are live; GUI editing is PD-only in v1.";
  const actions = $("#editor-session-actions");
  actions.innerHTML = editor.active && closed ? `<button id="editor-relaunch">Relaunch</button>` : "";
  $("#editor-relaunch")?.addEventListener("click", () => ws.send("relaunch_edit", {}));
  const focused = document.activeElement;
  const source = manifestSource(editor, patches, editorPatchChoice);
  if (!manifestDrag && !$("#manifest-editor").contains(focused)) renderManifestEditor(source);
  renderEditorPreview(editor);
  if ((interacting || focused?.matches?.('input[type="text"], input[type="number"], select')) && $("#editor-panel").contains(focused))
    return;
  const declarations = editorControlDeclarations(editor);
  const editorMember = {
    id: 0,
    automation_key: "editor",
    params: editor.params || {},
  };
  $("#editor-params").innerHTML = editor.active ? editorControlsMarkup(declarations, editorMember) : "";
  editorSurface.bind($("#editor-params"));
  const editorMaster = $("#editor-master");
  if (editorMaster) {
    editorMaster.oninput = () => {
      master = Number(editorMaster.value);
      editorMaster.previousElementSibling.value = Math.round(master * 100) + "%";
      ws.send("set_master", { value: master });
    };
    // Master is a 0..1 level shown as integer percent; precision entry drives it
    // in whole percent to match the readout and the slider's 1% step
    // (40-precision-param-input).
    const masterOut = editorMaster.previousElementSibling;
    if (masterOut?.dataset.precise === "true")
      window.PrecisionField.attach(
        masterOut,
        {
          min: 0,
          max: 100,
          integer: true,
          value: Math.round(master * 100),
          label: "master",
          disabled: false,
        },
        (value) => {
          master = value / 100;
          editorMaster.value = master;
          ws.send("set_master", { value: master });
        },
        (editing) => {
          if (!editing) renderEditor();
        },
      );
  }
}

function editorControlDeclarations(editor = installation.editor || {}) {
  const parameters = (editor.declarations || []).map((item) => ({
    ...item,
    path: item.path || [],
    identity: paramIdentity(item),
  }));
  const events = (editor.events || []).map((item) => ({
    ...item,
    kind: "event",
    path: item.path || [],
    identity: paramIdentity(item),
  }));
  return [...parameters, ...events];
}

// The editor is a one-member ControlSurface. It has no aggregate/mixed state:
// the member is the audition engine itself. Its automation key remains
// `editor` (not selector 0), matching the server-side isolation from Seat 0.
const editorSurface = window.ControlSurface.create({
  getState: () => ({
    ...installation,
    live_controls: { declarations: editorControlDeclarations() },
  }),
  send: ({ name, value }) => {
    const editor = installation.editor;
    if (editor) editor.params[name] = value;
    ws.send("set_editor_param", { name, value });
  },
  sendEvent: ({ identity, elements }) => {
    ws.send("fire_editor_event", { identity, elements });
    return 0;
  },
  sendAutomation: ({ name, args }) => ws.send("set_live_automation", { scope: "editor", id: null, name, args }),
  setInteracting: (editing) => {
    interacting = editing;
  },
  requestRender: () => renderEditor(),
});

function patchRosterRow(name, note, live) {
  return `<button type="button" class="patch-item${
    name === editorPatchChoice ? " selected" : ""
    }" data-patch="${
    esc(name)
    }"><span><strong>${
    esc(name)
    }</strong><small>${
    esc(note || "")
    }</small></span>${
    name === live ? '<span class="patch-live-tag">Live</span>' : ""
    }</button>`;
}

function editorControlsMarkup(declarations, editorMember) {
  return [
    `<div class="editor-master-row"><span>Audition master</span>`,
    `<output data-precise="true">${Math.round(master * 100)}%</output>`,
    `<input id="editor-master" type="range" min="0" max="1" step="0.01" value="${master}"></div>`,
    `<div class="promoted-controls">${
      declarations.length ? editorSurface.tree("editor", null, [editorMember], declarations, false) : '<p class="dim">No manifest controls.</p>'
      }</div>`,
  ].join("");
}
