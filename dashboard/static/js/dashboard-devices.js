// Physical device roster, diagnostics, administration and live controls.
function row(d, seat) {
  const status = d.online ? (Number(d.engine_alive) === 0 ? "crashed" : "online") : "offline";
  const heartbeatAt = heartbeats.get(d.uid);
  const assignment = d.revoking_assignment ? "clearing assignment" : seat ? `bound · Seat ${seat.id}` : "unbound";
  const telemetry = [d.version, d.rssi != null ? `${d.rssi} dBm` : null].filter(Boolean).join(" · ");
  const classes = `${d.uid === selected ? "selected" : ""} ${badgeTone(d.patch_badge)}`;
  const button = deviceRosterButton({
    classes,
    d,
    status,
    heartbeatAt,
    telemetry,
    assignment,
  });
  const unmanaged = window.WifiNetworks?.unmanaged(d) || "";
  return unmanaged ? `<div class="wifi-device-card ${classes}">${button}${unmanaged}</div>` : button;
}

function deviceEnabledPresentation(d) {
  const desired = d.device_enabled !== false;
  const status = String(d.enabled_status || "").toLowerCase();
  const unsettled = status && status !== "current" && status !== "confirmed";
  const state = desired ? "Device enabled" : "Device disabled";
  const suffix = unsettled ? ` · ${status}` : "";
  return { desired, status, label: state + suffix, terse: (desired ? "enabled" : "disabled") + suffix };
}

function deviceEnabledIndicator(d) {
  const enabled = deviceEnabledPresentation(d);
  const slash = enabled.desired ? "" : '<path d="M3 3l18 18"></path>';
  return deviceEnabledMarkup(enabled, slash);
}

function patchDiagnostics(d) {
  const installed = Array.isArray(d.patches) ? d.patches : [];
  const active = installed.find((patch) => patch.active) || installed.find((patch) => patch.name === d.report?.patch);
  const desired = installation.fleet_patch || {};
  const fetchPhase = desired.name ? (d.fetch || {})[`patch:${desired.name}`] : null;
  const rows = installed.map((patch) => installedPatchRow(patch)).join("");
  const reason = patchPushReason(d) || (!desired.name ? "No fleet patch set" : "");
  const switchAttempt = d.patch_switch || {};
  return [
    `<section id="patch-diagnostics">`,
    `<div class="section-head"><h2>Patch diagnostics</h2>${patchBadge(d.patch_badge)}</div>`,
    `<p class="dim">observed current: <b>${esc(active?.name ?? d.report?.patch ?? "—")}</b>`,
    `</p>`,
    `<dl>`,
    `<dt>Desired patch</dt>`,
    `<dd>${esc(desired.name || "not set")}</dd>`,
    `<dt>Desired fingerprint</dt>`,
    `<dd>${copyIdentity(desired.fingerprint, "—")}</dd>`,
    `<dt>Reported content identity</dt>`,
    `<dd>${copyIdentity(active?.fingerprint, "unreported")}</dd>`,
    `<dt>Observed active patch</dt>`,
    `<dd>${esc(active?.name ?? d.report?.patch ?? "—")}</dd>`,
    `<dt>Switch attempt</dt>`,
    `<dd>${esc(switchAttempt.status || "none")}${switchAttempt.reason ? ` · ${esc(switchAttempt.reason)}` : ""}</dd>`,
    `<dt>Fetch phase</dt>`,
    `<dd>${esc(fetchPhase || "none")}</dd>`,
    `<dt>Manifest / framework git</dt>`,
    `<dd>${esc(active?.manifest ? "valid manifest" : "invalid or unreported manifest")} · bopOS ${esc(d.report?.git_rev || "—")}</dd>`,
    `</dl>`,
    `<h3>Installed patches</h3>`,
    `<div class="patch-table-wrap">`,
    `<table class="patch-table">`,
    `<thead>`,
    `<tr>`,
    `<th>Patch</th>`,
    `<th>State</th>`,
    `<th>Manifest</th>`,
    `<th>Fingerprint / content identity</th>`,
    `</tr>`,
    `</thead>`,
    `<tbody>${rows || '<tr><td colspan="4">No patch listing reported.</td></tr>'}</tbody>`,
    `</table>`,
    `</div><div class="actions patch-remediation"><button id="fleet-patch-retry" ${reason || performanceActive() ? "disabled" : ""}>Update patch</button></div>`,
    reason ? `<p class="dim patch-target-note">${esc(reason)}</p>` : "",
    `</section>`,
  ].join("");
}
function bindPatchDiagnostics(d) {
  const retry = $("#fleet-patch-retry");
  if (retry) retry.onclick = () => {
    const current = installation.devices?.[d.uid];
    if (!current || patchPushReason(current) || !installation.fleet_patch?.name || performanceActive()) return;
    if (confirm(`Update patch on ${Identity.primary(current, installation)}? This may restart its audio engine.`))
      ws.send("retry_fleet_patch", { uid: current.uid });
  };
}

