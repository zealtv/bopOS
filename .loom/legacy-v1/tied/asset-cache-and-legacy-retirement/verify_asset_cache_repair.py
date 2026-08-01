#!/usr/bin/env python3
"""Focused regression for asset inventory identity and legacy-path retirement."""

import os
import pathlib
import sys
import tempfile

sys.dont_write_bytecode = True


def repo_root():
    here = pathlib.Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "tools" / "simfleet.py").is_file():
            return candidate
    raise RuntimeError("could not locate bopOS repository")


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "python"))

import fetcher  # noqa: E402
import identity  # noqa: E402


passed = 0


def check(label, condition, detail=""):
    global passed
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    passed += 1
    print(f"PASS {label}")


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


with tempfile.TemporaryDirectory(prefix="bopos-asset-cache-repair-") as temp:
    temp = pathlib.Path(temp)
    source_root = temp / "source"
    source_slot = source_root / "bop_samplepack"
    write(source_slot / "readme.md", b"root file sorts after numbered folders\n")
    write(source_slot / "000_birdsong" / "bird.wav", b"bird" * 257)
    write(source_slot / "002_blipkit" / "blip.wav", b"blip" * 131)

    identity._file_hashes.clear()
    canonical = identity.fingerprint(str(source_slot))
    cached = identity.cached_directory_info(str(source_slot))
    check("nonblocking inventory uses canonical global path order",
          cached["fingerprint"] == canonical,
          f"cached={cached['fingerprint']} canonical={canonical}")

    identity.save_hash_cache(str(source_root))
    identity._file_hashes.clear()
    loaded = identity.load_hash_cache(str(source_root))
    restarted = identity.cached_directory_info(str(source_slot))
    check("persistent cache reload preserves canonical slot identity",
          loaded == 3 and restarted["fingerprint"] == canonical,
          f"loaded={loaded} inventory={restarted}")

    destination_root = temp / "destination"
    uri = source_slot.resolve().as_uri() + "/"
    identity._file_hashes.clear()
    ok, detail = fetcher.fetch(uri, "bop_samplepack", str(destination_root))
    fetched_slot = destination_root / "bop_samplepack"
    seeded = identity.cached_directory_info(str(fetched_slot))
    check("fetch-time seeding immediately reports the verified identity",
          ok and seeded["fingerprint"] == canonical,
          f"ok={ok} detail={detail} inventory={seeded}")

    identity._file_hashes.clear()
    loaded = identity.load_hash_cache(str(destination_root))
    after_restart = identity.cached_directory_info(str(fetched_slot))
    check("fetched identity remains current across cache restart",
          loaded == 3 and after_restart["fingerprint"] == canonical,
          f"loaded={loaded} inventory={after_restart}")

    patch_root = temp / "patches"
    destination_patch = patch_root / "legacy-patch"
    (destination_patch / "bop").mkdir(parents=True)
    os.symlink(destination_root / "samplepacks",
               destination_patch / "bop" / "samplepacks")
    ok, detail = fetcher.fetch(source_slot.resolve().as_uri() + "/",
                               "patch:legacy-patch", str(destination_root),
                               str(patch_root))
    check("patch convergence rejects the retired compatibility symlink",
          not ok and "symlink" in detail,
          f"ok={ok} detail={detail}")

start_engine = (ROOT / "bash" / "start-engine.sh").read_text()
fetcher_source = (ROOT / "python" / "fetcher.py").read_text()
contract = (ROOT / "docs" / "OSC-CONTRACT.md").read_text()
check("engine start retires a legacy symlink without recreating its target",
      ('LEGACY_SAMPLEPACKS="$PATCH_PATH/bop/samplepacks"' in start_engine
       and 'rm "$LEGACY_SAMPLEPACKS"' in start_engine
       and 'rmdir "$ASSETS_DIR/samplepacks"' in start_engine
       and "SAMPLEPACKS_SLOT" not in start_engine
       and 'ln -s "$SAMPLEPACKS_SLOT"' not in start_engine))
check("patch convergence no longer preserves the compatibility symlink",
      "legacy_link" not in fetcher_source and "ignore_legacy" not in fetcher_source)
check("obsolete clearsamples helper is removed",
      not (ROOT / "bash" / "clearsamples.sh").exists())
check("contract records direct run-context asset access",
      "compatibility symlink is not created" in contract
      and "symlinked for one release" not in contract)

print(f"\n{passed}/9 checks passed")
