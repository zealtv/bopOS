# dist-1 results

The OSC contract is now v1.3 and records the ratified patch/asset mirror,
mandatory patch manifests, hostname reporting, new patch/drop verbs, the
`updatebopos` rename, and the hard removal of gdrive/getsamples/undeclared
launch. `patches/README.md` now describes the host layout and the ordinary
host-mirrored and advanced Git workflows.

The legacy `patches/<active>/bop/samplepacks` symlink remains a one-release
fleet guarantee. Bob's hard-break ruling explicitly named gdrive, getsamples,
manifest fallback, and the update spelling; it did not retire this path.

The top-level README's immediately contradictory claims (Git-only patches,
manifest fallback, contract version) were corrected. Demo paths and repository
layout remain for `dist-4-demos`, which performs the actual directory moves.

## Verification

Passed on 2026-07-14:

```sh
git diff --check
rg -n 'Version 1\.3|hostname|updatebopos|/os/patches|/os/droppatch|/os/dropassets|patch:<name>|Kite Choir|The Plants|kite-choir-brains' docs/OSC-CONTRACT.md patches/README.md
rg -nP '/os/update(?!bopos)' docs/OSC-CONTRACT.md patches/README.md
rg -n 'gdrive:|getsamples|SAMPLEPACKSURL|samplepacks symlink|legacy three sliders|without a manifest|No flag day|templates/supercollider-bopos|patches/default|always `main\.pd`|Each patch is a git' docs/OSC-CONTRACT.md patches/README.md
```

The negative searches returned only intentional migration, retirement, and
rejected-by-design references. This is a documentation-only stitch; no runtime
or hardware verification applies.
