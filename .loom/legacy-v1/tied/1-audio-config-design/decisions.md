# Device audio configuration — ratified design

**Status:** ratified by Bob on 2026-07-23. The Device tab configures only ALSA
cards the physical node currently reports as available. Enabling a board,
changing a boot overlay, or making an unavailable card appear remains a
provisioning/reboot task outside this feature.

## Property set

The first Device-tab surface owns these five node-level settings:

| UI label | `bopos.config` key | Allowed value |
|---|---|---|
| Sound card | `SOUNDCARD` | exact ID of a currently detected ALSA playback card |
| Mixer control | `MIXER_CONTROL` | **Auto** in the UI / JSON `null` on the wire, or one control currently enumerated for the selected card |
| Sample rate | `JACK_SAMPLE_RATE` | 22050, 32000, 44100, 48000, 88200, or 96000 Hz |
| Buffer size | `JACK_PERIOD_SIZE` | 64, 128, 256, 512, 1024, or 2048 frames |
| Periods | `JACK_NPERIODS` | 2 or 3 |

The installed defaults remain `DigiAMP`, `Digital`, 44100 Hz, 512 frames, and
two periods. Auto is stored as an empty `MIXER_CONTROL`; the existing ordered
mixer discovery then selects and remembers a working control.

`AUDIO_CHANNELS` remains a framework/reporting setting rather than a JACK
tuning control in this slice. JACK realtime priority, port maximum, timeout,
soft-mode, playback-only mode, and device-reservation flags remain
implementation-owned. The UI does not expose an arbitrary jackd command line.

The rate and period lists are candidate values, not claimed card capabilities.
ALSA does not provide a cheap, reliable capability query while JACK owns the
device. A candidate combination is proven by the transactional restart below.

## Discovery and reporting

The node reports an `audio` object in its existing `/os/report` JSON:

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

- `configured` is the validated value in node-level `bopos.config`.
- `active` is the last configuration with which JACK reached readiness, or
  JSON `null` if none has done so in this boot.
- `cards` contains ALSA playback cards visible now. IDs come from
  `/proc/asound/cards`; playback presence/labels come from `aplay -l`; simple
  mixer controls come from `amixer -c <id> scontrols`.
- Discovery is bounded and failure-tolerant. A card can be listed with an empty
  mixer-control list. It does not probe formats by taking the device away from
  the running JACK server.
- `status` is `active`, `applying`, `rolled-back`, or `error`. `error` is a
  short operator-facing explanation or null.

The report remains pull/on-change state, not a new periodic stream. Dashboard
state may retain the last report while a device is offline but cannot edit or
apply it.

If the saved card is no longer present, it remains visibly selected as
**Unavailable** rather than silently falling back to HDMI or another card.
Applying is disabled until that exact card is present or the operator selects
another detected card.

## Storage, apply, and recovery

The root `bopos.config` is the single source of desired node audio
configuration. It is already created as `pi:pi`, mode 0644, and sourced by
`bash/start-engine.sh`, so routine edits and engine restarts require no root.

The node applies one complete configuration transaction:

1. Validate every field and require the selected card/control to appear in the
   current discovery result.
2. Take the existing audio-apply lock and retain the previous file values.
3. Atomically replace only the five owned keys in `bopos.config`, preserving
   unrelated keys and comments. Values are shell-quoted safely.
4. Stop the engine/JACK stack and start it with the candidate settings.
5. On JACK readiness, update the node's in-memory config and active snapshot,
   then reapply `NOT (device_enabled AND NOT mute_all)` to the selected mixer.
6. If candidate startup fails, atomically restore the old values and start the
   old configuration. Report `err rolled-back` if recovery succeeds, or
   `err rollback-failed` if it does not.

The framework listener (`bopos.py`) remains alive throughout, so the Dashboard
can observe failure and retry. An engine restart is always required; a reboot
and `bash/provision.sh` are not. The transaction never edits boot overlays and
never accepts an unavailable or free-text card.

At ordinary boot, `start-engine.sh` consumes the same five defaults and records
the active snapshot only after JACK is ready. A failed cold start therefore
reports configured values with `active: null` when the node listener is
available.

The final mute enforcement is mandatory safety behavior. Changing cards while
Device disabled or MUTE ALL is active must not briefly leave the new DAC in an
enabled output state after JACK starts.

## Wire and ownership

Audio configuration is exact physical-device administration on the existing
LAN framework port:

```text
/all/os/to <uid> audio-config <json>
    -> /os/audio-config <uid> <ok|err> <phase> <json>
```

The request JSON is the complete five-field `configured` object; partial
updates are rejected. The terminal receipt phases are `applied`, `invalid`,
`rolled-back`, and `rollback-failed`. Its final JSON is the same `audio` object
used in `/os/report`, allowing the Dashboard to converge even when an
intermediate UI state was missed. The Dashboard also requests a fresh report
after its bounded receipt timeout.

This operation always uses the physical destination, including while
Simulation or Patch Edit owns execution traffic. It does not use localhost
`/admin`: that surface is for an engine on the node to request bounded
lifecycle actions and is not a Dashboard transport.

## Device-tab surface

The selected physical Device gains an **Audio** section between patch
diagnostics and Assets:

- current card and JACK status at the section head;
- detected-card, mixer-control, sample-rate, buffer-size, and periods selects;
- estimated buffering (`period_size * nperiods / sample_rate`) as explanatory
  text, not a promise of end-to-end latency;
- **Save & restart audio engine**, disabled when unchanged, offline, applying,
  invalid, or the card is unavailable;
- a confirmation naming the Device and warning that audio will stop briefly;
- explicit Applying, Applied, Restored previous settings, or Recovery failed
  feedback.

The form distinguishes saved and active values when they differ. It does not
label a saved value active merely because the request was sent.

## Simulator and audition

Simfleet and audition model the same report, request validation, terminal
receipt, applying state, and successful restart transition using a synthetic
stereo card. They do not claim ALSA hardware verification. Focused tests cover
unavailable cards, invalid enums, successful apply, failed apply with rollback,
rollback failure, persistence/comment preservation, physical routing in every
supervisor mode, and output-state reapplication.

Real-card enumeration, JACK acceptance, rollback, audible silence, and touch UI
remain physical Pi/iPad gates for the implementation stitch.
