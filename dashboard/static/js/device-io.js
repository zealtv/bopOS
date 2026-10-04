(function () {
  const scanTimes = new Map();
  // Tentative matches at the defaults used by the shipped drivers. A scan
  // observes addresses, not chip identities; never infer a module from one.
  const hints = {"0x48": "ADS1x15?", "0x19": "LIS3DH?", "0x5a": "MPR121?"};
  const escape = value => String(value ?? "").replace(/[&<>"']/g,
    character => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[character]));

  function section(device) {
    const io = device.report?.io;
    const addresses = Array.isArray(io?.addresses) ? [...io.addresses].sort(
      (left, right) => parseInt(left.address, 16) - parseInt(right.address, 16)) : [];
    const pending = !!device.io_scan_pending;
    const state = !io ? "unknown" : io.bus == null ? "no-bus"
      : !io.scanned ? "not-scanned" : addresses.length ? "addresses" : "empty";
    const status = state === "unknown" ? "Refresh the report to load IO status."
      : state === "no-bus" ? "No bus"
      : state === "not-scanned" ? "Not scanned yet"
      : state === "empty" ? "Bus is empty"
      : `${addresses.length} address${addresses.length === 1 ? "" : "es"}`;
    if (device.io_scan?.status === "ok" && Number.isFinite(device.io_scan.at)) {
      scanTimes.set(device.uid, device.io_scan.at);
    }
    const scannedAt = scanTimes.get(device.uid);
    const lastScan = scannedAt ? new Date(scannedAt * 1000).toLocaleString()
      : io && !io.scanned ? "never" : "time unavailable";
    const addressRows = state === "addresses" ? addresses.map(row => {
      const hint = row.claimed ? "" : hints[row.address];
      return `<li class="device-io-address" data-io-address="${escape(row.address)}">
        <code>${escape(row.address)}</code>
        ${row.claimed ? '<span class="device-io-claimed">Kernel claimed (UU)</span>'
          : hint ? `<span class="device-io-hint">${hint}</span>` : ""}</li>`;
    }).join("") : "";
    const modules = Object.entries(io?.modules || {}).sort(([left], [right]) => left.localeCompare(right));
    const moduleRows = modules.map(([name, row]) => {
      const moduleState = row.state || "unknown";
      const warning = ["errored", "missing"].includes(moduleState);
      return `<li class="device-io-module" data-io-module="${escape(name)}">
        <div class="device-io-identity"><strong>${escape(name)}</strong>
          <small>${escape(row.type)} · <code>${escape(row.address)}</code></small></div>
        <span class="device-io-state" data-state="${escape(moduleState)}">${warning ? '<span class="device-io-warning" aria-hidden="true">⚠</span> ' : ""}${escape(moduleState)}</span>
        ${row.error ? `<code class="device-io-reason">${escape(row.error)}</code>` : ""}</li>`;
    }).join("");
    const timeout = !pending && device.io_scan?.phase === "timeout";
    return `<section id="device-io" class="device-io" aria-labelledby="device-io-title" data-io-state="${state}">
      <div class="section-head"><h2 id="device-io-title">IO</h2>
        <button type="button" data-io-scan ${!device.online || pending ? "disabled" : ""}>${pending ? "Scanning…" : "Scan"}</button></div>
      <div class="device-io-summary"><p data-io-bus-status>${escape(status)}${io?.bus != null ? ' · I2C bus 1' : ''}</p>
        <small class="dim" data-io-last-scan>Last scanned: ${escape(lastScan)}</small></div>
      <output class="device-io-feedback" aria-live="polite">${timeout ? '<span class="device-io-warning" aria-hidden="true">⚠</span> Scan timed out. Try again.' : ""}</output>
      ${addressRows ? `<ul class="device-io-addresses" aria-label="Bus addresses">${addressRows}</ul>
        <p class="dim device-io-hint-note">Address hints are tentative.</p>` : ""}
      <h3>Modules</h3>
      ${moduleRows ? `<ul class="device-io-modules" aria-label="Modules">${moduleRows}</ul>`
        : `<p class="dim">${io ? "No modules reported." : "Module status unavailable."}</p>`}
      ${device.io_error ? `<p class="device-io-error" role="status"><span class="device-io-warning" aria-hidden="true">⚠</span> Last IO error: ${escape(device.io_error.name)} · ${escape(device.io_error.error)}</p>` : ""}
    </section>`;
  }

  function bind(root, device, send) {
    const button = root.querySelector("[data-io-scan]");
    if (!button) return;
    button.onclick = () => {
      if (!device.online || device.io_scan_pending) return;
      button.disabled = true;
      button.textContent = "Scanning…";
      send("io_scan", {uid: device.uid});
    };
  }

  function update(root, device, send) {
    const card = root.querySelector("#device-io");
    if (!card) return;
    card.outerHTML = section(device);
    bind(root, device, send);
  }

  window.DeviceIO = {section, bind, update};
})();
