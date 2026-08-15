#!/bin/bash
# Paired loud/quiet driver for the I2C cable soak.
# usage: paired.sh [cycles]   -- each cycle is 30 s stressor + 30 s silence.
# Aligned to the soak's 30 s buckets. Every transition is timestamped so buckets
# are classified by wall clock rather than by assuming zero drift.
CYCLES="${1:-20}"
HERE="$(cd "$(dirname "$0")" && pwd)"
# The WAV is generated, not committed (5.7 MB); make_stressor.py builds it beside this script.
WAV="${WAV:-$HERE/gated-noise.wav}"
LOG="${LOG:-$HOME/soak-logs/audio-schedule.txt}"
mkdir -p "$(dirname "$LOG")"
: > "$LOG"
for i in $(seq 1 "$CYCLES"); do
  echo "$(date +%s.%N) LOUD $i" >> "$LOG"
  aplay -q -D "${ALSA_DEV:-hw:1,0}" "$WAV"
  echo "$(date +%s.%N) QUIET $i" >> "$LOG"
  sleep 30
done
echo "$(date +%s.%N) END" >> "$LOG"
