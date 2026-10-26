---
name: "a-scoped-spec-surface-stamp-on-one-governor-of-a-shared-path"
description: "A scoped spec-surface stamp on one governor of a shared path exposes the next governor's unreconciled drift: the overla…"
metadata:
  type: feedback
---

A scoped spec-surface stamp on one governor of a shared path exposes the next governor's unreconciled drift: the overlap tolerance reads a path as reconciled while any co-governor's memlog has moved, so main can carry latent drift that only surfaces after a stamp (found 2026-10-26: doctor 50.1's pixi.toml task-description change, b59245a8c8, was unnamed on four absorbed governors -- spec-pixi-candidate-currency and herald's spec-deck-family-currency, spec-deck-family-lockstep, spec-pyforge-pages -- and the pyforge-core README had a second governor, spec-pyforge-unifying-strategy; each surfaced one run at a time). Before stamping, enumerate every baseline entry whose files map lists the changed path with a hash other than the live sha1 (scripts/.spec-surface-baseline.json, plain sha1 of file bytes, not git blob ids), name the path on every such Spec's memlog in one pass, then stamp each scoped. An absorbed Spec folder still governs what its surface lists (pixi.toml, pixi.lock on spec-pixi-candidate-currency per steward lesson 28).
