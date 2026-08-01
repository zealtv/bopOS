# OSC contract v1.11 draft — physical device audio configuration

Ratified design text for the implementation stitch to land in
`docs/OSC-CONTRACT.md`. Version 1.11 is additive to v1.10.

## Add to the exact-UID administrative surface

```text
/all/os/to <uid> audio-config <json>
    -> /os/audio-config <uid> <ok|err> <phase> <json>
```

`audio-config` is physical administration and always uses the installation LAN
route, independent of the active execution route. It is not the engine-sent
localhost `/admin` surface.

The request JSON is one complete object:

```json
{
  "card": "DigiAMP",
  "mixer_control": "Digital",
  "sample_rate": 44100,
  "period_size": 512,
  "nperiods": 2
}
```

- `card` must be the exact ID of a playback card currently enumerated by the
  target node.
- `mixer_control` is a currently enumerated simple control for that card, or
  JSON `null` for automatic discovery.
- `sample_rate` is one of 22050, 32000, 44100, 48000, 88200, or 96000.
- `period_size` is one of 64, 128, 256, 512, 1024, or 2048 frames.
- `nperiods` is 2 or 3.
- Missing, additional, partial, wrongly typed, unavailable, or out-of-range
  values reject the whole request.

Applying is transactional and restarts JACK plus the patch engine while the
framework listener remains alive. A failed candidate start restores and
restarts the previous configuration. The terminal receipt has phase `applied`,
`invalid`, `rolled-back`, or `rollback-failed`; its JSON argument is the
complete audio-report object described below.

Routine audio configuration is unprivileged. It changes only the node-level
`bopos.config`; it cannot install drivers, edit boot overlays, select hardware
the OS does not currently expose, or invoke provisioning.

## Add to `/os/report`

The report JSON gains `audio`:

```json
{
  "configured": {
    "card": "DigiAMP",
    "mixer_control": "Digital",
    "sample_rate": 44100,
    "period_size": 512,
    "nperiods": 2
  },
  "active": {
    "card": "DigiAMP",
    "mixer_control": "Digital",
    "sample_rate": 44100,
    "period_size": 512,
    "nperiods": 2
  },
  "cards": [
    {
      "id": "DigiAMP",
      "index": 1,
      "label": "IQaudIO DigiAMP",
      "mixer_controls": ["Digital"]
    }
  ],
  "status": "active",
  "error": null
}
```

`configured` is persistent desired state. `active` is the last configuration
with which JACK reached readiness in this boot, or null. `cards` is a
point-in-time list of detected ALSA playback cards, not a capability promise.
`status` is `active`, `applying`, `rolled-back`, or `error`. No audio-config
subscription or periodic stream is introduced.

After either a successful candidate start or a rollback start, the node
reapplies effective output safety (`device_enabled AND NOT mute_all`) to the
active card. Configuration must not bypass Device disabled or MUTE ALL.
