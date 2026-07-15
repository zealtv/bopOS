// SVG top-down floor plan and spatial point authoring. Coordinates are metres,
// origin top-left, x right, y down. Coloured fields show authored falloff
// geometry; the browser never sends per-device gains (nodes own decomposition).
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const TRAY_GAP = 0.3, TRAY_H = 1.2, PAD = 0.6, ELEMENT_R = 0.2, MOVE_MIN = 0.08;
  const ELEMENT_COLOURS = ["#45d483", "#5ea7ff", "#f2b84b", "#db79ff", "#ff7380", "#55d9d2"];
  const POINT_COLOURS = ["#5ea7ff", "#f2b84b", "#db79ff", "#ff7380", "#55d9d2", "#45d483"];
  let seatDrag = null, pointDrag = null, listenerDrag = null, headingDrag = null;
  let last = null;
  let selectedPoint = null;
  let lastClick = {seatId: null, time: 0};
  let pointFrame = {};
  let lastPointSend = 0;
  let lastListenerSend = 0;
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

  function render(installation, selected, select, ws) {
    last = [installation, selected, select, ws];
    if (seatDrag || pointDrag || listenerDrag || headingDrag) return;
    const svg = document.getElementById("spatial");
    if (!svg) return;
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
    let slot = 0;
    for (const seat of seats) {
      const d = Object.values(devices).find(item=>item.virtual&&Number(item.seat_id)===Number(seat.id)) || devices[seat.bound];
      const occupancy = d?.virtual ? "sim" : d?.online ? "online" : "offline";
      const node = el("g", {class: `node ${occupancy}${Number(seat.id) === Number(selected) ? " selected" : ""}`,
                            "data-uid": d?.uid || "", "data-seat-id": seat.id}, svg);
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
      const heading = Number(listener.heading) * Math.PI / 180;
      const hx = Math.sin(heading) * 0.72, hy = -Math.cos(heading) * 0.72;
      const g = el("g", {class: "listener-puck", "data-listener": "true",
                          transform: `translate(${listener.x} ${listener.y})`}, svg);
      el("line", {x1: 0, y1: 0, x2: hx, y2: hy, class: "listener-heading"}, g);
      el("circle", {cx: hx, cy: hy, r: 0.12, class: "listener-tip"}, g);
      el("circle", {r: 0.3, class: "listener-body"}, g);
      el("text", {x: 0, y: 0.07, class: "listener-label"}, g).textContent = "L";
      const readout = document.getElementById("listener-heading-readout");
      if (readout) readout.value = `${Math.round(Number(listener.heading) || 0)}°`;
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

  function bindMap(svg, W, D) {
    svg.onclick = event => {
      if (!event.target.matches("rect.room")) return;
      let [x, y] = toSvg(svg, event);
      x = Math.min(Math.max(round(x), 0), W); y = Math.min(Math.max(round(y), 0), D);
      const used = new Set(Object.values(last[0].seats || {}).map(seat => Number(seat.id)));
      let id = 0; while (used.has(id)) id++;
      last[3].send("add_seat", {id, name:`Seat ${id}`, positions:[[x, y]]});
    };
    svg.onpointerdown = event => {
      const headingHandle = event.target.closest(".listener-tip");
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
      if (headingDrag) {
        const listener = last[0].listener;
        const [x, y] = toSvg(svg, event);
        const dx = x - listener.x, dy = y - listener.y;
        if (Math.hypot(dx, dy) < MOVE_MIN) return;
        listener.heading = round((Math.atan2(dx, -dy) * 180 / Math.PI + 360) % 360);
        const angle = listener.heading * Math.PI / 180;
        const hx = Math.sin(angle) * 0.72, hy = -Math.cos(angle) * 0.72;
        headingDrag.group.querySelector(".listener-heading").setAttribute("x2", hx);
        headingDrag.group.querySelector(".listener-heading").setAttribute("y2", hy);
        headingDrag.group.querySelector(".listener-tip").setAttribute("cx", hx);
        headingDrag.group.querySelector(".listener-tip").setAttribute("cy", hy);
        const readout = document.getElementById("listener-heading-readout");
        if (readout) readout.value = `${Math.round(listener.heading)}°`;
        const now = performance.now();
        if (now - lastListenerSend >= 40) {
          lastListenerSend = now;
          last[3].send("set_listener", clone(listener));
        }
        return;
      }
      if (listenerDrag) {
        let [x, y] = toSvg(svg, event);
        x = Math.min(Math.max(x, 0), W); y = Math.min(Math.max(y, 0), D);
        if (!listenerDrag.moved && Math.hypot(x - listenerDrag.start[0], y - listenerDrag.start[1]) < MOVE_MIN) return;
        listenerDrag.moved = true;
        listenerDrag.at = [x, y];
        listenerDrag.group.setAttribute("transform", `translate(${x} ${y})`);
        const listener = last[0].listener;
        listener.x = round(x); listener.y = round(y);
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
    if (positions.length > 1) positions.splice(1, 1);
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

  window.Spatial = {render, renderEditor, frame, get dragging() { return seatDrag !== null || pointDrag !== null || listenerDrag !== null || headingDrag !== null || editorPointDrag !== null; }};
})();
