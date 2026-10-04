/* Authoring drafts stay local. Host state supplies only secret-presence flags. */
(function () {
  let draft = {country: "GB", networks: []}, dirty = false, awaiting = false;
  const panel = document.getElementById("wifi-panel");
  const rows = document.getElementById("wifi-networks");
  const country = document.getElementById("wifi-country");
  const warning = document.getElementById("wifi-warning");
  const send = document.getElementById("wifi-send");
  const dialog = document.getElementById("wifi-confirm");
  function status() {
    const messages = [];
    const enabled = new Set(draft.networks.filter(row => row.enabled).map(row => row.ssid));
    const active = new Map();
    for (const device of Object.values(installation.devices || {})) {
      const name = device.online && device.report?.wifi?.active;
      if (name && !enabled.has(name)) active.set(name, (active.get(name) || 0) + 1);
    }
    for (const [name, count] of active) {
      // Warn only for a network the operator is disabling/removing.
      if ((installation.wifi?.networks || []).some(row => row.ssid === name && row.enabled))
        messages.push(`⚠ ${count} devices are on ${name} now; they'll move to the next enabled network they can see`);
    }
    warning.textContent = messages.join("\n");
    send.disabled = !draft.networks.some(row => row.enabled) || awaiting;
  }
  function paint() {
    country.value = draft.country;
    rows.replaceChildren();
    draft.networks.forEach((row, index) => {
      const element = document.createElement("div");
      element.className = "wifi-network";
      element.innerHTML = `<div class="wifi-priority"><button data-move="-1" aria-label="▲" ${index === 0 ? "disabled" : ""}>▲</button><button data-move="1" aria-label="▼" ${index === draft.networks.length - 1 ? "disabled" : ""}>▼</button></div><label>SSID <input data-field="ssid" aria-label="SSID" autocomplete="off"></label><label><input type="checkbox" data-field="hidden"> hidden</label><label><input type="checkbox" data-field="enabled"> enabled</label><label>passphrase <input type="password" data-field="psk" aria-label="passphrase" autocomplete="new-password" minlength="8" maxlength="63"></label><button data-remove aria-label="✕">✕</button>`;
      element.querySelectorAll("[data-field]").forEach(input => {
        const key = input.dataset.field;
        if (input.type === "checkbox") input.checked = row[key];
        else input.value = row[key] || "";
        if (key === "psk" && (installation.wifi_secret_ssids || []).includes(row.ssid)) input.placeholder = "secret set";
        input.oninput = () => {
          row[key] = input.type === "checkbox" ? input.checked : input.value;
          dirty = true; status();
          if (key === "ssid") element.querySelector('[data-field="psk"]').placeholder = (installation.wifi_secret_ssids || []).includes(row.ssid) ? "secret set" : "";
        };
      });
      element.querySelectorAll("[data-move]").forEach(button => button.onclick = () => {
        const other = index + Number(button.dataset.move);
        [draft.networks[index], draft.networks[other]] = [draft.networks[other], draft.networks[index]];
        dirty = true; paint();
      });
      element.querySelector("[data-remove]").onclick = () => { draft.networks.splice(index, 1); dirty = true; paint(); };
      rows.append(element);
    });
    status();
  }
  country.onchange = () => { draft.country = country.value; dirty = true; };
  function add(ssid = "") {
    if (ssid && draft.networks.some(row => row.ssid === ssid)) return;
    draft.networks.push({ssid, hidden: false, enabled: true, psk: null});
    dirty = true; paint();
    rows.lastElementChild.querySelector('[data-field="ssid"]').focus();
  }
  document.getElementById("wifi-add").onclick = () => add();
  send.onclick = () => {
    awaiting = true; status();
    ws.send("set_wifi_networks", {config: {country: draft.country,
      networks: draft.networks.map(row => ({...row, psk: row.psk || null}))}});
  };
  ws.on("wifi_confirm", data => {
    const noun = data.passphrases === 1 ? "passphrase" : "passphrases";
    document.getElementById("wifi-confirm-warning").textContent = `⚠ This sends ${data.passphrases} ${noun} over the network. Anything on this network right now can read them. Send only on your own network.`;
    dialog.showModal();
  });
  dialog.onclose = () => {
    if (dialog.returnValue === "send") ws.send("send_wifi_networks", {confirmed: true});
    else { awaiting = false; status(); }
  };
  dialog.oncancel = () => { dialog.returnValue = "cancel"; };
  ws.on("error", () => { awaiting = false; status(); });
  ws.on("state", data => {
    country.innerHTML = (data.wifi_countries || ["GB"]).map(code => `<option>${esc(code)}</option>`).join("");
    if (!dirty) {
      draft = {country: data.wifi?.country || "GB", networks: (data.wifi?.networks || []).map(row => ({...row, psk: null}))};
      dirty = false; awaiting = false; paint();
    } else { country.value = draft.country; status(); }
  });
  ws.on("wifi_saved", () => {
    draft = {country: installation.wifi.country, networks: installation.wifi.networks.map(row => ({...row, psk: null}))};
    dirty = false; awaiting = false; paint();
  });
  panel.addEventListener("keydown", event => { if (event.key === "Enter" && event.target.matches("input")) { event.preventDefault(); if (!send.disabled) send.click(); } });
  document.getElementById("device-roster").addEventListener("click", event => {
    const button = event.target.closest("[data-wifi-adopt]");
    if (button) add(button.dataset.wifiAdopt);
  });
  window.WifiNetworks = {status, unmanaged(device) {
    return (device.report?.wifi?.unmanaged || []).map(name => `<div class="wifi-unmanaged"><span>${esc(name)}</span><button data-wifi-adopt="${esc(name)}">add to list</button></div>`).join("");
  }};
  paint();
  render(); // Draw unmanaged SSIDs even when the connect snapshot was replayed.
})();
