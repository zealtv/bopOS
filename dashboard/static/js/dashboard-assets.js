// Asset catalog and observed inventory for one eligible physical device.
function formatBytes(value) {
  const bytes = Number(value) || 0;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function assetTargets() {
  const seats = Object.values(installation.seats || {}),
    devices = Object.values(installation.devices || {});
  const assigned = new Set(seats.map((seat) => seat.bound).filter(Boolean));
  return devices
    .map((device) => {
      const reasons = [];
      if (device.virtual) reasons.push("simulation");
      if (!device.online) reasons.push("offline");
      if (!device.virtual && !assigned.has(device.uid)) reasons.push("unassigned");
      return { device, reasons, eligible: reasons.length === 0 };
    })
    .sort(
      (a, b) =>
        Number(b.eligible) - Number(a.eligible) ||
        Identity.primary(a.device, installation).localeCompare(Identity.primary(b.device, installation)),
    );
}
// The picker prunes a stale or ineligible choice to the first eligible chip, so
// the "did the chosen device go away" fallback that used to live here is the
// component's (02-component-unification/07).
function selectedAssetDevice(targets = assetTargets()) {
  const chosen = assetPicker.selection()[0];
  return targets.find((target) => target.eligible && target.device.uid === chosen)?.device || null;
}
function assetInventoryState(device, item) {
  if (!device || device.assets === null || !Array.isArray(device.assets)) return { label: "unknown", installed: null };
  const installed = device.assets.find((asset) => asset.name === item.name);
  if (!installed) return { label: "absent", installed: null };
  if (installed.fingerprint === null || typeof installed.fingerprint !== "string") return { label: "unknown", installed };
  return { label: installed.fingerprint === item.fingerprint ? "current" : "stale", installed };
}
function assetFacts(item) {
  const modified = Number(item.modified);
  const timestamp = Number.isFinite(modified) && modified > 0 ? new Date(modified * 1000) : null;
  return [
    `<dl class="asset-facts">`,
    `<dt>Files</dt>`,
    `<dd>${item.files == null ? "unknown" : esc(item.files)}</dd>`,
    `<dt>Size</dt>`,
    `<dd>${item.bytes == null ? "unknown" : formatBytes(item.bytes)}</dd>`,
    `<dt>Modified</dt>`,
    `<dd>${timestamp ? `<time datetime="${timestamp.toISOString()}">${timestamp.toLocaleString()}</time>` : "unknown"}</dd>`,
    `<dt>Fingerprint</dt>`,
    `<dd>${copyIdentity(item.fingerprint)}</dd>`,
    `</dl>`,
  ].join("");
}
function assetLiveState(device, slot, observed) {
  const phase = device?.fetch?.[slot];
  if (phase === "sent" || phase === "queued") return "queued";
  if (phase === "fetching") return "fetching";
  if (phase === "err") return "failed";
  if (phase === "timeout") return "timed out";
  return observed;
}
function assetCatalogRow(device, item) {
  const observed = assetInventoryState(device, item),
    state = assetLiveState(device, item.name, observed.label);
  const pending = state === "queued" || state === "fetching";
  let action = "",
    actionLabel = "";
  if (observed.label === "absent") {
    action = "send";
    actionLabel = "Send";
  } else if (observed.label === "stale") {
    action = "update";
    actionLabel = "Update";
  } else if (observed.label === "unknown") {
    action = "send-update";
    actionLabel = "Send / update";
  }
  const unavailable = !device || pending;
  const reason = !device ? "Choose an online, assigned physical device" : pending ? "Transfer already in progress" : "";
  const target = device ? Identity.primary(device, installation) : "selected device";
  const primaryLabel = esc(`${actionLabel} ${item.name} to ${target}`);
  const primary = action
    ? `<button data-asset-action="${action}" aria-label="${primaryLabel}" ` +
      `${unavailable ? `disabled title="${esc(reason)}"` : ""}>${actionLabel}</button>`
    : "";
  // Remove is offered on any installed catalog pack (current/stale/unknown),
  // not just device-only extras. The active-slot warning lives in
  // confirmAssetAction; server + node treat the drop by name (39-remove-installed-pack-from-device).
  const removable = device && observed.installed;
  const remove = removable ? assetRemoveButton(device, item, pending) : "";
  const controls = `${primary}${remove}` || '<span class="asset-no-action">No action needed</span>';
  return [
    `<article class="asset-row" data-slot="${esc(item.name)}" data-state="${esc(state)}">`,
    `<div class="asset-row-main"><strong>${esc(item.name)}</strong>${assetFacts(item)}</div>`,
    `<span class="asset-state asset-state-${state.replace(/[^a-z0-9]+/gi, "-")}" role="status" aria-live="polite">${esc(state)}</span>`,
    `<div class="asset-row-action">${controls}</div>`,
    `</article>`,
  ].join("");
}
function assetExtraRow(device, item) {
  const state = assetLiveState(device, item.name, "extra"),
    pending = state === "queued" || state === "fetching";
  return [
    `<article class="asset-row asset-extra" data-slot="${esc(item.name)}" data-state="${esc(state)}">`,
    `<div class="asset-row-main"><strong>${esc(item.name)}</strong>${assetFacts(item)}</div>`,
    `<span class="asset-state asset-state-${state.replace(/[^a-z0-9]+/gi, "-")}" role="status" aria-live="polite">${esc(state)}</span>`,
    `<div class="asset-row-action">`,
    assetRemoveButton(device, item, pending),
    `</div>`,
    `</article>`,
  ].join("");
}
function assetIsActive(device, slot) {
  return Array.isArray(device?.active_asset_slots) && device.active_asset_slots.includes(slot);
}

function assetRemoveButton(device, item, pending) {
  const label = esc(`Remove ${item.name} from ${Identity.primary(device, installation)}`);
  return `<button class="danger" data-asset-action="remove" aria-label="${label}" ` +
    `${pending ? 'disabled title="Transfer already in progress"' : ""}>Remove</button>`;
}
function confirmAssetAction(device, slot, action) {
  const active = assetIsActive(device, slot);
  if (action === "remove") {
    if (active)
      return confirm(
        `Asset slot "${slot}" is declared by the active patch. Removing it can immediately break the running ` +
          `patch. Safer sequence: send a new side-by-side generation, switch the patch, ` +
          `then remove the old slot. Remove anyway?`,
      );
    return confirm(`Remove asset slot "${slot}" from ${Identity.primary(device, installation)}?`);
  }
  if (active && action !== "send")
    return confirm(
      `Asset slot "${slot}" is declared by the active patch. Updating it in place can expose the running ` +
        `engine to a partial update or broken files. Safer sequence: send a new ` +
        `side-by-side generation, switch the patch, then remove the old slot. ${action === "update" ? "Update" : "Send / update"} anyway?`,
    );
  return true;
}
function resolveAssetFeedback(device) {
  const pending = assetFeedbackPending;
  if (!pending || !device || device.uid !== pending.uid || !Array.isArray(device.assets)) return;
  const observedAt = Number(device.assets_observed_at) || 0;
  if (observedAt <= pending.observedAt) return;
  const installed = device.assets.find((item) => item.name === pending.slot);
  const resolved = pending.action === "remove" ? !installed : installed?.fingerprint === pending.fingerprint;
  if (!resolved) return;
  assetFeedback =
    pending.action === "remove"
      ? `Removed ${pending.slot} from ${Identity.primary(device, installation)}; confirmed by observed inventory.`
      : `${pending.slot} is current on ${Identity.primary(device, installation)}; confirmed by observed inventory.`;
  assetFeedbackPending = null;
}
// The device domain of the shared target picker: one device, no All, and every
// discovered device present — an ineligible one is visible but disabled, wearing
// the reason it cannot be chosen (the Assets workflow is single-device by
// design, thread 11b).
const assetPicker = window.TargetPicker.create({
  host: $("#asset-target-host"),
  id: "assets",
  storageKey: "bopos.target.assets",
  spec: () => ({
    label: "device",
    allowAll: false,
    multiple: false,
    emptySummary: "No devices discovered",
    emptyTerse: "none",
    sections: window.TargetPicker.deviceSections(
      assetTargets().map((target) => ({
        uid: target.device.uid,
        label: Identity.primary(target.device, installation),
        sub: target.reasons.join(", ") || null,
        title: target.reasons.length ? target.reasons.join(" · ") : null,
        disabled: !target.eligible,
      })),
    ),
  }),
  onChange: () => {
    assetFeedback = "";
    renderAssets();
  },
});
function renderAssets() {
  const catalog = $("#asset-catalog"),
    extras = $("#asset-extras");
  if (!catalog || !extras) return;
  const active = document.activeElement,
    focusRow = active?.closest?.("[data-slot]"),
    focusSlot = focusRow?.dataset.slot,
    focusAction = active?.dataset?.assetAction,
    focusRefresh = active?.id === "asset-refresh";
  // Render the picker first: pruning a departed or now-ineligible device is
  // part of rendering it, and everything below reads the resolved choice.
  assetPicker.render();
  const targets = assetTargets(),
    device = selectedAssetDevice(targets);
  resolveAssetFeedback(device);
  const ineligible = targets.filter((target) => !target.eligible);
  $("#asset-target-reasons").innerHTML = ineligible.length
    ? ineligible
        .map(
          (target) =>
            `<span><strong>${esc(Identity.primary(target.device, installation))}</strong> · ${esc(target.reasons.join(" · "))}</span>`,
        )
        .join("")
    : targets.length
      ? '<span class="dim">Every discovered device is eligible.</span>'
      : '<span class="dim">No devices discovered.</span>';
  $("#asset-catalog-summary").textContent =
    `${
      distribution.assets.length
      } host slot${
      distribution.assets.length === 1 ? "" : "s"
      }${
      device ? ` · compared with ${
      Identity.primary(device, installation)
      }` : ""
      }`;
  $("#asset-feedback").textContent = assetFeedback;
  catalog.innerHTML = distribution.assets.length
    ? distribution.assets.map((item) => assetCatalogRow(device, item)).join("")
    : '<p class="empty">No asset slots in the host catalog.</p>';
  const hostNames = new Set(distribution.assets.map((item) => item.name));
  const extraItems = device && Array.isArray(device.assets) ? device.assets.filter((item) => !hostNames.has(item.name)) : [];
  const inventoryBanner = !device
    ? '<p class="asset-inventory-note">Choose an eligible target to compare its observed inventory.</p>'
    : !Array.isArray(device.assets)
      ? '<p class="asset-inventory-note unknown">Inventory unknown — this node has not ' +
        "replied yet, or does not support asset inventory.</p>"
      : `<p class="asset-inventory-note current">Observed ${
        device.assets.length
        } installed slot${
        device.assets.length === 1 ? "" : "s"
        }${
        device.assets_observed_at ? ` · ${
        ago(device.assets_observed_at)
        }` : ""
        }.</p>`;
  const quarantine = device?.assets_quarantine?.length
    ? `<p class="asset-inventory-note unknown">Inventory incomplete: ${
      device.assets_quarantine.length
      } malformed entr${
      device.assets_quarantine.length === 1 ? "y was" : "ies were"
      } excluded.</p>`
    : "";
  extras.innerHTML = `${inventoryBanner}${quarantine}${
    extraItems.length
      ? [
          `<div class="asset-extras-heading"><h3>Device-only slots</h3>`,
          `<p class="dim">Installed on this device but absent from the host catalog.</p>`,
          `</div>${extraItems.map((item) => assetExtraRow(device, item)).join("")}`,
        ].join("")
      : ""
  }`;
  document.querySelectorAll("#tab-assets [data-asset-action]").forEach(
    (button) =>
      (button.onclick = () => {
        const row = button.closest("[data-slot]"),
          slot = row.dataset.slot,
          action = button.dataset.assetAction;
        if (!device || !confirmAssetAction(device, slot, action)) return;
        assetFeedback =
          action === "remove"
            ? `Removing ${slot} from ${Identity.primary(device, installation)}…`
            : `${action === "update" ? "Updating" : "Sending"} ${slot} to ${Identity.primary(device, installation)}…`;
        const hostItem = distribution.assets.find((item) => item.name === slot);
        assetFeedbackPending = {
          uid: device.uid,
          slot,
          action,
          observedAt: Number(device.assets_observed_at) || 0,
          fingerprint: hostItem?.fingerprint || null,
        };
        $("#asset-feedback").textContent = assetFeedback;
        if (action === "remove") ws.send("drop_distribution", { uid: device.uid, kind: "asset", name: slot });
        else ws.send("send_distribution", { uid: device.uid, kind: "asset", name: slot, confirmed_active: false });
      }),
  );
  $("#asset-refresh").onclick = () => {
    assetFeedback = "Refreshing host catalog…";
    $("#asset-feedback").textContent = assetFeedback;
    ws.send("refresh_distribution", {});
  };
  if (focusSlot && focusAction)
    document.querySelector(`#tab-assets [data-slot="${CSS.escape(focusSlot)}"] [data-asset-action="${CSS.escape(focusAction)}"]`)?.focus();
  else if (focusRefresh) $("#asset-refresh").focus();
}