function audioConfigEqual(left, right) {
  return ["card", "mixer_control", "sample_rate", "period_size", "nperiods"].every(
    (key) => (left?.[key] ?? null) === (right?.[key] ?? null),
  );
}

function audioSection(d) {
  const audio = d.report?.audio;
  if (!audio || !audio.configured)
    return [
      `<section id="device-audio">`,
      `<div class="section-head">`,
      `<div><h2>Audio</h2>`,
      `<p class="dim">Refresh the report to load audio settings and detected cards.</p>`,
      `</div>`,
      `</div>`,
      `</section>`,
    ].join("");
  const configured = audio.configured,
    active = audio.active,
    cards = Array.isArray(audio.cards) ? audio.cards : [];
  const available = cards.some((card) => card.id === configured.card);
  const cardOptions = [
    ...(!available ? [`<option value="${esc(configured.card)}" selected disabled>${esc(configured.card)} — unavailable</option>`] : []),
    ...cards.map(
      (card) =>
        `<option value="${esc(card.id)}" ${card.id === configured.card ? "selected" : ""}>${esc(card.label || card.id)} · ${esc(card.id)}</option>`,
    ),
  ].join("");
  const rates = [22050, 32000, 44100, 48000, 88200, 96000];
  const periods = [64, 128, 256, 512, 1024, 2048];
  const latency =
    Math.round(((Number(configured.period_size) * Number(configured.nperiods)) / Number(configured.sample_rate)) * 10000) / 10;
  const mismatch = active && !audioConfigEqual(configured, active);
  const receipt = d.audio_apply;
  const feedback =
    receipt?.phase === "applied"
      ? "Applied; audio engine restarted."
      : receipt?.phase === "rolled-back"
        ? "Could not start requested settings; restored the previous configuration."
        : receipt?.phase === "rollback-failed"
          ? "Audio recovery failed; inspect the node before use."
          : receipt?.phase === "invalid"
            ? "The node rejected those audio settings."
            : receipt?.phase === "timeout"
              ? "Audio apply timed out; refreshing observed state."
              : audio.status === "applying"
                ? "Applying settings and restarting audio…"
                : audio.error || "";
  return [
    `<section id="device-audio" data-audio-status="${esc(audio.status || "unknown")}">
    <div class="section-head">`,
    `<div><h2>Audio</h2>`,
    `<p class="dim">${
      active ? `${
      esc(active.card)
      } · ${
      esc(active.sample_rate)
      } Hz · ${
      esc(active.period_size)
      } frames × ${
      esc(active.nperiods)
      }` : "No active JACK configuration reported"
      }${
      mismatch ? " · saved settings differ" : ""
      }</p>`,
    `</div>`,
    `<span class="audio-state">${esc(audio.status || "unknown")}</span>`,
    `</div>
    <div class="audio-config-grid">
      <label>sound card<select id="audio-card" ${
        d.online && cards.length ? "" : "disabled"
        }>${
        cardOptions || "<option disabled>No playback cards detected</option>"
        }</select>`,
    `</label>
      <label>sample rate<select id="audio-rate" ${d.online ? "" : "disabled"}>${rates
        .map((value) => `<option value="${value}" ${value === Number(configured.sample_rate) ? "selected" : ""}>${value} Hz</option>`)
        .join("")}</select>`,
    `</label>
      <label>buffer size<select id="audio-period" ${d.online ? "" : "disabled"}>${periods
        .map((value) => `<option value="${value}" ${value === Number(configured.period_size) ? "selected" : ""}>${value} frames</option>`)
        .join("")}</select>`,
    `</label>
      <label>periods<select id="audio-nperiods" ${d.online ? "" : "disabled"}>${[2, 3]
        .map((value) => `<option value="${value}" ${value === Number(configured.nperiods) ? "selected" : ""}>${value}</option>`)
        .join("")}</select>`,
    `</label>
    </div>
    <p class="dim audio-buffering">Approximate device buffering: <span id="audio-latency">${latency} ms</span>. End-to-end latency may be higher.</p>
    <div class="audio-apply-row">`,
    `<button id="audio-apply" ${!d.online || !available || audio.status === "applying" ? "disabled" : ""}>Save &amp; restart audio engine</button>`,
    `<output id="audio-feedback" class="${receipt?.status === "err" ? "error" : ""}" aria-live="polite">${esc(feedback)}</output>`,
    `</div>
  </section>`,
  ].join("");
}

