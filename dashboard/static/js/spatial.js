// SVG top-down floor plan and spatial point authoring. Coordinates are metres,
// origin top-left, x right, y down. Coloured fields show authored falloff
// geometry; the browser never sends per-device gains (nodes own decomposition).
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const TRAY_GAP = 0.3, TRAY_H = 1.2, PAD = 0.6, ELEMENT_R = 0.2, MOVE_MIN = 0.08;
  const LISTENER_RANGE_MIN = 0.5; // audition-falloff/2-range-widget floor
  const LISTENER_RANGE_DEFAULT = 3.0; // matches state.py LISTENER_RANGE_DEFAULT
  // 22-listener-range-ux: heading and range are disjoint gestures. The tip is a
  // pure aim handle at a fixed distance; range is scrubbed on a fixed collar that
  // never leaves the dot, so range stays settable with the listener at any edge.
  const LISTENER_HANDLE = 0.9;   // metres, ratified (not screen pixels)
  const LISTENER_COLLAR = 0.45;  // metres, fixed — never grows with range
  const LISTENER_SCRUB_GAIN = 2.5;      // ratified: relative pointer-distance delta
  const LISTENER_SCRUB_FINE = 0.25;     // shift multiplier
  const ELEMENT_COLOURS = ["#45d483", "#5ea7ff", "#f2b84b", "#db79ff", "#ff7380", "#55d9d2"];
  const POINT_COLOURS = ["#5ea7ff", "#f2b84b", "#db79ff", "#ff7380", "#55d9d2", "#45d483"];
  let seatDrag = null, pointDrag = null, listenerDrag = null, headingDrag = null, rangeDrag = null;
  let last = null;
  let selectedPoint = null;
  let lastClick = {seatId: null, time: 0};
  let pointFrame = {};
  let lastPointSend = 0;
  let lastListenerSend = 0;
  let valueLabelTimer = null;
  // Survives the re-render a gesture provokes: the keyboard/wheel paths send
  // set_listener, the server broadcasts, and render() rebuilds the puck — which
  // would otherwise wipe the label a few frames after it appeared.
  let valueLabelGesture = null;
  let valueLabelUntil = 0;
  let editorLast = null;
  let editorPointDrag = null;
  let selectedEditorPoint = null;
  let lastEditorPointSend = 0;
  const drafts = new Map();

  function el(name, attrs, parent) {
    const node = document.createElementNS(NS, name);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (parent) parent.appendChild(node);
    return node;
  }
  const status = d => d.online ? (Number(d.engine_alive) === 0 ? "crashed" : "online") : "offline";
  const round = value => Math.round(Number(value) * 100) / 100;
  const clone = value => JSON.parse(JSON.stringify(value));
  const toSvg = (svg, event) => {
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.getScreenCTM().inverse());
    return [point.x, point.y];
  };
  const pointsOf = installation => installation.points || (installation.points = {});
  const authoredPoint = (installation, id) => pointsOf(installation)[id] || pointsOf(installation)[String(id)] || drafts.get(Number(id));
  const shownXY = point => pointFrame[String(point.id)] || [point.x, point.y];
  const pointColour = id => POINT_COLOURS[Math.abs(Number(id)) % POINT_COLOURS.length];

  function render(installation, selected, select, ws, groupView={}) {
    last = [installation, selected, select, ws, groupView];
    if (seatDrag || pointDrag || listenerDrag || headingDrag || rangeDrag) return;
    const svg = document.getElementById("spatial");
    if (!svg) return;
    svg.classList.toggle("group-focused", groupView.focused != null);
    // A heartbeat re-render must not steal keyboard control of the listener
    // mid-nudge, or arrow keys work exactly once.
    const keepListenerFocus = !!document.activeElement?.closest?.("g[data-listener]");
    const room = installation.room || {width: 10, depth: 8};
    const W = Number(room.width) || 10, D = Number(room.depth) || 8;
    svg.setAttribute("viewBox", `${-PAD} ${-PAD} ${W + 2 * PAD} ${D + TRAY_GAP + TRAY_H + 2 * PAD}`);
    svg.replaceChildren();
    const defs = el("defs", {}, svg);
    const clip = el("clipPath", {id: "spatial-room-clip"}, defs);
    el("rect", {x: 0, y: 0, width: W, height: D}, clip);
    el("rect", {x: 0, y: 0, width: W, height: D, class: "room"}, svg);
    const origin = room.origin || [0, 0];
    const originGroup = el("g", {class: "space-origin",
                                  transform: `translate(${origin[0]} ${origin[1]})`}, svg);
    el("circle", {r: 0.16}, originGroup);
    el("line", {x1: -0.35, y1: 0, x2: 0.35, y2: 0}, originGroup);
    el("line", {x1: 0, y1: -0.35, x2: 0, y2: 0.35}, originGroup);
    el("text", {x: 0.22, y: 0.38}, originGroup).textContent = "0,0";
    el("rect", {x: 0, y: D + TRAY_GAP, width: W, height: TRAY_H, class: "tray"}, svg);
    el("text", {x: 0.15, y: D + TRAY_GAP + 0.38, class: "tray-label"}, svg).textContent = "UNPLACED";

    // One coloured falloff field per point sits behind constant device dots.
    const fields = el("g", {class: "point-fields", "clip-path": "url(#spatial-room-clip)"}, svg);
    for (const point of Object.values(pointsOf(installation))) {
      const [x, y] = shownXY(point);
      el("circle", {cx: x, cy: y, r: point.r, class: "point-radius",
                    style: `--point-colour:${pointColour(point.id)}`,
                    "data-radius-id": point.id}, fields);
    }

    const devices = installation.devices || {};
    const seats = Object.values(installation.seats || {}).sort((a,b)=>Number(a.id)-Number(b.id));
    const visibleSlots = (groupView.visibleSlots || groupView.visible || []).slice(0, 4);
    const visibleGroups = visibleSlots.filter(id => id != null).map(Number);
    const focusedGroup = groupView.focused == null ? null : Number(groupView.focused);
    const groupSlots = groupView.slots || [];
    let slot = 0;
    for (const seat of seats) {
      const d = Object.values(devices).find(item=>item.virtual&&Number(item.seat_id)===Number(seat.id)) || devices[seat.bound];
      const occupancy = d?.virtual ? "sim" : d?.online ? "online" : "offline";
      const memberships = (seat.groups || []).map(Number);
      const focusedMember = focusedGroup !== null && memberships.includes(focusedGroup);
      const comparedMember = visibleGroups.some(id => memberships.includes(id));
      const emphasis = focusedGroup !== null ? (focusedMember ? "" : " group-muted")
        : visibleGroups.length && !comparedMember ? " group-dim" : "";
      const membershipNames = memberships.map(id => {
        const group = installation.groups?.[String(id)] || installation.groups?.[id];
        return group ? `${group.name}, g${id}` : `g${id}`;
      });
      const node = el("g", {class: `node ${occupancy}${Number(seat.id) === Number(selected) ? " selected" : ""}${emphasis}`,
                            "data-uid": d?.uid || "", "data-seat-id": seat.id,
                            tabindex: "0", role: "button",
                            "aria-label": `Seat ${seat.id}; ${membershipNames.join("; ") || "no groups"}`}, svg);
      el("title", {}, node).textContent = `Seat ${seat.id} · ${membershipNames.join(", ") || "No groups"}`;
      const positions = (seat.positions || []).filter(Array.isArray);
      if (!positions.length) {
        positions.push([0.7 + 1.7 * slot++, D + TRAY_GAP + TRAY_H * 0.62]);
      }
      if (positions.length > 1) {
        el("line", {x1: positions[0][0], y1: positions[0][1],
                    x2: positions[1][0], y2: positions[1][1], class: "pair"}, node);
      }
      positions.forEach((position, index) => {
        const g = el("g", {class: "element", "data-element": index,
                           transform: `translate(${position[0]} ${position[1]})`}, node);
        el("circle", {r: 0.34, class: "element-hit", fill: "transparent",
                      "data-point": index}, g);
        visibleSlots.forEach((rawGroupId, railIndex) => {
          if (rawGroupId == null) return;
          const groupId = Number(rawGroupId);
          if (!memberships.includes(groupId)) return;
          const radius = ELEMENT_R + 0.11 + railIndex * 0.105;
          const slotStyle = groupSlots[railIndex] || {};
          const classes = `membership-rail slot-${railIndex + 1}${focusedGroup === groupId ? " focused" : ""}`;
          const style = `--group-colour:${slotStyle.colour || "currentColor"}`;
          el("circle", {r: radius, class: `${classes} back`, style,
                        "data-group-id": groupId, "vector-effect": "non-scaling-stroke"}, g);
          el("circle", {r: radius, class: classes, style,
                        "data-group-id": groupId, "vector-effect": "non-scaling-stroke"}, g);
        });
        const circle = el("circle", {r: ELEMENT_R, class: `element-dot ${index === 0 ? "p1" : "p2"}`,
                                     fill: ELEMENT_COLOURS[index % ELEMENT_COLOURS.length],
                                     "fill-opacity": 0.9,
                                     "data-point": index}, g);
        circle.dataset.baseRadius = ELEMENT_R;
        el("text", {x: 0, y: 0.09, class: "element-number"}, g).textContent = seat.id;
      });
    }

    const listener = installation.listener;
    if (listener && installation.simulation?.active) {
      const diagonal = Math.hypot(W, D);
      const range = clampRange(Number(listener.range) || Math.min(LISTENER_RANGE_DEFAULT, diagonal), diagonal);
      const grad = el("radialGradient", {id: "listener-field-gradient"}, defs);
      el("stop", {offset: "0", class: "listener-stop-in"}, grad);
      el("stop", {offset: "0.55", class: "listener-stop-mid"}, grad);
      el("stop", {offset: "1", class: "listener-stop-out"}, grad);
      // Range reads as a field, not as a line: gradient disc + outline, clipped to
      // the room (Bob 2026-07-21 — the dashed out-of-room arc is retired, nothing
      // draws outside the room). The clip must hang off an *untranslated* wrapper:
      // clipPathUnits is userSpaceOnUse, so it resolves in the referencing
      // element's coordinate system and a translate() here shifts the room window
      // by the listener position. The translate lives on the inner group instead.
      const at = `translate(${listener.x} ${listener.y})`;
      const wrap = el("g", {class: "listener-range-field",
                            "clip-path": "url(#spatial-room-clip)"});
      svg.insertBefore(wrap, fields);
      const placed = el("g", {class: "listener-range-at", transform: at}, wrap);
      el("circle", {r: range, class: "listener-field"}, placed);
      el("circle", {r: range, class: "listener-ring"}, placed);
      const heading = Number(listener.heading) * Math.PI / 180;
      const hx = Math.sin(heading) * LISTENER_HANDLE, hy = -Math.cos(heading) * LISTENER_HANDLE;
      const g = el("g", {class: "listener-puck", "data-listener": "true", transform: at,
                          tabindex: "0", role: "group",
                          "aria-label": `Listener; heading ${Math.round(Number(listener.heading))} degrees, range ${range} metres`}, svg);
      // Residual magnitude tick (Bob's ruling 5): the knobbly line survives faintly.
      // It lives in the clipped range group, not the puck — it is a range
      // indication and clips with the ring for consistency.
      el("line", {x1: 0, y1: 0, x2: Math.sin(heading) * range, y2: -Math.cos(heading) * range,
                  class: "listener-tick"}, placed);
      el("line", {x1: 0, y1: 0, x2: hx, y2: hy, class: "listener-heading"}, g);
      el("circle", {cx: hx, cy: hy, r: 0.12, class: "listener-tip"}, g);
      el("circle", {cx: hx, cy: hy, r: 0.12, class: "listener-tip-hit"}, g);
      el("circle", {r: LISTENER_COLLAR, class: "listener-collar"}, g);
      el("circle", {r: LISTENER_COLLAR, class: "listener-collar-hit"}, g);
      el("circle", {r: 0.3, class: "listener-body"}, g);
      el("text", {x: 0, y: 0.07, class: "listener-label"}, g).textContent = "L";
      // Gesture-only value readout, replacing the retired toolbar output. Sits
      // just below the collar so it clears the heading handle at any aim.
      el("text", {x: 0, y: LISTENER_COLLAR + 0.34, class: "listener-value"}, g);
      paintRange(svg, listener, diagonal, valueLabelGesture, true);
      if (keepListenerFocus) g.focus({preventScroll: true});
    }

    const handles = el("g", {class: "point-handles", "clip-path": "url(#spatial-room-clip)"}, svg);
    for (const point of Object.values(pointsOf(installation))) {
      const [x, y] = shownXY(point);
      const g = el("g", {class: `spatial-point${Number(point.id) === selectedPoint ? " selected" : ""}`,
                         "data-point-id": point.id, transform: `translate(${x} ${y})`,
                         style: `--point-colour:${pointColour(point.id)}`}, handles);
      el("circle", {r: 0.25, class: "point-handle"}, g);
      el("text", {x: 0, y: 0.08, class: "point-label"}, g).textContent = `P${point.id}`;
    }
    renderPointList(installation);
    bindMap(svg, W, D);
    bindPointEditor(installation, ws, W, D);
  }

  // Clamp kept at the room diagonal (Bob's ruling 2) — matches state.py:733, so
  // this stitch touches no server code.
  const clampRange = (value, diagonal) =>
    round(Math.min(Math.max(Number(value) || LISTENER_RANGE_MIN, LISTENER_RANGE_MIN), diagonal));

  // One placement path for the listener: the puck and the clipped range group
  // carry the same translate, so render, drag and paintRange can never disagree
  // (the range field used to lag a drag until the next re-render).
  function placeListener(svg, listener) {
    const at = `translate(${listener.x} ${listener.y})`;
    svg.querySelector(".listener-puck")?.setAttribute("transform", at);
    svg.querySelector(".listener-range-at")?.setAttribute("transform", at);
  }

  // With the toolbar retired (26-listener-range-fixes/02) the puck's aria-label is
  // the ONLY textual statement of heading and range, so it has to track every
  // gesture rather than only the render. The on-canvas label shows the value being
  // changed, and only while the gesture is live.
  function describeListener(svg, listener, diagonal, gesture, replay = false) {
    const puck = svg.querySelector(".listener-puck");
    if (!puck) return;
    const range = clampRange(listener.range, diagonal);
    const heading = Math.round(Number(listener.heading));
    puck.setAttribute("aria-label",
      `Listener; heading ${heading} degrees, range ${range} metres,`
      + ` position ${round(listener.x)}, ${round(listener.y)} metres`);
    const label = puck.querySelector(".listener-value");
    if (!label) return;
    const atMax = range >= round(diagonal) - 0.005;
    if (gesture === "range") label.textContent = `${range.toFixed(2)} m${atMax ? " (max)" : ""}`;
    else if (gesture === "heading") label.textContent = `${heading}°`;
    else if (gesture === "move") label.textContent = `${round(listener.x)}, ${round(listener.y)} m`;
    // The wheel and the arrow keys have no end event, so the label fades on a
    // deadline. A *replay* (a re-render redrawing a still-live label) must not
    // push that deadline out, or the heartbeat keeps the label up forever.
    if (gesture && !replay) valueLabelGesture = gesture;
    const live = !!gesture && (!replay || Date.now() < valueLabelUntil);
    puck.classList.toggle("gesturing", live);
    if (gesture && !replay) {
      valueLabelUntil = Date.now() + 900;
      clearTimeout(valueLabelTimer);
      valueLabelTimer = setTimeout(() => {
        valueLabelGesture = null;
        svg.querySelector(".listener-puck")?.classList.remove("gesturing");
      }, 900);
    }
  }

  // Live repaint of the range field/outline/tick, shared by the scrub, the wheel
  // and the keys.
  function paintRange(svg, listener, diagonal, gesture = null, replay = false) {
    const range = clampRange(listener.range, diagonal);
    const atMax = range >= round(diagonal) - 0.005;
    placeListener(svg, listener);
    ["listener-field", "listener-ring"].forEach(cls => {
      const node = svg.querySelector(`.${cls}`);
      if (!node) return;
      node.setAttribute("r", range);
      node.classList.toggle("at-max", atMax && cls !== "listener-field");
    });
    const heading = Number(listener.heading) * Math.PI / 180;
    const tick = svg.querySelector(".listener-tick");
    if (tick) {
      tick.setAttribute("x2", Math.sin(heading) * range);
      tick.setAttribute("y2", -Math.cos(heading) * range);
    }
    describeListener(svg, listener, diagonal, gesture, replay);
  }

  function paintHeading(group, listener) {
    const heading = Number(listener.heading) * Math.PI / 180;
    const hx = Math.sin(heading) * LISTENER_HANDLE, hy = -Math.cos(heading) * LISTENER_HANDLE;
    group.querySelector(".listener-heading").setAttribute("x2", hx);
    group.querySelector(".listener-heading").setAttribute("y2", hy);
    group.querySelectorAll(".listener-tip, .listener-tip-hit").forEach(node => {
      node.setAttribute("cx", hx); node.setAttribute("cy", hy);
    });
  }

  function sendListener(ws, listener, final) {
    const now = performance.now();
    if (!final && now - lastListenerSend < 40) return;
    lastListenerSend = now;
    ws.send("set_listener", clone(listener));
  }

  // Range nudge shared by wheel, arrow keys and double-click reset.
  function nudgeRange(svg, delta, W, D) {
    const [installation, , , ws] = last;
    const listener = installation.listener;
    if (!listener || !installation.simulation?.active) return;
    const diagonal = Math.hypot(W, D);
    listener.range = clampRange(Number(listener.range) + delta, diagonal);
    paintRange(svg, listener, diagonal, "range");
    sendListener(ws, listener, true);
  }

  function bindMap(svg, W, D) {
    svg.onkeydown = event => {
      const puck = event.target.closest?.("g[data-listener]");
      if (puck && ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) {
        event.preventDefault();
        const listener = last[0].listener;
        if (event.key === "ArrowUp" || event.key === "ArrowDown") {
          const step = (event.shiftKey ? 1 : 0.1) * (event.key === "ArrowUp" ? 1 : -1);
          nudgeRange(svg, step, W, D);
        } else {
          const step = (event.shiftKey ? 15 : 1) * (event.key === "ArrowRight" ? 1 : -1);
          listener.heading = round(((Number(listener.heading) + step) % 360 + 360) % 360);
          paintHeading(puck, listener);
          paintRange(svg, listener, Math.hypot(W, D), "heading");
          sendListener(last[3], listener, true);
        }
        return;
      }
      if (!["Enter", " "].includes(event.key)) return;
      const node = event.target.closest("g[data-seat-id]");
      if (!node) return;
      event.preventDefault();
      last[2](Number(node.dataset.seatId));
    };
    svg.onwheel = event => {
      if (!event.target.closest?.("g[data-listener]")) return;
      event.preventDefault();
      const step = (event.shiftKey ? 0.05 : 0.25) * (event.deltaY < 0 ? 1 : -1);
      nudgeRange(svg, step, W, D);
    };
    svg.ondblclick = event => {
      if (!event.target.closest?.(".listener-collar-hit, .listener-collar")) return;
      const listener = last[0].listener;
      const diagonal = Math.hypot(W, D);
      listener.range = clampRange(LISTENER_RANGE_DEFAULT, diagonal);
      paintRange(svg, listener, diagonal, "range");
      sendListener(last[3], listener, true);
    };
    svg.onclick = event => {
      if (!event.target.matches("rect.room")) return;
      let [x, y] = toSvg(svg, event);
      x = Math.min(Math.max(round(x), 0), W); y = Math.min(Math.max(round(y), 0), D);
      const used = new Set(Object.values(last[0].seats || {}).map(seat => Number(seat.id)));
      let id = 0; while (used.has(id)) id++;
      last[3].send("add_seat", {id, name:`Seat ${id}`, positions:[[x, y]]});
      last[2](id);  // keep the new map-first Seat selected as state arrives
    };
    svg.onpointerdown = event => {
      const collar = event.target.closest(".listener-collar-hit, .listener-collar");
      if (collar) {
        const group = collar.closest("g[data-listener]");
        const listener = last[0].listener;
        const [x, y] = toSvg(svg, event);
        // Grab axis: the radial direction the collar was pressed on. Travel is
        // read as SIGNED distance along it, so pulling in past the dot keeps
        // shrinking instead of bottoming out at the collar radius.
        const dx = x - listener.x, dy = y - listener.y;
        const length = Math.hypot(dx, dy) || 1;
        const axis = [dx / length, dy / length];
        rangeDrag = {group, axis, from: dx * axis[0] + dy * axis[1],
                     range: clampRange(listener.range, Math.hypot(W, D))};
        group.classList.add("scrubbing");
        svg.setPointerCapture(event.pointerId);
        event.preventDefault();
        return;
      }
      const headingHandle = event.target.closest(".listener-tip, .listener-tip-hit");
      if (headingHandle) {
        headingDrag = {group: headingHandle.closest("g[data-listener]")};
        svg.setPointerCapture(event.pointerId);
        event.preventDefault();
        return;
      }
      const listenerGroup = event.target.closest("g[data-listener]");
      if (listenerGroup) {
        listenerDrag = {group: listenerGroup, start: toSvg(svg, event), moved: false};
        svg.setPointerCapture(event.pointerId);
        event.preventDefault();
        return;
      }
      const pointGroup = event.target.closest("g[data-point-id]");
      if (pointGroup) {
        const id = Number(pointGroup.dataset.pointId);
        selectedPoint = id;
        pointDrag = {id, group: pointGroup, start: toSvg(svg, event), moved: false};
        svg.setPointerCapture(event.pointerId);
        bindPointEditor(last[0], last[3], W, D);
        event.preventDefault();
        return;
      }
      const circle = event.target.closest("circle[data-point]");
      const node = circle && circle.closest("g[data-seat-id]");
      const element = circle && circle.closest("g.element");
      if (!node || !element) return;
      seatDrag = {seatId:Number(node.dataset.seatId), index:Number(circle.dataset.point), moved:false, g:element,
                    start: toSvg(svg, event)};
      svg.setPointerCapture(event.pointerId);
      event.preventDefault();
    };
    svg.onpointermove = event => {
      if (rangeDrag) {
        // Relative scrub at 2.5x: only the CHANGE in pointer distance is read, so
        // the pointer never has to sit `range` metres from a listener at the edge.
        const listener = last[0].listener;
        const [x, y] = toSvg(svg, event);
        const distance = (x - listener.x) * rangeDrag.axis[0] + (y - listener.y) * rangeDrag.axis[1];
        const gain = LISTENER_SCRUB_GAIN * (event.shiftKey ? LISTENER_SCRUB_FINE : 1);
        const diagonal = Math.hypot(W, D);
        rangeDrag.range = clampRange(rangeDrag.range + (distance - rangeDrag.from) * gain, diagonal);
        rangeDrag.from = distance;
        listener.range = rangeDrag.range;
        paintRange(svg, listener, diagonal, "range");
        sendListener(last[3], listener, false);
        return;
      }
      if (headingDrag) {
        // Heading only — range is no longer written here (that was the defect).
        const listener = last[0].listener;
        const [x, y] = toSvg(svg, event);
        const dx = x - listener.x, dy = y - listener.y;
        if (Math.hypot(dx, dy) < MOVE_MIN) return;
        listener.heading = round((Math.atan2(dx, -dy) * 180 / Math.PI + 360) % 360);
        paintHeading(headingDrag.group, listener);
        paintRange(svg, listener, Math.hypot(W, D), "heading");
        sendListener(last[3], listener, false);
        return;
      }
      if (listenerDrag) {
        let [x, y] = toSvg(svg, event);
        x = Math.min(Math.max(x, 0), W); y = Math.min(Math.max(y, 0), D);
        if (!listenerDrag.moved && Math.hypot(x - listenerDrag.start[0], y - listenerDrag.start[1]) < MOVE_MIN) return;
        listenerDrag.moved = true;
        listenerDrag.at = [x, y];
        const listener = last[0].listener;
        listener.x = round(x); listener.y = round(y);
        placeListener(svg, listener);
        describeListener(svg, listener, Math.hypot(W, D), "move");
        const now = performance.now();
        if (now - lastListenerSend >= 40) {
          lastListenerSend = now;
          last[3].send("set_listener", clone(listener));
        }
        return;
      }
      if (pointDrag) {
        let [x, y] = toSvg(svg, event);
        x = Math.min(Math.max(x, 0), W); y = Math.min(Math.max(y, 0), D);
        if (!pointDrag.moved && Math.hypot(x - pointDrag.start[0], y - pointDrag.start[1]) < MOVE_MIN) return;
        pointDrag.moved = true;
        pointDrag.at = [x, y];
        pointDrag.group.setAttribute("transform", `translate(${x} ${y})`);
        movePoint(pointDrag.id, x, y, false);
        updateDisplay(last[0]);
        return;
      }
      if (!seatDrag) return;
      let [x, y] = toSvg(svg, event);
      if (!seatDrag.moved && Math.hypot(x - seatDrag.start[0], y - seatDrag.start[1]) < MOVE_MIN) return;
      seatDrag.moved = true;
      const inTray = y > D + TRAY_GAP / 2;
      x = Math.min(Math.max(x, 0), W);
      if (!inTray) y = Math.min(Math.max(y, 0), D);
      seatDrag.at = [x, y];
      seatDrag.g.setAttribute("transform", `translate(${x} ${y})`);
    };
    svg.onpointerup = () => {
      if (rangeDrag) {
        rangeDrag.group.classList.remove("scrubbing");
        rangeDrag = null;
        sendListener(last[3], last[0].listener, true);
        render(...last);
        return;
      }
      if (headingDrag) {
        last[3].send("set_listener", clone(last[0].listener));
        headingDrag = null;
        render(...last);
        return;
      }
      if (listenerDrag) {
        if (listenerDrag.moved) last[3].send("set_listener", clone(last[0].listener));
        listenerDrag = null;
        render(...last);
        return;
      }
      if (pointDrag) {
        if (pointDrag.moved && pointDrag.at) movePoint(pointDrag.id, ...pointDrag.at, true);
        pointDrag = null;
        render(...last);
        return;
      }
      if (!seatDrag) return;
      const [installation, , select, ws] = last;
      const seat = installation.seats?.[String(seatDrag.seatId)] || installation.seats?.[seatDrag.seatId];
      if (!seatDrag.moved) {
        const now = performance.now();
        if (seat && seatDrag.seatId === lastClick.seatId && now - lastClick.time < 400) toggleSecondElement(seat, ws, W);
        else select(seatDrag.seatId);
        lastClick = {seatId:seatDrag.seatId, time:now};
      } else if (seat && seatDrag.at) {
        const [x, y] = seatDrag.at;
        const positions = clone(seat.positions || []);
        if (y > D + TRAY_GAP / 2) {
          positions.splice(seatDrag.index, 1);
        } else {
          const pos = [round(x), round(y)];
          positions[seatDrag.index] = pos;
        }
        seat.positions = positions;
        ws.send("update_seat", {id:seat.id, positions});
      }
      seatDrag = null;
      render(...last);
    };
  }

  function movePoint(id, x, y, final) {
    const [installation, , , ws] = last;
    const point = authoredPoint(installation, id);
    if (!point) return;
    point.x = round(x); point.y = round(y);
    pointFrame[String(id)] = [x, y];
    if (point.motion?.type === "bounce") point.motion.origin = [point.x, point.y];
    const now = performance.now();
    if (final || now - lastPointSend >= 40) {
      lastPointSend = now;
      ws.send("set_point", {point: clone(point)});
    }
  }

  function bindPointEditor(installation, ws, W, D) {
    const editor = document.getElementById("point-editor");
    if (!editor) return;
    const active = authoredPoint(installation, selectedPoint);
    editor.hidden = selectedPoint === null || !active;
    if (!editor.hidden) {
      document.getElementById("point-title").textContent = `Point ${selectedPoint}`;
      document.getElementById("point-enabled").checked = !!(pointsOf(installation)[selectedPoint] || pointsOf(installation)[String(selectedPoint)]);
      if (!editor.contains(document.activeElement)) {
        document.getElementById("point-radius").value = active.r;
        document.getElementById("point-falloff").value = active.falloff;
        document.getElementById("point-motion").value = active.motion?.type === "bounce" ? "bounce" : "static";
        document.getElementById("point-vx").value = active.motion?.velocity?.[0] ?? 0.7;
        document.getElementById("point-vy").value = active.motion?.velocity?.[1] ?? 0.45;
      }
      document.getElementById("bounce-fields").hidden = document.getElementById("point-motion").value !== "bounce";
    }
    document.getElementById("point-add").onclick = () => {
      const used = new Set(Object.keys(pointsOf(installation)).map(Number));
      let id = 0; while (used.has(id)) id++;
      const point = {id, x: W / 2, y: D / 2, r: 3, falloff: 1};
      pointsOf(installation)[id] = point; selectedPoint = id;
      ws.send("set_point", {point: clone(point)}); render(...last);
    };
    if (editor.hidden) return;
    const sendEdit = () => {
      const point = authoredPoint(installation, selectedPoint); if (!point) return;
      const current = shownXY(point);
      point.x = round(current[0]); point.y = round(current[1]);
      pointFrame[String(point.id)] = [point.x, point.y];
      point.r = Number(document.getElementById("point-radius").value);
      point.falloff = Number(document.getElementById("point-falloff").value);
      if (document.getElementById("point-motion").value === "bounce") {
        point.motion = {type: "bounce", origin: [point.x, point.y],
                        velocity: [Number(document.getElementById("point-vx").value),
                                   Number(document.getElementById("point-vy").value)]};
      } else {
        delete point.motion;
        delete pointFrame[String(point.id)];
      }
      drafts.set(Number(point.id), clone(point));
      if (document.getElementById("point-enabled").checked) ws.send("set_point", {point: clone(point)});
      render(...last);
    };
    ["point-radius", "point-falloff", "point-motion", "point-vx", "point-vy"].forEach(id =>
      document.getElementById(id).onchange = sendEdit);
    document.getElementById("point-enabled").onchange = event => {
      const point = authoredPoint(installation, selectedPoint); if (!point) return;
      drafts.set(Number(point.id), clone(point));
      if (event.target.checked) {
        pointsOf(installation)[point.id] = clone(point);
        ws.send("set_point", {point: clone(point)});
      } else {
        delete pointsOf(installation)[point.id]; delete pointsOf(installation)[String(point.id)];
        ws.send("clear_point", {id: point.id});
      }
      render(...last);
    };
    document.getElementById("point-delete").onclick = () => {
      const id = selectedPoint; drafts.delete(id);
      delete pointsOf(installation)[id]; delete pointsOf(installation)[String(id)];
      pointFrame[String(id)] = undefined; selectedPoint = null;
      ws.send("clear_point", {id}); render(...last);
    };
  }

  function renderPointList(installation) {
    const list = document.getElementById("point-list");
    if (!list) return;
    const points = Object.values(pointsOf(installation)).sort((a, b) => Number(a.id) - Number(b.id));
    list.innerHTML = points.map(point => `<button class="point-list-button${Number(point.id) === selectedPoint ? " selected" : ""}" data-point-select="${Number(point.id)}" style="--point-colour:${pointColour(point.id)}"><i></i>Point ${Number(point.id)}</button>`).join("");
    list.querySelectorAll("[data-point-select]").forEach(button => button.onclick = () => {
      selectedPoint = Number(button.dataset.pointSelect);
      render(...last);
    });
  }

  function updateDisplay(installation) {
    const svg = document.getElementById("spatial"); if (!svg) return;
    for (const point of Object.values(pointsOf(installation))) {
      const xy = shownXY(point);
      const group = svg.querySelector(`[data-point-id="${point.id}"]`);
      if (group && !(pointDrag && pointDrag.id === Number(point.id))) group.setAttribute("transform", `translate(${xy[0]} ${xy[1]})`);
      const ring = svg.querySelector(`[data-radius-id="${point.id}"]`);
      if (ring) { ring.setAttribute("cx", xy[0]); ring.setAttribute("cy", xy[1]); ring.setAttribute("r", point.r); }
    }
  }

  function frame(points) {
    pointFrame = points || {};
    if (last) updateDisplay(last[0]);
  }

  function toggleSecondElement(seat, ws, W) {
    if (!Array.isArray(seat.positions?.[0])) return;
    const positions = clone(seat.positions);
    if (positions.length > 2) return;
    if (positions.length === 2) positions.splice(1, 1);
    else positions.push([Math.min(round(positions[0][0] + 0.8), W), positions[0][1]]);
    ws.send("update_seat", {id:seat.id, positions}); seat.positions = positions;
    render(...last);
  }

  function renderEditor(editor, ws) {
    editorLast = [editor, ws];
    const panel = document.getElementById("editor-preview");
    const svg = document.getElementById("editor-spatial");
    if (!panel || !svg) return;
    panel.hidden = !editor.active;
    if (!editor.active || editorPointDrag) return;
    const authored = editor.points || (editor.points = {});
    if (selectedEditorPoint !== null && !authored[selectedEditorPoint] && !authored[String(selectedEditorPoint)]) {
      selectedEditorPoint = null;
    }
    const W = 5, D = 4, P = 0.55;
    svg.setAttribute("viewBox", `${-W-P} ${-D-P} ${2*(W+P)} ${2*(D+P)}`);
    svg.replaceChildren();
    const defs = el("defs", {}, svg);
    const clip = el("clipPath", {id: "editor-room-clip"}, defs);
    el("rect", {x: -W, y: -D, width: 2*W, height: 2*D}, clip);
    el("rect", {x: -W, y: -D, width: 2*W, height: 2*D, class: "editor-room"}, svg);
    const fields = el("g", {"clip-path": "url(#editor-room-clip)"}, svg);
    for (const point of Object.values(authored)) {
      el("circle", {cx: point.x, cy: point.y, r: point.r,
                    class: "editor-point-radius", "data-editor-radius-id": point.id,
                    style: `--point-colour:${pointColour(point.id)}`}, fields);
    }
    const origin = el("g", {class: "editor-origin", "data-editor-origin": "true"}, svg);
    el("line", {x1: -.48, y1: 0, x2: .48, y2: 0}, origin);
    el("line", {x1: 0, y1: -.48, x2: 0, y2: .48}, origin);
    el("circle", {r: .28}, origin);
    el("text", {x: 0, y: .07}, origin).textContent = "E";
    const handles = el("g", {"clip-path": "url(#editor-room-clip)"}, svg);
    for (const point of Object.values(authored)) {
      const group = el("g", {class: "editor-spatial-point",
        "data-editor-point-id": point.id, transform: `translate(${point.x} ${point.y})`,
        style: `--point-colour:${pointColour(point.id)}`}, handles);
      el("circle", {r: .25, class: "editor-point-handle"}, group);
      el("text", {x: 0, y: .07, class: "editor-point-label"}, group).textContent = `P${point.id}`;
    }
    renderEditorPointList(authored);
    bindEditorPointControls(authored, ws);
    svg.onpointerdown = event => {
      const group = event.target.closest("g[data-editor-point-id]");
      if (!group) return;
      selectedEditorPoint = Number(group.dataset.editorPointId);
      editorPointDrag = {id: selectedEditorPoint, group};
      svg.setPointerCapture(event.pointerId);
      event.preventDefault();
    };
    svg.onpointermove = event => {
      if (!editorPointDrag) return;
      let [x, y] = toSvg(svg, event);
      x = Math.min(Math.max(x, -W), W); y = Math.min(Math.max(y, -D), D);
      editorPointDrag.at = [round(x), round(y)];
      editorPointDrag.group.setAttribute("transform", `translate(${x} ${y})`);
      const ring = svg.querySelector(`[data-editor-radius-id="${editorPointDrag.id}"]`);
      if (ring) { ring.setAttribute("cx", x); ring.setAttribute("cy", y); }
      sendEditorPoint(editorPointDrag.id, x, y, false);
    };
    svg.onpointerup = () => {
      if (!editorPointDrag) return;
      if (editorPointDrag.at) sendEditorPoint(editorPointDrag.id, ...editorPointDrag.at, true);
      editorPointDrag = null;
      renderEditor(...editorLast);
    };
  }

  function editorPoint(authored, id) {
    return authored[id] || authored[String(id)];
  }

  function sendEditorPoint(id, x, y, final) {
    if (!editorLast) return;
    const [editor, ws] = editorLast;
    const point = editorPoint(editor.points || {}, id);
    if (!point) return;
    point.x = round(x); point.y = round(y);
    const now = performance.now();
    if (final || now - lastEditorPointSend >= 40) {
      lastEditorPointSend = now;
      ws.send("set_editor_point", {point: clone(point)});
    }
  }

  function renderEditorPointList(authored) {
    const list = document.getElementById("editor-point-list");
    list.innerHTML = Object.values(authored).sort((a,b)=>Number(a.id)-Number(b.id)).map(point =>
      `<button class="point-list-button${Number(point.id)===selectedEditorPoint?' selected':''}" data-editor-point-select="${Number(point.id)}" style="--point-colour:${pointColour(point.id)}"><i></i>Point ${Number(point.id)}</button>`).join("");
    list.querySelectorAll("[data-editor-point-select]").forEach(button => button.onclick = () => {
      selectedEditorPoint = Number(button.dataset.editorPointSelect);
      renderEditor(...editorLast);
    });
  }

  function bindEditorPointControls(authored, ws) {
    const controls = document.getElementById("editor-point-controls");
    const editor = editorLast?.[0] || {};
    document.querySelectorAll('input[name="editor-point-element"]').forEach(input => {
      input.checked = Number(input.value) === Number(editor.point_element || 0);
      input.onchange = () => {
        if (!input.checked) return;
        editor.point_element = Number(input.value);
        ws.send("set_editor_point_element", {element: editor.point_element});
      };
    });
    const active = editorPoint(authored, selectedEditorPoint);
    controls.hidden = !active;
    document.getElementById("editor-point-add").onclick = () => {
      const used = new Set(Object.keys(authored).map(Number));
      let id = 0; while (used.has(id)) id++;
      const point = {id, x: -2, y: 0, r: 3, falloff: 1};
      authored[id] = point; selectedEditorPoint = id;
      ws.send("set_editor_point", {point: clone(point)});
      renderEditor(...editorLast);
    };
    if (!active) return;
    document.getElementById("editor-point-title").textContent = `Point ${active.id}`;
    if (!controls.contains(document.activeElement)) {
      document.getElementById("editor-point-radius").value = active.r;
      document.getElementById("editor-point-falloff").value = active.falloff;
    }
    const sendEdit = () => {
      active.r = Number(document.getElementById("editor-point-radius").value);
      active.falloff = Number(document.getElementById("editor-point-falloff").value);
      ws.send("set_editor_point", {point: clone(active)});
      renderEditor(...editorLast);
    };
    document.getElementById("editor-point-radius").onchange = sendEdit;
    document.getElementById("editor-point-falloff").onchange = sendEdit;
    document.getElementById("editor-point-delete").onclick = () => {
      const id = Number(active.id);
      delete authored[id]; delete authored[String(id)]; selectedEditorPoint = null;
      ws.send("clear_editor_point", {id}); renderEditor(...editorLast);
    };
  }

  window.Spatial = {render, renderEditor, frame, get dragging() { return seatDrag !== null || pointDrag !== null || listenerDrag !== null || headingDrag !== null || rangeDrag !== null || editorPointDrag !== null; }};
})();
