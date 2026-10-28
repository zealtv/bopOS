# Convert tilt audio banks to seven channels

Requested: back up all eleven 11-channel WAV files in assets/kc-test/tilt to ZIP, then remove tracks 2, 4, 8, and 10 in place (one-based numbering).

Completed 2026-10-28. Kept original tracks 1, 3, 5, 6, 7, 9, and 11, in order. Updated PCM channel count, block alignment, byte rate and applicable extensible speaker mask while retaining other RIFF chunks. Preserved frame counts, sample rates and 16-bit samples.

Backup: assets/kc-test/tilt/originals-11-channel-2026-10-28.zip (138461261 bytes), containing all eleven originals at their relative paths. ZIP integrity tested and every extracted entry compared byte for byte with its original before replacement. Every retained sample byte verified against the corresponding original channel. All eleven staged outputs checked with Python wave for seven channels and unchanged frames, rate and bit depth. riff2/001.wav verified unchanged by SHA-256.
