// Capture the venue's preset arrangement as a Show step —
// 08-control-tab-columns/4-n-columns/2-venue-wide-capture (D1–D3).
//
// ONE action, TWO surfaces, NO scope. Capture is venue-wide: the arrangement
// is rebuilt server-side from every Seat's `applied_preset`, so a scope
// argument never selected what the asking surface showed — it only decided
// which seats the server consulted, and got `groups` wrong. Both the Control
// tab's strip and the Show tab's edit bar reach the same unparameterised verb.
//
// It also holds NO state that the wire has to fetch. `applied_preset`,
// `preset_dirty`, `groups` and `current_show` all ride the `state` heartbeat,
// so the ambient count, the armed preview and both disabled states are derived
// locally. That is what let `preview_show_preset_capture` be deleted rather
// than re-shaped: it existed only because the Control tab used to be an iframe
// that could see neither the show nor the provenance.
//
// Hosts render strings (`show.js` re-renders its whole root; `control-host.js`
// fills two slots), so this component hands back HTML and takes clicks back,
// rather than owning DOM of its own. What it does own is the markup and the
// classes — `css/show-capture.css` is the app's sixth component stylesheet, and
// no surface may restyle a `.show-capture-*` class from its own file
// (`tests/test_css_component_ownership.py`).
(function () {
  "use strict";

  const UNDO_MS = 8000;
  // Beyond this the row is a paragraph, not a row. The rest are counted.
  const SEAT_IDS_SHOWN = 4;

  const commitListeners = [];

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[character]));
  }

  // The client half of `preset_application.capture_target` — the most portable
  // selector shape for one exact concrete Seat set. Mirrored rather than
  // fetched, because the whole point of this stitch is that the preview needs
  // no round trip; the server stays authoritative for what is actually minted,
  // and any drift shows as a preview that disagrees with the step, not as a
  // wrong capture.
  function captureTarget(memberIds, everyId, groups) {
    const selected = new Set(memberIds);
    if (selected.size === everyId.length
        && everyId.every(id => selected.has(id))) {
      return {scope: "all"};
    }
    const matches = [];
    Object.values(groups || {}).forEach(group => {
      const groupId = Number(group.id);
      const members = everyId.filter(id => (group.members || []).includes(id));
      if (members.length === selected.size && members.every(id => selected.has(id))) {
        matches.push(group);
      }
    });
    if (matches.length) {
      const best = matches.reduce((low, group) =>
        Number(group.id) < Number(low.id) ? group : low);
      return {scope: "group", id: Number(best.id), name: best.name || ""};
    }
    return {scope: "seats", ids: [...selected].sort((a, b) => a - b)};
  }

  // `capture_target` reads membership off the seats; groups in the public
  // state carry no member list, so build one here from the same source.
  function groupsWithMembers(state) {
    const groups = {};
    Object.values(state.groups || {}).forEach(group => {
      groups[String(group.id)] = {
        id: Number(group.id),
        name: group.name || "",
        members: Object.values(state.seats || {})
          .filter(seat => (seat.groups || []).map(Number).includes(Number(group.id)))
          .map(seat => Number(seat.id))
          .sort((a, b) => a - b),
      };
    });
    return groups;
  }

  function targetLabel(target) {
    if (target.scope === "all") return "→ all Seats";
    if (target.scope === "group") {
      return `→ group “${target.name || `g${target.id}`}”`;
    }
    const shown = target.ids.slice(0, SEAT_IDS_SHOWN);
    const extra = target.ids.length - shown.length;
    return `→ Seat ${shown.join(", ")}${extra ? ` +${extra}` : ""}`;
  }

  // What the server would mint, derived from the same facts it reads.
  function plan(state) {
    const seats = Object.values(state.seats || {})
      .sort((a, b) => Number(a.id) - Number(b.id));
    const everyId = seats.map(seat => Number(seat.id));
    const groups = groupsWithMembers(state);
    const grouped = new Map();
    seats.forEach(seat => {
      const marker = seat.applied_preset;
      if (!marker || !marker.patch || !marker.name) return;
      const key = `${marker.patch}/${marker.name}`;
      if (!grouped.has(key)) {
        grouped.set(key, {patch: marker.patch, name: marker.name,
                          ids: [], dirty: false});
      }
      const entry = grouped.get(key);
      entry.ids.push(Number(seat.id));
      if (seat.preset_dirty) entry.dirty = true;
    });
    // Sorted by (patch, name), as `_captured_show_preset_messages` sorts its
    // grouping — so preview order is mint order and the derived step name the
    // preview implies is the one the step gets.
    const messages = [...grouped.values()]
      .sort((a, b) => (a.patch + a.name).localeCompare(b.patch + b.name))
      .map(entry => ({...entry, target: captureTarget(entry.ids, everyId, groups)}));
    const applied = seats.filter(seat => seat.applied_preset?.name).length;
    return {seats, messages, applied, total: seats.length,
            omitted: seats.length - applied};
  }

  // The disabled states, with their causes told apart. `preset_provenance_seen`
  // is the dashboard saying "a preset has been applied since I started"; it is
  // false both on a fresh venue and after a restart, and those two really are
  // one observation — but they share one piece of advice (re-apply), which is
  // exactly what separates them from "applied, then cleared".
  function blockedReason(state, summary, showLoaded) {
    if (!showLoaded) {
      return {terse: "no Show loaded",
              full: "Load or create a Show before capturing an arrangement."};
    }
    if (!summary.total) {
      return {terse: "no Seats", full: "This venue has no Seats to capture."};
    }
    if (!summary.applied && !state.preset_provenance_seen) {
      return {
        terse: "nothing applied this session",
        full: "No preset has been applied since the dashboard started. " +
          "Applied-preset provenance is never saved, so a restart clears it " +
          "even though the venue still sounds the same — re-apply the presets " +
          "you want to capture.",
      };
    }
    if (!summary.applied) {
      return {terse: "nothing applied",
              full: "No Seat currently has a preset applied."};
    }
    return null;
  }

  function create({ws, getState, onChange}) {
    const state = () => getState?.() || {};
    // "idle" | "armed" | "captured"
    let phase = "idle";
    let captured = null;
    let pending = null;
    let undoTimer = null;
    let items = [];
    // `current_show` rides the `state` heartbeat, but `set_current_show`
    // broadcasts `shows` WITHOUT a full state — so a show created a moment ago
    // is loaded on the server while `installation` still says none is. The
    // `shows` catalog is the timely fact; state is the fallback until one
    // arrives.
    let catalogued = null;

    function changed() { onChange?.(); }

    function clearUndo() {
      if (undoTimer) { clearTimeout(undoTimer); undoTimer = null; }
      if (phase === "captured") { phase = "idle"; captured = null; }
    }

    function summary() {
      const current = state();
      const derived = plan(current);
      const loaded = catalogued === null
        ? !!current.current_show : !!catalogued;
      return {...derived, blocked: blockedReason(current, derived, loaded)};
    }

    function observeShows(data) {
      const loaded = data?.current || null;
      if (loaded === catalogued) return;
      catalogued = loaded;
      if (!loaded) { pending = null; phase = "idle"; clearUndo(); }
      changed();
    }

    function buttonHtml() {
      if (phase === "captured") {
        return `<span class="show-capture-done" role="status">captured “${esc(captured.alias)}”` +
          ` <button type="button" class="show-capture-undo" data-show-capture="undo">undo</button></span>`;
      }
      const info = summary();
      const off = phase === "idle" && info.blocked;
      const suffix = off
        ? esc(info.blocked.terse)
        : `${info.applied}/${info.total}`;
      const title = off ? info.blocked.full
        : phase === "armed" ? "Cancel the armed capture"
          : `Capture the applied preset arrangement as a Show step (${info.applied} of ${info.total} Seats).`;
      return `<button type="button" class="show-capture-button" data-show-capture="arm"` +
        `${off ? " disabled" : ""}${phase === "armed" ? ' aria-expanded="true"' : ""}` +
        ` title="${esc(title)}" aria-label="${esc(title)}">` +
        `capture step <b>· ${suffix}</b></button>`;
    }

    function rowHtml(message) {
      const portable = message.target.scope !== "seats";
      const notes = [];
      if (message.dirty) {
        notes.push('<span class="show-capture-warn">edited since applied —' +
          " captures the preset, not the edits</span>");
      }
      notes.push(portable
        ? '<span class="show-capture-note">portable</span>'
        : '<span class="show-capture-note">site-bound — Seat ids, not a group name</span>');
      return `<tr><td><span class="show-capture-pill">PRE</span></td>` +
        `<td>${esc(message.name)}</td><td>${esc(targetLabel(message.target))}</td>` +
        `<td>${notes.join(" · ")}</td></tr>`;
    }

    function panelHtml() {
      if (phase !== "armed") return "";
      const info = summary();
      if (info.blocked) return "";
      const count = info.messages.length;
      const omitted = info.omitted
        ? `<tr class="show-capture-omitted"><td>—</td><td>(none)</td>` +
          `<td>→ ${info.omitted} Seat${info.omitted === 1 ? "" : "s"}</td>` +
          `<td>no preset applied · not captured</td></tr>`
        : "";
      const heading = `Capture arrangement — ${count} message${count === 1 ? "" : "s"}` +
        (info.omitted ? `, ${info.omitted} Seat${info.omitted === 1 ? "" : "s"} omitted` : "");
      return `<div class="show-capture-preview" role="group" aria-label="${esc(heading)}">
        <h2>${esc(heading)}</h2>
        <table><tbody>${info.messages.map(rowHtml).join("")}${omitted}</tbody></table>
        <footer>
          <button type="button" data-show-capture="cancel">Cancel</button>
          <button type="button" class="show-capture-commit" data-show-capture="commit">Capture</button>
        </footer>
      </div>`;
    }

    function commit() {
      const info = summary();
      if (info.blocked) { phase = "idle"; changed(); return; }
      // Watch for the step the server appends rather than guessing its uid or
      // its name: the alias is DERIVED server-side (D3), and the undo label has
      // to read back what actually landed.
      pending = {known: new Set(items.map(item => item.uid))};
      phase = "idle";
      ws.send("capture_show_preset_step", {});
      changed();
      commitListeners.forEach(listener => listener());
    }

    // `undo_show` pops the last show mutation, whatever it was — so the offer
    // has to disappear the moment anything else edits the show, or "undo"
    // silently discards an unrelated edit. This is the check: the affordance
    // survives exactly the one broadcast that carries our own step.
    function observeShow(show) {
      items = Array.isArray(show?.items) ? show.items : [];
      const before = phase;
      if (pending) {
        const added = items.find(item =>
          item.kind === "step" && !pending.known.has(item.uid));
        pending = null;
        if (added) {
          captured = {uid: added.uid, alias: added.alias || "Captured presets"};
          phase = "captured";
          undoTimer = setTimeout(() => { clearUndo(); changed(); }, UNDO_MS);
        }
      } else if (phase === "captured"
                 // Ours is gone (undone here, undone elsewhere, or deleted), or
                 // it is no longer the last item — which means a later mutation
                 // now sits on top of the undo stack and `undo_show` would take
                 // THAT instead. Either way the offer has to stop being made.
                 && items[items.length - 1]?.uid !== captured.uid) {
        clearUndo();
      }
      if (phase !== before) changed();
    }

    function handle(event) {
      const control = event.target.closest?.("[data-show-capture]");
      if (!control || control.disabled) return false;
      const action = control.dataset.showCapture;
      if (action === "arm") {
        phase = phase === "armed" ? "idle" : "armed";
        clearUndo();
        changed();
      } else if (action === "cancel") {
        phase = "idle";
        changed();
      } else if (action === "commit") {
        commit();
      } else if (action === "undo") {
        ws.send("undo_show", {});
        clearUndo();
        changed();
      } else {
        return false;
      }
      return true;
    }

    return {summary, buttonHtml, panelHtml, handle, observeShow, observeShows,
            get armed() { return phase === "armed"; }};
  }

  window.ShowCapture = {
    create,
    // Fires on every surface when ANY surface commits, so the Show tab can hand
    // the new step to its click-to-edit rename (D3) even when the capture came
    // from the Control tab.
    onCommit(listener) { commitListeners.push(listener); },
  };
})();
