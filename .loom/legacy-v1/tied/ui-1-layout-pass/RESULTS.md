# ui-1 results

The spatial map is now the full-width first row of the technical page. The
device sidebar and technical detail sit beneath it, with synced cues moved into
the detail column. The existing provided master term is available in the
technical header, and the facilitator has a direct link back to `/`.

The Aloha investigation found only obsolete dashboard plumbing. OSC contract
§5 assigns discovery to heartbeat and locate/chirp to `/os/identify`; neither
the current node nor simfleet handles Aloha. Its technical controls,
facilitator Sound check label, allowlist entry, and wire special-case were
removed.

## Verification

- PASS: `node --check dashboard/static/js/dashboard.js`
- PASS: `node --check dashboard/static/js/facilitator.js`
- PASS: `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile dashboard/server.py dashboard/osc_bridge.py dashboard/state.py .loom/threads/dashboard/dashboard-9-ui-review/ui-1-layout-pass.stitching/verify_ui1_layout.py`
- PASS 10/10: `~/.venvs/bopos/bin/python .loom/threads/dashboard/dashboard-9-ui-review/ui-1-layout-pass.stitching/verify_ui1_layout.py`
- PASS: visual inspection of `ui1-layout.png` at 1400×1000; map hierarchy, header controls, and lower two-column layout are coherent.
- SETUP FAILURE, repeated twice: `.loom/tied/seam-2-master-term/verify_master_term.py` stops before assertions because its state contains no device with ID 1. The focused verifier proves server persistence and real simfleet `/os/master 0.42` delivery.
- SETUP FAILURE after 2 preliminary passes: `.loom/tied/seam-4-facilitator-promotion/verify_facilitator_promotion.py` times out waiting for its seeded `backing` declaration. It does not reach a changed UI assertion.

Not verified on iPad/touch or installation hardware. The deliberately deferred
facilitator locking mechanism remains unimplemented.
