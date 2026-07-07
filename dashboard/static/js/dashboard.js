const ws = new BopSocket("/ws");
let installation = {devices: {}};
let selected = null;
let muted = false;
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

function mergeDevice(device) { if (device && device.uid) installation.devices[device.uid] = device; render(); }
ws.on("connection", connected => { $("#ws-status").textContent = connected ? "connected" : "disconnected"; $("#ws-status").className = connected ? "online" : "offline"; });
ws.on("state", data => { installation = data; muted = !!data.muted; render(); });
ws.on("device_update", data => { if (data && data.devices) installation = data; else mergeDevice(data); });
ws.on("params_declaration", mergeDevice); ws.on("report", mergeDevice); ws.on("rev", mergeDevice);
ws.on("device_offline", data => { if (installation.devices[data.uid]) installation.devices[data.uid].online = false; render(); });
ws.on("mute_all", data => { muted = !!data.value; renderHeader(); });

function render() {
  const devices = Object.values(installation.devices || {});
  const assigned = devices.filter(d => Number(d.id) >= 0).sort((a,b) => a.id-b.id);
  const unassigned = devices.filter(d => Number(d.id) < 0);
  $("#assigned").innerHTML = assigned.map(row).join("");
  $("#unassigned").innerHTML = unassigned.map(row).join("") || '<p class="dim">None</p>';
  document.querySelectorAll(".device-row").forEach(el => el.onclick = () => select(el.dataset.uid));
  renderHeader(); renderDetail();
}
function row(d) {
  const status = d.online ? (Number(d.engine_alive) === 0 ? "crashed" : "online") : "offline";
  return `<button class="device-row ${d.uid===selected?'selected':''}" data-uid="${esc(d.uid)}"><i class="dot ${status}"></i><span><strong>${esc(d.name || d.uid)}</strong><small>ID ${esc(d.id)} · ${esc(d.version)}${d.rssi != null ? ` · ${d.rssi} dBm` : ''}</small></span></button>`;
}
function renderHeader() {
  const ds = Object.values(installation.devices || {}), online = ds.filter(d => d.online).length;
  $("#online-count").textContent = `${online} / ${ds.length} online`;
  $("#mute-all").classList.toggle("active", muted); $("#mute-all").textContent = muted ? "MUTED — UNMUTE" : "MUTE ALL";
}
function select(uid) { selected = uid; const d=installation.devices[uid]; if (!d.declared) ws.send("request_params", {uid}); render(); }
let interacting = false;
document.addEventListener("pointerdown", e => { if (e.target.closest("#detail input")) interacting = true; });
document.addEventListener("pointerup", () => { if (interacting) { interacting = false; renderDetail(); } });

