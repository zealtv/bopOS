# The Spotpear "Audio Module (B)" PWM board

When a node has the two-speaker AliExpress audio board marked "Audio Module (B)" (19/18 and OUT/IN jumpers, no HAT EEPROM), it is a PWM board on GPIO18/19, not an I²S DAC — set it up with `audremap` and full volume.

First set up on femi-bolt (Pi Zero 2 W, kernel 6.18.50, on a Suptronix 18650 UPS shield) with Bob, 2026-11-05.

## Setup

1. Add `dtoverlay=audremap,pins_18_19` under `[all]` in `/boot/firmware/config.txt`; keep `dtparam=audio=on`. Reboot.
2. `aplay -l` should then list `card 0: Headphones [bcm2835 Headphones]` ahead of HDMI.
3. Set volume to max: `amixer -c Headphones sset PCM 100%`, then `sudo alsactl store`.
4. Test: `speaker-test -D plughw:Headphones -c2 -t wav -l 1`.

The volume step matters. The mixer scale is logarithmic (−102.39 dB … +4 dB): 70% reads as −27.9 dB, and on femi-bolt it sounded faint enough to look like a fault. Spotpear's own steps also say "set audio voice max".

## Jumpers

- **19 / 18:** both fitted, or GPIO never reaches the board.
- **OUT / IN block:** IN drives the onboard speakers; OUT drives the white OUT connector (external speakers, louder). Bob's board shipped with 3 of 4 on IN and the slot nearest the GPIO header unpopulated; bridging that slot changed nothing.
- The 3.5 mm jack also worked on femi-bolt.
- One Spotpear forum user reports GPIO18 → right, GPIO19 → left (board text upright). Not yet checked here.

## Noise and loudness

A faint hiss that follows keystrokes over SSH stays audible up close. As of 2026-11-05 Bob judged it acceptable. What was ruled out on femi-bolt:

- `audio_pwm_mode=514` (mode 2, noise-shaped) is already the firmware default.
- The `performance` CPU governor made no audible difference (reverted to `ondemand`).
- No undervoltage (`throttled=0x0`).
- **Don't touch Wi-Fi power save.** bopOS turns it off on purpose (`bash/install-wifi-powersave.sh`); Bob said it's important.

Main remaining suspect, not yet tested: the 18650 shield's boost converter puts ripple on the shared 5 V rail. To check, power the Pi from a good USB supply with the shield removed. If that's quieter, filter the board's 5 V (ferrite + ~470–1000 µF). If not, only an I²S DAC or USB audio removes it.

Software volume is at its ceiling (+4 dB already risks clipping). More loudness has to come from hotter content in the patch, more sensitive speakers or enclosures, or 4 Ω speakers if the amp chip allows it (chip not identified yet).

## Context

- Vendor wiki: https://spotpear.com/index.php/wiki/Raspberry-Pi-GPIO-Audio-amplification-PWM-Sound-Card-Speaker-Buzzer.html
- Pin Q&A: https://spotpear.com/index.php/index/forum/detail/id/118.html
- femi-bolt keeps the pre-change config at `/boot/firmware/config.txt.bak-audio`.

## Triggers

- Audio Module (B)
- Spotpear
- audremap
- femi-bolt
- bcm2835 Headphones
- PWM audio

## Associations

- [[test-rig]]
- [[hardware-claims]]
