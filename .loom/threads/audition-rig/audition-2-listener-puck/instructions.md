# audition-2-listener-puck

Stage A of `../instructions.md`: spatial monitoring from a listener
perspective. Needs audition-1 (audible instances) tied.

- [ ] `tools/spatial_monitor.py`: small Python jack client holding an N×2 gain
      matrix; per-instance gain = falloff(distance(listener, device)) ×
      forward bias (listener heading · direction-to-device).
- [ ] Listener puck (position + heading) on the dashboard spatial map; state
      reaches the monitor via the dashboard WebSocket or a local OSC port —
      implementer's call, record it.
- [ ] Use the **same falloff math and `installation.json` positions** as
      spatial-audio's engine (spatial-0) — auditioning must predict the real
      rig. If spatial-0 is tied first, import/share its falloff code rather
      than reimplementing.
- [ ] Verify: 3 audible instances at distinct positions, drag the puck across
      the map, hear/measure the pan (jack-level capture of the matrix output
      is acceptable evidence; note what a human check would add).

Stage B (binaural/HRTF) stays in the parent — don't start it; it may collapse
into a SuperCollider engine decision (zero-2).
