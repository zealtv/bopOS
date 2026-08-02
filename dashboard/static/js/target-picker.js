// One target picker, two domains (02-component-unification/07).
//
// Two unrelated pickers existed: `SeatFilter`'s All/Groups/Seat radio tabs
// (mode-exclusive, one real consumer) and the Show inspector's chip disclosure
// (multi-select and mixable). Bob, 2026-07-30: "all or a selection of groups or
// a selection of seats or a mixture of all of them using that consistent target
// UI device." So the chip disclosure is the survivor and `SeatFilter`'s
// exclusive model is retired.
//
// TWO DOMAINS, ONE CHROME. Seats and groups are the site layer; physical
// devices are the hardware layer (the tied entity architecture review), and Bob
// named the distinction: "here we're targeting devices rather than seats. So
// perhaps a device picker and a seat picker are two different things." They are
// — so the domain supplies the roster and the wire selectors, while the
// disclosure, chips, summary and terse closed state are shared. The component
// never knows what a selector means; it only knows selectors are strings that
// hosts put on the wire.
//
// The component owns its whole appearance in `css/target-picker.css`, loaded by
// both documents. Anything a HOST needs to say about it is placement only —
// see `tests/test_css_component_ownership.py`.
(function () {
  "use strict";

  // The one shared seat. Written by the Seats tab, read by any picker that
  // follows focus, so choosing a Seat there and opening Control lands on the
  // same Seat (37/10, preserved deliberately).
  const FOCUS_SEAT_KEY = "bopos.selected-seat";

  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

  function readStored(key) {
    try { return localStorage.getItem(key); }
    catch (_error) { return null; }
  }

  function writeStored(key, value) {
    try { localStorage.setItem(key, String(value)); }
    catch (_error) { /* private mode: the choice just doesn't persist */ }
  }

  function focusedSeat() {
    const raw = Number(readStored(FOCUS_SEAT_KEY));
    return Number.isInteger(raw) ? raw : null;
  }

  function focusSeat(id) {
    if (id == null) return;
    writeStored(FOCUS_SEAT_KEY, Number(id));
  }

  // ---- selection algebra ---------------------------------------------------
  // A selection is an ordered list of wire selectors. `all` is exclusive with
  // everything else in every domain that offers it.

  function list(value, fallback = ["all"]) {
    if (Array.isArray(value)) return value.length ? value.slice() : fallback.slice();
    return typeof value === "string" && value ? [value] : fallback.slice();
  }

  function toggle(selection, selector, {aliases = [], multiple = true, fallback = ["all"]} = {}) {
    if (!multiple) return [selector];
    if (selector === "all") return ["all"];
    const current = list(selection, []).filter(entry => entry !== "all");
    const equivalents = [selector, ...aliases].filter(Boolean);
    const on = equivalents.some(entry => current.includes(entry));
    const next = on
      ? current.filter(entry => !equivalents.includes(entry))
      : [...current, selector];
    return next.length ? next : fallback.slice();
  }

  function remove(selection, selector, fallback = ["all"]) {
    const next = list(selection, []).filter(entry => entry !== selector);
    return next.length ? next : fallback.slice();
  }

  // A chip is "on" for its own value or any alias of it — the Show document may
  // hold the legacy `g<id>` form of a group the picker now renders by name.
  function chipOn(selection, chip) {
    if (selection.includes("all")) return false;
    return [chip.value, chip.legacy].filter(Boolean).some(entry => selection.includes(entry));
  }

  function labelsFrom(sections) {
    const labels = new Map();
    for (const section of sections) {
      for (const chip of section.chips || []) {
        labels.set(chip.value, chip.label);
        if (chip.legacy) labels.set(chip.legacy, chip.label);
      }
    }
    return labels;
  }

  // A selector with no chip is still nameable: strip the portable prefix and
  // show what the document actually holds. That is how a Show step targeting a
  // group this venue lacks stays legible instead of rendering blank.
  function labelFor(selector, labels) {
    const known = labels?.get?.(selector);
    if (known) return known;
    return String(selector).startsWith("group:") ? String(selector).slice(6) : String(selector);
  }

  function terse(selection, sections = [], {allTerse = "all", emptyTerse = "none"} = {}) {
    const entries = list(selection, []);
    if (!entries.length) return emptyTerse;
    if (entries.includes("all")) return allTerse;
    const labels = labelsFrom(sections);
    return entries.map(entry => labelFor(entry, labels)).join("+");
  }

  // ---- roster builders ----------------------------------------------------
  // One per domain. These are the only domain knowledge in the file, and they
  // produce nothing but chip definitions.

  function seatSections({groups = [], seats = [], groupSelector = "name"} = {}) {
    const groupChips = groups.map((group, index) => ({
      value: groupSelector === "id" ? `g${group.id}` : `group:${group.name}`,
      legacy: groupSelector === "id" ? `group:${group.name}` : `g${group.id}`,
      label: group.name || `Group ${group.id}`,
      sub: `g${group.id}`,
      slot: index % 4,
    }));
    const seatChips = seats.map(seat => ({
      value: String(seat.id),
      label: String(seat.id),
      title: seat.name || `Seat ${seat.id}`,
    }));
    const sections = [];
    if (groupChips.length) sections.push({kind: "group", chips: groupChips});
    if (seatChips.length) sections.push({kind: "seat", roster: true, chips: seatChips});
    return sections;
  }

  // Devices are named by their host — `Identity.primary` needs the installation
  // and eligibility reasons are the caller's vocabulary, neither of which is
  // this component's business.
  function deviceSections(devices = []) {
    const chips = devices.map(device => ({
      value: String(device.uid),
      label: device.label ?? String(device.uid),
      sub: device.sub || null,
      title: device.title || null,
      disabled: device.disabled === true,
    }));
    return chips.length ? [{kind: "device", roster: true, chips}] : [];
  }

  // ---- markup -------------------------------------------------------------

  function chipMarkup(chip, on, disabled, extra) {
    const off = disabled || chip.disabled ? " disabled" : "";
    const slot = chip.slot == null ? "" : ` slot-${chip.slot}`;
    const swatch = chip.slot == null ? "" : '<span class="target-chip-swatch" aria-hidden="true"></span>';
    const sub = chip.sub ? `<small>${esc(chip.sub)}</small>` : "";
    const title = chip.title ? ` title="${esc(chip.title)}"` : "";
    return `<button type="button" class="target-chip ${extra}${slot}${on ? " on" : ""}" data-target-toggle="${esc(chip.value)}"${
      chip.legacy ? ` data-target-legacy="${esc(chip.legacy)}"` : ""} aria-pressed="${on}"${title}${off}>${swatch}${esc(chip.label)}${sub}</button>`;
  }

  function chipClass(kind) {
    return kind === "group" ? "target-chip-group"
      : kind === "device" ? "target-chip-device"
      : "target-chip-seat";
  }

  function markup(spec) {
    const {
      id, label = "Target", sections = [], multiple = true, allowAll = true,
      allLabel = "All", allSummary = "every Seat", emptySummary = "No target",
      open = false, disabled = false, allDisabled = false, hostClass = "", warnings = [],
      allTerse = "all", emptyTerse = "none",
    } = spec;
    // An explicit empty array is a selection of NOTHING and renders as such —
    // only an absent selection takes the All default. `list`'s own fallback
    // would turn "no target" back into "every target" in the chrome, which is
    // the whole point of `pruneFallback: "empty"` (D5).
    const selection = Array.isArray(spec.selection)
      ? spec.selection.slice() : list(spec.selection, allowAll ? ["all"] : []);
    const isAll = allowAll && selection.includes("all");
    const off = disabled ? " disabled" : "";
    const labels = labelsFrom(sections);

    const head = allowAll
      ? [`<button type="button" class="target-chip target-chip-all${isAll ? " on" : ""}" data-target-toggle="all" aria-pressed="${isAll}"${allDisabled || disabled ? " disabled" : ""}>${esc(allLabel)}</button>`]
      : [];
    const rows = [];
    for (const section of sections) {
      const chips = (section.chips || []).map(chip =>
        chipMarkup(chip, chipOn(selection, chip), disabled, chipClass(section.kind)));
      if (section.roster) rows.push(`<div class="target-picker-chips target-picker-roster">${chips.join("")}</div>`);
      else head.push(...chips);
    }
    if (head.length) rows.unshift(`<div class="target-picker-chips">${head.join("")}</div>`);

    // The summary row exists to REMOVE entries from a mixture. A single-select
    // picker has nothing to remove — its one choice is replaced, not unset, and
    // the pressed chip plus the terse state already say which it is — so it has
    // no summary row rather than a dead one.
    const summary = !multiple ? ""
      : isAll
        ? `<div class="target-picker-summary"><span class="dim">${esc(allSummary)}</span></div>`
        : !selection.length
          ? `<div class="target-picker-summary"><span class="dim">${esc(emptySummary)}</span></div>`
          : `<div class="target-picker-summary">${selection.map(entry => `<button type="button" class="target-chip target-chip-selected" data-target-remove="${esc(entry)}" title="Remove ${esc(labelFor(entry, labels))}"${off}>${esc(labelFor(entry, labels))}<span aria-hidden="true"> ×</span></button>`).join("")}</div>`;

    const warningMarkup = warnings
      .map(warning => `<p class="target-picker-warning">${esc(warning)}</p>`).join("");
    return `<details class="target-picker${hostClass ? ` ${hostClass}` : ""}${disabled ? " target-picker-disabled" : ""}" data-target-picker="${esc(id)}"${open ? " open" : ""}>
      <summary><span>${esc(label)}</span><output class="target-picker-terse">${esc(terse(selection, sections, {allTerse, emptyTerse}))}</output></summary>
      <div class="target-picker-body">
        ${summary}
        ${rows.join("")}
        ${warningMarkup}
      </div>
    </details>`;
  }

  // What a click inside a picker means, so hosts do not each re-derive it from
  // the data-attributes. Returns null for a click that is not on a chip.
  function action(event) {
    const toggleChip = event.target?.closest?.("[data-target-toggle]");
    if (toggleChip) {
      return {kind: "toggle", value: toggleChip.dataset.targetToggle,
              aliases: [toggleChip.dataset.targetLegacy].filter(Boolean)};
    }
    const removal = event.target?.closest?.("[data-target-remove]");
    if (removal) return {kind: "remove", value: removal.dataset.targetRemove};
    return null;
  }

  // ---- imperative host wrapper -------------------------------------------
  // For hosts that own an element rather than a template string (the Control
  // surface, the Assets tab). Declarative hosts (the Show inspector, which
  // re-renders whole messages) use `markup` + `action` directly.
  //
  // Selection is PER HOST, persisted under its own key. That is deliberate:
  // `08-control-tab-columns` gives each column its own target, which one shared
  // multi-selection could not express. The single shared thing stays the FOCUS
  // SEAT — a picker with `followFocusSeat` adopts it when the Seats tab moves
  // it, which is the cross-tab behaviour that existed for a reason.
  //
  // `pruneFallback` separates "All is OFFERABLE" from "All is the FALLBACK"
  // (D5, Bob 2026-07-31). A host that keeps the All chip but must never be
  // widened into it behind the operator's back passes `"empty"`; it then reads
  // `dropped()` to say what was lost and renders its own unresolved state.
  //
  // A host may also own persistence itself, by passing no `storageKey` and
  // supplying `initialSelection` / `onOpenChange` instead. That is what the
  // Control tab's columns do: D9 puts the whole layout in ONE
  // `bopos.control.columns` record, and a picker quietly writing a key of its
  // own beside it would be a second authority for the same fact.
  function create({host, id, storageKey, spec, onChange, onOpenChange,
                   followFocusSeat = false, defaultOpen = true,
                   initialSelection = null, pruneFallback = "all"}) {
    const openKey = storageKey ? `${storageKey}.open` : null;
    let selection = null;
    // What the last prune took away, kept for as long as nothing has replaced
    // it, so a host can name the Seat or group that went.
    let dropped = [];
    // A host whose whole job is choosing a target opens by default — the Show
    // inspector's per-message picker is the one that starts closed. Either way
    // the operator's own collapse survives, so this is a default and not a mode.
    let open = openKey && readStored(openKey) != null
      ? readStored(openKey) === "true" : defaultOpen;
    let lastFocusSeat = focusedSeat();

    function base() {
      const built = spec() || {};
      return {allowAll: true, multiple: true, ...built};
    }

    function stored() {
      if (!storageKey) return null;
      try {
        const raw = JSON.parse(readStored(storageKey));
        return Array.isArray(raw) && raw.every(entry => typeof entry === "string") ? raw : null;
      } catch (_error) { return null; }
    }

    function persist() {
      if (storageKey) writeStored(storageKey, JSON.stringify(selection));
    }

    // A stored selector may name a Seat, group or device this venue no longer
    // has — or one that has since become unusable, like a device that went
    // offline while it was the Assets target. Prune rather than target either;
    // a disabled chip is not a selectable one, which is what makes the Assets
    // tab advance to the next eligible device as it did before the picker.
    //
    // What happens when NOTHING survives is the host's call. Substituting
    // `["all"]` is right for a picker that must always name something, and
    // wrong for a live control surface: a fader that drove Seat 7 would drive
    // the venue the moment Seat 7 was deleted, unasked. An empty target is
    // safe; an All target is not.
    function prune(current, built) {
      const known = new Set();
      for (const section of built.sections || []) {
        for (const chip of section.chips || []) {
          if (chip.disabled) continue;
          known.add(chip.value);
          if (chip.legacy) known.add(chip.legacy);
        }
      }
      const kept = current.filter(entry =>
        (entry === "all" && built.allowAll !== false && built.allDisabled !== true) || known.has(entry));
      if (kept.length) return built.multiple === false ? [kept[0]] : kept;
      if (pruneFallback === "empty") return [];
      if (built.allowAll !== false && built.allDisabled !== true) return ["all"];
      const first = (built.sections || []).flatMap(section => section.chips || [])
        .find(chip => !chip.disabled);
      return first ? [first.value] : [];
    }

    // Prune, and remember what that took. An unchanged empty selection keeps
    // the earlier casualty list: the host is still displaying it.
    function settle(next, built) {
      const pruned = prune(next, built);
      if (pruned.join(" ") !== next.join(" ")) {
        dropped = next.filter(entry => !pruned.includes(entry));
      } else if (pruned.length) {
        dropped = [];
      }
      return pruned;
    }

    function adoptFocusSeat(built) {
      if (!followFocusSeat) return false;
      const seat = focusedSeat();
      if (seat === lastFocusSeat) return false;
      lastFocusSeat = seat;
      if (seat == null) return false;
      selection = settle([String(seat)], built);
      persist();
      return true;
    }

    function resolve(built) {
      // An explicit empty `initialSelection` is a selection of NOTHING and
      // survives here, the same way `markup` treats one: a restored column
      // whose target the venue has lost must not reopen aimed at every Seat.
      if (selection == null) {
        selection = stored() ||
          (Array.isArray(initialSelection) ? initialSelection.slice() : null) ||
          (built.allowAll === false ? [] : ["all"]);
      }
      const moved = adoptFocusSeat(built);
      const pruned = settle(selection, built);
      if (pruned.join(" ") !== selection.join(" ")) {
        selection = pruned;
        persist();
      }
      return moved;
    }

    // A heartbeat re-render replaces the markup wholesale, which would otherwise
    // drop keyboard focus and scroll a long roster back to the top mid-choice.
    function render() {
      if (!host) return;
      const built = base();
      resolve(built);
      const active = host.contains(document.activeElement) ? document.activeElement : null;
      const focused = active?.dataset?.targetToggle ?? active?.dataset?.targetRemove ?? null;
      const focusedKind = active?.dataset?.targetToggle != null ? "toggle" : "remove";
      const scrolled = host.querySelector(".target-picker-roster")?.scrollTop || 0;
      host.innerHTML = markup({...built, id: id || "target", selection, open});
      if (focused != null) {
        const attribute = focusedKind === "toggle" ? "data-target-toggle" : "data-target-remove";
        host.querySelector(`[${attribute}="${CSS.escape(focused)}"]`)?.focus();
      }
      const roster = host.querySelector(".target-picker-roster");
      if (roster && scrolled) roster.scrollTop = scrolled;
    }

    function apply(next) {
      selection = next;
      dropped = [];
      persist();
      render();
      onChange?.(selection.slice());
    }

    // One delegated listener on the host, bound once: `render` replaces the
    // markup on every heartbeat, and per-element handlers would have to be
    // rebound each time (Playwright gotcha 16 is what that costs).
    if (host) {
      host.addEventListener("click", event => {
        const built = base();
        const intent = action(event);
        if (!intent) return;
        if (intent.kind === "toggle") {
          apply(toggle(selection || [], intent.value, {
            aliases: intent.aliases,
            multiple: built.multiple !== false,
            fallback: built.allowAll === false ? [intent.value] : ["all"],
          }));
        } else {
          apply(remove(selection || [], intent.value,
                       built.allowAll === false ? [] : ["all"]));
        }
      });
      // Capture phase, because `toggle` does not bubble. It also fires when a
      // re-render REPLACES the disclosure with one carrying the same state —
      // an echo of what we just drew, not an operator opening anything. Acting
      // on it wrote the open state back to the host on every heartbeat, which
      // is how a Control column restored as closed came back open.
      host.addEventListener("toggle", event => {
        const disclosure = event.target?.closest?.("[data-target-picker]");
        if (!disclosure || disclosure.open === open) return;
        open = disclosure.open;
        if (openKey) writeStored(openKey, open);
        onOpenChange?.(open);
      }, true);
      // The Control surface is a separate document from the Seats tab, so the
      // focus seat arrives as a storage event rather than a function call.
      window.addEventListener("storage", event => {
        if (event.key === FOCUS_SEAT_KEY && followFocusSeat) render();
      });
    }

    return {
      render,
      selection: () => (selection || []).slice(),
      dropped: () => dropped.slice(),
      // A host with nothing to render but "choose a target" needs to be able
      // to answer that button; opening the disclosure is the component's own
      // business, not the host's to reach in and set.
      reveal: () => {
        const opening = !open;
        open = true;
        if (openKey) writeStored(openKey, true);
        if (opening) onOpenChange?.(true);
        render();
        host?.querySelector("[data-target-toggle]")?.focus();
      },
      set: next => apply(list(next, [])),
    };
  }

  window.TargetPicker = {
    markup, action, create,
    list, toggle, remove, terse, labelFor, labelsFrom, chipOn,
    seatSections, deviceSections,
    focusSeat, focusedSeat, FOCUS_SEAT_KEY,
  };
})();
