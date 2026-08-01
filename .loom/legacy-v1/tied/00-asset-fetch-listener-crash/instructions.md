# 00-asset-fetch-listener-crash

Repair the node LAN-listener crash observed on Finn Jet when the Dashboard
sends an asset slot.

- Remove the parameter-automation local-name collision with the imported
  `identity` module.
- Add a living node-protocol regression that dispatches a real `/os/fetch`
  datagram for an asset slot.
- Verify locally, then verify the repaired listener and asset transfer on the
  live device without editing Pure Data files.
