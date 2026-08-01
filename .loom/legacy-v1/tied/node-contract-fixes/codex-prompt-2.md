Implement the three code deltas specified in
`.loom/threads/osc-schema-contract/node-contract-fixes.stitching/design-decisions.md`
in this repo (bopOS). Read that file first — it contains every design decision;
follow it exactly. Context if needed: `docs/OSC-CONTRACT.md` §1, §2, §7, §11, and the
stitch brief in `.loom/threads/osc-schema-contract/node-contract-fixes.stitching/instructions.md`.

Files to change: `python/io/sys_i2c.py`, `python/io/main.py`, `bash/start.sh`,
`bash/stop.sh`, `bash/start-laptop.sh`, `bash/stop-laptop.sh`, `python/helper.py`,
`tools/simfleet.py`, `.gitignore` (add `run/`).
Files to create: `bash/start-engine.sh`, `bash/stop-engine.sh` (both executable).

Hard constraints:
- NEVER touch any `.pd` file.
- Minimal deltas: match each file's existing style (helper.py is old-school pyOSC3
  procedural code — keep it that way; do not refactor, do not add type hints or
  dataclasses, do not reformat untouched lines).
- Bash stays plain bash, no new dependencies. Python stays stdlib + already-imported
  libs (pyOSC3 in helper.py/io, python-osc in simfleet).
- start.sh must preserve its current observable boot behaviour (waits, echo output,
  jack args, the PD `-send` line) apart from the specified changes.
- simfleet.py: add `restart-engine` to the helper verbs — schedule the
  `helper-reply restart-engine` report ~0.5 s after receipt, device stays running
  (engine state is not visible in today's wire protocol). Keep message bytes inside
  LegacyProtocol; follow the file's existing patterns.
- In pyOSC3, callbacks are registered with `server.addMsgHandler("/restart-engine", ...)`
  and replies are sent as in the existing callbacks (OSCMessage to the 6661 client).
- helper.py must locate the bash scripts relative to its own file like the existing
  callbacks do (`os.path.dirname(os.path.realpath(__file__))`).

Verification you can do here (no I2C hardware, no pyOSC3 installed — do NOT pip install):
- `bash -n` every touched/created shell script.
- `python3 -m py_compile` on every touched Python file.
- For sys_i2c: `python3 -c` import test in a clean env (no smbus2 present) — `scan_bus()`
  must return `[]` and `have_bus()` must return False without raising.
- For simfleet: `PYTHONPATH=/tmp/claude-1000/-home-bob-repos-bopOS/2065335f-c834-48b5-b0b3-09be072e327c/scratchpad/pylib`
  makes python-osc importable; you may smoke-test if sockets work in your sandbox, but
  if socket creation is blocked, say so and leave live testing to the caller.
- helper.py and io/main.py cannot be imported without pyOSC3 — do not stub it into the
  repo; compile-check only and leave runtime testing to the caller.

When done, summarize what you changed, how you verified it, and anything you could not
do. If you could not complete the task, say so explicitly.