function logSection(d) {
  const log = d.report?.log;
  if (!log || !log.destination)
    return [
      `<section id="device-log">`,
      `<div class="section-head">`,
      `<div><h2>Logging</h2>`,
      `<p class="dim">Refresh the report to load the log destination.</p>`,
      `</div>`,
      `</div>`,
      `</section>`,
    ].join("");
  const destination = log.destination,
    effective = log.effective,
    usbPresent = !!log.usb_present;
  if (logDestinationDrafts.get(d.uid) === destination) logDestinationDrafts.delete(d.uid);
  const choice = logDestinationDrafts.get(d.uid) ?? destination;
  const fellBack = destination === "usb" && effective === "internal";
  const receipt = d.log_apply;
  const feedback =
    receipt?.phase === "applied"
      ? fellBack
        ? "Saved — USB not mounted, logging to internal storage."
        : "Saved log destination."
      : receipt?.phase === "invalid"
        ? "The node rejected that log destination."
        : receipt?.phase === "timeout"
          ? "Log destination apply timed out; refreshing observed state."
          : receipt?.status === "pending"
            ? "Saving log destination…"
            : fellBack
              ? "USB selected but no stick is mounted — logging to internal storage."
              : "";
  const sub =
    effective === "ram"
      ? "Performance"
      : `Writing to ${
        effective === "usb" ? "USB stick" : "internal storage"
        }${
        fellBack ? " (USB not mounted)" : ""
        } · USB ${
        usbPresent ? "present" : "absent"
        }`;
  const opt = (value, label) => `<option value="${value}" ${value === choice ? "selected" : ""}>${label}</option>`;
  return [
    `<section id="device-log" data-log-effective="${esc(effective || "internal")}" data-log-usb="${usbPresent ? "1" : "0"}">
    <div class="section-head">`,
    `<div><h2>Logging</h2>`,
    `<p class="dim">${esc(sub)}</p>`,
    `</div>`,
    `<span class="log-state">${esc(effective || "internal")}</span>`,
    `</div>
    <div class="log-config-row">
      <label>destination<select id="log-destination" ${
        d.online ? "" : "disabled"
        }>${
        opt("internal", "Internal storage (SD card)")
        }${
        opt("usb", "USB stick")
        }</select>`,
    `</label>
      <button id="log-apply" ${!d.online || choice === destination ? "disabled" : ""}>Save log destination</button>
      <output id="log-feedback" class="${receipt?.status === "err" ? "error" : ""}" aria-live="polite">${esc(feedback)}</output>
    </div>`,
    `</section>`,
  ].join("");
}

