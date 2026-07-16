(function(global) {
  "use strict";

  function uidOf(deviceOrUid) {
    return typeof deviceOrUid === "string" ? deviceOrUid : deviceOrUid?.uid || "";
  }

  function uidTail(deviceOrUid) {
    const uid = uidOf(deviceOrUid);
    return uid.length > 8 ? `…${uid.slice(-8)}` : uid;
  }

  function alias(deviceOrUid, installation) {
    const uid = uidOf(deviceOrUid);
    const projected = typeof deviceOrUid === "object" ? deviceOrUid?.alias : null;
    return projected || installation?.device_registry?.[uid]?.alias || null;
  }

  function primary(deviceOrUid, installation) {
    const uid = uidOf(deviceOrUid);
    const device = typeof deviceOrUid === "object" ? deviceOrUid : installation?.devices?.[uid];
    return alias(deviceOrUid, installation) || device?.hostname || uid;
  }

  function technical(deviceOrUid) {
    const device = typeof deviceOrUid === "object" ? deviceOrUid : null;
    const tail = uidTail(deviceOrUid);
    return [device?.hostname, tail].filter((value, index, values) => value && values.indexOf(value) === index).join(" · ");
  }

  function full(deviceOrUid, installation) {
    return [primary(deviceOrUid, installation), technical(deviceOrUid)]
      .filter((value, index, values) => value && values.indexOf(value) === index).join(" · ");
  }

  global.DeviceIdentity = Object.freeze({alias, full, primary, technical, uidTail});
})(window);