function renderDetail() {
  const d = installation.devices[selected]; if (!d) return;
  // never rebuild the panel out from under a drag or mid-typing
  const active = document.activeElement;
  if (interacting || ($("#detail").contains(active) && active.matches('input[type="text"]'))) return;
  const declarations = d.declared || [];
  let previousGroup = null;
  const controls = declarations.map(p => {
    const group = p.group || "parameters", label = group !== previousGroup ? `<h3>${esc(group)}</h3>` : ""; previousGroup=group;
    const value = d.params?.[p.name] ?? p.default ?? "";
    if (p.type === "s") return `${label}<label>${esc(p.name)}<input data-param="${esc(p.name)}" type="text" value="${esc(value)}"></label>`;
    if (p.type === "i" && p.min===0 && p.max===1) return `${label}<label class="toggle">${esc(p.name)}<input data-param="${esc(p.name)}" type="checkbox" ${value?'checked':''}></label>`;
    return `${label}<label>${esc(p.name)} <output>${esc(value)}</output><input data-param="${esc(p.name)}" type="range" min="${p.min??0}" max="${p.max??1}" step="${p.type==='i'?1:0.01}" value="${esc(value)}"></label>`;
  }).join("");
  $("#detail").innerHTML = `<section><h2>${esc(d.name || d.uid)} ${d.undeclared?'<b class="badge">UNDECLARED</b>':''}</h2><dl><dt>UID</dt><dd>${esc(d.uid)}</dd><dt>ID</dt><dd>${esc(d.id)}</dd><dt>Status</dt><dd>${d.online?'online':'offline'}</dd><dt>Version</dt><dd>${esc(d.version)}</dd><dt>Engine</dt><dd>${d.engine_alive?'alive':'stopped'}</dd><dt>RSSI</dt><dd>${esc(d.rssi)}</dd><dt>IP</dt><dd>${esc(d.ip)}</dd><dt>Converged</dt><dd>${d.rev?`${esc(d.rev.sha)} (${esc(d.rev.model)}, ${ago(d.rev.at)})`:'—'}</dd></dl></section>
    <section><div class="section-head"><h2>Params</h2><label><input id="broadcast" type="checkbox"> broadcast to all</label></div><div class="params">${controls || '<p class="dim">Loading declaration…</p>'}</div></section>
    <section><h2>Actions</h2><div class="actions">${["reboot","shutdown","restart-engine","update","get_samples","aloha"].map(v=>`<button data-action="${v}">${v.replace('_',' ')}</button>`).join('')}<button data-identify>Identify</button></div></section>
    <section><div class="section-head"><h2>Report</h2><button id="refresh-report">Refresh report</button></div>${report(d.report)}</section>`;
  bindControls(d);
}
function report(r) { if (!r) return '<p class="dim">No report loaded.</p>'; const keys=["engine","patch","git_rev","uptime","has_i2c","has_wifi","audio_channels","screen","update_model","contract_version"]; return `<dl>${keys.map(k=>`<dt>${k}</dt><dd>${k==='uptime'?human(r[k]):esc(r[k])}</dd>`).join('')}</dl>`; }
function human(seconds) { seconds=Number(seconds)||0; return `${Math.floor(seconds/3600)}h ${Math.floor(seconds%3600/60)}m ${seconds%60}s`; }
function ago(epoch) { const s=Math.max(0,Math.round(Date.now()/1000-Number(epoch))); return s<60?`${s}s ago`:s<3600?`${Math.floor(s/60)}m ago`:`${Math.floor(s/3600)}h ago`; }
function bindControls(d) {
  let last=0, timer;
  document.querySelectorAll("[data-param]").forEach(input => {
    const send = () => {
      let value=input.type==='checkbox'?(input.checked?1:0):input.value; if(input.type==='range') value=Number(value);
      ws.send("set_param", {uid:d.uid,name:input.dataset.param,value,broadcast:!!$("#broadcast")?.checked});
      // optimistic local update so the post-drag re-render shows the sent value,
      // not the last server echo; re-sends are safe (idempotent full-state)
      const local = installation.devices[d.uid]; if (local) local.params[input.dataset.param] = value;
    };
    input.oninput = () => { input.previousElementSibling?.tagName==='OUTPUT' && (input.previousElementSibling.value=input.value); const now=performance.now(); if(now-last>=33){last=now;send();} else {clearTimeout(timer);timer=setTimeout(send,33-(now-last));} };
    input.onchange=send;
    // fires target-phase, before the document pointerup re-render can detach
    // the input and strand the final change event on a dead node
    input.onpointerup=send;
  });
  document.querySelectorAll("[data-action]").forEach(button => button.onclick=()=>{ const verb=button.dataset.action; if(["reboot","shutdown"].includes(verb)&&!confirm(`${verb} ${d.name||d.uid}?`))return; ws.send("action",{uid:d.uid,verb}); });
  $("[data-identify]").onclick=()=>ws.send("identify",{uid:d.uid});
  $("#refresh-report").onclick=()=>ws.send("request_report",{uid:d.uid});
}
$("#mute-all").onclick=()=>{muted=!muted;ws.send("mute_all",{value:muted?1:0});renderHeader();};
document.querySelectorAll("[data-all]").forEach(b=>b.onclick=()=>{const verb=b.dataset.all;if(["reboot","update"].includes(verb)&&!confirm(`${verb} all devices?`))return;ws.send("action",{uid:"all",verb});});
