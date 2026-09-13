---
title: 'Extract detector in detectors-ci'
type: 'feature'
created: '2026-09-13'
status: 'done'
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** A 20k truncate of `SPEC.md` keeps Why and drops
Capabilities. Wholesale bodies blow the token budget.

**Approach:** Doctor gather in `detectors-ci` reads CAP heading +
intent/success only (Scribe 13.1 / 14.1 shape). HARD on
unclassified `CAP-N` and `A-only` without expiry.

## Boundaries & Constraints

**Always:**
- Extract contract is `extract.md`.
- Post-PIN unclassified paths are `--append`.

**Never:**
- Never inventory via `_node_from_text_file` on `SPEC.md`.
- Never flip 44.1.

</intent-contract>

## Acceptance Criteria

1. Fixture SPEC: detector sees `CAP-9`, not a unique Why sentence.
2. Unclassified `CAP-N` is HARD.
3. `A-only` without expiry is HARD.
4. Post-PIN file without a row is `--append`.