// The Device tab renders the same live controls the Control tab does, through
// the shared component (37/07). Only the scope and the send differ: a device
// write targets one device, resolved node-side to its seat selector.
const deviceSurface = window.ControlSurface.create({
  getState: () => installation,
  deviceForSeat: (seat) => (seat?.bound ? installation.devices?.[seat.bound] : null),
  deviceForScope: (uid) => installation.devices?.[uid],
  send: ({ scope, id, name, value }) => ws.send("set_live_param", { scope, id, name, value }),
  // Returns the lead so the panel's fire button can sweep for exactly as long
  // as the event is actually scheduled for (04-event-fire-affordance).
  sendEvent: ({ scope, id, identity, elements }) => {
    const selector = scope === "all" ? "all" : scope === "group" ? `g${id}` : String(id);
    const leadMs = Math.min(10000, Math.max(0, Number(installation.event_lead_ms ?? 500) || 0));
    ws.send("fire_event", { selector, identity, elements, lead_ms: leadMs });
    return leadMs;
  },
  sendAutomation: ({ scope, id, name, args }) => ws.send("set_live_automation", { scope, id, name, args }),
  requestRender: () => renderDeviceDetail(),
});

const DEVICE_CONTROL_OPEN = "bopos.device-control-open";
function deviceControlOpen() {
  // Collapsed by default (Bob, 2026-07-25); the choice is remembered.
  try {
    return localStorage.getItem(DEVICE_CONTROL_OPEN) === "1";
  } catch (_error) {
    return false;
  }
}
function setDeviceControlOpen(open) {
  try {
    localStorage.setItem(DEVICE_CONTROL_OPEN, open ? "1" : "0");
  } catch (_error) {
    /* private mode: the panel just forgets */
  }
}

function deviceLiveSchema() {
  const schema = installation.live_controls;
  if (!schema || !Array.isArray(schema.declarations)) return null;
  // Event declarations travel beside the params (they are not `/p/*` values)
  // and are folded back in here, at the surface that renders rows — so nothing
  // else that reads `declarations` ever sees them.
  const items = [...schema.declarations, ...(Array.isArray(schema.events) ? schema.events : [])];
  return { patch: schema.patch, declarations: items.map((item) => ({ ...item, path: item.path || [] })) };
}

function deviceControlSection(d) {
  const seat = Object.values(installation.seats || {}).find((item) => item.bound === d.uid);
  const schema = deviceLiveSchema();
  const open = deviceControlOpen();
  const declarations = schema?.declarations || [];
  const live = !!d.online && Number(d.engine_alive) !== 0;
  // Offline shows last known values, disabled — never hidden (Bob, 2026-07-25).
  const disabled = !seat || !live;
  const why = !seat
    ? "Unbound device — showing patch defaults. Live control targets content by Seat, " + "so bind this device to a Seat first."
    : !live
      ? "Offline — showing the last known values."
      : "";
  const body = !declarations.length
    ? '<p class="dim">This patch declares no parameters.</p>'
    : `<div class="promoted-controls">${deviceSurface.tree("device", d.uid, seat ? [seat] : [], declarations, disabled)}</div>`;
  const source = schema?.patch ? `<p class="dim">${esc(schema.patch)} · fleet patch</p>` : "";
  return [
    `<section id="device-control" class="device-control${disabled ? " disabled" : ""}">
    <div class="section-head">`,
    `<div><h2>Device control</h2>${source}</div>`,
    `<button id="device-control-toggle" aria-expanded="${open}" aria-controls="device-control-body">${open ? "Hide" : "Show"}</button>`,
    `</div>
    <div id="device-control-body" ${open ? "" : "hidden"}>${why ? `<p class="dim">${esc(why)}</p>` : ""}${body}</div>
  </section>`,
  ].join("");
}

