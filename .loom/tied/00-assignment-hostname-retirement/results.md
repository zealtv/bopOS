# Result

Seat assignment and engine `/config` no longer mutate or seed the device OS
hostname. The removed legacy path interpolated the human-facing Seat name into
three interactive `sudo` shell commands; on Finn Jet, `Seat 0` was both an
invalid hostname and unavailable to unattended systemd startup.

The exact-UID `/os/hostname` action and its validating privileged helper remain
the sole hostname mutation boundary.

## Verification

- `tests/test_node_fetch_dispatch.py`: 2 passed, including assignment of
  `Seat 0` without any shell or subprocess hostname action.
- `tests/test_asset_slot_context.py`: 8 passed.
- `verify_alias_hostname.py`: 10 passed, 0 failures, including the node helper
  and Dashboard exact-UID action.
- `py_compile` passed for `python/bopos.py` and the living test.
- `git diff --check` passed.

## Finn Jet

Finn Jet updated to `d72ac05` and rebooted. The post-boot gate showed:

```text
hostname: finn-jet
bopos.service: active
ASSIGNED: id 0 name Seat 0 pos [...]
```

The boot journal contained no `Hostname change`, interactive-sudo password, or
`pam_unix(sudo)` messages. The checkout was clean before reboot.

No Pure Data file was edited or staged by this stitch.
