// SVG top-down floor plan and spatial point authoring. Coordinates are metres,
// origin top-left, x right, y down. The browser mirrors falloff for display
// only; it never sends per-device gains (nodes own decomposition).
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const TRAY_GAP = 0.3, TRAY_H = 1.2, PAD = 0.6, ELEMENT_R = 0.2, MOVE_MIN = 0.08;
  const ELEMENT_COLOURS = ["#45d483", "#5ea7ff", "#f2b84b", "#db79ff", "#ff7380", "#55d9d2"];
  let deviceDrag = null, pointDrag = null;
  let last = null;
  let selectedPoint = null;
  let lastClick = {uid: null, time: 0};
  let pointFrame = {};
  let lastPointSend = 0;
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

  function falloff(kind, distance, radius) {
    if (!(radius > 0)) return 0;
    const ratio = distance / radius;
    if (Number(kind) === 0) return Math.max(0, 1 - ratio);
    if (Number(kind) === 2) return Math.exp(-(ratio * ratio));
    const x = Math.min(1, Math.max(0, 1 - ratio));
    return x * x * (3 - 2 * x);
  }

  function proximityAt(position, installation) {
    let value = 0;
    for (const point of Object.values(pointsOf(installation))) {
      const [x, y] = shownXY(point);
      value = Math.max(value, falloff(point.falloff, Math.hypot(position[0] - x, position[1] - y), point.r));
    }
    return value;
  }

  function render(installation, selected, select, ws) {
    last = [installation, selected, select, ws];
    if (deviceDrag || pointDrag) return;
    const svg = document.getElementById("spatial");
    if (!svg) return;
    const room = installation.room || {width: 10, depth: 8};
    const W = Number(room.width) || 10, D = Number(room.depth) || 8;
    svg.setAttribute("viewBox", `${-PAD} ${-PAD} ${W + 2 * PAD} ${D + TRAY_GAP + TRAY_H + 2 * PAD}`);
    svg.replaceChildren();
    el("rect", {x: 0, y: 0, width: W, height: D, class: "room"}, svg);
    el("rect", {x: 0, y: D + TRAY_GAP, width: W, height: TRAY_H, class: "tray"}, svg);
    el("text", {x: 0.15, y: D + TRAY_GAP + 0.38, class: "tray-label"}, svg).textContent = "UNPLACED";

    // Radius fields sit behind devices; point handles are drawn last.
    for (const point of Object.values(pointsOf(installation))) {
      const [x, y] = shownXY(point);
      el("circle", {cx: x, cy: y, r: point.r, class: "point-radius",
                    "data-radius-id": point.id}, svg);
    }

    const devices = Object.values(installation.devices || {}).filter(d => Number(d.id) >= 0);
    let slot = 0;
    for (const d of devices) {
      const node = el("g", {class: `node ${status(d)}${d.uid === selected ? " selected" : ""}`,
                            "data-uid": d.uid}, svg);
      const positions = [d.pos1, d.pos2].filter(Array.isArray);
      if (!positions.length) {
        positions.push([0.7 + 1.7 * slot++, D + TRAY_GAP + TRAY_H * 0.62]);
      }
      if (positions.length > 1) {
        el("line", {x1: positions[0][0], y1: positions[0][1],
                    x2: positions[1][0], y2: positions[1][1], class: "pair"}, node);
      }
      positions.forEach((position, index) => {
        const placed = Array.isArray(index === 0 ? d.pos1 : d.pos2);
        const proximity = placed ? proximityAt(position, installation) : 0;
        const scale = 0.82 + proximity * 0.72;
        const g = el("g", {class: "element", "data-element": index,
                           transform: `translate(${position[0]} ${position[1]})`}, node);
        const circle = el("circle", {r: ELEMENT_R * scale, class: `element-dot ${index === 0 ? "p1" : "p2"}`,
                                     fill: ELEMENT_COLOURS[index % ELEMENT_COLOURS.length],
                                     "fill-opacity": 0.35 + proximity * 0.65,
                                     "data-point": index === 0 ? "pos1" : "pos2"}, g);
        circle.dataset.baseRadius = ELEMENT_R;
        el("text", {x: 0, y: 0.09, class: "element-number"}, g).textContent = d.id;
      });
    }

    for (const point of Object.values(pointsOf(installation))) {
      const [x, y] = shownXY(point);
      const g = el("g", {class: `spatial-point${Number(point.id) === selectedPoint ? " selected" : ""}`,
                         "data-point-id": point.id, transform: `translate(${x} ${y})`}, svg);
      el("circle", {r: 0.25, class: "point-handle"}, g);
      el("text", {x: 0, y: 0.08, class: "point-label"}, g).textContent = `P${point.id}`;
    }
    bindMap(svg, W, D);
    bindPointEditor(installation, ws, W, D);
  }

  function bindMap(svg, W, D) {
    svg.onpointerdown = event => {
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
      const node = circle && circle.closest("g[data-uid]");
      const element = circle && circle.closest("g.element");
      if (!node || !element) return;
      deviceDrag = {uid: node.dataset.uid, point: circle.dataset.point, moved: false, g: element,
                    start: toSvg(svg, event)};
      svg.setPointerCapture(event.pointerId);
      event.preventDefault();
    };
    svg.onpointermove = event => {
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
      if (!deviceDrag) return;
      let [x, y] = toSvg(svg, event);
      if (!deviceDrag.moved && Math.hypot(x - deviceDrag.start[0], y - deviceDrag.start[1]) < MOVE_MIN) return;
      deviceDrag.moved = true;
      const inTray = y > D + TRAY_GAP / 2;
      x = Math.min(Math.max(x, 0), W);
      if (!inTray) y = Math.min(Math.max(y, 0), D);
      deviceDrag.at = [x, y];
      deviceDrag.g.setAttribute("transform", `translate(${x} ${y})`);
    };
    svg.onpointerup = () => {
      if (pointDrag) {
        if (pointDrag.moved && pointDrag.at) movePoint(pointDrag.id, ...pointDrag.at, true);
        pointDrag = null;
        render(...last);
        return;
      }
      if (!deviceDrag) return;
      const [installation, , select, ws] = last;
      const device = installation.devices[deviceDrag.uid];
      if (!deviceDrag.moved) {
        const now = performance.now();
        if (device && deviceDrag.uid === lastClick.uid && now - lastClick.time < 400) togglePos2(device, ws, W);
        else select(deviceDrag.uid);
        lastClick = {uid: deviceDrag.uid, time: now};
      } else if (device && deviceDrag.at) {
        const [x, y] = deviceDrag.at;
        if (y > D + TRAY_GAP / 2) {
          ws.send("set_position", {uid: deviceDrag.uid, pos1: null, pos2: null});
          device.pos1 = device.pos2 = null;
        } else {
          const pos = [round(x), round(y)];
          ws.send("set_position", {uid: deviceDrag.uid, [deviceDrag.point]: pos});
          device[deviceDrag.point] = pos;
        }
      }
      deviceDrag = null;
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

  function updateDisplay(installation) {
    const svg = document.getElementById("spatial"); if (!svg) return;
    for (const point of Object.values(pointsOf(installation))) {
      const xy = shownXY(point);
      const group = svg.querySelector(`[data-point-id="${point.id}"]`);
      if (group && !(pointDrag && pointDrag.id === Number(point.id))) group.setAttribute("transform", `translate(${xy[0]} ${xy[1]})`);
      const ring = svg.querySelector(`[data-radius-id="${point.id}"]`);
      if (ring) { ring.setAttribute("cx", xy[0]); ring.setAttribute("cy", xy[1]); ring.setAttribute("r", point.r); }
    }
    svg.querySelectorAll("g.node[data-uid] g.element").forEach(group => {
      const device = installation.devices[group.closest("g.node").dataset.uid];
      const position = Number(group.dataset.element) === 0 ? device?.pos1 : device?.pos2;
      if (!Array.isArray(position)) return;
      const value = proximityAt(position, installation);
      const circle = group.querySelector(".element-dot");
      circle.setAttribute("r", ELEMENT_R * (0.82 + value * 0.72));
      circle.setAttribute("fill-opacity", 0.35 + value * 0.65);
    });
  }

  function frame(points) {
    pointFrame = points || {};
    if (last) updateDisplay(last[0]);
  }

  function togglePos2(device, ws, W) {
    if (!Array.isArray(device.pos1)) return;
    const pos2 = Array.isArray(device.pos2) ? null
      : [Math.min(round(device.pos1[0] + 0.8), W), device.pos1[1]];
    ws.send("set_position", {uid: device.uid, pos2}); device.pos2 = pos2;
    render(...last);
  }

  window.Spatial = {render, frame, get dragging() { return deviceDrag !== null || pointDrag !== null; }};
})();
