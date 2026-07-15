# 02-patch-switch-terminal-state

Replace indefinite `patch_switch` truthiness with bounded switching,
success/reconciliation, timeout/failure and Retry. A lost/unattributable
`/os/rev` must not leave Switching forever when later patch observations prove
success or failure. Verify normal, lost-receipt and one-device retry paths.
