# Stage 0 relay decisions

1. One audition process represents N virtual nodes. Running N full helpers
   would duplicate machine administration and persistence, and fixed engine
   port 6661 would still collide.
2. The relay generalizes helper's SC boundary: match the fleet selector once,
   strip it, and deliver an engine-local message to a per-node port.
3. Stage 0 is a composition sound-check, not a second implementation of all
   helper behavior. Selected patch/admin values needed by the engine are
   relayed. Clock synchronization, cue scheduling, and point decomposition
   remain out of scope until a later stitch explicitly models them.
4. Virtual identity is deterministic and independent of host IP. Heartbeats
   use distinct synthetic uids and integer ids so dashboard rows do not
   collapse on the single Mac address.
5. macOS uses PD's PortAudio/CoreAudio backend first. JACK is a Linux backend
   and a future Mac option only if concurrent CoreAudio clients fail.
6. Process cleanup is ownership-based. The launcher records child process
   groups/PIDs and never uses blanket `pkill` as its normal cleanup path.
