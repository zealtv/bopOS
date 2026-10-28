# 83-identify-from-status-dot

Bob, 2026-10-28: *"i'd like to be able to send an identify message when i
click the status led of a device in the device tab - and also in the remote
page. the remote page should also name the device next to its seat"*

## Do

- **Devices tab:** clicking a roster row's status dot sends `identify` for
  that device (the existing `identify` websocket message, which becomes
  `/all/os/to <uid> identify`), without selecting the row. The roster row is
  itself a `<button>`, so the dot can't be a nested button: it's a pointer
  shortcut, and keyboard users keep the Identify button in the device
  detail's Actions.
- **Remote (`/facilitator`):** the Seat card's status dot becomes a button
  that sends `identify` for the Seat's bound physical device. The dot stays
  7 px; the button gives it a phone-sized hit area. It's gated by a
  ControlColumn capability, so the desktop Control tab's cards are
  unchanged.
- **Remote Seat cards name the device:** "Seat 3 · Bria Fox · online".
- **Feedback:** the dot pulses briefly when an identify is sent. This
  survives heartbeat re-renders by using the same elapsed-time pattern as
  `heartbeatBlip` (0b416d8).
- Virtual devices and Seats with no device get no identify affordance.

## Verify

A Playwright journey with physical-protocol peers on private ports:

- a dot click on the Devices tab sends `/all/os/to <uid> identify` and
  doesn't change the selection;
- on the Remote, a dot click sends it for the Seat's device;
- the card meta names the device;
- an unbound Seat has no button;
- 390 px width works;
- no page errors.
