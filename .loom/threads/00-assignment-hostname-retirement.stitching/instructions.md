# 00-assignment-hostname-retirement

Retire the legacy coupling between Seat assignment and the device's OS
hostname. A Seat display name such as `Seat 0` is not an OS hostname and must
never trigger interactive `sudo` during unattended startup.

- Assignment persists Seat identity only.
- `/config` reports the resolved ID without consulting the legacy
  `bopos.devices` hostname seed.
- The exact-UID, alias-derived `/os/hostname` action remains the sole hostname
  mutation boundary.
- Add a living node regression and verify on Finn Jet.
