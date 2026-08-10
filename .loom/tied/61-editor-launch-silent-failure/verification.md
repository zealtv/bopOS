# verification — 61-editor-launch-silent-failure

**Confirmed by Bob on the test machine, 2026-08-10: "editor opens."**

That is the check none of the three stitches could make for themselves — a real
*Launch editor* opening Pure Data on the machine that had the failure. It closes
the adoption check `1-pd-binary-resolution` left open (this session's machine
carried exactly `Pd-0.55-2.app`, the build the old literal named, so it could
never have reproduced the fault) and confirms `3-python-floor` on the
interpreter that actually raised the `TypeError`.

The thread's stated goal was that *Launch editor* either works or says why.
Both halves are now evidenced:

- **Works** — Bob's confirmation above.
- **Says why** — twice, in this session. `2-supervisor-stderr-visibility`
  turned Bob's second failure into a reported cause
  (`TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`)
  rather than another code-reading session; that report is what produced
  `3-python-floor`. It also surfaced an incidental port collision as
  `stopped unexpectedly: audition: [Errno 48] Address already in use`.

## Left open, deliberately

- **The Python floor.** `install-dashboard.sh` now enforces 3.9, measured
  rather than asserted (full `fast` suite plus a live editor supervisor pass
  under a 3.9.6 venv). Its old text claimed 3.11+ and enforced nothing. If 3.11
  is the intended floor it should be raised deliberately — no reason for that
  number is recorded anywhere. This is a question for Bob, not a defect.
- **Any stopgap `/Applications/Pd-0.55-2.app` symlink** on the test machine
  should be removed if one was made; the resolver no longer needs it.
