# 07-suite-runner-and-pre-tie-wiring

Make the living suite easy and routine to run.

- Implement the stable entry point selected in `01`, with a fast
  browser-free tier and an explicit slower browser/integration tier.
- Run from the repository root and use the bopOS venv documented in
  `CLAUDE.md`; do not depend on files inside `.loom/tied/`.
- Wire the fast tier into the repository's actual CI if one exists by then;
  otherwise establish and document the pre-tie command without inventing an
  external service.
- Keep hardware-only checks explicit and out of software pass claims.
- Update `docs/VERIFICATION.md` so new stitches know where durable tests go and
  how to run them.

The result must start green and produce actionable per-surface failures.
