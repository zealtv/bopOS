#!/bin/bash
# Pi-side capture: process state every 1s + py-spy dumps every 5s, for DURATION.
DURATION="${1:-150}"
LOG=/tmp/bopos-capture.log
PYSPY=/home/pi/venv/bin/py-spy
: > "$LOG"
echo "capture start $(date '+%H:%M:%S') dur=${DURATION}s" >> "$LOG"
BOPOS_PID=$(pgrep -f 'python.*bopos.py' | head -1)
echo "bopos pid=$BOPOS_PID" >> "$LOG"
i=0
end=$((SECONDS+DURATION))
while [ $SECONDS -lt $end ]; do
  ts=$(date '+%H:%M:%S')
  bp=$(pgrep -f 'python.*bopos.py' | head -1)
  jk=$(pgrep -x jackd | head -1)
  pd=$(pgrep -f 'pd -nogui' | head -1)
  la=$(cut -d' ' -f1 /proc/loadavg)
  mf=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
  echo "$ts PROC bopos=$bp jackd=$jk pd=$pd load=$la memavail_kb=$mf" >> "$LOG"
  if [ -z "$bp" ]; then echo "$ts !!! bopos.py GONE" >> "$LOG"; fi
  if [ $((i % 5)) -eq 0 ] && [ -n "$bp" ]; then
    echo "--- $ts py-spy dump pid=$bp ---" >> "$LOG"
    sudo -n "$PYSPY" dump --pid "$bp" >> "$LOG" 2>&1 || "$PYSPY" dump --pid "$bp" >> "$LOG" 2>&1 || echo "(py-spy failed: needs sudo?)" >> "$LOG"
  fi
  i=$((i+1))
  sleep 1
done
echo "capture end $(date '+%H:%M:%S')" >> "$LOG"
