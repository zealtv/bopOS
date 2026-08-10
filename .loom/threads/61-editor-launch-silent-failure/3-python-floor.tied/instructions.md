# 3-python-floor

Make the supervisor importable on the interpreter the dashboard is actually
running. Raised by Bob on 2026-08-10 from the test machine, after `1` and `2`
shipped: *Launch editor* still failed, and — because `2` had landed — it now
said why:

```
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

## The mechanism

`VirtualNode` (`tools/audition.py:133`) is a `@dataclass`, so its field
annotations are evaluated when the class body runs, not lazily:

```python
process: subprocess.Popen | None = None      # :144
param_generator: paramgen.GeneratorEngine | None = None
audio_error: str | None = None               # :155
```

PEP 604 unions are a **runtime** `TypeError` before Python 3.10. So on 3.9
`tools/audition.py` cannot be imported at all: the supervisor dies at import,
long before `send_ready()`, and both Patch Edit and Simulation are unreachable.

Why a *new* install: `install-dashboard.sh` printed "install Python 3.11+
first" but only checked that `python3` **existed**. On a fresh macOS the
`python3` on PATH is the system 3.9, the venv is built from it, and nothing
ever compares. The advertised floor and the enforced floor were different
numbers.

## The change

1. `from __future__ import annotations` at the top of `tools/audition.py`.
2. A real version check in `install-dashboard.sh`, with the floor **measured**
   rather than asserted.
3. A durable guard for the class, as a source check — CI runs one interpreter
   and this failure only appears on another.

## Verify

Under a real 3.9 interpreter, not by inspection.