function renderDeviceDetail() {
  const d = installation.devices?.[selected];
  if (!d || d.virtual) {
    $("#detail").innerHTML = '<section><p class="dim">Select a physical device.</p></section>';
    return;
  }
  const active = document.activeElement;
  if ($("#detail").contains(active) && active.matches("input,select")) {
    updateDeviceEnabledControls(d);
    updateDeviceHostnameControls(d);
    DeviceIO.update($("#detail"), d, (kind, data) => ws.send(kind, data));
    return;
  }
  const seat = Object.values(installation.seats || {}).find((item) => item.bound === d.uid);
  const emptySeats = Object.values(installation.seats || {})
    .filter((item) => !item.bound)
    .sort((a, b) => a.id - b.id);
  const assignOptions = emptySeats
    .map((item) => `<option value="${item.id}">${esc(item.name || `Seat ${item.id}`)} · ID ${item.id}</option>`)
    .join("");
  const health = !d.online ? "offline" : Number(d.engine_alive) === 0 ? "engine stopped" : "healthy";
  const displayAlias = Identity.primary(d, installation);
  const hostnameTarget = displayAlias.trim().toLowerCase().replace(/\s+/g, "-");
  const hostnamePending = d.hostname_status === "pending";
  const hostnameCurrent = String(d.hostname || "").toLowerCase() === hostnameTarget;
  const hostnameActionLabel = hostnamePending
    ? "Setting…"
    : hostnameCurrent
      ? "Hostname set"
      : d.hostname_status === "err"
        ? "Retry hostname"
        : "Set hostname";
  const enabled = deviceEnabledPresentation(d);
  // Wi-Fi RSSI is useful only with a coarse reading of what the number means.
  // These thresholds deliberately describe installation reliability rather
  // than theoretical link viability: -60 dBm or better is good, -61..-75 is
  // marginal, and below -75 is poor. Wired/absent reports stay neutral.
  const rssi = rssiPresentation(d.rssi);
  const rssiMarkup = `<span class="device-rssi" data-rssi-health="${rssi.health}">${esc(rssi.text)}</span>`;
  const binding = d.revoking_assignment
    ? '<section id="device-binding"><h2>Assignment</h2><p class="dim">Clearing a stale ' +
      "node assignment. This device cannot be rebound until it acknowledges ID " +
      "-1.</p></section>"
    : seat
      ? [
          `<section id="device-binding">`,
          `<div class="section-head">`,
          `<div><h2>Assignment</h2>`,
          `<p class="dim">Bound to ${esc(seat.name || `Seat ${seat.id}`)} · ID ${seat.id}</p>`,
          `</div>`,
          `<button id="device-open-seat">Open Seat</button>`,
          `</div>`,
          `</section>`,
        ].join("")
      : [
          `<section id="device-binding"><h2>Assignment</h2>`,
          `<p class="dim">Unbound physical device. Assignment uses the same authoritative Seat transaction.</p>`,
          `<div class="assign">`,
          `<label>empty Seat <select id="device-seat" ${assignOptions ? "" : "disabled"}>${assignOptions || "<option>No empty Seats</option>"}</select>`,
          `</label>`,
          `<button id="device-bind" ${assignOptions && d.online ? "" : "disabled"}>Assign</button>`,
          `</div>`,
          `</section>`,
        ].join("");
  $("#detail").innerHTML = [
    `<section>${deviceTitleMarkup(displayAlias, d, enabled)}${deviceAliasMarkup({
      displayAlias,
      d,
      hostnamePending,
      hostnameCurrent,
      hostnameActionLabel,
    })}${deviceFactsMarkup({
      d,
      seat,
      health,
      rssiMarkup,
    })}</section>
    ${deviceActionsMarkup(d, seat)}
    ${binding}
    ${patchDiagnostics(d)}
    ${deviceControlSection(d)}
    ${audioSection(d)}
    ${logSection(d)}
    ${DeviceIO.section(d)}
    ${deviceAssetsMarkup(d)}
    ${deviceReportMarkup(d)}`,
  ].join("");
  bindDeviceDetailControls(d);
  bindPatchDiagnostics(d);
  DeviceIO.bind($("#detail"), d, (kind, data) => ws.send(kind, data));
}

function rssiPresentation(raw) {
  if (raw == null || raw === "") {
    return { health: "neutral", text: "wired / unavailable" };
  }
  const value = Number(raw);
  if (!Number.isFinite(value)) {
    return { health: "neutral", text: "wired / unavailable" };
  }
  const health = value >= -60 ? "good" : value >= -75 ? "marginal" : "poor";
  return { health, text: `${raw} dBm · ${health}` };
}

function updateDeviceEnabledControls(d) {
  const enabled = deviceEnabledPresentation(d),
    button = $("#device-enabled-toggle"),
    status = $("#device-enabled-status");
  if (button) button.textContent = d.device_enabled === false ? "Enable" : "Disable";
  if (status) status.value = enabled.terse;
}

