# asset-cache-and-legacy-retirement

Repair the two issues exposed by the first real `bop000` asset send:

- after a manifest-verified transfer, node inventory must converge to the
  canonical host fingerprint immediately and remain correct across restart;
- retire the one-release `assets/samplepacks` compatibility directory and its
  active-patch symlink so engine startup no longer recreates a phantom asset
  slot.

Add focused regression coverage for cold-cache startup, fetch-time seeding,
concurrent warming, restart-derived inventory, and engine startup without the
legacy directory. Update the ratified contract and operator documentation to
remove the retired compatibility path. Do not edit `.pd` files.

Verify locally first, then deploy the repaired runtime files to `bop000`,
restart through the existing operator-controlled path, and confirm the real
device reports `bop_samplepack` current with no `samplepacks` slot.
