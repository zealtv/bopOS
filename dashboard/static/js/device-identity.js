(function(global) {
  "use strict";

  function uidOf(deviceOrUid) {
    return typeof deviceOrUid === "string" ? deviceOrUid : deviceOrUid?.uid || "";
  }

  function alias(deviceOrUid, installation) {
    const uid = uidOf(deviceOrUid);
    const projected = typeof deviceOrUid === "object" ? deviceOrUid?.alias : null;
    return projected || installation?.device_registry?.[uid]?.alias || null;
  }

  function primary(deviceOrUid, installation) {
    const uid = uidOf(deviceOrUid);
    const device = typeof deviceOrUid === "object" ? deviceOrUid : installation?.devices?.[uid];
    if (device?.virtual) return device.hostname || `Virtual ${device.id ?? "device"}`;
    return alias(deviceOrUid, installation) || "Unnamed device";
  }

  // Hostname and UID are intentionally absent here. They are diagnostic
  // identity and belong only in the selected Device detail view.
  global.DeviceIdentity = Object.freeze({alias, primary});
})(window);
