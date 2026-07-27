# 03-fetch-convergence-tests

Promote the durable patch/asset fetch-convergence behavior into living tests.

- Audit `tests/test_node_fetch_dispatch.py` and related current coverage first.
- Mine only enduring behavior from the patch/fleet tied guards: progress,
  per-device serialization, byte convergence before switch, and continued
  responsiveness.
- Avoid stale pins such as exact refresh lists, old contract versions, retired
  samplepack paths, incidental copy, or fake-object implementation details.
- State the simulation boundary explicitly: fresh-Pi cold-cache and real
  transfer timeout behavior remain hardware/integration concerns.

Exercise production helpers and simfleet where practical, then record the exact
focused commands and results.
