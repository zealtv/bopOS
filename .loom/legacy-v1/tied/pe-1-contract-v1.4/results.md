# pe-1 verification

## Result

OSC contract v1.4 now includes the ratified additive `cues` manifest field
alongside the already-landed patch fingerprint amendment. The shared manifest
loader accepts an absent key, preserves valid declarations, and rejects bad
container/entry/field types and duplicate IDs. `demo-pd` declares its existing
`snap` behavior; no `.pd` file was edited.

## Passing verification

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  python/manifest.py \
  .loom/threads/patch-editor/pe-1-contract-v1.4.stitching/verify_pe1_cues.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/patch-editor/pe-1-contract-v1.4.stitching/verify_pe1_cues.py
~/.venvs/bopos/bin/python -m json.tool patches/demo-pd/bopos.patch.json
git diff --check
```

Focused cue-manifest verification: **10/10 passed**. JSON syntax, Python
compile, and diff checks passed.

The browser-free portions of two adjacent tied regressions were run directly:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -c \
  "import runpy; ns=runpy.run_path('.loom/tied/dist-4-demos/verify_dist4_demos.py'); ns['static_checks'](); raise SystemExit(1 if ns['FAILURES'] else 0)"
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -c \
  "import runpy; ns=runpy.run_path('.loom/tied/dashboard-7-remove-param-roles/verify_role_removal.py'); ns['unit_checks'](); raise SystemExit(1 if ns['FAILURES'] else 0)"
```

Demo-manifest compatibility: **10/10 passed**. Existing role-validation
compatibility: **5/5 passed**.

## Non-blocking legacy and environment boundaries

The full tied `patch-manifest/test_patch_manifest.py` was also probed. It
reported seven unrelated failures because that old artifact still expects
pre-v1.3 manifest fallback, older report shapes, and the retired engine-alive
behavior; its applicable manifest checks passed. None exercises `cues`.

Full `dist-4-demos` and `dashboard-7-remove-param-roles` runs reached their
passing browser-free checks, then could not exercise their localhost browser
phases in the workspace sandbox. The pe-1 stitch specifies browser-free
verification, so no network, browser, hardware, audible engine, or touch gate
was requested.