function updateDeviceHostnameControls(d) {
  const alias = Identity.primary(d, installation);
  const target = alias.trim().toLowerCase().replace(/\s+/g, "-");
  const pending = d.hostname_status === "pending";
  const current = String(d.hostname || "").toLowerCase() === target;
  const button = $("#device-hostname-set");
  if (button) {
    button.disabled = !d.online || pending || current;
    button.textContent = pending ? "Setting…" : current ? "Hostname set" : d.hostname_status === "err" ? "Retry hostname" : "Set hostname";
  }
  const value = $("#device-hostname-value");
  if (value) value.textContent = d.hostname || "—";
}

function bindDeviceDetailControls(d) {
  const alias = Identity.primary(d, installation),
    registryEntry = installation.device_registry?.[d.uid] || {};
  document.querySelectorAll("#detail [data-action]").forEach(
    (button) =>
      (button.onclick = () => {
        const verb = button.dataset.action;
        if (!confirm(`${actionLabel(verb)} ${alias}?`)) return;
        ws.send("action", { uid: d.uid, verb });
      }),
  );
  document.querySelectorAll("#detail [data-identify]").forEach((button) => (button.onclick = () => ws.send("identify", { uid: d.uid })));
  const openSeat = $("#device-open-seat");
  if (openSeat)
    openSeat.onclick = () => {
      const seat = Object.values(installation.seats || {}).find((item) => item.bound === d.uid);
      if (seat) {
        selectSeat(Number(seat.id));
        activateTab("seats");
      }
    };
  const bind = $("#device-bind");
  if (bind)
    bind.onclick = () => {
      const id = Number($("#device-seat").value);
      if (Number.isInteger(id)) ws.send("bind_seat", { id, uid: d.uid, confirmed: false });
    };
  const aliasSave = $("#device-alias-save");
  if (aliasSave)
    aliasSave.onclick = () => {
      const input = $("#device-alias"),
        value = input.value;
      if (input.reportValidity()) {
        input.blur();
        ws.send("set_device_alias", { uid: d.uid, alias: value });
      }
    };
  const aliasReset = $("#device-alias-reset");
  if (aliasReset)
    aliasReset.onclick = () => {
      if (registryEntry.source !== "custom" || confirm(`Reset custom alias ${alias} to its generated name?`))
        ws.send("reset_device_alias", { uid: d.uid });
    };
  const hostnameSet = $("#device-hostname-set");
  if (hostnameSet) hostnameSet.onclick = () => ws.send("set_device_hostname", { uid: d.uid });
  const enabledToggle = $("#device-enabled-toggle");
  if (enabledToggle)
    enabledToggle.onclick = () => {
      const current = installation.devices?.[d.uid] || d;
      ws.send("set_device_enabled", { uid: d.uid, value: current.device_enabled === false ? 1 : 0 });
    };
  bindAudioControls(d);
  bindLogControls(d);
  bindDeviceControl(d);
  const forget = $("#device-forget");
  if (forget)
    forget.onclick = () => {
      const loss = registryEntry.source === "custom" ? " Its custom alias will be deleted." : "";
      if (confirm(`Forget ${alias}?${loss}`)) ws.send("forget_device", { uid: d.uid });
    };
  $("#refresh-report").onclick = () => ws.send("request_report", { uid: d.uid });
  const openAssets = $("#device-open-assets");
  if (openAssets)
    openAssets.onclick = () => {
      assetPicker.set([d.uid]);
      activateTab("assets");
    };
}

function bindDeviceControl(d) {
  const toggle = $("#device-control-toggle");
  if (toggle)
    toggle.onclick = () => {
      setDeviceControlOpen(!deviceControlOpen());
      renderDeviceDetail();
    };
  const body = $("#device-control-body");
  if (body && !body.hidden) deviceSurface.bind(body);
}

