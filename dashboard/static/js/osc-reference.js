/* The OSC tab: what the dashboard's input port accepts, from `state.osc_input`. */
(function () {
  const $id = (id) => document.getElementById(id);
  const text = (value) => String(value ?? "—").replace(/[&<>"']/g,
    (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"})[c]);
  const copy = (label, value) => `<div class="osc-copy"><small>${text(label)}</small><code>${text(value)}</code>`
    + `<button type="button" data-copy-identity="${text(value)}" aria-label="Copy ${text(label)}">`
    + `<span class="copy-label">Copy</span><span class="copy-feedback" role="status"></span></button></div>`;
  const empty = (message) => `<p class="dim">${text(message)}</p>`;
  const num = (value) => (Number.isInteger(value) ? String(value) : String(+Number(value).toPrecision(6)));
  function range(item) {
    const bits = [];
    if (item.kind === "enum") bits.push(`<span><b>options</b> ${item.options.map(text).join(" · ")}</span>`);
    else if (item.min !== undefined || item.max !== undefined)
      bits.push(`<span><b>range</b> ${item.min === undefined ? "…" : num(item.min)} to ${item.max === undefined ? "…" : num(item.max)}</span>`);
    if (item.default !== undefined) bits.push(`<span><b>default</b> ${text(item.default)}</span>`);
    return bits.join("");
  }
  function addresses(plane, identity, shortOk) {
    return `<div class="osc-addresses"><code>/&lt;target&gt;/${text(identity)}</code>`
      + `<small>explicit <code>/&lt;target&gt;/${plane}/${text(identity)}</code></small>`
      + (shortOk ? "" : `<span class="osc-flag">⚠ short form is ambiguous; use the explicit address</span>`) + `</div>`;
  }
  function field(f) {
    return `<span class="${f.optional ? "osc-opt" : ""}"><b>${text(f.name)}</b> ${text(f.kind)}${f.optional ? " (optional)" : ""} ${range(f)}</span>`;
  }
  function render(input) {
    if (!input || !input.reference) return;
    const ref = input.reference, target = input.target || {};
    const mode = {off: "Live", simulate: "Simulation", edit: "Patch Edit"}[target.mode] || target.mode;
    $id("osc-target").textContent = target.patch
      ? `Generated from ${target.mode === "edit" ? "the edited patch" : "the fleet patch"} ${target.patch} · ${mode}`
      : `No patch is active in ${mode}; only commands and groups apply.`;
    $id("osc-endpoint").innerHTML = (input.host ? copy("IP", input.host) : `<p class="dim">The dashboard could not find its LAN address.</p>`)
      + copy("Port", input.port);
    $id("osc-commands").innerHTML = `<div class="osc-rows">${ref.commands.map((c) =>
      `<div class="osc-row"><div class="osc-addresses"><code>${text(c.address)} ${text(c.args)}</code></div>`
      + `<div class="osc-detail">${text(c.note)}</div></div>`).join("")}</div>`;
    $id("osc-events").innerHTML = ref.events.length
      ? `<div class="osc-rows">${ref.events.map((e) => `<div class="osc-row">${addresses("e", e.identity, e.short_ok)}`
        + `<div class="osc-detail">${e.fields.length ? e.fields.map(field).join("") : "no fields"}</div></div>`).join("")}</div>`
      : empty("This patch declares no events.");
    $id("osc-params").innerHTML = ref.params.length
      ? `<div class="osc-rows">${ref.params.map((p) => `<div class="osc-row">${addresses("p", p.identity, p.short_ok)}`
        + `<div class="osc-detail"><span><b>kind</b> ${text(p.kind)}</span>${range(p)}</div></div>`).join("")}</div>`
      : empty("This patch declares no parameters.");
    $id("osc-groups").innerHTML = `<div class="osc-groups"><div class="osc-group"><strong>all</strong></div>`
      + `<div class="osc-group"><strong>a Seat number</strong><code>as in Seats</code></div>`
      + ref.groups.map((g) => `<div class="osc-group"><strong>${text(g.name || "(unnamed)")}</strong><code>g${g.id}</code></div>`).join("")
      + `</div>`;
    $id("osc-recent").innerHTML = input.recent.length
      ? [...input.recent].reverse().map((r) => `<div class="osc-recent-row osc-recent-${text(r.kind)}">`
        + `<time>${new Date(r.time * 1000).toLocaleTimeString([], {hour12: false})}</time><span class="osc-who">${text(r.sender)}</span>`
        + `<code>${text(r.address || "—")}</code><span class="osc-why">${text(r.reason)}</span></div>`).join("")
      : empty("Nothing rejected or clamped.");
  }
  ws.on("state", (data) => render(data.osc_input));
})();
