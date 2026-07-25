// A reusable target filter — All / Groups / Seat (thread 37, stitch 10).
//
// Bob's ruling was "let's use a shared seat filter as a reusable component",
// so this is deliberately not a widget belonging to the Control tab. It renders
// into any host element, owns its own keyboard behaviour, and reports the
// chosen target back; what a host does with that target is the host's business.
//
// The seat choice is shared rather than per-view: it is written to (and read
// from) one localStorage key, so selecting a Seat on the Seats tab and then
// opening Control lands on the same Seat. The Control surface is an iframe on
// its own document, so a shared key is what "the global selected seat" can
// honestly mean across that boundary.
(function () {
  "use strict";

  const SELECTED_SEAT_KEY = "bopos.selected-seat";
  const MODE_KEY = "bopos.target-filter-mode";
  const MODES = ["all", "groups", "seat"];
  const LABELS = {all: "All", groups: "Groups", seat: "Seat"};

  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

  function readStored(key) {
    try { return localStorage.getItem(key); }
    catch (_error) { return null; }
  }

  function writeStored(key, value) {
    try { localStorage.setItem(key, String(value)); }
    catch (_error) { /* private mode: the choice just doesn't persist */ }
  }

  function selectedSeat() {
    const raw = Number(readStored(SELECTED_SEAT_KEY));
    return Number.isInteger(raw) ? raw : null;
  }

  function selectSeat(id) {
    if (id == null) return;
    writeStored(SELECTED_SEAT_KEY, Number(id));
  }

  function create({host, getSeats, onChange, label = "Target"}) {
    let mode = MODES.includes(readStored(MODE_KEY)) ? readStored(MODE_KEY) : "all";

    function seats() {
      const list = getSeats() || [];
      return list.slice().sort((a, b) => Number(a.id) - Number(b.id));
    }

    // The stored Seat may not exist in this venue; fall back to the first.
    function currentSeat() {
      const list = seats();
      if (!list.length) return null;
      const stored = selectedSeat();
      return list.find(seat => Number(seat.id) === stored) || list[0];
    }

    function target() {
      if (mode === "seat") {
        const seat = currentSeat();
        return {mode, seat, id: seat ? Number(seat.id) : null};
      }
      return {mode, seat: null, id: null};
    }

    function render() {
      if (!host) return;
      const buttons = MODES.map(item =>
        `<button type="button" role="tab" data-target-mode="${item}" aria-selected="${item === mode}" tabindex="${item === mode ? 0 : -1}">${LABELS[item]}</button>`).join("");
      const list = seats();
      const seat = currentSeat();
      const picker = mode === "seat"
        ? `<label class="target-filter-seat">Seat <select data-target-seat ${list.length ? "" : "disabled"}>${
            list.length
              ? list.map(item => `<option value="${esc(item.id)}" ${seat && Number(item.id) === Number(seat.id) ? "selected" : ""}>${esc(item.name || `Seat ${item.id}`)}</option>`).join("")
              : '<option>No Seats</option>'}</select></label>`
        : "";
      host.innerHTML = `<div class="target-filter" role="tablist" aria-label="${esc(label)}">${buttons}</div>${picker}`;
      bind();
    }

    function activate(next, moveFocus = false) {
      if (!MODES.includes(next)) return;
      mode = next;
      writeStored(MODE_KEY, mode);
      render();
      if (moveFocus) host.querySelector(`[data-target-mode="${mode}"]`)?.focus();
      onChange?.(target());
    }

    function bind() {
      host.querySelectorAll("[data-target-mode]").forEach(button => {
        button.onclick = () => activate(button.dataset.targetMode);
        button.onkeydown = event => {
          if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
          event.preventDefault();
          const index = MODES.indexOf(mode);
          const next = event.key === "Home" ? 0
            : event.key === "End" ? MODES.length - 1
            : event.key === "ArrowRight" ? Math.min(MODES.length - 1, index + 1)
            : Math.max(0, index - 1);
          activate(MODES[next], true);
        };
      });
      const picker = host.querySelector("[data-target-seat]");
      if (picker) picker.onchange = () => {
        selectSeat(Number(picker.value));
        onChange?.(target());
      };
    }

    return {render, target, mode: () => mode, activate};
  }

  window.SeatFilter = {create, selectedSeat, selectSeat, MODES, SELECTED_SEAT_KEY};
})();