function bindAudioControls(d) {
  const audio = d.report?.audio,
    card = $("#audio-card"),
    rate = $("#audio-rate"),
    period = $("#audio-period"),
    nperiods = $("#audio-nperiods"),
    apply = $("#audio-apply");
  if (!audio?.configured || !card || !rate || !period || !nperiods || !apply) return;
  const cards = Array.isArray(audio.cards) ? audio.cards : [];
  const config = () => {
    const selected = cards.find((item) => item.id === card.value);
    const retainMixer =
      card.value === audio.configured.card &&
      (audio.configured.mixer_control == null || selected?.mixer_controls?.includes(audio.configured.mixer_control));
    return {
      card: card.value,
      mixer_control: retainMixer ? audio.configured.mixer_control : null,
      sample_rate: Number(rate.value),
      period_size: Number(period.value),
      nperiods: Number(nperiods.value),
    };
  };
  const refresh = () => {
    const value = config(),
      selected = cards.find((item) => item.id === value.card);
    apply.disabled = !d.online || audio.status === "applying" || !selected || audioConfigEqual(value, audio.configured);
    const latency = Math.round(((value.period_size * value.nperiods) / value.sample_rate) * 10000) / 10;
    const output = $("#audio-latency");
    if (output) output.textContent = `${latency} ms`;
  };
  card.onchange = refresh;
  [rate, period, nperiods].forEach((control) => (control.onchange = refresh));
  refresh();
  apply.onclick = () => {
    const desired = config();
    if (
      !confirm(`Restart the audio engine on ${Identity.primary(d, installation)}? Audio will stop briefly while these settings are tested.`)
    )
      return;
    apply.disabled = true;
    const feedback = $("#audio-feedback");
    if (feedback) {
      feedback.className = "";
      feedback.value = "Applying settings and restarting audio…";
    }
    ws.send("set_audio_config", { uid: d.uid, config: desired });
  };
}

function bindLogControls(d) {
  const log = d.report?.log,
    select = $("#log-destination"),
    apply = $("#log-apply");
  if (!log?.destination || !select || !apply) return;
  const refresh = () => {
    apply.disabled = !d.online || select.value === log.destination;
  };
  select.onchange = () => {
    logDestinationDrafts.set(d.uid, select.value);
    refresh();
  };
  refresh();
  apply.onclick = () => {
    const destination = select.value;
    logDestinationDrafts.delete(d.uid);
    const feedback = $("#log-feedback");
    if (feedback) {
      feedback.className = "";
      feedback.value = "Saving log destination…";
    }
    apply.disabled = true;
    ws.send("set_log_config", { uid: d.uid, destination });
  };
}

function deviceRosterButton({ classes, d, status, heartbeatAt, telemetry, assignment }) {
  return [
    `<button class="device-row ${classes}" data-uid="${esc(d.uid)}"><i class="dot ${status}"></i>`,
    `<i class="heartbeat-blip${heartbeatAt ? " pulse" : ""}" ${heartbeatAt ? `data-heartbeat-at="${esc(heartbeatAt)}"` : ""} aria-hidden="true"></i>`,
    `<span><strong>${esc(Identity.primary(d, installation))}</strong>`,
    telemetry ? `<small>${esc(telemetry)}</small>` : "",
    `<small class="device-binding-badge">${esc(assignment)}</small>`,
    `<small class="wifi-chip" data-wifi-sync>${esc(d.wifi_sync || "no Wi-Fi")}</small>`,
    `</span>${deviceEnabledIndicator(d)}${patchBadge(d.patch_badge)}</button>`,
  ].join("");
}

function deviceEnabledMarkup(enabled, slash) {
  const unsettled = enabled.status && !["current", "confirmed"].includes(enabled.status);
  return [
    `<span class="device-enabled-indicator ${enabled.desired ? "enabled" : "disabled"} ${unsettled ? "unsettled" : ""}"`,
    ` data-device-enabled-indicator data-enabled-status="${esc(enabled.status || "current")}"`,
    ` role="img" aria-label="${esc(enabled.label)}" title="${esc(enabled.label)}">`,
    `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 5L6 9H3v6h3l5 4V5z"></path>`,
    `<path d="M15.5 9.5a4 4 0 010 5"></path>${slash}</svg>`,
    `</span>`,
  ].join("");
}

function installedPatchRow(patch) {
  return [
    `<tr><td>${esc(patch.name)}</td>`,
    `<td>${patch.active ? "active" : "inactive"}</td>`,
    `<td>${patch.manifest ? "valid" : "invalid"}</td>`,
    `<td>${copyIdentity(patch.fingerprint, "unreported")}</td></tr>`,
  ].join("");
}

