# Device-enabled state follows successful mixer application

Apply the requested effective output (`requested device_enabled AND NOT
mute_all`) before changing the live flag or persistent device_enabled key.
If enforce_mute fails, leave both at their previous values and send no success
receipt. A failed disable therefore cannot turn an enabled live report or
persisted setting into disabled. The absent-key default stays absent/enabled;
a failed enable similarly retains the previous disabled state.

After successful mixer application, update the live flag and persist it before
acknowledging success, preserving the existing contract. If persistence fails,
the live flag reflects the successful mixer operation, the store retains its
last durable value and no success receipt is sent. Reverting only the live flag
would misreport the mixer operation; no engine-stop or other fallback is added.

This changes the application/persistence order, not wire grammar or fields.
The existing /os/report booleans, output formula and /os/enabled success receipt
stay intact. No operator-visible wording is added. A card-specific explanation
would need Bob's ruling; the real Ciro Toast failure/silence check is pending,
so no new capability message is proposed speculatively.

Scope is set_device_enabled. This is not a claim of mixer readback, acoustic
silence, or re-enforcement after boot/card changes; those require hardware
observations. The existing successful-amixer result is the application signal.
