---
spec: machine-checked-recipe-knowledge
status: ready
owner-dream: docs/dreams/machine-checked-recipe-knowledge.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/machine-checked-recipe-knowledge.md
  - ../../../../../../docs/intake/external-repos-analysis-2026-08-22/report.md
open_questions:
  - "Catalog file home: .claude/skills/conda-forge-expert/config/ vs data/ — decide at 7.1 (it is derived+tracked, so config-side)."
---

# SPEC — Machine-checked recipe knowledge

## Why
The CFE G-corpus (110+ gotchas) is prose with no machine linkage to the
checks that enforce it — knowledge and enforcement drift silently. Proven
pattern: auto-recipe's spec-generated 45-row catalog with lint-resolved
`enforced_by` pointers (2026-08-22 analysis; unlicensed, pattern only).

## Capabilities
- **CAP-1 — the generated catalog.** `failure-catalog.yaml` derives from
  SKILL.md's gotchas: per row, greppable `symptom_signature` tokens + an
  `enforced_by:` pointer into the real CFE check/test surface, or an
  explicit `null`. *Success:* regeneration is deterministic; hand-editing
  the catalog is detectably wrong (derived-artifact discipline).
- **CAP-2 — the lint + drift gate.** Every non-null pointer resolves against
  the live check surface; catalog↔SKILL.md drift fails CI; the null-rows
  report is the prioritized machine-check backlog. *Success:* planting a
  bogus pointer or editing a gotcha without regenerating reds the suite.

## Constraints
Prose stays authoritative (the catalog derives); Rules 1/2 govern (CFE
surface — the landing carries its retro obligations); doctor's detector
conventions for the drift gate; no verbatim auto-recipe text/YAML.

## Non-goals
Rewriting gotchas; auto-generating new checks (the null backlog is a report,
not an actuator).

## Success signal
`enforced_by` coverage is a number the fleet can watch, drift is impossible
to land silently, and the next new gotcha arrives with its row + pointer or
an honest null.
