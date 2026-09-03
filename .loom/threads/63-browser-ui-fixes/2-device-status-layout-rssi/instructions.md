# Reorder Device status actions and show RSSI health

On the Device tab, move the existing Actions section so it is the second card,
immediately after the device status card (the card ending in RSSI, IP and
Converged). Do not change action behavior or confirmation semantics.

Give the RSSI value a restrained visual health indication within the status
card. Use explicit, documented thresholds with three states (good, marginal,
poor); keep wired/unavailable neutral and preserve the numeric dBm reading.
The treatment must work in both themes and communicate through text/semantics,
not color alone.

Add focused browser coverage for section order, health classification, neutral
unavailable state, and the unchanged action bindings. Run the adjacent Device
workspace journey and browser tier before tying.
