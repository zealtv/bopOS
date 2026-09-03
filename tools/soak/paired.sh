#!/bin/bash
# Paired loud/quiet driver for the I2C cable soak.
# usage: paired.sh [cycles]   -- each cycle is 30 s stressor + 30 s silence.
# Aligned to the soak's 30 s buckets. Every transition is timestamped so buckets
# are classified by wall clock rather than by assuming zero drift.
#
# ⚠️ THIS SCRIPT MUST FAIL LOUDLY. A soak whose interferer never played is
# indistinguishable, in i2c_soak.py's output, from one that ran at full level --
# both report zero errors and PASS. On 2026-09-03 a reboot renumbered the ALSA
# cards (DigiAMP+ card 1 -> card 0) and every aplay failed with "audio open
# error: Unknown error 524" while the soak reported a clean audio run. It was
# caught only because a human was listening. Hence: name-based device lookup, a
# preflight that refuses to start, and an exit-status check on every play.
set -uo pipefail
CYCLES="${1:-20}"
HERE="$(cd "$(dirname "$0")" && pwd)"
# The WAV is generated, not committed (5.7 MB); make_stressor.py builds it beside this script.
WAV="${WAV:-$HERE/gated-noise.wav}"
LOG="${LOG:-$HOME/soak-logs/audio-schedule.txt}"

# Resolve the output device BY NAME, not by card number -- card numbering is not
# stable across reboots.
if [ -z "${ALSA_DEV:-}" ]; then
  card=$(aplay -l 2>/dev/null | sed -n 's/^card [0-9]*: \([A-Za-z0-9_]*\) .*/\1/p' \
         | grep -i -m1 digiamp)
  ALSA_DEV="hw:${card:-DigiAMP},0"
fi

[ -r "$WAV" ] || { echo "paired.sh: stressor not found: $WAV" >&2
                   echo "  build it: python3 $HERE/make_stressor.py gated-noise 30 $WAV -6" >&2
                   exit 1; }

# Preflight: prove the device opens before committing to a 20-minute run. This
# also gives the operator an audible cue that the interferer is really running.
echo "paired.sh: device $ALSA_DEV -- preflight (you should HEAR one second of noise)" >&2
if ! aplay -q -d 1 -D "$ALSA_DEV" "$WAV" 2>/tmp/paired-preflight.err; then
  echo "paired.sh: ABORT -- cannot open $ALSA_DEV:" >&2
  sed 's/^/  /' /tmp/paired-preflight.err >&2
  echo "  available devices:" >&2
  aplay -l 2>&1 | sed -n 's/^\(card .*\)/  \1/p' >&2
  exit 1
fi

mkdir -p "$(dirname "$LOG")"
: > "$LOG"
for i in $(seq 1 "$CYCLES"); do
  echo "$(date +%s.%N) LOUD $i" >> "$LOG"
  if ! aplay -q -D "$ALSA_DEV" "$WAV"; then
    echo "$(date +%s.%N) ABORT aplay-failed $i" >> "$LOG"
    echo "paired.sh: ABORT -- aplay failed on cycle $i; the run is NOT an audio run." >&2
    exit 1
  fi
  echo "$(date +%s.%N) QUIET $i" >> "$LOG"
  sleep 30
done
echo "$(date +%s.%N) END" >> "$LOG"
