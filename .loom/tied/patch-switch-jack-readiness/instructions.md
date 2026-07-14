# patch-switch-jack-readiness

Make real-device patch switching fail closed when the JACK audio backend does
not stop or restart cleanly. The stop lifecycle must wait for the old JACK
process to release, the start lifecycle must verify JACK readiness instead of
sleeping blindly, and node convergence must require both the selected engine
and JACK before reporting success. A failed replacement must restore and
relaunch the previous patch.

Add focused regression coverage for the observed bop000 failure: the old JACK
server remained alive while the replacement logged `Failed to open server`, PD
started anyway, and the UI converged despite both patch audio and Identify
being silent. Verify locally, then deploy to bop000 and perform an audible
demo-pd/bonks-pd switch gate with Bob present.
