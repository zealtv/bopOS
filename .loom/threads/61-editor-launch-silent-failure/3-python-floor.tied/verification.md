# verification — 3-python-floor

## Reproduced first

`/usr/bin/python3` on this machine is **3.9.6**, so Bob's failure reproduces
locally, verbatim:

```
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

from a three-line dataclass with `subprocess.Popen | None`, and from
`import audition` under a 3.9 venv built with `python-osc`.

## Ran

- **Under a real Python 3.9.6 venv** (`/usr/bin/python3 -m venv`, dashboard
  requirements + `pyOSC3` installed):
  - `import audition` — fails before the fix, **imports ok** after.
  - `tools/audition.py --no-engine --devices 2` — runs, still alive at 6s.
  - A real editor supervisor through `Dashboard.launch_supervisor`, with the
    actual `--edit` command line: **alive after 4s, `supervisor_errors` empty**.
    This is the exact path that failed on the test machine.
  - `BOPOS_PYTHON=<py39> ./tools/run-tests.sh fast` — **Ran 324 tests, OK.**
- **On 3.14.6** (this machine's project venv): `./tools/run-tests.sh fast` —
  **Ran 324 tests, OK.** So the future import costs nothing on a modern
  interpreter.
- **`tests/test_python_floor.py`** — 6 tests. Guard validity checked by
  reverting: with `tools/audition.py` stashed it fails 2 of 6, naming the
  offending lines and the missing deferral.
- `bash -n install-dashboard.sh` passes; the new check is a `sys.version_info`
  comparison that prints the version it actually found.

## Not run

- The installer's **failure** branch was not exercised against a <3.9
  interpreter — there isn't one on this machine. The check is a two-line
  `sys.version_info` comparison; the success branch runs on both 3.9.6 and
  3.14.6.
- No browser suite under 3.9. The client is unchanged by this stitch, and the
  server path under 3.9 is covered by the fast suite and the live supervisor
  launch above.
- **Not confirmed on Bob's test machine.** The reproduction here is a
  same-version interpreter, not the same box.
