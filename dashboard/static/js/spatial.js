// SVG top-down floor plan: metres, origin top-left, x right, y down (the
// coordinate system spatial-audio consumes — keep it explicit).
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const TRAY_GAP = 0.3, TRAY_H = 1.2, PAD = 0.6, R1 = 0.24, R2 = 0.16, MOVE_MIN = 0.08;
  let drag = null;   // {uid, point, moved} — never rebuild the map mid-drag
  let last = null;   // args of the latest render, for post-drag refresh
  let lastClick = {uid: null, time: 0};   // manual dblclick: select() rebuilds
                                          // the SVG between the two clicks, so
                                          // the native event never fires

  function el(name, attrs, parent) {
    const node = document.createElementNS(NS, name);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (parent) parent.appendChild(node);
    return node;
  }
  const status = d => d.online ? (Number(d.engine_alive) === 0 ? "crashed" : "online") : "offline";
  const toSvg = (svg, event) => {
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.getScreenCTM().inverse());
    return [point.x, point.y];
  };

  function render(installation, selected, select, ws) {
    last = [installation, selected, select, ws];
    if (drag) return;
    const svg = document.getElementById("spatial");
    if (!svg) return;
    const room = installation.room || {width: 10, depth: 8};
    const W = Number(room.width) || 10, D = Number(room.depth) || 8;
    svg.setAttribute("viewBox", `${-PAD} ${-PAD} ${W + 2 * PAD} ${D + TRAY_GAP + TRAY_H + 2 * PAD}`);
    svg.replaceChildren();
    el("rect", {x: 0, y: 0, width: W, height: D, class: "room"}, svg);
    el("rect", {x: 0, y: D + TRAY_GAP, width: W, height: TRAY_H, class: "tray"}, svg);
    el("text", {x: 0.15, y: D + TRAY_GAP + 0.38, class: "tray-label"}, svg).textContent = "UNPLACED";

    const devices = Object.values(installation.devices || {}).filter(d => Number(d.id) >= 0);
    let slot = 0;
    for (const d of devices) {
      const placed = Array.isArray(d.pos1);
      const [x, y] = placed ? d.pos1 : [0.7 + 1.7 * slot++, D + TRAY_GAP + TRAY_H * 0.62];
      const g = el("g", {class: `node ${status(d)}${d.uid === selected ? " selected" : ""}`,
                         "data-uid": d.uid}, svg);
      if (placed && Array.isArray(d.pos2)) {
        el("line", {x1: x, y1: y, x2: d.pos2[0], y2: d.pos2[1], class: "pair"}, g);
        el("circle", {cx: d.pos2[0], cy: d.pos2[1], r: R2, class: "p2", "data-point": "pos2"}, g);
      }
      el("circle", {cx: x, cy: y, r: R1, class: "p1", "data-point": "pos1"}, g);
      el("text", {x, y: y + R1 + 0.34, class: "label"}, g).textContent = d.name || `ID ${d.id}`;
    }
    bind(svg, W, D);
  }

  function bind(svg, W, D) {
    svg.onpointerdown = event => {
      const circle = event.target.closest("circle[data-point]");
      const g = circle && circle.closest("g[data-uid]");
      if (!g) return;
      drag = {uid: g.dataset.uid, point: circle.dataset.point, moved: false, g, circle,
              start: toSvg(svg, event)};
      svg.setPointerCapture(event.pointerId);
      event.preventDefault();
    };
    svg.onpointermove = event => {
      if (!drag) return;
      let [x, y] = toSvg(svg, event);
      if (!drag.moved && Math.hypot(x - drag.start[0], y - drag.start[1]) < MOVE_MIN) return;
      drag.moved = true;
      const inTray = y > D + TRAY_GAP / 2;
      x = Math.min(Math.max(x, 0), W);
      if (!inTray) y = Math.min(Math.max(y, 0), D);
      drag.at = [x, y];
      drag.circle.setAttribute("cx", x); drag.circle.setAttribute("cy", y);
      if (drag.point === "pos1") {
        const label = drag.g.querySelector("text");
        label.setAttribute("x", x); label.setAttribute("y", y + R1 + 0.34);
      }
      const line = drag.g.querySelector("line.pair");
      if (line) {
        line.setAttribute(drag.point === "pos1" ? "x1" : "x2", x);
        line.setAttribute(drag.point === "pos1" ? "y1" : "y2", y);
      }
    };
    svg.onpointerup = () => {
      if (!drag) return;
      const [installation, , select, ws] = last;
      const device = installation.devices[drag.uid];
      if (!drag.moved) {
        const now = performance.now();
        if (device && drag.uid === lastClick.uid && now - lastClick.time < 400) {
          togglePos2(device, ws, W);
        } else {
          select(drag.uid);
        }
        lastClick = {uid: drag.uid, time: now};
      } else if (device && drag.at) {
        const [x, y] = drag.at;
        if (y > D + TRAY_GAP / 2) {
          // dropped back in the tray: unplace the device
          ws.send("set_position", {uid: drag.uid, pos1: null, pos2: null});
          device.pos1 = device.pos2 = null;
        } else {
          const pos = [Math.round(x * 100) / 100, Math.round(y * 100) / 100];
          ws.send("set_position", {uid: drag.uid, [drag.point]: pos});
          device[drag.point] = pos;
        }
      }
      drag = null;
      render(...last);
    };
  }

  function togglePos2(device, ws, W) {
    // double-click toggles the second speaker point on a placed device
    if (!Array.isArray(device.pos1)) return;
    const pos2 = Array.isArray(device.pos2)
      ? null
      : [Math.min(Math.round((device.pos1[0] + 0.8) * 100) / 100, W), device.pos1[1]];
    ws.send("set_position", {uid: device.uid, pos2});
    device.pos2 = pos2;
    render(...last);
  }

  window.Spatial = {render, get dragging() { return drag !== null; }};
})();