function deviceTitleMarkup(displayAlias, d, enabled) {
  return [
    `<div class="section-head device-title"><h2>${esc(displayAlias)} ${d.undeclared ? '<b class="badge">UNDECLARED</b>' : ""}</h2>`,
    `<div class="device-enabled-control"><output id="device-enabled-status" aria-live="polite">${esc(enabled.terse)}</output>`,
    `<button id="device-enabled-toggle">${d.device_enabled === false ? "Enable" : "Disable"}</button>`,
    `</div>`,
    `</div>`,
  ].join("");
}

function deviceAliasMarkup({ displayAlias, d, hostnamePending, hostnameCurrent, hostnameActionLabel }) {
  return [
    `<div class="assign device-alias-editor">`,
    `<label>device alias <input id="device-alias" type="text" maxlength="25" ` +
      `pattern="[A-Za-z]{2,12} [A-Za-z]{2,12}" value="${esc(displayAlias)}"></label>`,
    `<button id="device-alias-save">Rename</button>`,
    `<button id="device-alias-reset">Reset</button>`,
    `<button id="device-hostname-set" ${!d.online || hostnamePending || hostnameCurrent ? "disabled" : ""}>${hostnameActionLabel}</button>`,
    `</div>`,
  ].join("");
}

function deviceFactsMarkup({ d, seat, health, rssiMarkup }) {
  return [
    `<dl>`,
    `<dt>Hostname</dt>`,
    `<dd id="device-hostname-value">${esc(d.hostname || "—")}</dd>`,
    `<dt>UID</dt>`,
    `<dd><code>${esc(d.uid)}</code>`,
    `</dd>`,
    `<dt>Seat</dt>`,
    `<dd>${seat ? `${esc(seat.name || `Seat ${seat.id}`)} · ID ${seat.id}` : "unbound"}</dd>`,
    `<dt>Health</dt>`,
    `<dd class="device-health ${health === "healthy" ? "online" : health === "offline" ? "offline" : ""}">${health}</dd>`,
    `<dt>Last seen</dt>`,
    `<dd>${d.last_seen ? ago(d.last_seen) : "—"}</dd>`,
    `<dt>Version</dt>`,
    `<dd>${esc(d.version)}</dd>`,
    `<dt>Engine</dt>`,
    `<dd>${d.engine_alive ? "alive" : "stopped"}</dd>`,
    `<dt>RSSI</dt>`,
    `<dd>${rssiMarkup}</dd>`,
    `<dt>IP</dt>`,
    `<dd>${esc(d.ip)}</dd>`,
    `<dt>Converged</dt>`,
    `<dd>${
      d.rev ? `${
      esc(d.rev.sha)
      } (${
      esc(d.rev.model)
      }, ${
      ago(d.rev.at)
      })${
      d.rev.status ? ` · ${
      esc(d.rev.status)
      } ${
      esc(d.rev.phase || "unknown")
      }` : ""
      }` : "—"
      }</dd>`,
    `</dl>`,
  ].join("");
}

function deviceActionsMarkup(d, seat) {
  return `<section><h2>Actions</h2><div class="actions"><button data-identify ${
    d.online ? "" : "disabled"
    }>Identify</button>${
    ["reboot", "shutdown", "restart-engine", "updatebopos"].map((v) => `<button data-action="${
    v
    }" ${
    d.online ? "" : "disabled"
    }>${
    actionLabel(v)
    }</button>`).join("")
    }${
    seat ? "" : '<button id="device-forget">Forget</button>'
    }</div></section>`;
}

function deviceAssetsMarkup(d) {
  return [
    `<section class="device-assets-summary">`,
    `<div class="section-head">`,
    `<div><h2>Assets</h2>`,
    `<p class="dim">${!Array.isArray(d.assets) ? "Inventory not yet reported" : `${d.assets.length} installed slot${d.assets.length === 1 ? "" : "s"}`}</p>`,
    `</div>`,
    `<button id="device-open-assets">Open Assets</button>`,
    `</div>`,
    `</section>`,
  ].join("");
}

function deviceReportMarkup(d) {
  return `<section><div class="section-head"><h2>Report</h2><button id="refresh-report" ${
    d.online ? "" : "disabled"
    }>Refresh report</button></div>${
    report(d.report)
    }</section>`;
}
